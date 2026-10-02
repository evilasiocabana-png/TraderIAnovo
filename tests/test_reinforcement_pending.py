import json
from types import SimpleNamespace as NS
import pytest
from application import reinforcement_pending as module
from application.source_channel_gate import POLICY,loss_limit


def setup(tmp_path,monkeypatch,route='M30',symbol='XAUUSD'):
    model={'M30':'MODELO_30_ADAPTIVE_M23_SOURCE_M7','M29':'MODELO_29_BASKET_ACCUMULATOR_SOURCE_M7','COPY':'MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29'}[route]
    comment={'M30':'TraderIA M30 S7 NOR','M29':'TraderIA M29 S7 TEST','COPY':'TraderIA M23 S29 M7 TEST'}[route]
    order=NS(ticket=123,type=4,magic=260630 if route=='M30' else 260629,symbol=symbol,comment=comment)
    record=dict(accepted=True,ticket=123,execution_account_mode='DEMO',observed_account_login=1,observed_account_server='demo',symbol=symbol,side='BUY',operational_model=model,plan_snapshot=dict(stop_management_parameters=dict(reinforcement_policy=POLICY,reinforcement_source=7)))
    path=tmp_path/'execution.jsonl';path.write_text(json.dumps(record)+'\n')
    sends=[];logs=[]
    p=NS(log_path=path,magic=260629,execution_account=NS(mode='DEMO'),_initialize_check=lambda:None,_demo_account_check=lambda:None,
         mt5=NS(account_info=lambda:NS(login=1,server='demo'),orders_get=lambda **kw:[order],TRADE_ACTION_REMOVE=8,TRADE_RETCODE_DONE=10009),
         _checked_order_send=lambda request:(sends.append(request) or NS(retcode=10009)),_write_management_log=logs.append)
    monkeypatch.setattr(module,'reference_state',lambda *a:dict(blocked=True))
    return p,order,record,sends,logs


@pytest.mark.parametrize('route',['M29','M30','COPY'])
@pytest.mark.parametrize('symbol',['XAUUSD','BTCUSD','EURJPY'])
def test_cancel_only_pending_on_downtrend(tmp_path,monkeypatch,route,symbol):
    p,o,r,sends,logs=setup(tmp_path,monkeypatch,route,symbol)
    result=module.cancel_downtrend_pending(p)
    assert result['cancelled']==1 and len(sends)==1
    assert sends[0]['action']==8 and sends[0]['order']==123
    assert logs[0]['accepted']


@pytest.mark.parametrize('problem',['normal','history_failure','filled','other_account','other_source','legacy','original','real','rejected'])
def test_protect_original_positions_and_failures(tmp_path,monkeypatch,problem):
    p,o,r,sends,logs=setup(tmp_path,monkeypatch)
    if problem=='normal':monkeypatch.setattr(module,'reference_state',lambda *a:dict(blocked=False))
    elif problem=='history_failure':monkeypatch.setattr(module,'reference_state',lambda *a:(_ for _ in ()).throw(RuntimeError('offline')))
    elif problem=='filled':p.mt5.orders_get=lambda **kw:[] if kw else [o]
    elif problem=='other_account':r['observed_account_login']=2
    elif problem=='other_source':o.comment='TraderIA M30 S18 NOR'
    elif problem=='legacy':r['plan_snapshot']['stop_management_parameters']['reinforcement_policy']='old'
    elif problem=='original':r['operational_model']='MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7';o.comment='TraderIA M23 S7 TEST'
    elif problem=='real':p.execution_account.mode='REAL'
    elif problem=='rejected':p._checked_order_send=lambda req:(sends.append(req) or NS(retcode=10013))
    p.log_path.write_text(json.dumps(r)+'\n')
    result=module.cancel_downtrend_pending(p)
    assert result['cancelled']==0
    assert len(sends)==(1 if problem=='rejected' else 0)


@pytest.mark.parametrize('model,symbol,quantity,limit',[
    ('MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7','XAUUSD',.1,200),
    ('MODELO_23_BASKET_ACCUMULATOR_SOURCE_M7','XAUUSD',.2,200),
    ('MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29','XAUUSD',.2,400),
    ('MODELO_29_BASKET_ACCUMULATOR_SOURCE_M7','XAUUSD',.2,400),
    ('MODELO_30_ADAPTIVE_M23_SOURCE_M7','XAUUSD',.2,400),
    ('MODELO_30_ADAPTIVE_M23_SOURCE_M7','BTCUSD',.1,200)])
def test_financial_limit_scope(model,symbol,quantity,limit):
    o=NS(operational_model=model,symbol=symbol,quantity=quantity,plan_snapshot=dict(stop_management_parameters=dict(reinforcement_policy=POLICY)))
    assert loss_limit(o)==limit


def test_m30_initializes_connection_before_account_check(tmp_path,monkeypatch):
    from tests.test_model30_independent import provider,order
    from application.model30_independent import submit
    from application.learning_store import LearningStore
    from domain.contracts.execution_result import ExecutionResult
    from application.source_channel_gate import channel_state
    monkeypatch.setattr("application.model30_independent.reference_state", lambda *a, **k: channel_state([]))
    p=provider();account=p.mt5.account_info();connected=[]
    p.mt5.account_info=lambda:account if connected else None
    p._initialize_check=lambda:(connected.append(True) or None)
    assert submit(lambda *a:ExecutionResult(True,'ACCEPTED','ok',1),p,order(),LearningStore(tmp_path/'db')).accepted
    assert connected==[True]
