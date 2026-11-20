from dataclasses import replace
from types import SimpleNamespace
import pytest
from application.model23_m29_copy import COPY_ID, copy_confirmed_m29, copy_order_error
from application.model23_basket_accumulator import model23_entry_type, model23_variant_id
from application.model29_basket_accumulator import MODEL_29_ID
from application.model29_entry_sync import is_gold_m7, GoldM7EntrySync
from application.mt5_demo_robot_service import MT5DemoRobotService
from tests.test_model23_context_integration import setup_service
from tests.test_model29_entry_sync import result
from tests import test_mt5_demo_execution_provider as helpers

@pytest.mark.parametrize('mode,volume', [('NORMAL',0.1),('ESPELHADO',0.2)])
def test_copy_preserves_plan_volume_and_isolates_source(tmp_path,monkeypatch,mode,volume):
    service,row,plan=setup_service(tmp_path,monkeypatch)
    plan=replace(plan,stop_management_parameters={'source_operational_model':'MODELO_7_LAB_XAU_BTC','m29_m7_mode':mode,'m29_entry_type':'TREND','active_entry_order_type':'MARKET'})
    model,cr,cp=copy_confirmed_m29(MODEL_29_ID+'_SOURCE_M7',row,plan,result())
    assert model==COPY_ID==model23_variant_id(MODEL_29_ID)
    assert (cp.direction,cp.entry_price,cp.stop,cp.target)==(plan.direction,plan.entry_price,plan.stop,plan.target)
    assert cp.stop_management_parameters['execution_volume']==volume
    assert not is_gold_m7(cp)
    assert plan.stop_management_parameters['source_operational_model']=='MODELO_7_LAB_XAU_BTC'
    assert copy_confirmed_m29(model,cr,cp,result()) is None
    signal=SimpleNamespace(operational_model=COPY_ID)
    assert MT5DemoRobotService._execution_volume(None,signal,cp)==volume
    robot_plan=service._to_mt5_demo_trade_plan(cr,cp,operational_model=COPY_ID)
    assert robot_plan.stop==cp.stop
    helper=helpers.MT5DemoExecutionProviderTest();native=helpers._FakeMT5();provider=helper._provider(native)
    order=replace(helper._order(),symbol='XAUUSD',quantity=volume,operational_model=model,
        side=cp.direction,entry_price=cp.entry_price,stop=cp.stop,target=cp.target,
        plan_snapshot={'stop_management_parameters':cp.stop_management_parameters})
    assert copy_order_error(order) is None
    from application.source_channel_gate import channel_state, parameters
    cp.stop_management_parameters.update(parameters(channel_state([]),7,cp.direction))
    cp.stop_management_parameters["execution_volume"]=.2
    cp.stop_management_parameters["reinforcement_filter_version"]="M29_ALL_ASSETS_UP_BREAKOUT_LATCH_V3"
    order=replace(order,quantity=.2)
    monkeypatch.setattr('application.source_channel_gate.reference_state',lambda *a,**k:channel_state([]))
    sent=provider.submit_order(order)
    if mode == 'ESPELHADO':
        assert not sent.accepted and 'Espelhamento desativado' in sent.message
        return
    assert sent.accepted,sent.message
    assert 'M23 S29' in native.last_request['comment']
    assert native.last_request['volume']==.2
    assert copy_order_error(replace(order,quantity=0.3))

@pytest.mark.parametrize('outcome',[result('REJECTED',False),result('WAITING'),result(ticket=None)])
def test_no_copy_without_confirmed_parent(tmp_path,monkeypatch,outcome):
    _,row,plan=setup_service(tmp_path,monkeypatch)
    assert copy_confirmed_m29(MODEL_29_ID+'_SOURCE_M7',row,plan,outcome) is None

def test_distinct_parent_sources_and_non_gold(tmp_path,monkeypatch):
    _,row,plan=setup_service(tmp_path,monkeypatch)
    plan=replace(plan,stop_management_parameters={'m29_entry_type':'REENTRY','active_entry_order_type':'BUY_STOP'})
    for source in ('M3','M4','M6','M21','M22'):
        assert copy_confirmed_m29(MODEL_29_ID+'_SOURCE_'+source,row,plan,result()) is None
        helper = helpers.MT5DemoExecutionProviderTest()
        order = replace(helper._order(), symbol='XAUUSD', quantity=0.1,
            operational_model=COPY_ID, plan_snapshot={'stop_management_parameters': {
                'm23_m29_mode': 'NORMAL', 'm23_m29_origin_source': source,
                'm23_m29_admission': 'VALIDATED_SIGNAL'}})
        assert copy_order_error(order)
    assert copy_confirmed_m29(MODEL_29_ID+'_SOURCE_M7',row,replace(plan,symbol='BTCUSD'),result()) is not None


@pytest.mark.parametrize('source', ['M1','M2','M5','M8','M10','M18','M20'])
def test_restored_sources_copy_normally_without_m7_mode(tmp_path, monkeypatch, source):
    _, row, plan = setup_service(tmp_path, monkeypatch)
    plan = replace(plan, stop_management_parameters={'m29_entry_type':'TREND', 'm29_m7_mode':'ESPELHADO'})
    model, _, copied = copy_confirmed_m29(MODEL_29_ID+'_SOURCE_'+source, row, plan, result())
    p = copied.stop_management_parameters
    assert p['m23_m29_origin_source'] == source
    assert p['m23_m29_mode'] == 'NORMAL'
    assert p['execution_volume'] == 0.1
    assert (copied.direction,copied.stop,copied.target) == (plan.direction,plan.stop,plan.target)
    helper = helpers.MT5DemoExecutionProviderTest()
    order = replace(helper._order(), symbol='XAUUSD', quantity=0.1, operational_model=model,
        plan_snapshot={'stop_management_parameters':p})
    assert copy_order_error(order) is None
    bad = replace(order, quantity=0.2, plan_snapshot={'stop_management_parameters':{**p,'m23_m29_mode':'ESPELHADO'}})
    assert copy_order_error(bad)
