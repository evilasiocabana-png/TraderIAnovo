from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from application.dashboard_service import (
    DashboardService,
    MT5_ACTIVE_SOURCE_MODEL_IDS,
    MT5_CUSTOM_OPERATIONAL_MODELS,
    MT5_MODEL_25_SOURCE_MODEL_IDS,
    MT5_OPERATIONAL_MODEL_25,
)
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.model25_multi_asset_rsi50_basket import (
    MODEL_25_CONTRACT_VERSION,
    MODEL_25_CONTRACT_FINGERPRINT,
    MODEL_25_ID,
    MODEL_25_INITIAL_VOLUME,
    MODEL_25_REENTRY_VOLUME,
    MODEL_25_SOURCE_MODEL_IDS,
    MODEL_25_SYMBOLS,
    Model25BasketManager,
    is_model25,
    model25_order_comment,
    model25_position_source,
    model25_variant_id,
)
from application.model8_xau_m5_sma_rsi_reentry import MODEL_8_ID
from application.xau_m5_sma_rsi_model_family import (
    MODEL_10_ID,
    MODEL_18_ID,
    MODEL_19_ID,
    MODEL_20_ID,
    MODEL_21_ID,
    MODEL_22_ID,
)
from domain.operational_model_policy import (
    is_active_operational_model,
    operational_model_number,
)
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def test_model25_contract_is_xauusd_m5_only_with_exact_seven_sources() -> None:
    assert MODEL_25_CONTRACT_VERSION == "M25_XAU_SOURCES_V6_20260820"
    assert len(MODEL_25_CONTRACT_FINGERPRINT) == 16
    assert MODEL_25_SYMBOLS == ("XAUUSD",)
    assert MODEL_25_SOURCE_MODEL_IDS == (
        MODEL_8_ID,
        MODEL_10_ID,
        MODEL_18_ID,
        MODEL_19_ID,
        MODEL_20_ID,
        MODEL_21_ID,
        MODEL_22_ID,
    )
    assert MT5_MODEL_25_SOURCE_MODEL_IDS == MODEL_25_SOURCE_MODEL_IDS
    assert MODEL_25_INITIAL_VOLUME == 0.10
    assert MODEL_25_REENTRY_VOLUME == 0.10


def test_active_governance_pins_model25_contract_fingerprint() -> None:
    marker = (
        f"M25_CONTRACT={MODEL_25_CONTRACT_VERSION}; "
        f"FINGERPRINT={MODEL_25_CONTRACT_FINGERPRINT}"
    )
    for relative_path in (
        "governance/execution/PROJECT_STATUS.md",
        "governance/execution/NEXT_MISSION.md",
        "governance/programs/PROGRAM_STATUS.md",
        "docs/ACCEPTANCE_CRITERIA.md",
        "docs/ARCHITECTURE.md",
    ):
        assert marker in Path(relative_path).read_text(encoding="utf-8")


def test_model25_is_selectable_aggregator_not_a_direct_signal_source() -> None:
    assert operational_model_number(MODEL_25_ID) == 25
    assert is_active_operational_model(MODEL_25_ID)
    assert is_model25(MODEL_25_ID)
    assert MT5_OPERATIONAL_MODEL_25 == MODEL_25_ID
    assert MODEL_25_ID not in MT5_ACTIVE_SOURCE_MODEL_IDS
    assert MODEL_25_ID in MT5_CUSTOM_OPERATIONAL_MODELS


def test_model25_variant_and_comment_keep_source_identity() -> None:
    variant = model25_variant_id(MODEL_8_ID)
    assert variant == f"{MODEL_25_ID}_SOURCE_M8"
    assert model25_order_comment(variant) == "TraderIA M25 S8"
    assert model25_position_source(
        SimpleNamespace(comment="TraderIA M25 S22 INITIAL")
    ) == "M22"
    with pytest.raises(ValueError):
        model25_variant_id("MODELO_9_XAU")


