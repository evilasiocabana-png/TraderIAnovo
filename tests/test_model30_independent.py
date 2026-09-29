import random
from dataclasses import dataclass, replace
from types import SimpleNamespace
import pytest
from application.model30_independent import floor_state, variant, POLICY, submit, preflight, reference_state, tables
from application.learning_store import LearningStore, encoded
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult


def rows(values):
    return [dict(id=str(i),net=v,time=i) for i,v in enumerate(values)]


def test_start_normal_and_no_floor_without_confirmed_rising_channel():
    for values in ([], [100]*20, [-100]*20, [100,-100]*10):
        state=floor_state(rows(values))
        assert state['mode']=='NORMAL' and not state['events']


def test_below_floor_holds_mirror_until_reentry():
    base=[100,-100,200,-100,200,-100]
    before=floor_state(rows(base))
    assert before['channel'] and before['mode']=='NORMAL'
    one=floor_state(rows(base+[0]))
    two=floor_state(rows(base+[0,0]))
    assert one['mode']=='ESPELHADO' and two['mode']=='ESPELHADO'
    assert len(two['events'])==1
    assert floor_state(rows(base+[0,0,500]))['mode']=='NORMAL'
    assert floor_state(rows(base+[0,0])+rows(base+[0,0])) == two


def test_above_roof_does_not_toggle_and_prefix_is_causal():
    values=[100,-100,200,-100,200,-100,10000]
    assert floor_state(rows(values))['mode']=='NORMAL'
    rng=random.Random(8)
    values += [rng.choice([-200,0,100,500]) for _ in range(80)]
    full=floor_state(rows(values))
    for n in range(len(values)+1):
        assert floor_state(rows(values[:n]))['events']==[e for e in full['events'] if e['operation']<=n]


@dataclass
class Plan:
    direction:str='BUY'
    entry_price:float=100
    stop:float=90
    target:float=125
    risk_reward:float=2.5
    stop_management_parameters:dict=None
    stop_management:str='FIXED'
    exit_model:str='SOURCE'

@dataclass
class Row:
    decision:str='BUY'
    theoretical_entry_direction:str='BUY'
    active_model:str='source'


@pytest.mark.parametrize('side,stop,target,mirrored', [('BUY',90,125,'SELL'),('SELL',110,75,'BUY')])
def test_independent_m7_geometry_and_source_unchanged(side,stop,target,mirrored):
    plan=Plan(side,100,stop,target,2.5,{})
    original=repr(plan)
    state=dict(mode='ESPELHADO',reference='x')
    model,row,new=variant(Row(),plan,'MODELO_7_TEST',state,.1)
    assert model.endswith('SOURCE_M7') and new.direction==mirrored
    assert new.target==stop and new.stop==200-stop
    assert new.stop_management_parameters['m30_execution_volume']==.1
    assert repr(plan)==original
    assert variant(Row(),plan,'MODELO_18_TEST',state,.1)[2].direction==side


def provider():
    account=SimpleNamespace(login=1,server='demo',trade_mode=0,margin_mode=2)
    return SimpleNamespace(mt5=SimpleNamespace(account_info=lambda:account,ACCOUNT_TRADE_MODE_DEMO=0,
        ACCOUNT_MARGIN_MODE_RETAIL_HEDGING=2, positions_get=lambda:[],orders_get=lambda:[]),
        execution_account=SimpleNamespace(mode='DEMO'),_write_log=lambda *a:None,
        _external_mt5_read=lambda *a,**k:dict(ok=True,account=vars(account),rows=[],open_positions=[]))


def order(source='M7'):
    p=dict(m30_policy=POLICY,source_operational_model='MODELO_'+source[1:]+'_TEST',
        m30_mode='NORMAL',m30_reference=floor_state([])['reference'],m30_execution_volume=.1,
        m30_effective_stop=90,m30_effective_target=110,source_entry_setup='entry')
    return ExecutionOrder('BUY',.1,100,90,110,symbol='XAUUSD',operational_model='MODELO_30_ADAPTIVE_M23_SOURCE_'+source,
        plan_snapshot=dict(symbol='XAUUSD',direction='BUY',candle_time='2026-09-29T10:00:00',timeframe='H1',stop_management_parameters=p))


def test_independent_submission_without_m23_and_dedup_restart(tmp_path):
    store=LearningStore(tmp_path/'db');p=provider();o=order();sent=[]
    def send(p,o):
        assert preflight(p,o,store)==''
        sent.append(o)
        return ExecutionResult(True,'ACCEPTED','ok',123)
    assert submit(send,p,o,store).accepted
    assert not submit(send,p,o,LearningStore(store.path)).accepted
    assert len(sent)==1


@pytest.mark.parametrize('trade,margin,mode',[(2,2,'DEMO'),(0,0,'DEMO'),(0,2,'REAL')])
def test_no_real_or_netting(tmp_path,trade,margin,mode):
    store=LearningStore(tmp_path/'db');p=provider()
    p.mt5.account_info().trade_mode=trade;p.mt5.account_info().margin_mode=margin;p.execution_account.mode=mode
    assert not submit(lambda *a:pytest.fail('must not send'),p,order(),store).accepted


def test_uncertain_send_never_retries(tmp_path):
    store=LearningStore(tmp_path/'db');p=provider();sent=[]
    def fail(*a):
        sent.append(1);raise TimeoutError()
    assert not submit(fail,p,order(),store).accepted
    assert not submit(fail,p,order(),store).accepted
    assert sent==[1]


