from types import SimpleNamespace as NS
import pytest
from application.model23_fixed_loss_stop import protected_request

class Broker:
    ORDER_TYPE_BUY=0
    ORDER_TYPE_SELL=1
    def account_info(self): return NS(currency='USD')
    def symbol_info(self, symbol): return NS(trade_tick_size=.01,digits=2)
    def order_calc_profit(self, side, symbol, volume, entry, close):
        return (close-entry)*volume*100*(1 if side==0 else -1)

def fixture(source, side, distance, volume=.1):
    entry=4284.08
    order=NS(operational_model='MODELO_23_BASKET_ACCUMULATOR_SOURCE_'+source,
             symbol='XAUUSD',side=side,quantity=volume)
    return order,dict(price=entry,sl=round(entry+distance*(1 if side=='SELL' else -1),2),
                      tp=4200 if side=='SELL' else 4400,volume=volume,comment='unchanged')

@pytest.mark.parametrize('source',['M1','M7','M8','M10','M18','M20','M26'])
@pytest.mark.parametrize('side',['BUY','SELL'])
@pytest.mark.parametrize('distance',[8.29,20,100])
def test_structural_or_capped(source,side,distance):
    order,request=fixture(source,side,distance)
    before=request.copy()
    actual=protected_request(order,request,Broker())
    risk=-Broker().order_calc_profit(0 if side=='BUY' else 1,order.symbol,.1,actual['price'],actual['sl'])
    assert risk<=200.00000001
    assert abs(actual['sl']-actual['price'])<=distance+1e-9
    if distance<20: assert actual is request
    assert request==before
    assert {k:v for k,v in actual.items() if k!='sl'}=={k:v for k,v in before.items() if k!='sl'}

@pytest.mark.parametrize('volume',[.01,.1,.2,1.0])
def test_broker_volume_and_symbol(volume):
    order,request=fixture('M18','SELL',100,volume)
    order.symbol='EURJPY'
    actual=protected_request(order,request,Broker())
    assert -Broker().order_calc_profit(1,order.symbol,volume,request['price'],actual['sl'])<=200.00000001

@pytest.mark.parametrize('failure',['none','nan','raise','currency','tick','negative_volume','positive_profit'])
def test_fails_closed(failure):
    order,request=fixture('M20','SELL',100)
    b=Broker()
    if failure=='none': b.order_calc_profit=lambda *a:None
    if failure=='nan': b.order_calc_profit=lambda *a:float('nan')
    if failure=='raise':
        def fail(*args): raise RuntimeError('offline')
        b.order_calc_profit=fail
    if failure=='currency': b.account_info=lambda:NS(currency='BRL')
    if failure=='tick': b.symbol_info=lambda *a:NS(trade_tick_size=0)
    if failure=='negative_volume': request['volume']=-1
    if failure=='positive_profit': b.order_calc_profit=lambda *a:1
    with pytest.raises((ValueError,RuntimeError)): protected_request(order,request,b)

@pytest.mark.parametrize('model',['MODELO_29_BASKET_ACCUMULATOR_SOURCE_M7','MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29','MODELO_18'])
def test_m29_and_other_models_untouched(model):
    order,request=fixture('M18','SELL',100)
    order.operational_model=model
    assert protected_request(order,request,None) is request

@pytest.mark.parametrize('source',['M18','M20'])
@pytest.mark.parametrize('side',['BUY','SELL'])
@pytest.mark.parametrize('distance',[8.29,100])
@pytest.mark.parametrize('failure',[False,True])
def test_provider_checks_before_send(tmp_path,source,side,distance,failure):
    from tests.test_mt5_demo_execution_provider import _FakeMT5
    from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
    from domain.contracts.execution_order import ExecutionOrder
    b=_FakeMT5()
    b.tick=NS(ask=4284.08,bid=4284.08)
    b.profit_scale=100
    if failure: b.order_calc_profit=lambda *args:None
    provider=MT5DemoExecutionProvider(mt5=b,log_path=tmp_path/'orders.jsonl')
    simple,request=fixture(source,side,distance)
    order=ExecutionOrder(symbol=simple.symbol,side=side,quantity=.1,entry_price=request['price'],
        stop=request['sl'],target=request['tp'],operational_model=simple.operational_model,
        plan_snapshot={'stop_management_parameters':{'source_operational_model':'MODELO_'+source[1:]+'_XAU_M5'}})
    result=provider.submit_order(order)
    if failure:
        assert not result.accepted
        assert 'Defesa financeira M23' in result.message
        assert b.requests==[]
    else:
        assert result.accepted,result.message
        sent=b.last_request
        assert sent['tp']==request['tp'] and sent['volume']==.1
        assert -b.order_calc_profit(b.ORDER_TYPE_BUY if side=='BUY' else b.ORDER_TYPE_SELL,
            simple.symbol,.1,sent['price'],sent['sl'])<=200.00000001
        if distance<20: assert sent['sl']==request['sl']
