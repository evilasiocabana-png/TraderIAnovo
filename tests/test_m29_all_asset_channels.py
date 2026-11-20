from dataclasses import replace
import pytest
from application import source_channel_gate as gate
from application.gold_reinforcement_filter import apply_filter
from tests.test_model30_independent import provider, order

@pytest.mark.parametrize('symbol',['XAUUSD','EURUSD','USDJPY','BTCUSD'])
@pytest.mark.parametrize('source',sorted(gate.SOURCES))
@pytest.mark.parametrize('state,allowed',[('Alta',True),('Transicao',False),('Lateral',False),('Baixa',False),('Formacao',False)])
def test_m29_all_assets_by_source(symbol,source,state,allowed):
    result=gate.m29_filter(dict(state=state,channel={'trend':'Alta'},zone='Acima do teto',reference='test'),source,symbol)
    assert result['blocked'] is not allowed
    assert gate.entry_volume(gate.parameters(result,source,'BUY'),symbol,.1,route='M29')==.2
    assert gate.m29_filter(dict(state=state,channel=None),source,symbol)['blocked']

@pytest.mark.parametrize('model',['MODELO_29_BASKET_ACCUMULATOR_SOURCE_M18','MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29'])
@pytest.mark.parametrize('symbol',['XAUUSD','EURUSD'])
@pytest.mark.parametrize('side',['BUY','SELL'])
def test_guard_routes_and_rejects_old_lot(monkeypatch,model,symbol,side):
    state=gate.m29_filter(dict(state='Alta',channel={'trend':'Alta'},reference='current'),18,symbol)
    o=replace(order(),operational_model=model,symbol=symbol,side=side,quantity=.2)
    p=o.plan_snapshot['stop_management_parameters']
    p.update(gate.parameters(state,18,side),source_operational_model='MODELO_18_TEST',m23_m29_origin_source='M18')
    calls=[]
    monkeypatch.setattr(gate,'reference_state',lambda *a,**kw:(calls.append(kw['route']) or state))
    assert gate.order_error(provider(),o) is None
    assert calls==['M29'] and gate.loss_limit(o)==300
    assert gate.order_error(provider(),replace(o,quantity=.3))
    state.update(gate.m29_filter({**state,'state':'Baixa'},18,symbol))
    assert gate.order_error(provider(),o)

def test_m30_stays_gold_six_filters():
    state=dict(state='Baixa',channel={'trend':'Baixa'},zone='Meio')
    assert not apply_filter(state,18,'XAUUSD')['blocked']
    assert gate.m29_filter(state,18,'XAUUSD')['blocked']
    assert apply_filter(state,18,'EURUSD')['blocked']
    assert gate.entry_volume({'reinforcement_policy':gate.POLICY},'XAUUSD',.1,route='M30')==.3

@pytest.mark.parametrize('trend',[None,'Baixa','Lateral','Transicao'])
def test_up_structure_requires_up_channel(trend):
    assert gate.m29_filter(dict(state='Alta',channel={'trend':trend}),8,'EURUSD')['blocked']

def test_previous_transition_policy_plan_is_rejected(monkeypatch):
    state=gate.m29_filter(dict(state='Alta',channel={'trend':'Alta'},reference='current'),18,'EURUSD')
    o=replace(order(),operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29',symbol='EURUSD',quantity=.2)
    p=o.plan_snapshot['stop_management_parameters']
    p.update(gate.parameters(state,18,'BUY'),m23_m29_origin_source='M18',reinforcement_filter_version='M29_ALL_ASSETS_UP_TRANSITION_V1')
    monkeypatch.setattr(gate,'reference_state',lambda *a,**kw:pytest.fail('Old plan must not proceed'))
    assert 'anterior' in gate.order_error(provider(),o)
