from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import json

import pytest

from application.learning_store import LearningStore, encoded
from application.model30_learning import clone_contract, submit_pair, preflight, matches, MODEL_30_MAGIC
from application.learning_policy import tables, cycle, metrics, passes, admission, discover
from domain.contracts.execution_order import ExecutionOrder


def order():
    return ExecutionOrder("BUY", 0.1, 100, 90, 110, symbol="XAUUSD", plan_identity="original",
        operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M8",
        plan_snapshot={"symbol": "XAUUSD", "direction": "BUY", "candle_time": "2026-09-24T10:00:00",
            "initial_stop": 70, "target": 110,
            "stop_management_parameters": {"source_operational_model": "MODELO_8_TEST", "active_entry_order_type": "BUY_STOP"}})


def provider():
    account = SimpleNamespace(login=1, server="demo", trade_mode=0, margin_mode=2)
    mt5 = SimpleNamespace(account_info=lambda: account, ACCOUNT_TRADE_MODE_DEMO=0,
                          ACCOUNT_MARGIN_MODE_RETAIL_HEDGING=2, positions_get=lambda: [], orders_get=lambda: [])
    sent = []
    def send(o):
        sent.append(o)
        return SimpleNamespace(accepted=True, ticket=100, message="accepted")
    return SimpleNamespace(mt5=mt5, execution_account=SimpleNamespace(mode="DEMO"), submit_order=send, sent=sent)


def test_m30_effective_contract_keeps_m23_untouched():
    original = order()
    clone = clone_contract(original, 42)
    assert clone.stop == 90 and clone.plan_snapshot["initial_stop"] == 90
    assert original.plan_snapshot["initial_stop"] == 70
    assert clone.quantity == original.quantity and clone.target == original.target
    assert clone.operational_model.startswith("MODELO_30_")
    assert clone.plan_snapshot["stop_management_parameters"]["active_entry_order_type"] == "BUY_STOP"


def test_pair_idempotent_across_restart(tmp_path):
    store = LearningStore(tmp_path / "ledger.sqlite3")
    p = provider()
    submit_pair(p, order(), 42, store)
    submit_pair(p, order(), 42, LearningStore(store.path))
    assert len(p.sent) == 1
    with store.connect() as db:
        row = db.execute("SELECT * FROM m30_pairs").fetchone()
    assert row["status"] == "ACCEPTED" and row["clone_ticket"] == 100


@pytest.mark.parametrize("trade,margin,mode", [(2,2,"DEMO"),(0,0,"DEMO"),(0,2,"REAL")])
def test_real_or_netting_never_sent(tmp_path, trade, margin, mode):
    p = provider()
    p.mt5.account_info().trade_mode = trade
    p.mt5.account_info().margin_mode = margin
    p.execution_account.mode = mode
    with pytest.raises(RuntimeError):
        submit_pair(p, order(), 42, LearningStore(tmp_path / "x.sqlite3"))
    assert p.sent == []


def test_uncertain_send_is_not_retried(tmp_path):
    store = LearningStore(tmp_path / "x.sqlite3")
    p = provider()
    def fail(o):
        p.sent.append(o)
        raise TimeoutError("unknown outcome")
    p.submit_order = fail
    with pytest.raises(TimeoutError):
        submit_pair(p, order(), 42, store)
    assert submit_pair(p, order(), 42, store) is None
    assert len(p.sent) == 1


def test_position_identity_isolated():
    assert matches(SimpleNamespace(magic=MODEL_30_MAGIC, comment="TraderIA M30 S8 P42"))
    assert not matches(SimpleNamespace(magic=260629, comment="TraderIA M23 S8"))
    assert not matches(SimpleNamespace(magic=260629, comment="TraderIA M30"))


def test_m30_basket_cannot_close_m23(tmp_path):
    from application.model23_basket_accumulator import Model23BasketManager
    positions = [SimpleNamespace(ticket=1,magic=260629,comment="TraderIA M23 S8",profit=5000,type=0,symbol="XAUUSD",volume=.1),
                 SimpleNamespace(ticket=2,magic=MODEL_30_MAGIC,comment="TraderIA M30 S8",profit=1001,type=0,symbol="XAUUSD",volume=.1)]
    closed=[]
    service=SimpleNamespace(list_open_positions=lambda:positions,
        close_position=lambda **kw: closed.append(kw) or SimpleNamespace(accepted=True,status="ACCEPTED",message="ok"))
    manager=Model23BasketManager(service,state_path=tmp_path/"m30.json",audit_path=tmp_path/"m30.jsonl",
                                position_matches=matches,model_label="M30")
    result=manager.evaluate_once()
    assert result.net_result_usd == 1001
    assert [x["ticket"] for x in closed] == [2]
    assert closed[0]["reason"].startswith("M30_")


def test_daily_scheduler_persists_and_insufficient_evidence_never_applies(tmp_path):
    store=LearningStore(tmp_path/"x.sqlite3")
    cycle(store,"2026-09-24T10:00:00+00:00")
    cycle(LearningStore(store.path),"2026-09-24T10:01:00+00:00")
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM learning_journal").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM learning_candidates").fetchone()[0] == 0
    assert admission(order().plan_snapshot,store)["version"] == "BASELINE"


def test_promotion_metrics_require_future_days_and_limit_good_discards():
    selected={"source":"M8"}
    samples=[dict(context=selected,net=-10,day=f"2026-09-{i%20+1:02}") for i in range(100)]
    assert passes(metrics(samples,selected))
    assert not passes(metrics(samples[:10],selected))
    for row in samples:
        row["net"]=10
    assert not passes(metrics(samples,selected))


def test_candidate_frozen_and_future_promotion_atomic(tmp_path, monkeypatch):
    import application.learning_policy as module
    store=LearningStore(tmp_path/"x.sqlite3")
    selected={"source":"M8"}
    with store.connect() as db:
        tables(db)
        baseline=store.baseline(db,{"v":1})
        db.execute("INSERT INTO learning_candidates VALUES ('candidate',?,'2026-09-01T00:00:00+00:00','TESTING',?,'{}','2026-09-01T00:00:00+00:00',NULL)",
                   (baseline,encoded(selected)))
    samples=[dict(context=selected,net=-10,day=f"2026-09-{i%20+2:02}",opened_at=f"2026-09-{i%20+2:02}T00:00:00+00:00") for i in range(100)]
    monkeypatch.setattr(module,"read_samples",lambda *a:samples)
    cycle(store,"2026-09-24T00:00:00+00:00")
    with store.connect() as db:
        assert db.execute("SELECT state FROM learning_candidates").fetchone()[0] == "APPLIED"
        assert db.execute("SELECT value FROM metadata WHERE key='m30_active_filter'").fetchone()[0] == "candidate"
        assert db.execute("SELECT state FROM learning_journal").fetchone()[0] == "APLICADO"
        store.baseline(db,{"v":2})
    cycle(store,"2026-09-25T00:00:00+00:00")
    with store.connect() as db:
        assert db.execute("SELECT state FROM learning_candidates").fetchone()[0] == "REVERTED"
        assert db.execute("SELECT value FROM metadata WHERE key='m30_active_filter'").fetchone() is None
