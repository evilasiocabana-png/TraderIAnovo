import json
from dataclasses import replace
from types import SimpleNamespace as NS
import pytest
from application.gold_mirror_reinforcement import mirror_plan,protect_request,original_confirmation,EXIT_POLICY
from application.gold_reinforcement_filter import apply_filter,MIRROR_CONTEXTS
from application.source_channel_gate import parameters,order_error
from tests.test_model30_independent import Plan,Row,order,provider
from tests.test_model23_fixed_loss_stop import Broker

@pytest.mark.parametrize('side,stop,expected',[('BUY',90,'SELL'),('SELL',110,'BUY')])
def test_geometry_and_original_preserved(side,stop,expected):
 p=Plan(direction=side,stop=stop,stop_management_parameters={})
 result=mirror_plan(p,{})
 assert p.direction==side and result.direction==expected
 assert result.target==stop and abs(result.stop-100)==abs(stop-100)
 assert result.risk_reward==1 and result.stop_management==EXIT_POLICY
 assert result.stop_management_parameters['active_entry_order_type']=='MARKET'

@pytest.mark.parametrize('side',['BUY','SELL'])
@pytest.mark.parametrize('distance',[8.29,20,90])
def test_cap_and_symmetric_target(side,distance):
 o=replace(order(),side=side,quantity=.2)
 o.plan_snapshot['stop_management_parameters'].update(reinforcement_mode='ESPELHADO',reinforcement_exit_policy=EXIT_POLICY,reinforcement_risk_distance=distance)
 req=dict(price=4284.08,sl=4200,tp=4400,volume=.2)
 out,r=protect_request(NS(mt5=Broker()),o,req)
 risk=abs(r['price']-r['sl'])
 assert risk<=min(distance,20)+1e-8
 assert r['tp']==pytest.approx(2*r['price']-r['sl'])
 assert out.target==r['tp'] and out.stop==r['sl']
 if distance<20:assert risk==pytest.approx(distance)

@pytest.mark.parametrize('fail',[None,float('nan')])
def test_broker_failure_blocks(fail):
 o=order();o.plan_snapshot['stop_management_parameters'].update(reinforcement_mode='ESPELHADO',reinforcement_exit_policy=EXIT_POLICY,reinforcement_risk_distance=30)
 b=Broker();b.order_calc_profit=lambda *a:fail
 with pytest.raises(ValueError):protect_request(NS(mt5=b),o,dict(price=100,sl=90,tp=110,volume=.2))

@pytest.mark.parametrize('route',['MODELO_29_BASKET_ACCUMULATOR_SOURCE_M8','MODELO_30_ADAPTIVE_M23_SOURCE_M8','MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29'])
def test_source_gate_rejects_mirror_even_with_original(monkeypatch,route):
 from application import source_channel_gate as gate
 from application import gold_mirror_reinforcement as mirror
 state=apply_filter(dict(state='Alta',zone='Meio',reference='r',closed=5),8,'XAUUSD')
 o=replace(order(),operational_model=route,side='SELL',quantity=.3)
 p=o.plan_snapshot['stop_management_parameters'];p.update(parameters(state,8,'BUY'),reinforcement_mode='ESPELHADO',reinforcement_exit_policy=EXIT_POLICY,source_operational_model='MODELO_8_TEST',m23_m29_origin_source='M8')
 monkeypatch.setattr(gate,'reference_state',lambda *a:state)
 monkeypatch.setattr(mirror,'original_confirmation',lambda *a:dict(ticket=123,position=123))
 assert 'Espelhamento por faixa desativado' in order_error(provider(),o)
 assert 'reinforcement_original_ticket' not in p
 assert order_error(provider(),replace(o,side='BUY'))
 p.pop('reinforcement_exit_policy')
 assert order_error(provider(),o)

