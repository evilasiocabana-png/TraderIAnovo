"""M30: paired Demo execution using the effective, accepted M23 contract."""

from dataclasses import replace
from datetime import datetime, timezone
from functools import wraps
import json
import os
import re
import threading
import time

from application.learning_store import LearningStore, ROOT, encoded, now

MODEL_30_ID = "MODELO_30_ADAPTIVE_M23"
MODEL_30_MAGIC = 260630
_PAIR_LOCK = threading.Lock()
_RISK_LAST = 0.0


def is_model30(value):
    return str(value).upper().startswith(MODEL_30_ID)


def matches(position):
    return int(getattr(position, "magic", 0)) == MODEL_30_MAGIC and bool(
        re.search(r"\bM30\b", str(getattr(position, "comment", "")).upper()))


def tables(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS m30_pairs (
            pair_id TEXT PRIMARY KEY, original_ticket INTEGER NOT NULL,
            account TEXT NOT NULL, source TEXT NOT NULL, symbol TEXT NOT NULL,
            created_at TEXT NOT NULL, status TEXT NOT NULL, clone_ticket INTEGER,
            filter_version TEXT NOT NULL, reason TEXT NOT NULL, snapshot TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS m30_recent ON m30_pairs(created_at DESC);
    """)


def enabled(store=None):
    store = store or LearningStore()
    if not store.path.exists():
        return False
    with store.connect() as db:
        row = db.execute("SELECT value FROM metadata WHERE key='m30_enabled'").fetchone()
    return bool(row and row[0] == "true")


def clone_contract(order, ticket):
    snapshot = dict(order.plan_snapshot or {})
    params = dict(snapshot.get("stop_management_parameters") or {})
    params.update(m30_original_ticket=int(ticket), m30_baseline_model=order.operational_model,
                  m30_effective_stop=order.stop, m30_effective_target=order.target,
                  m30_execution_volume=order.quantity)
    operational_model = order.operational_model.replace("MODELO_23_BASKET_ACCUMULATOR", MODEL_30_ID, 1)
    snapshot.update(operational_model=operational_model, initial_stop=order.stop,
                    target=order.target, stop_management_parameters=params)
    return replace(order, operational_model=operational_model,
                   plan_identity=f"M30:{ticket}:{order.plan_identity}",
                   plan_snapshot=snapshot)


def paired_submit(fn):
    @wraps(fn)
    def wrapped(provider, order):
        result = fn(provider, order)
        if (not order.operational_model.startswith("MODELO_23_BASKET_ACCUMULATOR")
                or not result.accepted or not result.ticket):
            return result
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TRADERIA_LEARNING_DISABLED") == "1":
            return result
        try:
            if enabled():
                recorded = getattr(provider, "_m30_last_accepted", None)
                if recorded and recorded[0] == result.ticket:
                    submit_pair(provider, recorded[1], result.ticket)
        except Exception as exc:
            # A failure in the additional strategy cannot replace the M23 result.
            provider._m30_last_error = str(exc)[:300]
        return result
    return wrapped


def submit_pair(provider, order, ticket, store=None):
    store = store or LearningStore()
    if not order.operational_model.startswith("MODELO_23_BASKET_ACCUMULATOR") or int(ticket or 0) <= 0:
        raise ValueError("M30 somente recebe ordem M23 confirmada")
    account = provider.mt5.account_info()
    if (account is None or int(account.trade_mode) != int(provider.mt5.ACCOUNT_TRADE_MODE_DEMO)
            or int(account.margin_mode) != int(provider.mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING)
            or provider.execution_account.mode != "DEMO"):
        raise RuntimeError("M30 exige Demo confirmada e conta hedging; nenhuma copia enviada")
    account_id = str(account.login) + "@" + str(account.server)
    pair_id = account_id + ":" + str(ticket)
    clone = clone_contract(order, ticket)
    from application.learning_policy import admission
    decision = admission(clone.plan_snapshot, store)
    with _PAIR_LOCK:
        with store.connect() as db:
            tables(db)
            cursor = db.execute("""INSERT OR IGNORE INTO m30_pairs VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (pair_id, int(ticket), account_id, str((clone.plan_snapshot.get("stop_management_parameters") or {}).get("source_operational_model", "")),
                 order.symbol, now(), "SENDING" if decision["allowed"] else "FILTERED", None,
                 decision["version"], decision["reason"], encoded(clone.plan_snapshot)))
            if cursor.rowcount != 1:
                return None
        if not decision["allowed"]:
            return None
        try:
            result = provider.submit_order(clone)
        except Exception as exc:
            with store.connect() as db:
                db.execute("UPDATE m30_pairs SET status='UNCERTAIN',reason=? WHERE pair_id=?", (str(exc)[:300], pair_id))
            raise
        with store.connect() as db:
            db.execute("UPDATE m30_pairs SET status=?,clone_ticket=?,reason=? WHERE pair_id=?",
                       ("ACCEPTED" if result.accepted else "REJECTED", result.ticket, result.message, pair_id))
        return result


def model30_comment(order):
    params = (order.plan_snapshot or {}).get("stop_management_parameters") or {}
    source = str(params.get("m23_m29_origin_source") or params.get("source_operational_model", ""))
    match = re.search(r"(?:MODELO_|M)(\d+)", source)
    number = match[1] if match else "0"
    return f"TraderIA M30 S{number} P{int(params.get('m30_original_ticket', 0))}"[:31]


def preflight(provider, order, store=None):
    store = store or LearningStore()
    account = provider.mt5.account_info()
    if (account is None or account.trade_mode != provider.mt5.ACCOUNT_TRADE_MODE_DEMO
            or account.margin_mode != provider.mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING
            or provider.execution_account.mode != "DEMO"):
        return "M30 exige conta Demo hedging confirmada"
    params = (order.plan_snapshot or {}).get("stop_management_parameters") or {}
    ticket = int(params.get("m30_original_ticket", 0))
    key = str(account.login) + "@" + str(account.server) + ":" + str(ticket)
    with store.connect() as db:
        tables(db)
        pair = db.execute("SELECT * FROM m30_pairs WHERE pair_id=?", (key,)).fetchone()
    if not pair or pair["status"] != "SENDING":
        return "M30 sem pareamento persistente autorizado"
    expected = json.loads(pair["snapshot"])
    if (expected.get("symbol") != order.symbol or expected.get("direction") != order.side
            or float(params.get("m30_execution_volume", 0)) != float(order.quantity)
            or float(expected.get("initial_stop", 0)) != float(order.stop)
            or float(expected.get("target", 0) or 0) != float(order.target or 0)):
        return "M30 contrato diverge da ordem original confirmada"
    positions = provider.mt5.positions_get()
    orders = provider.mt5.orders_get()
    if positions is None or orders is None:
        return "M30 nao confirmou posicoes e pendencias"
    if any(matches(p) and f"P{ticket}" in str(getattr(p, "comment", "")).split() for p in [*positions, *orders]):
        return "M30 ja possui copia desta ordem M23"
    if any(matches(p) and same_route(order, p, store) for p in positions):
        return "M30 ainda possui posicao nesta fonte e tipo de entrada"
    return ""


def same_route(order, position, store=None):
    store = store or LearningStore()
    if not matches(position):
        return False
    from application.model23_basket_accumulator import model23_entry_type
    with store.connect() as db:
        tables(db)
        old = db.execute("SELECT snapshot FROM m30_pairs WHERE clone_ticket=?", (int(position.ticket),)).fetchone()
    if not old:
        return True  # Unknown M30 ownership is not permission to duplicate it.
    def route(snapshot):
        p = snapshot.get("stop_management_parameters") or {}
        return (p.get("m30_baseline_model"), model23_entry_type(p, entry_setup=snapshot.get("entry_setup", "")))
    return route(order.plan_snapshot or {}) == route(json.loads(old[0]))


def manage_basket(execution_service, force=False):
    global _RISK_LAST
    state_path = ROOT / ".traderia" / "model30_basket_state.json"
    if (not enabled() and not state_path.exists()) or (not force and time.monotonic()-_RISK_LAST < 10):
        return None
    from application.model23_basket_accumulator import Model23BasketManager
    provider = getattr(execution_service, "provider", execution_service)
    if str(getattr(getattr(provider, "execution_account", None), "mode", "")) != "DEMO":
        raise RuntimeError("M30 gestao restrita a Demo")
    try:
        snapshot = Model23BasketManager(
            execution_service=execution_service, state_path=state_path,
            audit_path=ROOT / ".traderia" / "model30_basket_audit.jsonl",
            position_matches=matches, model_label="M30",
        ).evaluate_once()
    except Exception:
        with LearningStore().connect() as db:
            db.execute("DELETE FROM metadata WHERE key='m30_risk_ready'")
        raise
    with LearningStore().connect() as db:
        db.execute("INSERT OR REPLACE INTO metadata VALUES ('m30_risk_ready',?)", (now(),))
    _RISK_LAST = time.monotonic()
    return snapshot


def risk_ready(store=None):
    store = store or LearningStore()
    if not store.path.exists():
        return False
    with store.connect() as db:
        row = db.execute("SELECT value FROM metadata WHERE key='m30_risk_ready'").fetchone()
    return bool(row and (datetime.now(timezone.utc)-datetime.fromisoformat(row[0])).total_seconds() < 120)


def pair_page(store=None, limit=100):
    store = store or LearningStore()
    if not store.path.exists():
        return []
    with store.connect() as db:
        tables(db)
        return [dict(r) for r in db.execute("SELECT * FROM m30_pairs ORDER BY created_at DESC LIMIT ?", (min(100, limit),))]


def comparison(store=None):
    store = store or LearningStore()
    if not store.path.exists():
        return []
    with store.connect() as db:
        tables(db)
        rows = db.execute("""SELECT p.created_at,p.original_ticket,p.clone_ticket,p.status,
            e.net AS m23_net,c.net AS m30_net,e.status AS m23_state,c.status AS m30_state
            FROM m30_pairs p LEFT JOIN executions e ON e.ticket=p.original_ticket AND e.account_mode='DEMO'
            LEFT JOIN executions c ON c.ticket=p.clone_ticket AND c.account_mode='DEMO'
            ORDER BY p.created_at DESC LIMIT 1000""").fetchall()
    result = []
    seen = set()
    total23 = total30 = 0.0
    for row in reversed(rows):
        if row["original_ticket"] in seen:
            continue
        seen.add(row["original_ticket"])
        if row["m23_state"] != "CLOSED" or (row["m30_state"] != "CLOSED" and row["status"] != "FILTERED"):
            continue
        total23 += row["m23_net"]
        total30 += row["m30_net"] if row["m30_state"] == "CLOSED" else 0.0
        result.append({"Par": len(result)+1, "M23 liquido": total23, "M30 liquido": total30})
    return result
