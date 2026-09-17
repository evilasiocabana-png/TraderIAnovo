import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from zoneinfo import ZoneInfo

import pytest

from core.weekly_robot_schedule import weekly_entry_allowed, weekly_robot_schedule_decision
from application.dashboard_service import DashboardService
from tests.test_weekly_robot_schedule import _FakeExecutionService
from tests import test_mt5_demo_execution_provider as helpers

BRT = ZoneInfo("America/Sao_Paulo")
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("moment,forex", [
    (datetime(2026, 9, 11, 17, 29, 59, tzinfo=BRT), True),
    (datetime(2026, 9, 11, 17, 30, tzinfo=BRT), False),
    (datetime(2026, 9, 12, 12, tzinfo=BRT), False),
    (datetime(2026, 9, 13, 18, 4, 59, tzinfo=BRT), False),
    (datetime(2026, 9, 13, 18, 5, tzinfo=BRT), True),
])
def test_asset_window(moment, forex, monkeypatch):
    monkeypatch.setenv("TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED", "1")
    assert weekly_entry_allowed("BTCUSD", moment) is forex
    assert weekly_entry_allowed("XAUUSD", moment) is forex
    assert weekly_entry_allowed("EURUSD", moment) is forex
    assert weekly_entry_allowed("ETHUSD", moment) is forex
    assert weekly_entry_allowed("XAUUSD", moment.astimezone(ZoneInfo("UTC"))) is forex


def test_scheduled_close_preserves_btc(monkeypatch):
    monkeypatch.delenv("TRADERIA_ADDITIONAL_REAL_CONTROL", raising=False)
    execution = _FakeExecutionService()
    execution.positions.append(SimpleNamespace(ticket=103, symbol="BTCUSD", volume=.1, type=0))
    service = DashboardService.__new__(DashboardService)
    object.__setattr__(service, "demo_robot_execution_service", execution)
    object.__setattr__(service, "_mt5_demo_execution_enabled", lambda: True)
    object.__setattr__(service, "_enable_mt5_demo_provider", lambda: None)
    result = service.close_all_demo_positions(exclude_symbols=("BTCUSD",))
    assert result["closed"] == 2 and result["remaining"] == 0
    assert [p.symbol for p in execution.positions] == ["BTCUSD"]


def test_pending_cleanup_preserves_btc_and_other_robots(monkeypatch):
    provider = helpers.MT5DemoExecutionProviderTest()._provider(helpers._FakeMT5())
    orders = [SimpleNamespace(ticket=t, symbol=s, magic=m) for t,s,m in [
        (1,"BTCUSD",provider.magic), (2,"XAUUSD",provider.magic), (3,"EURUSD",123),
    ]]
    monkeypatch.setattr(provider, "_initialize_check", lambda: None)
    monkeypatch.setattr(provider, "_demo_account_check", lambda: None)
    monkeypatch.setattr(provider.mt5, "orders_get", lambda: list(orders), raising=False)
    monkeypatch.setattr(provider.mt5, "TRADE_ACTION_REMOVE", 8, raising=False)
    monkeypatch.setattr(provider, "_write_management_log", lambda payload: None)
    def send(request):
        orders[:] = [o for o in orders if o.ticket != request["order"]]
        return SimpleNamespace(retcode=10009)
    monkeypatch.setattr(provider, "_checked_order_send", send)
    assert provider.cancel_weekly_pending_orders(exclude_symbols=("BTCUSD",)) == {"remaining":0,"cancelled":1}
    assert [o.ticket for o in orders] == [1,3]


def load_ui_function(name, namespace):
    tree = ast.parse((ROOT / "dashboard_app.py").read_text(encoding="utf-8-sig"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), "dashboard_app.py", "exec"), namespace)
    return namespace[name]


def test_weekend_scheduler_disarms_all_symbols():
    service = Mock()
    service.close_all_demo_positions.return_value = {"remaining":0}
    from threading import Lock
    ns = {"DashboardService":DashboardService, "datetime":datetime,
          "weekly_robot_schedule_decision":weekly_robot_schedule_decision,
          "_load_demo_robot_online_state":lambda: {"online":False,"pair":"TODOS","timeframe":"H1"},
          "_load_weekly_robot_schedule_state":lambda: {},
          "_persist_demo_robot_online_state":Mock(), "_start_demo_robot_background_cycle_once":Mock(),
          "_weekly_flat_check_due":lambda *a: True, "MT5_FOREX_CYCLE_LOCK":Lock(),
          "_write_weekly_robot_schedule_state":Mock(), "_write_demo_robot_background_state":Mock()}
    fn = load_ui_function("_enforce_weekly_robot_schedule", ns)
    result = fn(service, now=datetime(2026,9,12,12,tzinfo=BRT))
    service.arm_demo_robot.assert_not_called()
    service.disarm_demo_robot.assert_called_once_with(pair="TODOS",timeframe="H1")
    assert ns["_persist_demo_robot_online_state"].call_args.kwargs["pair"] == "TODOS"
    assert "exclude_symbols" not in service.close_all_demo_positions.call_args.kwargs
    assert result["status"] == "WEEKLY_WINDOW_CLOSED"


def test_market_feed_pauses_saturday():
    fn = load_ui_function("_mt5_forex_market_cycle_allowed_now", {"datetime":datetime, "_is_mt5_forex_closed_holiday":lambda now: False})
    assert not fn(datetime(2026,9,12,12,tzinfo=BRT))


def test_transport_blocks_all_weekend_entries_but_allows_exits(monkeypatch):
    monkeypatch.setenv("TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED", "1")
    monkeypatch.setattr("core.weekly_robot_schedule.weekly_robot_schedule_decision", lambda now=None: SimpleNamespace(operating=False))
    native = helpers._FakeMT5()
    provider = helpers.MT5DemoExecutionProviderTest()._provider(native)
    blocked = provider._checked_order_send({"action":native.TRADE_ACTION_DEAL,"symbol":"XAUUSD"})
    assert native.last_request is None
    provider._checked_order_send({"action":native.TRADE_ACTION_DEAL,"symbol":"BTCUSD"})
    assert native.last_request is None
    provider._checked_order_send({"action":native.TRADE_ACTION_DEAL,"symbol":"XAUUSD","position":123})
    assert native.last_request["position"] == 123
