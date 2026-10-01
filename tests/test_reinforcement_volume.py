from dataclasses import replace
from types import SimpleNamespace as NS
import pytest
from application.source_channel_gate import POLICY,entry_volume,parameters,channel_state,order_error
from application.model30_independent import variant
from tests.test_model30_independent import Row,Plan,provider,order
from tests.test_model23_fixed_loss_stop import Broker,fixture
from application.model29_fixed_loss_stop import protected_request

@pytest.mark.parametrize('symbol,expected',[('XAUUSD',.2),('BTCUSD',.1),('EURJPY',.1)])
def test_volume_is_gold_only(symbol,expected):
    row=Row();row.pair=symbol
    _,_,p=variant(row,Plan(stop_management_parameters={}), 'MODELO_7_TEST',channel_state([]),.1)
    assert p.stop_management_parameters['m30_execution_volume']==expected
    assert entry_volume({},symbol,.1)==.1

@pytest.mark.parametrize('side',['BUY','SELL'])
@pytest.mark.parametrize('distance',[5,100])
def test_defense_at_double_volume_preserves_small_stop_and_caps_large(side,distance):
    o,request=fixture('M29',side,distance,.2)
    o.plan_snapshot=dict(stop_management_parameters=dict(reinforcement_policy=POLICY,m23_m29_origin_source='M18',m23_m29_mode='NORMAL'))
    result=protected_request(o,request,Broker())
    loss=-Broker().order_calc_profit(0 if side=='BUY' else 1,'XAUUSD',.2,result['price'],result['sl'])
    assert loss<=200.000001 and result['tp']==request['tp']
    if distance==5:assert result['sl']==request['sl']


def test_final_guard_rejects_cached_old_volume(monkeypatch):
    state=channel_state([]);o=order();o.plan_snapshot['stop_management_parameters'].update(parameters(state,7,'BUY'))
    monkeypatch.setattr('application.source_channel_gate.reference_state',lambda *a:state)
    assert '0.20' in order_error(provider(),o)
    assert order_error(provider(),replace(o,quantity=.2)) is None
    assert order_error(provider(),replace(o,operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7')) is None


def test_m29_copy_and_own_lot_and_original_m23(tmp_path,monkeypatch):
    from tests.test_model23_context_integration import setup_service
    from application.model23_m29_copy import copy_m29_signal,copy_order_error
    from application.mt5_demo_robot_service import MT5DemoRobotService
    service,row,plan=setup_service(tmp_path,monkeypatch)
    plan=replace(plan,stop_management_parameters={**parameters(channel_state([]),18,plan.direction),'m29_m18_mode':'NORMAL'})
    model,_,copied=copy_m29_signal('MODELO_29_BASKET_ACCUMULATOR_SOURCE_M18',row,plan)
    assert copied.stop_management_parameters['execution_volume']==.2
    assert copy_order_error(NS(operational_model=model,symbol='XAUUSD',quantity=.2,plan_snapshot={'stop_management_parameters':copied.stop_management_parameters})) is None
    assert MT5DemoRobotService._execution_volume(None,NS(operational_model='MODELO_29_BASKET_ACCUMULATOR_SOURCE_M18'),plan)==.2
    original=replace(plan,stop_management_parameters={})
    assert MT5DemoRobotService._execution_volume(NS(volume=.1),NS(operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M18'),original)==.1
