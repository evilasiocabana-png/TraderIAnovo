from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import application.dashboard_service as module
from application.dashboard_service import DashboardService
from application.model29_basket_accumulator import (
    MODEL_29_ID, Model29BasketManager, model29_entry_type_token,
    model29_variant_id,
)
from application.model23_pattern_filter import M23PatternFilterService, M23PatternFilterReport
from application.model29_sequence_history import closed_m7_positions, sequence_mode
from domain.operational_model_policy import is_active_operational_model
from tests import test_mt5_demo_execution_provider as provider_helpers
from tests.test_model23_context_integration import setup_service


def test_selection_does_not_enable_or_read_m23():
    service = DashboardService()
    service.set_mt5_operational_models((), basket_models=(MODEL_29_ID,), direct_models_enabled=False)
    assert service._mt5_model29_routing_enabled()
    assert not service._mt5_model23_routing_enabled()
    assert not service._mt5_direct_routing_enabled()
    assert service._mt5_operational_models_to_evaluate() == module.MT5_MODEL_29_SOURCE_MODEL_IDS
    assert service._mt5_operational_models_to_evaluate() == (module.MT5_OPERATIONAL_MODEL_7,)
    assert MODEL_29_ID not in module.MT5_MODEL_23_SOURCE_MODEL_IDS
    assert is_active_operational_model(model29_variant_id(module.MT5_OPERATIONAL_MODEL_7))
    service.set_mt5_operational_model(module.MT5_OPERATIONAL_MODEL_28)
    assert not service._mt5_model29_routing_enabled()