def fixture_original(tmp_path):
 o=replace(order(),side='SELL',quantity=.3)
 o.plan_snapshot.update(candle_time='2026-10-01 10:00',timeframe='M5')
 p=o.plan_snapshot['stop_management_parameters'];p.update(reinforcement_mode='ESPELHADO',reinforcement_exit_policy=EXIT_POLICY,reinforcement_source=8,reinforcement_original_direction='BUY',source_entry_setup='REENTRY')
 record=dict(accepted=True,execution_account_mode='DEMO',observed_account_login=123,observed_account_server='Demo',operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M8',symbol='XAUUSD',side='BUY',ticket=456,plan_snapshot=dict(candle_time='2026-10-01 10:00',timeframe='M5',stop_management_parameters=dict(source_entry_setup='REENTRY')))
 path=tmp_path/'log';path.write_text(json.dumps(record))
 position=NS(identifier=789,symbol='XAUUSD',magic=42,comment='TraderIA M23 S8 REENTRY',type=0)
 native=NS(state=4,position_id=789)
 broker=NS(account_info=lambda:NS(login=123,server='Demo',trade_mode=0),ACCOUNT_TRADE_MODE_DEMO=0,ORDER_STATE_FILLED=4,positions_get=lambda:[position],history_orders_get=lambda **k:[native])
 return NS(mt5=broker,magic=42,log_path=path),o,native,position,record

def test_original_must_be_filled_same_source_signal_and_account(tmp_path):
 p,o,native,pos,record=fixture_original(tmp_path)
 assert original_confirmation(p,o)==dict(ticket=456,position=789)
 native.state=1
 with pytest.raises(ValueError):original_confirmation(p,o)
 native.state=4;pos.comment='TraderIA M23 S18'
 with pytest.raises(ValueError):original_confirmation(p,o)
 pos.comment='TraderIA M23 S8 REENTRY';record['plan_snapshot']['candle_time']='old';p.log_path.write_text(json.dumps(record))
 with pytest.raises(ValueError):original_confirmation(p,o)

def test_m30_variant_has_own_exit_and_mirror_geometry():
 from application.model30_independent import variant
 st=dict(apply_filter(dict(state='Alta',zone='Meio',reference='r'),8,'XAUUSD'),mode='ESPELHADO',blocked=False)
 source_row=Row();source_row.pair='XAUUSD'
 model,row,plan=variant(source_row,Plan(stop_management_parameters={}), 'MODELO_8_TEST',st,.1)
 assert plan.direction=='SELL' and plan.target==90 and plan.stop==110
 assert plan.stop_management_parameters['m30_mode']=='ESPELHADO'
 assert plan.stop_management_parameters['m30_execution_volume']==.3

def test_original_and_normal_requests_unchanged():
 o=order();req=dict(price=100,sl=90,tp=125,volume=.1)
 assert protect_request(None,o,req)==(o,req)

def test_mirror_has_no_rsi_or_trailing_exit():
 from application.position_manager_service import PositionManagerService,PositionTradePlan
 p=PositionTradePlan(symbol='XAUUSD',side='SELL',entry=100,stop=120,target=80,stop_management='SOURCE_RSI',stop_management_parameters=dict(reinforcement_mode='ESPELHADO',reinforcement_exit_policy=EXIT_POLICY),operational_model='MODELO_18_XAU_M5_SMA_RSI_REENTRY_TP75')
 service=object.__new__(PositionManagerService)
 decision=service._decide(p,NS(ticket=42,evidence=()))
 assert decision.action=='HOLD' and not decision.allowed_to_execute
 assert decision.requested_stop is None and decision.requested_target is None

def test_report_exposes_mirror_without_changing_entry_channel():
 from application.report_entry_channel import entry_channel_columns
 out=entry_channel_columns(NS(plan_snapshot=dict(stop_management_parameters=dict(reinforcement_source=8,reinforcement_state='Transicao',reinforcement_mode='ESPELHADO'))))
 assert out['Modo do reforço']=='Espelhado' and out['Canal na entrada']=='Transição'

@pytest.mark.parametrize('side',['BUY','SELL'])
def test_provider_blocks_withdrawn_mirrors_before_send(tmp_path,monkeypatch,side):
 from tests import test_mt5_demo_execution_provider as h
 from application import source_channel_gate as gate,gold_mirror_reinforcement as mirror
 from application.model23_m29_copy import COPY_ID
 b=h._FakeMT5();b.profit_scale=100
 prov=h.MT5DemoExecutionProviderTest()._provider(b)
 st=dict(apply_filter(dict(state='Alta',zone='Meio',reference='r'),8,'XAUUSD'),mode='ESPELHADO',blocked=False)
 original='BUY' if side=='SELL' else 'SELL'
 p=dict(parameters(st,8,original),reinforcement_exit_policy=EXIT_POLICY,reinforcement_risk_distance=100,
        m23_m29_mode='ESPELHADO',m29_m8_mode='ESPELHADO',m29_mirrored=True,
        m23_m29_origin_source='M8',m23_m29_admission='VALIDATED_SIGNAL',source_operational_model='MODELO_29_BASKET_ACCUMULATOR',active_entry_order_type='MARKET')
 o=replace(h.MT5DemoExecutionProviderTest()._order(),symbol='XAUUSD',quantity=.3,operational_model=COPY_ID,side=side,entry_price=100,stop=10 if side=='BUY' else 190,target=190 if side=='BUY' else 10,plan_snapshot=dict(stop_management_parameters=p))
 monkeypatch.setattr(gate,'reference_state',lambda *a:st)
 monkeypatch.setattr(mirror,'original_confirmation',lambda *a:dict(ticket=123,position=123))
 result=prov.submit_order(o)
 assert not result.accepted
 assert 'Espelhamento por faixa desativado' in result.message
 assert not b.last_request
