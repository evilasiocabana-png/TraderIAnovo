"""Manual channel hypotheses, isolated from learned admission and promotion."""
import json
from datetime import datetime, timezone
from application.learning_store import digest, encoded, now
from application.learning_scopes import scope_identity
from application.realized_equity_pivot_channels import analyze_pivot_channels

SPEC = dict(version='MANUAL_REALIZED_CHANNEL_V1', origin='MANUAL', confirmations=1,
            reference='M23_ORIGINAL_CLOSED_NET_PER_SCOPE', sensitivity=1.0,
            mirror='CONFIRMED_DESCENDING_TOPS_AND_BOTTOMS', normal='UPPER_BREAK_OR_RISING_CHANNEL',
            volume='SAME_AS_REFERENCE', target='ORIGINAL_INITIAL_STOP', stop='SYMMETRIC_RR_1',
            promotion='NOT_ELIGIBLE_FOR_AUTOMATIC_ADMISSION')


def tables(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS learning_channel_hypotheses (
        id TEXT PRIMARY KEY, scope TEXT NOT NULL, baseline TEXT NOT NULL,
        frozen_at TEXT NOT NULL, spec TEXT NOT NULL, state TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS learning_channel_trials (
        candidate TEXT NOT NULL, pair_id TEXT NOT NULL, mode TEXT NOT NULL,
        state TEXT NOT NULL, evidence TEXT NOT NULL,
        PRIMARY KEY(candidate,pair_id));''')


def channel_decision(results):
    study = analyze_pivot_channels(results, confirmations=1, sensitivity=1.0)
    if not study['segments']:
        return 'WAITING_STRUCTURE'
    segment = study['segments'][-1]
    if segment['trend'] != 'Baixa':
        return 'NORMAL'
    # An upper break ends the descending regime even before new rising pivots.
    upper_breaks = [e for e in study['events'] if e['operation'] >= segment['anchor'] and e['side'] == 'Acima']
    return 'NORMAL' if upper_breaks else 'ESPELHADO'


def register_scopes(db, timestamp=None):
    timestamp = timestamp or now()
    tables(db)
    baseline = db.execute('SELECT id FROM baselines ORDER BY captured_at DESC LIMIT 1').fetchone()
    if not baseline:
        return
    rows = db.execute("""SELECT s.snapshot,e.account FROM signals s JOIN executions e ON e.signal_id=s.id
        WHERE s.executor='M23' AND e.account_mode='DEMO' AND e.account<>''
        ORDER BY s.first_seen DESC LIMIT 10000""")
    scopes = {scope_identity(json.loads(row['snapshot']), row['account']) for row in rows}
    for scope in scopes - {''}:
        if db.execute('SELECT 1 FROM learning_channel_hypotheses WHERE scope=? AND baseline=?', (scope,baseline[0])).fetchone():
            continue
        key = digest([scope, baseline[0], SPEC, timestamp])
        db.execute('INSERT INTO learning_channel_hypotheses VALUES (?,?,?,?,?,?)',
                   (key,scope,baseline[0],timestamp,encoded(SPEC),'WAITING_FUTURE'))


def channel_hypothesis_page(store):
    with store.connect() as db:
        tables(db)
        return [dict(r) for r in db.execute('SELECT * FROM learning_channel_hypotheses ORDER BY frozen_at DESC LIMIT 100')]


def evaluate_future(store):
    """At most one optional market read per observer cycle; no trading calls."""
    from application.learning_channel_replay import replay
    budget = 1
    with store.connect() as db:
        register_scopes(db)
        latest = db.execute('SELECT id FROM baselines ORDER BY captured_at DESC LIMIT 1').fetchone()
        candidates = [dict(r) for r in db.execute('SELECT * FROM learning_channel_hypotheses WHERE baseline=?', (latest[0] if latest else '',))]
    for candidate in candidates:
        identity = json.loads(candidate['scope'])
        with store.connect() as db:
            pairs = [dict(r) for r in db.execute('''SELECT p.pair_id,p.snapshot,p.created_at,e.evidence,e.net,e.status,
                s.snapshot AS original_snapshot,s.first_seen
                FROM m30_pairs p JOIN executions e ON e.ticket=p.original_ticket AND e.account=p.account AND e.account_mode='DEMO'
                JOIN signals s ON s.id=e.signal_id AND s.executor='M23'
                WHERE p.account=? AND s.baseline=? AND s.provenance='PROSPECTIVE' AND s.first_seen>?
                ORDER BY p.created_at LIMIT 1000''', (identity['account'],candidate['baseline'],candidate['frozen_at']))]
            references = [dict(r) for r in db.execute('''SELECT e.ticket,e.net,e.evidence,s.snapshot FROM executions e JOIN signals s ON s.id=e.signal_id
                WHERE e.account=? AND e.account_mode='DEMO' AND e.status='CLOSED' AND e.net IS NOT NULL
                AND s.executor='M23' AND s.baseline=? ORDER BY e.recorded_at LIMIT 10000''', (identity['account'],candidate['baseline']))]
        for pair in pairs:
            snapshot = json.loads(pair['original_snapshot'])
            if scope_identity(snapshot,identity['account']) != candidate['scope']:
                continue
            with store.connect() as db:
                prior = db.execute('SELECT state FROM learning_channel_trials WHERE candidate=? AND pair_id=?', (candidate['id'],pair['pair_id'])).fetchone()
            if prior and prior[0] in ('RESOLVED','RESOLVED_ESTIMATED_COSTS'):
                continue
            evidence = json.loads(pair['evidence'])
            deals = evidence.get('deals',[])
            opened = min((float(d.get('time_msc') or float(d.get('time',0))*1000)/1000 for d in deals), default=0)
            if not opened or opened <= datetime.fromisoformat(candidate['frozen_at']).timestamp():
                continue
            historical, seen = [], set()
            for ref in references:
                ref_snapshot = json.loads(ref['snapshot'])
                if (ref_snapshot.get('stop_management_parameters') or {}).get('m23_m29_origin_source'):
                    continue
                if ref['ticket'] in seen or scope_identity(ref_snapshot,identity['account']) != candidate['scope']:
                    continue
                rd = json.loads(ref['evidence']).get('deals',[])
                closed = max((float(d.get('time',0)) for d in rd),default=0)
                if closed and closed < opened:
                    seen.add(ref['ticket'])
                    historical.append(dict(net=ref['net'],closed=closed))
            mode = channel_decision(sorted(historical,key=lambda r:r['closed']))
            result = dict(state='WAITING_REFERENCE_CLOSE',mode=mode)
            if mode == 'WAITING_STRUCTURE':
                result['state']='WAITING_STRUCTURE'
            elif pair['status']=='CLOSED' and pair['net'] is not None:
                if mode=='NORMAL':
                    result.update(state='RESOLVED',net=pair['net'],cost_method='REFERENCE_NATIVE_NET')
                else:
                    plan=json.loads(pair['snapshot'])
                    params=plan.get('stop_management_parameters') or {}
                    kind=str(params.get('active_entry_order_type') or 'MARKET').upper()
                    if 'STOP' in kind or 'LIMIT' in kind:
                        result['state']='WAITING_PENDING_ORDER_SIMULATION'
                    elif budget:
                        budget-=1
                        result.update(replay(dict(account=identity['account'],symbol=identity['symbol'],opened=opened,
                            original_side=snapshot.get('direction'),original_stop=plan.get('initial_stop'),
                            volume=params.get('m30_execution_volume'),
                            reference_fees=sum(float(d.get('commission',0))+float(d.get('fee',0)) for d in deals))))
                    else:
                        result['state']='WAITING_READ_BUDGET'
            result.update(reference_results=len(historical),checked_at=now(),created_at=pair['created_at'])
            with store.connect() as db:
                db.execute("UPDATE learning_channel_hypotheses SET state='TESTING_SIMULATION' WHERE id=?",(candidate['id'],))
                db.execute('INSERT OR REPLACE INTO learning_channel_trials VALUES (?,?,?,?,?)',
                           (candidate['id'],pair['pair_id'],mode,result['state'],encoded(result)))


def manual_comparison(store):
    from application.model30_learning import comparison_group
    scoped = {}
    with store.connect() as db:
        tables(db)
        baseline = db.execute('SELECT id FROM baselines ORDER BY captured_at DESC LIMIT 1').fetchone()
        for candidate in db.execute('SELECT * FROM learning_channel_hypotheses WHERE baseline=? ORDER BY frozen_at', (baseline[0] if baseline else '',)):
            identity=json.loads(candidate['scope'])
            key=comparison_group(dict(source=identity['source'],symbol=identity['symbol'],account=identity['account'],route_snapshot=encoded(dict(entry_setup=identity['setup'],timeframe=identity['timeframe']))))
            trials=db.execute('''SELECT t.*,p.created_at,e.net AS original,c.net AS clone,e.status AS original_state,c.status AS clone_state,p.status AS pair_state
                FROM learning_channel_trials t JOIN m30_pairs p ON p.pair_id=t.pair_id
                LEFT JOIN executions e ON e.ticket=p.original_ticket AND e.account=p.account AND e.account_mode='DEMO'
                LEFT JOIN executions c ON c.ticket=p.clone_ticket AND c.account=p.account AND c.account_mode='DEMO'
                WHERE t.candidate=? ORDER BY p.created_at''',(candidate['id'],)).fetchall()
            rows,seen=[],set()
            total23=total30=totalcandidate=0.0
            pending='Aguardando resultados futuros'
            for trial in trials:
                if trial['pair_id'] in seen:
                    continue
                seen.add(trial['pair_id'])
                if trial['state'] not in ('RESOLVED','RESOLVED_ESTIMATED_COSTS') or trial['original_state']!='CLOSED' or (trial['clone_state']!='CLOSED' and trial['pair_state']!='FILTERED'):
                    pending=trial['state']
                    break
                evidence=json.loads(trial['evidence'])
                total23+=float(trial['original'])
                total30+=float(trial['clone']) if trial['clone_state']=='CLOSED' else 0.0
                totalcandidate+=float(evidence['net'])
                rows.append({'Par':len(rows)+1,'M23':total23,'M30':total30,'Candidato em teste':totalcandidate})
            scoped[key]=dict(state='TESTING' if rows else 'WAITING',version=candidate['id'],start=candidate['frozen_at'],
                             rows=rows,manual=True,pending=pending)
    return scoped