def test_mode_change_not_retried_as_new_source_signal(tmp_path):
    store=LearningStore(tmp_path/'db');p=provider();o=order('M18')
    assert submit(lambda *a:ExecutionResult(True,'ACCEPTED','ok',123),p,o,store).accepted
    changed=replace(o,side='SELL')
    assert not submit(lambda *a:pytest.fail('duplicate'),p,changed,store).accepted


def test_acceptance_of_m23_no_longer_clones(monkeypatch):
    from application.model30_learning import paired_submit
    import application.model30_learning as old
    monkeypatch.setattr(old,'submit_pair',lambda *a:pytest.fail('legacy copy'))
    p=provider();o=replace(order(),operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7')
    assert paired_submit(lambda *a:ExecutionResult(True,'ACCEPTED','ok',1))(p,o).accepted


def test_reference_rejects_wrong_account_or_failed_read(tmp_path):
    p=provider();store=LearningStore(tmp_path/'db')
    p._external_mt5_read=lambda *a,**k:dict(ok=True,account=dict(login=2,server='demo',trade_mode=0))
    with pytest.raises(ValueError):reference_state(p,'XAUUSD',store)
    p._external_mt5_read=lambda *a,**k:dict(ok=False)
    with pytest.raises(ValueError):reference_state(p,'XAUUSD',store)


def test_native_reference_only_closed_original_m23_not_m29_or_copies(tmp_path):
    p=provider();store=LearningStore(tmp_path/'db');deals=[]
    for position,comment in [(1,'TraderIA M23 S7'),(2,'TraderIA M29 S7'),(3,'TraderIA M23 S29'),(4,'TraderIA M23 S7')]:
        for entry in [0,1]:
            deals.append(dict(ticket=position*10+entry,position_id=position,entry=entry,type=entry,
                comment=comment,symbol='XAUUSD',volume=.1,profit=100*entry,commission=-1,swap=0,fee=0,time=position*10+entry))
    p._external_mt5_read=lambda *a,**k:dict(ok=True,account=vars(p.mt5.account_info()),rows=deals+deals,
        open_positions=[dict(identifier=4)])
    result=reference_state(p,'XAUUSD',store)
    assert result['closed']==1 and result['reference']==floor_state([dict(id='1',net=98.,time=11000)])['reference']
    p._external_mt5_read=lambda *a,**k:dict(ok=True,account=vars(p.mt5.account_info()),rows=[],open_positions=[])
    with pytest.raises(ValueError,match='incompleto'):reference_state(p,'XAUUSD',store)


def test_falling_channel_mirrors():
    assert floor_state(rows([-100,100,-200,100,-200,100]))['mode']=='ESPELHADO'


def test_sources_match_current_m23_without_derived_m29():
    import re
    from application.dashboard_service import MT5_MODEL_23_SOURCE_MODEL_IDS
    from application.model30_independent import SOURCES
    assert SOURCES=={'M'+re.search(r'MODELO_(\d+)',m)[1] for m in MT5_MODEL_23_SOURCE_MODEL_IDS}


@pytest.mark.parametrize('number',[18,20])
def test_source_route_does_not_consult_m23_acceptance(tmp_path,monkeypatch,number):
    from tests.test_model23_context_integration import setup_service
    import application.dashboard_service as module
    service,row,plan=setup_service(tmp_path,monkeypatch)
    monkeypatch.setattr(module.DashboardService,'_mt5_model23_variant_from_source',lambda *a,**k:pytest.fail('M23 dependency'))
    source=getattr(module,'MT5_OPERATIONAL_MODEL_'+str(number))
    result=service._mt5_model30_variant_from_source(row,plan,source_operational_model=source)
    assert result is not None
    model,_,new=result
    assert model.endswith('SOURCE_M'+str(number))
    assert (new.direction,new.entry_price,new.stop,new.target)==(plan.direction,plan.entry_price,plan.stop,plan.target)
    assert new.stop_management_parameters['m30_mode']=='NORMAL'


def test_online_m23_closing_does_not_block_independent_m30(tmp_path,monkeypatch):
    from tests.test_model23_context_integration import setup_service
    import application.dashboard_service as module
    service,_,_=setup_service(tmp_path,monkeypatch)
    object.__setattr__(service.mt5_demo_robot_service,'enabled',True)
    for name,fn in {
        '_mt5_demo_execution_enabled':lambda *a:True,
        '_enable_mt5_demo_provider':lambda *a:None,
        '_evaluate_model23_risk_gate':lambda *a:'M23_CLOSING',
        '_evaluate_model29_risk_gate':lambda *a:None,
        '_evaluate_model24_risk_gate':lambda *a:None,
        '_evaluate_model25_risk_gate':lambda *a:None,
        '_mt5_model29_routing_enabled':lambda *a:False,
        'load_mt5_forex_signals':lambda *a,**k:None,
        'run_demo_robot_for_all':lambda *a,**k:'M30_CONTINUES',
    }.items():monkeypatch.setattr(module.DashboardService,name,fn)
    monkeypatch.setattr('application.model30_learning.enabled',lambda *a:True)
    assert service.run_online_demo_robot_cycle()=='M30_CONTINUES'
