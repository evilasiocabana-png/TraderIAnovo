from dataclasses import replace
from unittest.mock import Mock
import pytest
from application.model7_lab_alternative_markets import MODEL_7_ID
from application.model23_basket_accumulator import MODEL_23_ID
from application.model29_basket_accumulator import MODEL_29_ID
from tests import test_mt5_demo_execution_provider as helpers


@pytest.mark.parametrize('model',[MODEL_7_ID,MODEL_23_ID+'_SOURCE_M7',MODEL_29_ID+'_SOURCE_M7',MODEL_23_ID])
@pytest.mark.parametrize('order_type',['MARKET','BUY_STOP'])
def test_bitcoin_m7_blocked_before_terminal_and_send(model,order_type,tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    helper=helpers.MT5DemoExecutionProviderTest()
    provider=helper._provider(helpers._FakeMT5())
    monkeypatch.setattr(type(provider),'_operational_selection_preflight',lambda *a:None)
    init=Mock(side_effect=AssertionError('must not reach terminal'))
    monkeypatch.setattr(type(provider),'_initialize_check',init)
    order=replace(helper._order(),symbol='BTCUSD',operational_model=model,
        plan_snapshot={'stop_management_parameters':{'source_operational_model':MODEL_7_ID,
            'active_entry_order_type':order_type}})
    result=provider.submit_order(order)
    assert not result.accepted and 'Bitcoin retirado' in result.message
    init.assert_not_called()


def test_gold_and_other_bitcoin_models_unchanged():
    helper=helpers.MT5DemoExecutionProviderTest()
    provider=helper._provider(helpers._FakeMT5())
    for model,symbol in [(MODEL_7_ID,'XAUUSD'),(MODEL_23_ID+'_SOURCE_M7','XAUUSD'),
                         (MODEL_23_ID+'_SOURCE_M1','BTCUSD')]:
        order=replace(helper._order(),symbol=symbol,operational_model=model)
        assert provider._xau_route_scope_preflight(order) is None