def test_online_cycle_not_stopped_by_m23_basket(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = DashboardService()
    service.set_mt5_operational_models((), basket_models=(module.MT5_OPERATIONAL_MODEL_23, MODEL_29_ID))
    object.__setattr__(service.mt5_demo_robot_service, "enabled", True)
    monkeypatch.setattr(DashboardService, "_mt5_demo_execution_enabled", lambda s: True)
    monkeypatch.setattr(DashboardService, "_enable_mt5_demo_provider", lambda s: None)
    monkeypatch.setattr(DashboardService, "_evaluate_model23_risk_gate", lambda *a: "M23_CLOSING")
    monkeypatch.setattr(DashboardService, "_evaluate_model29_risk_gate", lambda *a: None)
    monkeypatch.setattr(DashboardService, "load_mt5_forex_signals", lambda *a, **kw: None)
    monkeypatch.setattr(DashboardService, "run_demo_robot_for_all", lambda *a, **kw: "M29_CONTINUES")
    assert service.run_online_demo_robot_cycle() == "M29_CONTINUES"


@pytest.mark.parametrize("source", [module.MT5_OPERATIONAL_MODEL_8, module.MT5_OPERATIONAL_MODEL_18, module.MT5_OPERATIONAL_MODEL_20])
def test_original_plan_not_m23_route(tmp_path, monkeypatch, source):
    service, row, plan = setup_service(tmp_path, monkeypatch)
    independent_filter = M23PatternFilterService(tmp_path / "filter.json")
    independent_filter.save(M23PatternFilterReport(
        generated_at="2026-09-12", source_rows=0, eligible_rows=0,
        contextualized_rows=0, ignored_legacy_rows=0, rules=(), samples=(),
    ))
    monkeypatch.setattr(module, "_MODEL29_PATTERN_FILTER_SERVICE", independent_filter)
    monkeypatch.setattr(DashboardService, "_mt5_model23_variant_from_source", Mock(side_effect=AssertionError("M23 not allowed")))
    new_row, new_plan = service._mt5_model29_variant_from_source(row, plan, source_operational_model=source)
    assert new_plan.status == "M29_CONFIG_WAITING"
    assert new_plan.direction == new_row.decision == "WAIT"
    assert new_plan.entry_price is None
    assert new_plan.stop is None and new_plan.target is None


def test_mirror_plan_uses_own_mode(tmp_path, monkeypatch):
    service, row, plan = setup_service(tmp_path, monkeypatch)
    monkeypatch.setattr("application.model29_sequence_history.sequence_mode", lambda *a: "ESPELHADO")
    new_row, new_plan = service._apply_model29_m7_mode(row, plan, "M7")
    assert (new_plan.direction, new_plan.stop, new_plan.target) == ("BUY", 90, 110)
    assert new_row.decision == "BUY"
    assert new_plan.risk_reward == 1
    assert new_plan.stop_management_parameters["m29_mirrored"]
    assert plan.direction == "SELL"
    signal = service._position_manager_signal_from_execution_record({
        "operational_model": model29_variant_id(module.MT5_OPERATIONAL_MODEL_7),
        "plan_snapshot": {"stop_management_parameters": new_plan.stop_management_parameters},
    })
    assert signal["operational_model"].startswith(MODEL_29_ID)
    assert signal["stop_management"] == "RESEARCH_FIXED_SL_TP"


@pytest.mark.parametrize("number", [1, 2, 5, 8, 10, 18, 20, 21, 22])
def test_removed_sources_rejected_before_mt5(number):
    helper = provider_helpers.MT5DemoExecutionProviderTest()
    provider = helper._provider(provider_helpers._FakeMT5())
    order = replace(helper._order(), symbol="XAUUSD", operational_model=f"{MODEL_29_ID}_SOURCE_M{number}")
    for check in (provider._model29_source_position_preflight, provider._model29_pending_source_preflight_locked):
        result = check(order)
        assert result is not None and not result.accepted
        assert "nao autorizado" in result.message


def test_provider_order_is_separate_from_m23(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    helper = provider_helpers.MT5DemoExecutionProviderTest()
    native = provider_helpers._FakeMT5()
    provider = helper._provider(native)
    order = helper._order()
    order = replace(order, symbol="XAUUSD", operational_model=model29_variant_id(module.MT5_OPERATIONAL_MODEL_7),
                    plan_snapshot={"stop_management_parameters": {
                        "source_operational_model": module.MT5_OPERATIONAL_MODEL_7,
                        "m29_entry_type": "ALPHA001",
                    }})
    result = provider.submit_order(order)
    assert result.accepted, result.message
    assert native.last_request["comment"] == f"TraderIA M29 S7 {model29_entry_type_token('ALPHA001')}"
    assert native.last_request["sl"] == order.stop
    assert native.last_request["tp"] == order.target


def test_m23_position_does_not_block_m29_but_own_duplicate_does(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    helper = provider_helpers.MT5DemoExecutionProviderTest()
    position = SimpleNamespace(ticket=1, symbol="XAUUSD",
        comment=f"TraderIA M23 S7 {model29_entry_type_token('TEST_SETUP')}")
    native = provider_helpers._FakeMT5(open_positions=[position])
    provider = helper._provider(native)
    order = replace(helper._order(), symbol="XAUUSD",
                    operational_model=model29_variant_id(module.MT5_OPERATIONAL_MODEL_7))
    assert provider._model29_source_position_preflight(order) is None
    position.comment = position.comment.replace("M23", "M29")
    assert provider._model29_source_position_preflight(order) is not None


def test_provider_mirrored_m7_keeps_tp(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    helper = provider_helpers.MT5DemoExecutionProviderTest()
    native = provider_helpers._FakeMT5()
    provider = helper._provider(native)
    order = replace(helper._order(), symbol="XAUUSD", side="SELL", stop=110, target=90,
                    operational_model=model29_variant_id(module.MT5_OPERATIONAL_MODEL_7),
                    plan_snapshot={"stop_management_parameters": {
                        "source_operational_model": module.MT5_OPERATIONAL_MODEL_7,
                        "m29_entry_type": "ALPHA001", "m29_mirrored": True,
                    }})
    result = provider.submit_order(order)
    assert result.accepted, result.message
    assert native.last_request["tp"] == 90
    assert native.last_request["sl"] == 110


def test_basket_only_closes_m29_tickets(tmp_path):
    def position(ticket, model, profit):
        return SimpleNamespace(ticket=ticket, symbol="XAUUSD", type=0, volume=0.1,
                               profit=profit, swap=0, commission=0, fee=0,
                               comment=f"TraderIA M{model} S7")
    service = Mock()
    service.list_open_positions.return_value = [position(1, 23, 2000), position(2, 29, 1001)]
    service.close_position.return_value = SimpleNamespace(accepted=True, status="ACCEPTED")
    manager = Model29BasketManager(execution_service=service,
                state_path=tmp_path/"state.json", audit_path=tmp_path/"audit.jsonl")
    manager.evaluate_once()
    assert [c.kwargs["ticket"] for c in service.close_position.call_args_list] == [2]


def deals(position, net, model=23, symbol="XAUUSD"):
    return [
        dict(position_id=position, ticket=position*2, type=0, entry=0, volume=0.1,
             symbol=symbol, time=position*10, comment=f"TraderIA M{model} S7", commission=-1),
        dict(position_id=position, ticket=position*2+1, type=1, entry=1, volume=0.1,
             symbol=symbol, time=position*10+1, comment="[sl]", profit=net+1),
    ]


def test_full_closures_net_costs_and_account_isolation(tmp_path):
    rows = sum((deals(i+1, v) for i,v in enumerate([1,-1,1,-1,-1,-1,-1,-1])), [])
    payload = dict(ok=True, account={"login": 1,"server": "DEMO"}, rows=rows, open_positions=[])
    provider = Mock()
    provider._external_mt5_read.return_value = payload
    assert sequence_mode(provider, "XAUUSD", tmp_path) == "ESPELHADO"
    # Own M29 gains cannot switch the mode; new M23 gains can.
    payload["rows"] += sum((deals(i+10, v, 29) for i,v in enumerate([-1,1,-1,1,1,1])), [])
    assert sequence_mode(provider, "XAUUSD", tmp_path) == "ESPELHADO"
    payload["rows"] += sum((deals(i+30, v) for i,v in enumerate([-1,1,-1,1,1,1])), [])
    assert sequence_mode(provider, "XAUUSD", tmp_path) == "NORMAL"
    assert sequence_mode(provider, "XAUUSD", tmp_path) == "NORMAL"
    payload["account"] = {"login":2,"server":"REAL"}
    payload["rows"] = []
    assert sequence_mode(provider, "XAUUSD", tmp_path) == "NORMAL"
    assert len(list(tmp_path.glob("*.json"))) == 2
    partial = dict(rows=deals(100, -1), open_positions=[])
    partial["rows"][1]["volume"] = 0.05
    assert closed_m7_positions(partial) == []


@pytest.mark.parametrize("symbol,mode,quantity,blocked", [
    ("BTCUSD", "NORMAL", 0.1, True),
    ("EURJPY", "NORMAL", 0.1, True),
    ("XAUUSD", "NORMAL", 0.2, True),
    ("XAUUSD", "ESPELHADO", 0.1, True),
    ("XAUUSD", "NORMAL", 0.1, False),
    ("XAUUSD", "ESPELHADO", 0.2, False),
])
def test_m29_gold_mode_volume_guard(symbol, mode, quantity, blocked):
    helper = provider_helpers.MT5DemoExecutionProviderTest()
    provider = helper._provider(provider_helpers._FakeMT5())
    order = replace(helper._order(), symbol=symbol, quantity=quantity,
        operational_model=model29_variant_id(module.MT5_OPERATIONAL_MODEL_7),
        plan_snapshot={"stop_management_parameters": {"m29_m7_mode": mode, "m29_entry_type": "TEST_SETUP"}})
    for check in (provider._model29_source_position_preflight, provider._model29_pending_source_preflight_locked):
        result = check(order)
        assert (result is not None) == blocked
