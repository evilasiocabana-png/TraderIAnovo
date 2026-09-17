from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, Mock
import os

from core import dual_mt5 as dual
from scripts import run_additional_real as worker
from tests import test_mt5_real_execution_account as fixtures


def test_real_authorization_and_revocation(tmp_path):
    path = tmp_path / "control.json"
    assert not dual.real_control_allows(entry=False, path=path)
    dual.set_real_enabled(True, path)
    assert dual.real_control_allows(entry=True, path=path)
    dual.set_real_enabled(False, path)
    assert not dual.real_control_allows(entry=True, path=path)
    assert dual.real_control_allows(entry=False, path=path)
    path.write_text("broken")
    assert not dual.real_control_allows(entry=False, path=path)


def test_child_environment_is_not_primary_environment():
    with patch.dict(os.environ, {"TRADERIA_EXECUTION_ACCOUNT_MODE": "DEMO", "MT5_PASSWORD": "unused-test", "MT5_PATH": "demo.exe"}):
        child = dual.real_worker_environment()
        assert child["TRADERIA_EXECUTION_ACCOUNT_MODE"] == "REAL"
        assert child["MT5_PATH"] == str(dual.REAL_TERMINAL)
        assert "MT5_PASSWORD" not in child
        assert os.environ["MT5_PATH"] == "demo.exe"
        assert Path(child["TRADERIA_ACCOUNT_RUNTIME_ROOT"]) != dual.PROJECT


def test_off_at_transport_boundary_blocks_entries_but_keeps_management(tmp_path):
    path = tmp_path / "control.json"
    dual.set_real_enabled(True, path)
    with patch.dict(os.environ, {"TRADERIA_ADDITIONAL_REAL_CONTROL": str(path)}):
        mt5, provider, _ = fixtures.MT5RealAccountTest().real()
        def check(request):
            dual.set_real_enabled(False, path)
            return SimpleNamespace(retcode=0)
        mt5.order_check = check
        with patch("core.dual_mt5.read_json", wraps=dual.read_json) as read:
            read.side_effect = lambda p: __import__("json").loads(p.read_text()) if p == path else {"online": True}
            response = provider._order_send({"action": mt5.TRADE_ACTION_DEAL})
            assert not provider._result_from_response(response).accepted
            assert not mt5.requests
            response = provider._order_send({"action": mt5.TRADE_ACTION_SLTP, "position": 321})
            assert provider._result_from_response(response).accepted


def test_input_sync_excludes_execution_and_account_state(tmp_path):
    project, root = tmp_path / "project", tmp_path / "real"
    dual.write_json(project / ".traderia/mt5_operational_model.json", {"selections": ["M28"]})
    dual.write_json(project / ".traderia/position_manager_state.json", {"ticket": 123})
    dual.write_json(project / ".traderia/mt5_demo_execution.jsonl", {"ticket": 123})
    with patch.object(worker, "PROJECT", project), patch.object(worker, "REAL_ROOT", root):
        worker.synchronize_inputs()
    assert (root / ".traderia/mt5_operational_model.json").exists()
    assert not (root / ".traderia/position_manager_state.json").exists()
    assert not (root / ".traderia/mt5_demo_execution.jsonl").exists()


def test_disabled_worker_never_calls_strategy_or_order_send():
    mt5, _, _ = fixtures.MT5RealAccountTest().real()
    service = Mock()
    with patch("core.mt5_execution_account.MT5ExecutionAccount.rejection", return_value=None), \
         patch.object(worker, "real_control_allows", return_value=False):
        assert worker.cycle(service, mt5)["status"] == "DISABLED"
    assert not service.mock_calls
    assert not mt5.requests


def test_enabled_worker_uses_existing_strategy_and_selected_pair():
    mt5, _, _ = fixtures.MT5RealAccountTest().real()
    service = Mock()
    service.run_online_demo_robot_cycle.return_value = SimpleNamespace(status="WAIT", result_message="No pattern")
    with patch("core.mt5_execution_account.MT5ExecutionAccount.rejection", return_value=None), \
         patch.object(worker, "real_control_allows", return_value=True), \
         patch.object(worker, "synchronize_inputs"), patch.object(worker, "apply_models") as models, \
         patch.object(worker, "read_json", return_value={"online": True, "pair": "TODOS", "timeframe": "M5"}), \
         patch.dict(os.environ, {"TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED": "0"}):
        assert worker.cycle(service, mt5)["status"] == "WAIT"
    models.assert_called_once_with(service)
    service.run_online_demo_robot_cycle.assert_called_once_with(pair="TODOS", timeframe="M5")