@pytest.mark.parametrize(
    ("source_model", "order_type", "target"),
    (
        (MODEL_8_ID, "MARKET", 0.0),
        (MODEL_18_ID, "BUY_STOP", 130.0),
    ),
)
def test_model25_copies_source_entry_stop_and_target_exactly(
    source_model: str,
    order_type: str,
    target: float,
) -> None:
    service = object.__new__(DashboardService)
    row = DashboardMT5ForexSignalRowViewModel(
        pair="XAUUSD",
        status="OK",
        timeframe="M5",
        decision="BUY",
        theoretical_entry_direction="BUY",
        theoretical_entry_status="SINAL_TEORICO",
        theoretical_entry_price=120.0,
        research_plan_status="PLANO_VALIDO",
    )
    source_plan = MT5ResearchTradePlan(
        symbol="XAUUSD",
        timeframe="M5",
        direction="BUY",
        entry_price=120.0,
        stop=110.0,
        target=target,
        risk_reward=1.0 if target else 0.0,
        stop_multiplier=1.0,
        exit_model="SOURCE_EXIT",
        exit_score=1.0,
        exit_candidates=1,
        status="PLANO_VALIDO",
        stop_reason="SL fonte",
        target_reason="TP fonte",
        stop_management="SOURCE_MANAGEMENT",
        stop_management_parameters={"active_entry_order_type": order_type},
        source="SOURCE_SIGNAL",
        reason="Sinal fonte",
    )

    copied_row, copied_plan = service._mt5_model25_variant_from_source(
        row,
        source_plan,
        source_operational_model=source_model,
    )

    assert copied_row.decision == "BUY"
    assert copied_plan.entry_price == source_plan.entry_price
    assert copied_plan.stop == source_plan.stop
    assert copied_plan.target == source_plan.target
    assert copied_plan.stop_management_parameters["source_operational_model"] == source_model
    assert copied_plan.stop_management_parameters["m25_entry_role"] == (
        "REENTRY" if order_type == "BUY_STOP" else "INITIAL"
    )


def test_model25_does_not_add_an_entry_filter_to_the_source() -> None:
    service = object.__new__(DashboardService)
    row = DashboardMT5ForexSignalRowViewModel(
        pair="XAUUSD",
        timeframe="M5",
        decision="BUY",
        theoretical_entry_direction="BUY",
        theoretical_entry_price=120.0,
        research_plan_status="PLANO_VALIDO",
    )
    plan = MT5ResearchTradePlan(
        symbol="XAUUSD",
        timeframe="M5",
        direction="BUY",
        entry_price=120.0,
        stop=110.0,
        target=130.0,
        risk_reward=1.0,
        stop_multiplier=1.0,
        exit_model="SOURCE_EXIT",
        exit_score=1.0,
        exit_candidates=1,
        status="PLANO_VALIDO",
        stop_management_parameters={"active_entry_order_type": "BUY_STOP"},
    )

    copied_row, copied_plan = service._mt5_model25_variant_from_source(
        row,
        plan,
        source_operational_model=MODEL_18_ID,
    )

    assert copied_row.decision == "BUY"
    assert copied_plan.status == "PLANO_VALIDO"
    assert copied_plan.entry_price == 120.0
    assert copied_plan.stop_management_parameters["source_model_label"] == "M18"
    assert copied_plan.stop_management_parameters["m25_entry_role"] == "REENTRY"
    assert "m25_distance_atr" not in copied_plan.stop_management_parameters
    assert "m25_distance_informational" not in copied_plan.stop_management_parameters


