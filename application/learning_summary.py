"""Read-only, bounded overview of the persisted learning lifecycle."""
import json
import sqlite3
from application.learning_store import LearningStore


def learning_summary(store=None):
    store = store or LearningStore()
    empty = dict(available=True, candidates=0, testing=0, applied=0, rejected=0, reverted=0, latest=None)
    if not store.path.exists():
        return empty
    try:
        with sqlite3.connect(store.path.resolve().as_uri() + '?mode=ro', uri=True, timeout=1) as db:
            db.row_factory = sqlite3.Row
            names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if 'learning_candidates' not in names:
                return empty
            counts = dict(db.execute('SELECT state,COUNT(*) FROM learning_candidates GROUP BY state'))
            active = db.execute("""SELECT COUNT(*) FROM learning_candidates c
                JOIN metadata m ON m.key LIKE 'm30_active_filter:%' AND m.value=c.id
                WHERE c.state='APPLIED' AND c.baseline=(SELECT id FROM baselines ORDER BY captured_at DESC LIMIT 1)""").fetchone()[0]
            latest = db.execute('SELECT created_at,state,message,evidence FROM learning_journal ORDER BY created_at DESC LIMIT 1').fetchone()
            return dict(available=True,candidates=sum(counts.values()),testing=counts.get('TESTING',0),
                        applied=active,rejected=counts.get('REJECTED',0),reverted=counts.get('REVERTED',0),
                        latest=dict(latest) if latest else None)
    except sqlite3.Error:
        return {**empty,'available':False}