def test_disable_keeps_management_without_new_entries():
    mt5, _, _ = fixtures.MT5RealAccountTest().real()
    service = Mock()
    with patch("core.mt5_execution_account.MT5ExecutionAccount.rejection", return_value=None), \
         patch.object(worker, "real_control_allows", side_effect=lambda entry: not entry), \
         patch.object(worker, "synchronize_inputs"), patch.object(worker, "apply_models"), \
         patch.object(worker, "read_json", return_value={"online": True, "timeframe": "M5"}), \
         patch.dict(os.environ, {"TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED": "0"}):
        assert worker.cycle(service, mt5)["status"] == "MANAGEMENT_ONLY"
    service.run_online_demo_robot_cycle.assert_not_called()
    service.export_mt5_visual_signals.assert_called_once()


def test_missing_strategy_input_does_not_abandon_existing_positions():
    mt5, _, _ = fixtures.MT5RealAccountTest().real()
    service = Mock()
    with patch("core.mt5_execution_account.MT5ExecutionAccount.rejection", return_value=None), \
         patch.object(worker, "real_control_allows", return_value=True), \
         patch.object(worker, "synchronize_inputs", side_effect=RuntimeError("input missing")), \
         patch.object(worker, "read_json", return_value={"online": True}), \
         patch.dict(os.environ, {"TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED": "0"}):
        assert worker.cycle(service, mt5)["status"] == "CONFIG_BLOCKED"
    service.run_online_demo_robot_cycle.assert_not_called()
    service.export_mt5_visual_signals.assert_called_once()


def test_demo_identity_is_pinned_separately():
    from core.mt5_execution_account import MT5ExecutionAccount
    mt5 = fixtures._FakeMT5()
    account = SimpleNamespace(trade_mode=0, login=999, server="Pepperstone-Demo")
    with patch.dict(os.environ, {"TRADERIA_DEMO_ACCOUNT_LOGIN": "61551556", "TRADERIA_DEMO_ACCOUNT_SERVER": "Pepperstone-Demo"}):
        assert MT5ExecutionAccount().rejection(mt5, account)
        account.login = 61551556
        assert MT5ExecutionAccount().rejection(mt5, account) is None


def test_real_respects_weekly_close():
    mt5, _, _ = fixtures.MT5RealAccountTest().real()
    service = Mock()
    service.close_all_demo_positions.return_value = {"message": "Closed"}
    with patch("core.mt5_execution_account.MT5ExecutionAccount.rejection", return_value=None), \
         patch.object(worker, "real_control_allows", return_value=True), \
         patch.object(worker, "synchronize_inputs"), patch.object(worker, "apply_models"), \
         patch.object(worker, "read_json", return_value={"online": True}), \
         patch.dict(os.environ, {"TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED": "1"}), \
         patch("core.weekly_robot_schedule.weekly_robot_schedule_decision", return_value=SimpleNamespace(operating=False)):
        assert worker.cycle(service, mt5)["status"] == "WEEKLY_WINDOW_CLOSED"
    service.close_all_demo_positions.assert_called_once_with(reason="WEEKLY_FRIDAY_1730_BRT")
    service.run_online_demo_robot_cycle.assert_not_called()


def test_real_weekly_close_leaves_manual_positions_alone():
    from application.dashboard_service import DashboardService
    service = DashboardService()
    execution = Mock()
    execution.provider.magic = 260629
    execution.list_open_positions.side_effect = [
        [SimpleNamespace(ticket=1, symbol="XAUUSD", volume=0.11, type=0, magic=0),
         SimpleNamespace(ticket=2, symbol="XAUUSD", volume=0.11, type=0, magic=260629)],
        [],
    ]
    execution.close_position.return_value = SimpleNamespace(accepted=True, status="ACCEPTED", message="ok")
    object.__setattr__(service, "demo_robot_execution_service", execution)
    with patch.object(DashboardService, "_mt5_demo_execution_enabled", return_value=True), \
         patch.object(DashboardService, "_enable_mt5_demo_provider"), \
         patch.dict(os.environ, {"TRADERIA_ADDITIONAL_REAL_CONTROL": "test-only"}):
        result = service.close_all_demo_positions()
    assert result["closed"] == 1
    assert execution.close_position.call_args.kwargs["ticket"] == 2