def test_model25_sends_all_ready_sources_from_the_same_snapshot() -> None:
    service = DashboardService()
    source_row = SimpleNamespace(
        pair="XAUUSD",
        last_candle_time="2026-08-19T23:15:00+00:00",
    )
    ready_row = DashboardMT5ForexSignalRowViewModel(
        pair="XAUUSD",
        status="OK",
        timeframe="M5",
        decision="SELL",
        theoretical_entry_direction="SELL",
        theoretical_entry_status="SINAL_TEORICO",
        theoretical_entry_price=4495.46,
        research_plan_status="PLANO_VALIDO",
    )
    ready_plan = MT5ResearchTradePlan(
        symbol="XAUUSD",
        timeframe="M5",
        direction="SELL",
        entry_price=4495.46,
        stop=4503.54,
        target=0.0,
        risk_reward=0.0,
        stop_multiplier=1.0,
        exit_model="SOURCE_EXIT",
        exit_score=1.0,
        exit_candidates=1,
        status="PLANO_VALIDO",
        source="SOURCE_SIGNAL",
    )
    evaluated_models: list[str] = []

    def evaluate_once(_signal, robot_plan):
        evaluated_models.append(robot_plan.operational_model)
        return SimpleNamespace(
            status="EXECUTED",
            message="Ordem aceita.",
            execution_result=None,
        )

    robot = SimpleNamespace(
        enabled=True,
        execution_service=None,
        evaluate_once=evaluate_once,
    )
    object.__setattr__(service, "mt5_demo_robot_service", robot)
    object.__setattr__(service, "_mt5_demo_execution_enabled", lambda: True)
    object.__setattr__(service, "get_mt5_forex_signals", lambda: object())
    object.__setattr__(
        service,
        "_candidate_rows_for_demo_robot",
        lambda *_args, **_kwargs: [source_row],
    )
    object.__setattr__(service, "_mt5_research_source_for_reports", lambda: object())
    object.__setattr__(service, "_active_mt5_research_models_by_market", lambda *_: {})
    object.__setattr__(service, "_active_mt5_research_rows_by_market", lambda *_: {})
    object.__setattr__(service, "_active_mt5_research_model_for_row", lambda *_: None)
    object.__setattr__(
        service,
        "_active_mt5_research_row_for_source_row",
        lambda *_: None,
    )
    object.__setattr__(service, "_to_view_model_mt5_forex_signal_row", lambda *_: ready_row)
    object.__setattr__(service, "_mt5_research_trade_plan_for_view_row", lambda *_: ready_plan)
    object.__setattr__(service, "_enable_mt5_demo_provider", lambda: None)
    object.__setattr__(service, "_mt5_model23_routing_enabled", lambda: False)
    object.__setattr__(service, "_mt5_model24_routing_enabled", lambda: False)
    object.__setattr__(service, "_mt5_model25_routing_enabled", lambda: True)
    object.__setattr__(service, "_mt5_direct_routing_enabled", lambda: False)
    object.__setattr__(
        service,
        "_mt5_operational_models_to_evaluate",
        lambda: list(MODEL_25_SOURCE_MODEL_IDS),
    )
    object.__setattr__(service, "_evaluate_model23_risk_gate", lambda *_: None)
    object.__setattr__(service, "_evaluate_model24_risk_gate", lambda *_: None)
    object.__setattr__(service, "_evaluate_model25_risk_gate", lambda *_: None)
    object.__setattr__(
        service,
        "_mt5_apply_operational_model",
        lambda *_args, **_kwargs: (ready_row, ready_plan),
    )
    object.__setattr__(
        service,
        "_mt5_model25_variant_from_source",
        lambda row, plan, **_kwargs: (row, plan),
    )
    object.__setattr__(service, "_mt5_multi_model_selection_active", lambda: False)
    object.__setattr__(service, "_mt5_server_timestamp", lambda *_: None)
    object.__setattr__(
        service.forex_time_layer,
        "classify",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    object.__setattr__(
        service,
        "_mt5_demo_signal_from_view_row",
        lambda *_args, **_kwargs: SimpleNamespace(),
    )
    object.__setattr__(
        service,
        "_to_mt5_demo_trade_plan",
        lambda _row, _plan, *, operational_model: SimpleNamespace(
            operational_model=operational_model
        ),
    )
    object.__setattr__(service, "_demo_robot_rejection_tree", lambda *_args, **_kwargs: ())
    object.__setattr__(
        service,
        "_demo_robot_view_model",
        lambda *, status, **_kwargs: SimpleNamespace(status=status),
    )
    object.__setattr__(service, "_append_demo_robot_visual_signal", lambda *_: None)

    result = service.evaluate_armed_demo_robot_once("TODOS", "M5")

    assert result.status == "EXECUTED"
    assert evaluated_models == [
        model25_variant_id(source_model)
        for source_model in MODEL_25_SOURCE_MODEL_IDS
    ]


def test_model25_basket_closes_only_m25_at_one_thousand(tmp_path) -> None:
    positions = [
        SimpleNamespace(symbol="XAUUSD", ticket=1, type=0, volume=0.2, profit=600.0, swap=0.0, commission=0.0, fee=0.0, comment="TraderIA M25 S8 INITIAL"),
        SimpleNamespace(symbol="XAUUSD", ticket=2, type=1, volume=0.1, profit=410.0, swap=0.0, commission=0.0, fee=0.0, comment="TraderIA M25 S18 REENTRY"),
        SimpleNamespace(symbol="XAUUSD", ticket=3, type=0, volume=0.1, profit=900.0, swap=0.0, commission=0.0, fee=0.0, comment="TraderIA M24 INITIAL"),
    ]

    class Provider:
        closed: list[int] = []

        def list_open_positions(self):
            return positions

        def close_position(self, **kwargs):
            self.closed.append(int(kwargs["ticket"]))
            return SimpleNamespace(accepted=True, message="ok")

    provider = Provider()
    snapshot = Model25BasketManager(
        execution_service=provider,
        state_path=tmp_path / "basket.json",
        audit_path=tmp_path / "audit.jsonl",
    ).evaluate_once()
    assert snapshot.status == "EXIT_SUBMITTED"
    assert snapshot.net_result_usd == 1010.0
    assert provider.closed == [1, 2]
