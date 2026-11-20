from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from application.model29_entry_sync import CHANNEL_SOURCES
from research.mt5_research_trade_plan import MT5ResearchTradePlan


@pytest.mark.parametrize("source", ["M8", "M10", "M18", "M20"])
@pytest.mark.parametrize("original_accepted", [True, False])
def test_normal_copy_reaches_executor_without_m7_confirmation(tmp_path, monkeypatch, source, original_accepted):
    import application.dashboard_service as module
    from application.dashboard_service import DashboardService
    from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel

    monkeypatch.chdir(tmp_path)
    service = DashboardService()
    service.set_mt5_operational_models((), basket_models=(module.MT5_OPERATIONAL_MODEL_23,))
    row = DashboardMT5ForexSignalRowViewModel(
        pair="XAUUSD", status="OK", timeframe="M5", decision="SELL",
        active_model=source + " TEST", theoretical_entry_candle="candle1", last_candle_time="candle1",
    )
    plan = MT5ResearchTradePlan(
        symbol="XAUUSD", timeframe="M5", direction="SELL", entry_price=100,
        stop=110, target=75, risk_reward=2.5, stop_multiplier=1, exit_model="TEST",
        exit_score=0, exit_candidates=0, status="PLANO_VALIDO",
        stop_management_parameters={"source_operational_model": CHANNEL_SOURCES[source],
            "source_entry_setup": "TEST", "source_initial_stop": 110, "source_target": 75},
    )
    overrides = {
        "_mt5_demo_execution_enabled": lambda: True,
        "get_mt5_forex_signals": lambda: None,
        "_candidate_rows_for_demo_robot": lambda *a: [row],
        "_mt5_research_source_for_reports": lambda: None,
        "_active_mt5_research_models_by_market": lambda *a: {},
        "_active_mt5_research_rows_by_market": lambda *a: {},
        "_active_mt5_research_model_for_row": lambda *a: None,
        "_active_mt5_research_row_for_source_row": lambda *a: None,
        "_to_view_model_mt5_forex_signal_row": lambda *a: row,
        "_mt5_research_trade_plan_for_view_row": lambda *a: plan,
        "_enable_mt5_demo_provider": lambda: None,
        "_mt5_operational_models_to_evaluate": lambda: (CHANNEL_SOURCES[source],),
        "_mt5_apply_operational_model": lambda *a, **k: (row, plan),
        "_mt5_model23_variant_from_source": lambda *a, **k: (row, plan),
        "_mt5_model29_variant_from_source": lambda *a, **k: (row, plan),
        "_record_m7_execution_diagnostic": lambda *a, **k: None,
        "_mt5_server_timestamp": lambda *a: None,
        "_mt5_demo_signal_from_view_row": lambda *a, **k: k["operational_model"],
        "_to_mt5_demo_trade_plan": lambda row, p, **k: p,
        "_demo_robot_audit_rows": lambda: (),
        "_demo_robot_rejection_tree": lambda *a, **k: None,
        "_demo_robot_view_model": lambda **k: SimpleNamespace(**k),
        "_append_demo_robot_visual_signal": lambda *a: None,
    }
    for n in (23, 29, 24, 25):
        overrides[f"_evaluate_model{n}_risk_gate"] = lambda *a: None
    for name, value in overrides.items():
        object.__setattr__(service, name, value)
    provider = Mock()
    object.__setattr__(service, "demo_robot_execution_service", SimpleNamespace(provider=provider, list_open_positions=lambda: []))
    sent = []

    def send(model, candidate):
        sent.append((model, candidate))
        accepted = original_accepted or model.endswith("_SOURCE_M29")
        return SimpleNamespace(status="EXECUTED" if accepted else "REJECTED", message="test",
            execution_result=SimpleNamespace(accepted=accepted, ticket=123 if accepted else None,
                status="ACCEPTED" if accepted else "REJECTED", message="test"))

    object.__setattr__(service, "mt5_demo_robot_service", SimpleNamespace(enabled=True, evaluate_once=send))
    object.__setattr__(service, "forex_time_layer", SimpleNamespace(classify=lambda *a, **k: None))
    monkeypatch.setattr(module, "model23_entry_gate", lambda *a: (True, ""))
    service.evaluate_armed_demo_robot_once()
    assert [m for m, p in sent] == [
        "MODELO_23_BASKET_ACCUMULATOR_SOURCE_" + source,
        "MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29",
    ]
    copy = sent[1][1]
    assert copy.direction == "SELL"
    assert copy.stop == plan.stop and copy.target == plan.target
    assert copy.stop_management_parameters["m23_m29_origin_source"] == source
    assert copy.stop_management_parameters["m23_m29_mode"] == "NORMAL"
    assert copy.stop_management_parameters["execution_volume"] == 0.1
    assert "m23_m29_pair_original_ticket" not in copy.stop_management_parameters
    provider._external_mt5_read.assert_not_called()
