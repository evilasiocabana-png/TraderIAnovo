from dataclasses import replace
import pytest
from application import source_channel_gate as gate
from tests.test_model30_independent import provider, order, rows, Plan, Row
from application.model30_independent import variant

@pytest.mark.parametrize("values,blocked", [([],False),([100,-100,200,-100,200,-100],False),([-100,100,-200,100,-200,100],True),([-100,100,-200,100,-200,100,1000],False),([100,-100]*8,False)])
def test_only_confirmed_downtrend_blocks(values,blocked):
    state=gate.channel_state(rows(values))
    assert state['blocked'] is blocked and state['mode']=='NORMAL'

@pytest.mark.parametrize('source',sorted(gate.SOURCES))
@pytest.mark.parametrize('side', ['BUY','SELL'])
def test_all_sources_preserve_original_geometry_and_volume(source,side):
    plan=Plan(side,100,90 if side=='BUY' else 110,125 if side=='BUY' else 75,2.5,{})
    state=gate.channel_state([])
    _,_,new=variant(Row(),plan,f'MODELO_{source}_TEST',state,.1)
    assert (new.direction,new.stop,new.target,new.risk_reward)==(plan.direction,plan.stop,plan.target,plan.risk_reward)
    assert new.stop_management_parameters['m30_execution_volume']==.1
    with pytest.raises(ValueError):variant(Row(),plan,f'MODELO_{source}_TEST',{**state,'blocked':True},.1)

def deals(position,source='M7',symbol='XAUUSD'):
    return [dict(ticket=position*10+e,position_id=position,entry=e,type=e,comment='TraderIA M23 S'+source[1:],symbol=symbol,volume=.1,profit=100*e,commission=-1,swap=-2*e,fee=-.5,time=position*10+e) for e in (0,1)]

def test_reference_is_source_asset_closed_and_net():
    original=deals(1)
    payload=dict(rows=original+original+deals(2,'M18')+deals(3,symbol='BTCUSD')+deals(4,'M29')+deals(5),open_positions=[dict(identifier=5)])
    assert gate.reconciled_results(payload,7,'XAUUSD')==[dict(id='1',net=95.,time=11000)]
    assert [r['id'] for r in gate.reconciled_results(payload,18,'XAUUSD')]==['2']

@pytest.mark.parametrize('failure',['volume','cost','nan','missing_exit'])
def test_incomplete_reference_fails_closed(failure):
    ds=deals(1)
    if failure=='volume': ds[1]['volume']=.05
    elif failure=='cost':ds[0].pop('fee')
    elif failure=='nan':ds[1]['profit']=float('nan')
    else:ds.pop()
    with pytest.raises(ValueError):gate.reconciled_results(dict(rows=ds),7,'XAUUSD')

@pytest.mark.parametrize('model',['MODELO_29_BASKET_ACCUMULATOR_SOURCE_M7','MODELO_30_ADAPTIVE_M23_SOURCE_M7','MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29'])
def test_final_gate_rechecks_all_routes_without_affecting_original(monkeypatch,model):
    state=gate.channel_state([]);o=order();p=o.plan_snapshot['stop_management_parameters']
    p.update(gate.parameters(state,7,'BUY'));p.update(m23_m29_origin_source='M7')
    o=replace(o,operational_model=model,quantity=.2)
    monkeypatch.setattr(gate,'reference_state',lambda *a,**k:state)
    assert gate.order_error(provider(),o) is None
    state['blocked']=True
    assert 'baixa' in gate.order_error(provider(),o)
    original=replace(o,operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7')
    assert gate.order_error(provider(),original) is None
    state['blocked']=False;p['reinforcement_reference']='stale'
    assert 'mudou' in gate.order_error(provider(),o)
    p['reinforcement_reference']=state['reference'];p['reinforcement_source']=18
    assert 'fonte' in gate.order_error(provider(),o)

def test_failed_read_and_cached_mirror_never_send(monkeypatch):
    o=replace(order(),quantity=.2);p=o.plan_snapshot['stop_management_parameters'];state=gate.channel_state([])
    p.update(gate.parameters(state,7,'BUY'))
    monkeypatch.setattr(gate,'reference_state',lambda *a,**k:(_ for _ in ()).throw(RuntimeError('offline')))
    assert 'indisponivel' in gate.order_error(provider(),o)
    p['m30_mode']='ESPELHADO'
    assert 'Espelhamento desativado' in gate.order_error(provider(),o)

def test_m29_waits_but_original_plan_is_unchanged(tmp_path,monkeypatch):
    from tests.test_model23_context_integration import setup_service
    service,row,plan=setup_service(tmp_path,monkeypatch);before=repr(plan)
    monkeypatch.setattr(gate,'reference_state',lambda *a,**k:{**gate.channel_state([]),'blocked':True})
    _,waiting=service._apply_model29_m7_mode(row,plan,'M18')
    assert waiting.direction=='WAIT' and repr(plan)==before
    monkeypatch.setattr(gate,'reference_state',lambda *a,**k:gate.channel_state([]))
    _,normal=service._apply_model29_m7_mode(row,plan,'M18')
    assert (normal.direction,normal.stop,normal.target)==(plan.direction,plan.stop,plan.target)
