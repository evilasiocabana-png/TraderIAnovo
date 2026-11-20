"""Read-only prospective counterfactual on the same reconciled Demo pairs."""

from datetime import datetime, timezone
import json

from application.learning_policy import context
from application.learning_store import LearningStore


def candidate_curve(candidate, rows):
    frozen = datetime.fromisoformat(candidate["frozen_at"])
    selected = json.loads(candidate["context"])
    totals = [0.0, 0.0, 0.0]
    result, seen = [], set()
    for row in sorted(rows, key=lambda r: r["created_at"]):
        if row["pair_id"] in seen:
            continue
        if row["m23_state"] != "CLOSED" or row["m23_net"] is None:
            continue
        if row["m30_state"] != "CLOSED" and row["status"] != "FILTERED":
            continue
        if row["m30_state"] == "CLOSED" and row["m30_net"] is None:
            continue
        if row["provenance"] != "PROSPECTIVE" or row["baseline"] != candidate["baseline"]:
            continue
        if datetime.fromisoformat(row["first_seen"]) <= frozen:
            continue
        try:
            evidence = json.loads(row["evidence"])
            deals = evidence.get("deals", [])
            opened = datetime.fromtimestamp(min(float(d["time"]) for d in deals), timezone.utc)
            snapshot = json.loads(row["signal_snapshot"])
        except (TypeError, ValueError, KeyError):
            continue
        if opened <= frozen:
            continue
        seen.add(row["pair_id"])
        original = float(row["m23_net"])
        totals[0] += original
        totals[1] += float(row["m30_net"]) if row["m30_state"] == "CLOSED" else 0.0
        totals[2] += 0.0 if context(snapshot) == selected else original
        result.append(dict(zip(("Par", "M23", "M30", "Candidato em teste"), (len(result)+1, *totals))))
    return result


def candidate_comparison(store=None):
    store = store or LearningStore()
    empty = {"state": "NONE", "rows": []}
    if not store.path.exists():
        return empty
    with store.connect() as db:
        from application.learning_scopes import scope_tables, scope_identity
        from application.model30_learning import comparison_group
        scope_tables(db)
        candidates = db.execute("SELECT c.*,s.scope FROM learning_candidates c JOIN learning_candidate_scopes s ON s.candidate=c.id WHERE c.state='TESTING' ORDER BY c.created_at").fetchall()
        if not candidates:
            return empty
        baseline = db.execute("SELECT id FROM baselines ORDER BY captured_at DESC LIMIT 1").fetchone()
        scoped = {}
        for candidate in candidates:
            candidate = dict(candidate)
            identity = json.loads(candidate['scope'])
            key = comparison_group(dict(source=identity['source'],symbol=identity['symbol'],account=identity['account'],
                                        route_snapshot=json.dumps(dict(entry_setup=identity['setup'],timeframe=identity['timeframe']))))
            if key in scoped:
                continue
            meta = {"version": candidate["id"], "start": candidate["frozen_at"], "rows": []}
            if not baseline or baseline[0] != candidate["baseline"]:
                scoped[key] = {**meta, "state": "BASE_CHANGED"}
                continue
            rows = db.execute("""SELECT p.pair_id,p.created_at,p.status,p.source,p.symbol,p.account,p.snapshot AS route_snapshot,
            e.net AS m23_net,c.net AS m30_net,e.status AS m23_state,c.status AS m30_state,
            s.provenance,s.baseline,s.first_seen,s.snapshot AS signal_snapshot,e.evidence
            FROM m30_pairs p
            JOIN executions e ON e.ticket=p.original_ticket AND e.account=p.account AND e.account_mode='DEMO'
            JOIN signals s ON s.id=e.signal_id AND s.executor='M23'
            LEFT JOIN executions c ON c.ticket=p.clone_ticket AND c.account=p.account AND c.account_mode='DEMO'
            WHERE p.created_at>? AND p.account=? ORDER BY p.created_at LIMIT 10000""", (candidate["frozen_at"], identity['account'])).fetchall()
            rows = [dict(r) for r in rows if scope_identity(json.loads(r['signal_snapshot']),r['account']) == candidate['scope']]
            curve = candidate_curve(candidate, rows)
            scoped[key] = {**meta, "state": "TESTING" if curve else "WAITING", "rows": curve}
    return {**empty, "scoped": scoped}
