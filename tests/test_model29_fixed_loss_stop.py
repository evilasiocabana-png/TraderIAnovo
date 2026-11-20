from types import SimpleNamespace as NS
import pytest
from application.model29_fixed_loss_stop import protected_request
from application.model23_m29_copy import COPY_ID


class Broker:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    def account_info(self):
        return NS(currency="USD")
    def symbol_info(self, symbol):
        return NS(trade_tick_size=0.01, digits=2)
    def order_calc_profit(self, side, symbol, volume, entry, close):
        return (close - entry) * volume * 100 * (1 if side == 0 else -1)


def fixture(source="M8", mode="NORMAL", side="BUY", stop=None):
    order = NS(operational_model=COPY_ID, symbol="XAUUSD", quantity=0.1,
        side=side, plan_snapshot={"stop_management_parameters": {
            "m23_m29_origin_source": source, "m23_m29_mode": mode}})
    return order, dict(price=4000.0, sl=stop or (3900.0 if side == "BUY" else 4100.0),
        tp=4010.0 if side == "BUY" else 3990.0, volume=0.1)


@pytest.mark.parametrize("source", ["M8", "M10", "M18", "M20"])
@pytest.mark.parametrize("side", ["BUY", "SELL"])
def test_caps_risk_preserves_entry_target_and_input(source, side):
    order, request = fixture(source, side=side)
    actual = protected_request(order, request, Broker())
    assert actual["sl"] == (3985.0 if side == "BUY" else 4015.0)
    assert {k:v for k,v in actual.items() if k != "sl"} == {k:v for k,v in request.items() if k != "sl"}
    assert request["sl"] in (3900.0, 4100.0)


@pytest.mark.parametrize("source,mode", [("M7","NORMAL"),("M7","ESPELHADO"),("M8","ESPELHADO"),("M1","NORMAL")])
def test_other_orders_untouched(source, mode):
    order, request = fixture(source, mode)
    assert protected_request(order, request, None) is request


def test_preserves_closer_stop():
    order, request = fixture(stop=3990)
    assert protected_request(order, request, Broker()) is request


@pytest.mark.parametrize("side", ["BUY", "SELL"])
def test_fractional_tick_rounds_toward_entry(side):
    order, request = fixture(side=side)
    request["price"] = 4000.003
    actual = protected_request(order, request, Broker())
    pnl = Broker().order_calc_profit(0 if side == "BUY" else 1, "XAUUSD", 0.1, request["price"], actual["sl"])
    assert -150 <= pnl < -149.8


def test_original_m23_order_not_protected():
    order, request = fixture()
    order.operational_model = "MODELO_23_BASKET_ACCUMULATOR_SOURCE_M8"
    assert protected_request(order, request, None) is request


@pytest.mark.parametrize("failure", ["currency", "calculation", "volume", "tick"])
def test_fails_closed(failure):
    order, request = fixture()
    broker = Broker()
    if failure == "currency":
        broker.account_info = lambda: NS(currency="BRL")
    elif failure == "calculation":
        broker.order_calc_profit = lambda *args: None
    elif failure == "volume":
        order.quantity = 0.2
    else:
        broker.symbol_info = lambda *args: NS(trade_tick_size=0)
    with pytest.raises(ValueError):
        protected_request(order, request, broker)
