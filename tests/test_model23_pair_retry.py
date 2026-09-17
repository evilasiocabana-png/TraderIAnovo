from dataclasses import replace
from types import SimpleNamespace
import pytest
from application.model29_entry_sync import RejectedGoldCopyRetry
from application.model23_m29_copy import copy_m29_signal
from tests.test_model29_entry_sync import plan, result

def context(tmp_path):
    row=SimpleNamespace()
    # Lineage fields match the normal builder, without a UI dependency.
    base=plan(True)
    p=replace(base,stop_management_parameters={**base.stop_management_parameters,
        "source_operational_model":"MODELO_29_BASKET_ACCUMULATOR",
        "m23_m29_origin_source":"M7", "m23_m29_pair_original_ticket":"123",
        "m23_m29_mode":"ESPELHADO", "execution_volume":0.2})
    snapshot=dict(ok=True,account=dict(login=1,server="TEST"),open_positions=[
        dict(ticket=123,identifier=123,symbol="XAUUSD",comment="TraderIA M23 S7 TEST")])
    provider=SimpleNamespace(_external_mt5_read=lambda *a,**k:snapshot)
    return RejectedGoldCopyRetry(tmp_path),provider,p,snapshot

def test_retry_survives_restart_and_is_consumed_before_dispatch(tmp_path):
    retry,provider,p,snapshot=context(tmp_path)
    retry.remember(provider,p,"one",result("REJECTED",False))
    restarted=RejectedGoldCopyRetry(tmp_path)
    assert restarted.claim(provider,p,"one")=="123"
    assert restarted.claim(provider,p,"one") is None

@pytest.mark.parametrize("change",["closed","copy_open","candle","mode","size","invalid","account","unknown"])
def test_no_retry_without_same_valid_plan_and_open_original(tmp_path,change):
    retry,provider,p,snapshot=context(tmp_path)
    retry.remember(provider,p,"one",result("REJECTED",False))
    candle="one"
    if change=="closed": snapshot["open_positions"]=[]
    elif change=="copy_open": snapshot["open_positions"].append(dict(ticket=456,symbol="XAUUSD",comment="TraderIA M23 S29 M7 TEST"))
    elif change=="candle": candle="two"
    elif change=="invalid": p=replace(p,status="WAIT")
    elif change=="account": snapshot["account"]["login"]=2
    elif change=="unknown": snapshot["ok"]=False
    else:
        field="execution_volume" if change=="size" else "m23_m29_mode"
        p=replace(p,stop_management_parameters={**p.stop_management_parameters,field:0.1 if change=="size" else "NORMAL"})
    if change=="unknown":
        with pytest.raises(RuntimeError):retry.claim(provider,p,candle)
    else: assert retry.claim(provider,p,candle) is None

@pytest.mark.parametrize("state",["ACCEPTED","ERROR","TIMEOUT"])
def test_uncertain_or_accepted_result_never_creates_retry(tmp_path,state):
    retry,provider,p,snapshot=context(tmp_path)
    outcome=result("REJECTED",False)
    outcome.execution_result.status=state
    retry.remember(provider,p,"one",outcome)
    assert retry.claim(provider,p,"one") is None


def test_executor_allows_rejected_pair_same_candle_but_consumes_acceptance(tmp_path,monkeypatch):
    from application.demo_execution_service import DemoExecutionService
    from application.mt5_demo_robot_service import MT5DemoRobotService
    from tests.test_mt5_demo_robot_service import MT5DemoRobotServiceTest, _AcceptingProvider
    from domain.contracts.execution_result import ExecutionResult
    monkeypatch.chdir(tmp_path)
    h=MT5DemoRobotServiceTest()
    signal=replace(h._signal("BUY"), operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29")
    trade=replace(h._plan("BUY"), stop_management_parameters={"source_operational_model":"MODELO_29_BASKET_ACCUMULATOR", "m23_m29_origin_source":"M7", "m23_m29_pair_original_ticket":"123"})
    execution=DemoExecutionService(provider=_AcceptingProvider())
    outcomes=iter([ExecutionResult(False,"REJECTED","Mercado fechado"),ExecutionResult(True,"ACCEPTED","OK",ticket=456)])
    monkeypatch.setattr(execution,"submit_demo_order",lambda *a,**k:next(outcomes))
    robot=MT5DemoRobotService(execution_service=execution,enabled=True)
    assert robot.evaluate_once(signal,trade).status=="REJECTED"
    assert robot.evaluate_once(signal,trade).status=="EXECUTED"
    assert robot.evaluate_once(signal,trade).status=="NO_NEW_CANDLE"

@pytest.mark.parametrize("state",["open","closed","unavailable","wrong_source"])
def test_provider_rechecks_original_at_admission(state):
    from tests import test_mt5_demo_execution_provider as h
    helper=h.MT5DemoExecutionProviderTest(); native=h._FakeMT5(); provider=helper._provider(native)
    order=replace(helper._order(),operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29",
        plan_snapshot={"stop_management_parameters":{"m23_m29_pair_original_ticket":"123"}})
    native.positions_get=lambda: None if state=="unavailable" else [] if state=="closed" else [SimpleNamespace(
        ticket=123,identifier=123,symbol="XAUUSD",comment="TraderIA M23 S7 TEST" if state=="open" else "TraderIA M29 S7 TEST")]
    outcome=provider._model23_copy_pair_preflight(order)
    assert (outcome is None)==(state=="open")
