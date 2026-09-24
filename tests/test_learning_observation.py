import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from application.learning_store import LearningStore
from application.learning_observer import LearningObserver, capture, item_from_snapshot, observe_plans
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def snapshot(**changes):
    return {"symbol": "XAUUSD", "timeframe": "M5", "candle_time": "2026-09-24T12:00:00",
            "direction": "BUY", "entry_price": 100, "initial_stop": 90, "target": 110,
            "operational_model": "MODELO_8_TEST", "setup_id": "TEST",
            "stop_management_parameters": {}, **changes}


def item(**changes):
    return item_from_snapshot(snapshot(**changes), provenance="PROSPECTIVE", stage="SOURCE", status="READY")


def test_dedup_restart_and_first_context_immutable(tmp_path):
    path = tmp_path / "signals.sqlite3"
    store = LearningStore(path)
    with store.connect() as db:
        first = store.register(db, item())
        store.register(db, item(entry_price=109))
    with LearningStore(path).connect() as db:
        assert store.register(db, item(entry_price=108)) == first
        row = db.execute("SELECT * FROM signals").fetchone()
        assert json.loads(row["snapshot"])["entry_price"] == 100
        assert db.execute("SELECT COUNT(*) FROM signals").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM observations").fetchone()[0] == 1


def test_original_copy_mirror_grouped(tmp_path):
    store = LearningStore(tmp_path / "x.sqlite3")
    with store.connect() as db:
        store.register(db, item())
        store.register(db, item(operational_model="MODELO_23_TEST",
            stop_management_parameters={"source_operational_model": "MODELO_8_TEST", "source_entry_setup": "TEST"}))
        store.register(db, item(operational_model="MODELO_23_TEST", direction="SELL",
            stop_management_parameters={"m23_m29_origin_source": "M8", "source_entry_setup": "TEST", "m23_m29_mode": "ESPELHADO"}))
    page = store.page()
    assert page["total"] == 3 and page["groups"] == 1
    selected = store.page(executor="M23", limit=1)
    assert selected["total"] == 2 and selected["groups"] == 1
    assert len(selected["rows"]) == 1 and selected["rows"][0]["executor"] == "M23"


def test_legacy_m7_mirror_mode_corrected_without_duplicate(tmp_path):
    store=LearningStore(tmp_path/"x.sqlite3")
    current=item(operational_model="MODELO_29_TEST",stop_management_parameters={
        "source_operational_model":"MODELO_7_TEST","m29_m7_mode":"ESPELHADO","m29_mirrored":True})
    assert current["mode"]=="ESPELHADO"
    with store.connect() as db:
        store.register(db,{**current,"mode":"NORMAL"})
        store.register(db,current)
    assert store.page()["total"]==1
    assert store.page()["rows"][0]["mode"]=="ESPELHADO"


def test_bound_queue_and_no_mutable_references(tmp_path):
    worker = LearningObserver(LearningStore(tmp_path / "x.sqlite3"), tmp_path)
    original = item()
    worker.submit(original)
    original["snapshot"]["entry_price"] = 999
    with worker.store.connect() as db:
        worker.drain(db)
    assert json.loads(worker.store.page()["rows"][0]["snapshot"])["entry_price"] == 100
    for n in range(600):
        worker.submit(item(candle_time=str(n)))
    assert worker.queue.qsize() == 512
    assert worker.dropped == 88


def test_log_incremental_import_not_prospective(tmp_path):
    runtime = tmp_path / ".traderia"
    runtime.mkdir()
    record = {"timestamp": "2026-09-24T12:01:00", "ticket": 42, "accepted": True,
              "execution_account_mode": "DEMO", "plan_snapshot": snapshot(), "quantity": 0.1}
    (runtime / "mt5_demo_execution.jsonl").write_text(json.dumps(record)+"\n", encoding="utf8")
    worker = LearningObserver(LearningStore(tmp_path / "x.sqlite3"), tmp_path)
    for _ in range(2):
        with worker.store.connect() as db:
            worker.ingest_log(db)
    page = worker.store.page()
    assert page["total"] == 1
    assert page["rows"][0]["provenance"] == "EXECUTION_LOG_IMPORT"
    assert page["rows"][0]["baseline"] is None
    assert page["executions"][0]["net"] is None


def test_native_costs_once_and_partial_not_closed(tmp_path):
    store = LearningStore(tmp_path / "x.sqlite3")
    with store.connect() as db:
        key = store.register(db, item())
        db.execute("""INSERT INTO executions(id,signal_id,ticket,account_mode,account,recorded_at,status,evidence,snapshot)
                      VALUES ('e',?,42,'DEMO','','today','ACCEPTED_UNRECONCILED','','{}')""", (key,))
        entry = dict(ticket=1, entry=0, volume=0.1, profit=0, commission=-1, swap=0, fee=0)
        exit_deal = dict(ticket=2, entry=1, volume=0.1, profit=20, commission=-1, swap=-2, fee=0)
        ev = dict(ok=True, account="demo", position_id=42, open=True, deals=[entry])
        store.reconcile(db, "e", ev)
        assert db.execute("SELECT status FROM executions").fetchone()[0] == "OPEN"
        ev.update(open=False, deals=[entry, exit_deal, exit_deal])
        store.reconcile(db, "e", ev)
        store.reconcile(db, "e", ev)
        row = db.execute("SELECT status,net FROM executions").fetchone()
        assert tuple(row) == ("CLOSED", 16)
        assert db.execute("SELECT COUNT(*) FROM deals").fetchone()[0] == 2


def test_observation_wrapper_preserves_decision_even_collection_failure(monkeypatch):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    row = DashboardMT5ForexSignalRowViewModel(pair="XAUUSD", last_candle_time="c1", decision="BUY")
    plan = MT5ResearchTradePlan(symbol="XAUUSD", timeframe="M5", direction="BUY", entry_price=100,
        stop=90, target=110, risk_reward=1, stop_multiplier=1, exit_model="TEST", exit_score=0,
        exit_candidates=0, status="PLANO_VALIDO")
    result = (row, plan)
    collected = []
    import application.learning_observer as module
    monkeypatch.setattr(module, "observer", lambda: SimpleNamespace(submit=lambda x: collected.append(x)))
    @observe_plans("SOURCE", "M8")
    def evaluate(self, row, plan):
        return result
    assert evaluate(None, row, plan) is result
    assert len(collected) == 1
    monkeypatch.setattr(module, "observer", lambda: 1/0)
    assert evaluate(None, row, plan) is result


def test_no_signal_or_unknown_candle_does_not_inflate_counts():
    row = SimpleNamespace(last_candle_time="N/D")
    assert capture(row, SimpleNamespace(direction="WAIT"), stage="SOURCE") is None


def test_baseline_hash_stable_and_changes(tmp_path):
    (tmp_path / "config").mkdir()
    path = tmp_path / "config" / "m29_pattern_filter.json"
    path.write_text('{"rules": []}')
    worker = LearningObserver(LearningStore(tmp_path / "x.sqlite3"), tmp_path)
    with worker.store.connect() as db:
        worker.refresh_baseline(db)
        first = worker.baseline_id
        worker.refresh_baseline(db)
        assert worker.baseline_id == first
        path.write_text('{"rules": [1]}')
        worker.refresh_baseline(db)
        assert worker.baseline_id != first
