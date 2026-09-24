from dataclasses import replace
from types import SimpleNamespace
import pytest

from application.learning_store import LearningStore, encoded, now
from application.model30_learning import clone_contract, tables, MODEL_30_MAGIC
from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
from tests.test_mt5_demo_execution_provider import _FakeMT5
from tests.test_model30_learning import order


@pytest.fixture(autouse=True)
def isolated_round_state(tmp_path, monkeypatch):
    import application.learning_store as store_module
    monkeypatch.setattr(store_module, "ROOT", tmp_path)


def test_actual_provider_request_preserves_effective_contract(tmp_path, monkeypatch):
    import application.model30_learning as module
    store = LearningStore(tmp_path / "x.sqlite3")
    monkeypatch.setattr(module, "LearningStore", lambda: store)
    monkeypatch.setattr(module, "enabled", lambda *a: True)
    monkeypatch.setattr(module, "risk_ready", lambda *a: True)
    native = _FakeMT5()
    native.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING = 2
    native.account_info = lambda: SimpleNamespace(trade_mode=0,margin_mode=2,login=1,server="demo",
                                                 currency="USD",trade_allowed=True,trade_expert=True)
    provider = MT5DemoExecutionProvider(mt5=native, log_path=tmp_path/"orders.jsonl")
    original = replace(order(), operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M1",
        plan_snapshot={"symbol":"XAUUSD","direction":"BUY","candle_time":"2026-09-24T10:00:00",
            "stop_management_parameters":{"source_operational_model":"MODELO_1_ALPHA_ATUAL","active_entry_order_type":"MARKET"}})
    clone=clone_contract(original,42)
    with store.connect() as db:
        tables(db)
        db.execute("INSERT INTO m30_pairs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                   ("1@demo:42",42,"1@demo","M1","XAUUSD",now(),"SENDING",None,"BASELINE","",encoded(clone.plan_snapshot)))
    result=provider.submit_order(clone)
    assert result.accepted,result.message
    assert native.last_request["magic"]==MODEL_30_MAGIC
    assert native.last_request["comment"]=="TraderIA M30 S1 P42"
    assert native.last_request["volume"]==.1
    assert native.last_request["sl"]==original.stop
    assert native.last_request["tp"]==original.target
    assert "M23" not in native.last_request["comment"]


def test_original_basket_does_not_recognize_m30():
    from application.model23_basket_accumulator import model23_position_matches
    assert not model23_position_matches(SimpleNamespace(comment="TraderIA M30 S8 P42",magic=MODEL_30_MAGIC))


def test_original_submit_triggers_only_one_real_provider_clone(tmp_path, monkeypatch):
    import application.model30_learning as module
    store=LearningStore(tmp_path/"x.sqlite3")
    monkeypatch.setattr(module,"LearningStore",lambda:store)
    monkeypatch.setattr(module,"enabled",lambda *a:True)
    monkeypatch.setattr(module,"risk_ready",lambda *a:True)
    monkeypatch.delenv("PYTEST_CURRENT_TEST")
    native=_FakeMT5()
    native.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING=2
    native.account_info=lambda:SimpleNamespace(trade_mode=0,margin_mode=2,login=1,server="demo",currency="USD",trade_allowed=True,trade_expert=True)
    def send(request):
        native.requests.append(request)
        native.last_request=request
        return SimpleNamespace(retcode=10009,order=700+len(native.requests),price=request.get("price",100),comment="Done")
    native.order_send=send
    p=MT5DemoExecutionProvider(mt5=native,log_path=tmp_path/"orders.jsonl")
    original=replace(order(),operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M1",
        plan_snapshot={"symbol":"XAUUSD","direction":"BUY","candle_time":"2026-09-24T10:00:00",
          "stop_management_parameters":{"source_operational_model":"MODELO_1_ALPHA_ATUAL","active_entry_order_type":"MARKET","m23_entry_type":"INITIAL","m23_structural_target_enabled":True}})
    result=p.submit_order(original)
    assert result.accepted,result.message
    assert len(native.requests)==2,getattr(p,"_m30_last_error", "")
    assert "M23" in native.requests[0]["comment"]
    assert "M30" in native.requests[1]["comment"]
    assert native.requests[1]["sl"]==native.requests[0]["sl"]
    assert native.requests[1]["tp"]==native.requests[0]["tp"]
    assert result.ticket==701
