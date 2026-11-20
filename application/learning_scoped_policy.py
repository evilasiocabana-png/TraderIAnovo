"""One frozen learned hypothesis per account/source/setup, never pooled evidence."""
from datetime import datetime, timedelta
import json
from application.learning_store import LearningStore, now, encoded
from application.learning_scopes import scope_tables, active_key


def scoped_cycle(store=None, timestamp=None):
    from application import learning_policy as p
    store, timestamp = store or LearningStore(), timestamp or now()
    current = datetime.fromisoformat(timestamp)
    with store.connect() as db:
        p.tables(db)
        scope_tables(db)
        last = db.execute("SELECT value FROM metadata WHERE key='learning_next_review'").fetchone()
        if last and timestamp < last[0]:
            return
        # Old global candidates remain auditable but cannot govern any new scope.
        db.execute("UPDATE learning_candidates SET state='LEGACY_UNSCOPED' WHERE state IN ('TESTING','APPLIED') AND id NOT IN (SELECT candidate FROM learning_candidate_scopes)")
        db.execute("DELETE FROM metadata WHERE key='m30_active_filter'")
        baseline = db.execute('SELECT id FROM baselines ORDER BY captured_at DESC LIMIT 1').fetchone()
        baseline = baseline[0] if baseline else ''
        groups = {}
        for sample in p.read_samples(db, baseline) if baseline else []:
            if sample.get('scope'):
                groups.setdefault(sample['scope'], []).append(sample)
        for row in db.execute('SELECT DISTINCT scope FROM learning_candidate_scopes'):
            groups.setdefault(row[0], [])
        if not groups:
            p.journal(db, 'INCONCLUSIVO', 'BASELINE', 'Sem amostras elegiveis com origem/setup/conta confirmados; aprendizado separado aguardando dados.', {}, timestamp)
        for scope, samples in groups.items():
            active = db.execute("SELECT c.* FROM learning_candidates c JOIN learning_candidate_scopes s ON s.candidate=c.id WHERE s.scope=? AND c.state='APPLIED' ORDER BY c.applied_at DESC LIMIT 1", (scope,)).fetchone()
            testing = db.execute("SELECT c.* FROM learning_candidates c JOIN learning_candidate_scopes s ON s.candidate=c.id WHERE s.scope=? AND c.state='TESTING' ORDER BY c.created_at LIMIT 1", (scope,)).fetchone()
            candidate = active or testing
            if candidate:
                start = candidate['applied_at'] if active else candidate['frozen_at']
                future = [s for s in samples if s['opened_at'] > start]
                m = p.metrics(future, json.loads(candidate['context']))
                m['scope'] = json.loads(scope)
                age = (current-datetime.fromisoformat(candidate['created_at'])).days
                if candidate['baseline'] != baseline or (not active and age > p.POLICY['maximum_candidate_age_days']):
                    state = 'REVERTED' if active else 'REJECTED'
                elif active:
                    state = 'REVERTED' if p.sufficient(m) and m['upper99_daily_blocks'] < 0 else 'APPLIED'
                elif p.sufficient(m) and age >= p.POLICY['future_days']:
                    state = 'APPLIED' if p.passes(m) else 'REJECTED'
                else:
                    state = 'TESTING'
                applied = candidate['applied_at'] or (timestamp if state == 'APPLIED' else None)
                db.execute('UPDATE learning_candidates SET state=?,metrics=?,applied_at=? WHERE id=?', (state, encoded(m), applied, candidate['id']))
                if state == 'APPLIED':
                    db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', (active_key(scope), candidate['id']))
                else:
                    db.execute('DELETE FROM metadata WHERE key=?', (active_key(scope),))
                p.journal(db, state, candidate['id'], 'Avaliacao isolada por origem/setup; nenhuma evidencia de outra fonte e reutilizada.', m, timestamp)
            else:
                previous = db.execute('SELECT c.created_at FROM learning_candidates c JOIN learning_candidate_scopes s ON s.candidate=c.id WHERE s.scope=? ORDER BY c.created_at DESC LIMIT 1', (scope,)).fetchone()
                if previous and (current-datetime.fromisoformat(previous[0])).days < 7:
                    continue
                before = {r[0] for r in db.execute('SELECT id FROM learning_candidates')}
                p.discover(db, samples, baseline, timestamp, scope=scope)
                for new in db.execute("SELECT id FROM learning_candidates WHERE baseline=? AND created_at=? AND state='TESTING' AND id NOT IN (SELECT candidate FROM learning_candidate_scopes)", (baseline, timestamp)):
                    if new[0] not in before:
                        db.execute('INSERT INTO learning_candidate_scopes VALUES (?,?)', (new[0], scope))
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('learning_next_review',?)", ((current+timedelta(days=1)).isoformat(),))
