"""Conservative, persisted statistical filter lifecycle for M30 Demo only.

Calendar opens a review; it never substitutes for independent future evidence.
The counterfactual holds the recorded M23 opportunities fixed, not market fills.
"""

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import random

from application.learning_store import LearningStore, digest, encoded, now

POLICY = {"version": "M30_POLICY_1", "discovery_groups": 200, "calibration_groups": 100,
          "training_days": 30, "future_groups": 100, "future_days": 14,
          "context_groups": 30, "max_good_discard_fraction": 0.25,
          "bootstrap_repetitions": 1000, "daily_review_seconds": 86400,
          "promotion_interval_days": 7, "maximum_candidate_age_days": 90}


def tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS learning_candidates (
            id TEXT PRIMARY KEY, baseline TEXT NOT NULL, created_at TEXT NOT NULL,
            state TEXT NOT NULL, context TEXT NOT NULL, metrics TEXT NOT NULL,
            frozen_at TEXT NOT NULL, applied_at TEXT);
        CREATE TABLE IF NOT EXISTS learning_journal (
            id TEXT PRIMARY KEY, created_at TEXT NOT NULL, state TEXT NOT NULL,
            candidate TEXT NOT NULL, message TEXT NOT NULL, evidence TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS journal_recent ON learning_journal(created_at DESC);
    """)


def journal(db, state, candidate, message, evidence, timestamp):
    key = digest([timestamp[:10], state, candidate, message])
    db.execute("INSERT OR IGNORE INTO learning_journal VALUES (?,?,?,?,?,?)",
               (key, timestamp, state, candidate, message, encoded(evidence)))


def context(snapshot):
    p = snapshot.get("stop_management_parameters") or {}
    features = snapshot.get("features") or snapshot
    return {"source": str(p.get("m23_m29_origin_source") or p.get("source_operational_model") or ""),
            "symbol": str(snapshot.get("symbol", "")),
            "direction": str(snapshot.get("direction", "")),
            "trend": str(features.get("trend") or "UNKNOWN"),
            "mode": str(p.get("m23_m29_mode") or "NORMAL")}


def read_samples(db, baseline):
    rows = db.execute("""SELECT s.group_id,s.snapshot,s.first_seen,e.net,e.evidence,e.recorded_at
        FROM signals s JOIN executions e ON e.signal_id=s.id
        WHERE s.executor='M23' AND s.provenance='PROSPECTIVE' AND s.baseline=?
        AND e.status='CLOSED' AND e.net IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM signals sg JOIN executions eg ON eg.signal_id=sg.id
            WHERE sg.group_id=s.group_id AND sg.executor='M23'
            AND eg.status NOT IN ('CLOSED','REJECTED','CANCELLED_UNFILLED'))
        ORDER BY e.recorded_at DESC LIMIT 10000""", (baseline,))
    grouped = {}
    for row in rows:
        snapshot = json.loads(row["snapshot"])
        ctx = context(snapshot)
        if not ctx["source"] or ctx["trend"] in {"UNKNOWN", "INDEFINIDA", "N/D"}:
            continue
        native = json.loads(row["evidence"])
        deals = native.get("deals", [])
        if not deals:
            continue
        closed_at = datetime.fromtimestamp(max(float(d.get("time", 0)) for d in deals), timezone.utc).isoformat()
        opened_at = datetime.fromtimestamp(min(float(d.get("time", 0)) for d in deals), timezone.utc).isoformat()
        # Group correlated routes; conflicting contexts do not train a simple rule.
        key = row["group_id"]
        previous = grouped.get(key)
        if previous and previous["context"] != ctx:
            previous["ambiguous"] = True
            continue
        if not previous:
            grouped[key] = {"group": key, "context": ctx, "net": 0.0, "opened_at": opened_at,
                            "closed_at": closed_at, "day": opened_at[:10], "ambiguous": False}
        grouped[key]["net"] += float(row["net"])
        grouped[key]["closed_at"] = max(grouped[key]["closed_at"], closed_at)
    return sorted((r for r in grouped.values() if not r["ambiguous"]), key=lambda r: r["opened_at"])


def drawdown(values):
    equity = peak = worst = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        worst = max(worst, peak-equity)
    return worst


def metrics(samples, selected):
    original = [r["net"] for r in samples]
    filtered = [0.0 if r["context"] == selected else r["net"] for r in samples]
    matching = [r for r in samples if r["context"] == selected]
    good = sum(r["net"] > 0 for r in matching)
    wins = sum(r["net"] > 0 for r in samples)
    daily = defaultdict(float)
    for r, old, new in zip(samples, original, filtered):
        daily[r["day"]] += new-old
    deltas = list(daily.values())
    low = high = 0.0
    if len(deltas) >= POLICY["future_days"]:
        rng = random.Random(30)
        draws = sorted(sum(rng.choices(deltas, k=len(deltas))) for _ in range(POLICY["bootstrap_repetitions"]))
        # One candidate per frozen future window; conservative two-sided 99% interval.
        low, high = draws[4], draws[-5]
    return {"groups": len(samples), "days": len(daily), "context_groups": len(matching),
            "baseline_net": sum(original), "filtered_fixed_opportunities_net": sum(filtered),
            "delta": sum(filtered)-sum(original), "lower99_daily_blocks": low,
            "upper99_daily_blocks": high, "baseline_drawdown": drawdown(original),
            "filtered_drawdown": drawdown(filtered), "good_discarded": good,
            "good_discard_fraction": good/max(1, wins), "bad_discarded": sum(r["net"] < 0 for r in matching),
            "execution_model": "FIXED_RECORDED_M23_OPPORTUNITIES_NOT_SYNTHETIC_FILLS"}


def sufficient(m):
    return (m["groups"] >= POLICY["future_groups"] and m["days"] >= POLICY["future_days"]
            and m["context_groups"] >= POLICY["context_groups"])


def passes(m):
    return (sufficient(m) and m["lower99_daily_blocks"] > 0
            and m["filtered_drawdown"] <= m["baseline_drawdown"]
            and m["good_discard_fraction"] <= POLICY["max_good_discard_fraction"])


def cycle(store=None, timestamp=None):
    store = store or LearningStore()
    timestamp = timestamp or now()
    current = datetime.fromisoformat(timestamp)
    with store.connect() as db:
        tables(db)
        last = db.execute("SELECT value FROM metadata WHERE key='learning_next_review'").fetchone()
        if last and timestamp < last[0]:
            return
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('learning_policy',?)", (encoded(POLICY),))
        baseline = db.execute("SELECT id FROM baselines ORDER BY captured_at DESC LIMIT 1").fetchone()
        baseline = baseline[0] if baseline else ""
        active = db.execute("SELECT * FROM learning_candidates WHERE state='APPLIED' ORDER BY applied_at DESC LIMIT 1").fetchone()
        samples = read_samples(db, baseline) if baseline else []
        if active:
            future = [s for s in samples if s["opened_at"] > active["applied_at"]]
            m = metrics(future, json.loads(active["context"]))
            if active["baseline"] != baseline or (sufficient(m) and m["upper99_daily_blocks"] < 0):
                db.execute("UPDATE learning_candidates SET state='REVERTED' WHERE id=?", (active["id"],))
                db.execute("DELETE FROM metadata WHERE key='m30_active_filter'")
                journal(db, "REVERTIDO", active["id"], "Retorno a base: versao mudou ou vantagem deixou de se sustentar.", m, timestamp)
            else:
                journal(db, "MONITORANDO", active["id"], "Filtro mantido apenas no M30 Demo; M23 permanece referencia.", m, timestamp)
        else:
            candidate = db.execute("SELECT * FROM learning_candidates WHERE state='TESTING' LIMIT 1").fetchone()
            if candidate:
                future = [s for s in samples if s["opened_at"] > candidate["frozen_at"]]
                m = metrics(future, json.loads(candidate["context"]))
                age = (current-datetime.fromisoformat(candidate["created_at"])).days
                if candidate["baseline"] != baseline or age > POLICY["maximum_candidate_age_days"]:
                    db.execute("UPDATE learning_candidates SET state='REJECTED' WHERE id=?", (candidate["id"],))
                    journal(db, "REJEITADO", candidate["id"], "Teste invalidado por mudanca da base ou prazo sem evidencia suficiente.", m, timestamp)
                elif sufficient(m) and age >= POLICY["future_days"]:
                    state = "APPLIED" if passes(m) else "REJECTED"
                    db.execute("UPDATE learning_candidates SET state=?,metrics=?,applied_at=? WHERE id=?",
                               (state, encoded(m), timestamp if state == "APPLIED" else None, candidate["id"]))
                    if state == "APPLIED":
                        db.execute("INSERT OR REPLACE INTO metadata VALUES ('m30_active_filter',?)", (candidate["id"],))
                    journal(db, "APLICADO" if state == "APPLIED" else "REJEITADO", candidate["id"],
                            "Filtro aplicado somente ao M30 Demo." if state == "APPLIED" else "Filtro nao atingiu os criterios preregistrados.", m, timestamp)
                else:
                    journal(db, "INCONCLUSIVO", candidate["id"], "Candidato congelado em teste futuro; nenhuma mudanca nas entradas.", m, timestamp)
            else:
                last_candidate = db.execute("SELECT created_at FROM learning_candidates ORDER BY created_at DESC LIMIT 1").fetchone()
                cooldown = last_candidate and (current-datetime.fromisoformat(last_candidate[0])).days < 7
                if not cooldown:
                    discover(db, samples, baseline, timestamp)
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('learning_next_review',?)",
                   ((current+timedelta(days=1)).isoformat(),))


def discover(db, samples, baseline, timestamp):
    evidence = {"groups": len(samples), "days": len({s["day"] for s in samples}), "policy": POLICY}
    if len(samples) < 300 or evidence["days"] < POLICY["training_days"]:
        journal(db, "INCONCLUSIVO", "BASELINE", "Base mantida: ainda faltam grupos e dias prospectivos para selecionar um filtro.", evidence, timestamp)
        return
    split = min(len(samples)-100, max(200, int(len(samples)*0.67)))
    calibration = samples[split:]
    if len(calibration) < 100:
        return
    cutoff = calibration[0]["opened_at"]
    discovery = [s for s in samples[:split] if s["closed_at"] < cutoff]
    if len(discovery) < 200:
        journal(db, "INCONCLUSIVO", "BASELINE", "Separacao temporal ainda insuficiente apos remover operacoes sobrepostas.", evidence, timestamp)
        return
    contexts = {encoded(s["context"]) for s in discovery}
    candidates = []
    for key in contexts:
        ctx = json.loads(key)
        train = [s for s in discovery if s["context"] == ctx]
        check = [s for s in calibration if s["context"] == ctx]
        if len(train) >= 30 and len(check) >= 15 and sum(s["net"] for s in train) < 0 and sum(s["net"] for s in check) < 0:
            candidates.append((sum(s["net"] for s in check), key))
    if not candidates:
        journal(db, "INCONCLUSIVO", "BASELINE", "Nenhum contexto ruim repetiu evidencia na descoberta e na calibracao.", evidence, timestamp)
        return
    _, selected = min(candidates)
    key = digest([baseline, timestamp, selected, POLICY])
    db.execute("INSERT INTO learning_candidates VALUES (?,?,?,?,?,?,?,NULL)",
               (key, baseline, timestamp, "TESTING", selected, encoded(evidence), timestamp))
    journal(db, "EM_TESTE", key, "Um filtro de contexto foi congelado; aguardando sinais novos para avaliar sem ajustar o teste.",
            {**evidence, "context": json.loads(selected)}, timestamp)


def admission(snapshot, store=None):
    store = store or LearningStore()
    if not store.path.exists():
        return {"allowed": True, "version": "BASELINE", "reason": "Sem filtro aprendido validado"}
    with store.connect() as db:
        tables(db)
        row = db.execute("""SELECT c.* FROM learning_candidates c JOIN metadata m ON m.value=c.id
            WHERE m.key='m30_active_filter' AND c.state='APPLIED'""").fetchone()
        baseline = db.execute("SELECT id FROM baselines ORDER BY captured_at DESC LIMIT 1").fetchone()
        if not row or not baseline or row["baseline"] != baseline[0]:
            return {"allowed": True, "version": "BASELINE", "reason": "Sem filtro aprendido validado nesta base"}
        blocked = context(snapshot) == json.loads(row["context"])
        return {"allowed": not blocked, "version": row["id"],
                "reason": "Contexto bloqueado pelo filtro validado M30" if blocked else "Contexto aprovado pelo filtro M30"}


def journal_page(store=None, limit=50):
    store = store or LearningStore()
    if not store.path.exists():
        return []
    with store.connect() as db:
        tables(db)
        return [dict(r) for r in db.execute("SELECT * FROM learning_journal ORDER BY created_at DESC LIMIT ?", (min(100, limit),))]
