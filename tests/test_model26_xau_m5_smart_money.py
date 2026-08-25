from __future__ import annotations

from types import SimpleNamespace

from application.dashboard_service import DashboardService, MT5_OPERATIONAL_MODEL_26
from application.dashboard_view_model import DashboardMT5ForexSignalRowViewModel
from application.model26_xau_m5_smart_money import (
    MODEL_26_CLOSED_CANDLES,
    MODEL_26_CONTRACT_FINGERPRINT,
    MODEL_26_ID,
    MODEL_26_SYMBOL,
    MODEL_26_TIMEFRAME,
    MODEL_26_VOLUME,
    evaluate_model26_entry,
)
from domain.candle import Candle
from domain.operational_model_policy import (
    is_active_operational_model,
    operational_model_number,
)
from infrastructure.execution.mt5_demo_execution_provider import (
    MT5DemoExecutionProvider,
)
from application.mt5_demo_robot_service import MT5DemoRobotService
from research.mt5_research_trade_plan import MT5ResearchTradePlan


def _bullish_fixture() -> list[Candle]:
    rows = []
    for index in range(201):
        price = 90.0 + index * 0.02
        rows.append(
            Candle(str(index), price, price + 0.3, price - 0.3, price + 0.05, 1)
        )

    def set_bar(index: int, open_: float, high: float, low: float, close: float) -> None:
        rows[index] = Candle(str(index), open_, high, low, close, 1)

    set_bar(178, 102, 103, 101.5, 102.5)
    set_bar(179, 103, 104, 102.5, 103.5)
    set_bar(180, 104, 105, 103.5, 104.5)
    set_bar(181, 103, 103.5, 101.5, 102)
    set_bar(182, 101, 102, 100, 101.5)
    set_bar(183, 102, 104, 101.5, 103.5)
    set_bar(184, 105, 108, 104.5, 107)
    set_bar(185, 106, 106.5, 104, 105)
    set_bar(186, 104, 104.5, 103, 104)
    set_bar(187, 104, 105, 103.5, 104.5)
    set_bar(188, 105, 105.5, 104.5, 105)
    set_bar(189, 105, 106.2, 104.8, 106)
    set_bar(190, 104.5, 104.8, 102.5, 103.5)
    set_bar(191, 106.8, 110.5, 106.8, 110)
    for index in range(192, 199):
        set_bar(index, 108 + index % 2, 109.5 + index % 2, 107.5 + index % 2, 109 + index % 2)
    set_bar(199, 106.55, 107.2, 106.5, 106.9)
    set_bar(200, 107, 107.4, 106.8, 107.1)
    return rows


def _mirror(rows: list[Candle]) -> list[Candle]:
    return [
        Candle(
            row.data,
            300 - row.abertura,
            300 - row.minima,
            300 - row.maxima,
            300 - row.fechamento,
            row.volume,
        )
        for row in rows
    ]


def _fallback_plan() -> MT5ResearchTradePlan:
    return MT5ResearchTradePlan(
        symbol="XAUUSD",
        timeframe="M5",
        direction="WAIT",
        entry_price=None,
        stop=None,
        target=None,
        risk_reward=0.0,
        stop_multiplier=0.0,
        exit_model="NONE",
        exit_score=0.0,
        exit_candidates=0,
        status="SEM_PLANO",
    )


def test_model26_contract_is_independent_xauusd_m5() -> None:
    assert MODEL_26_ID == MT5_OPERATIONAL_MODEL_26
    assert MODEL_26_SYMBOL == "XAUUSD"
    assert MODEL_26_TIMEFRAME == "M5"
    assert MODEL_26_CLOSED_CANDLES == 200
    assert MODEL_26_VOLUME == 0.10
    assert len(MODEL_26_CONTRACT_FINGERPRINT) == 16
    assert operational_model_number(MODEL_26_ID) == 26
    assert is_active_operational_model(MODEL_26_ID)


def test_model26_bullish_confluence_builds_structural_rr2_plan() -> None:
    decision = evaluate_model26_entry(_bullish_fixture())
    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.market_structure == "BULLISH"
    assert decision.initial_stop < decision.entry_price < decision.target
    assert decision.risk_reward >= 2.0
    assert decision.liquidity_sweep_ok
    assert decision.bos_displacement_ok
    assert decision.fvg_ok
    assert decision.order_block_ok
    assert decision.retest_ok


def test_model26_bearish_is_exact_directional_mirror() -> None:
    decision = evaluate_model26_entry(_mirror(_bullish_fixture()))
    assert decision.ready
    assert decision.direction == "SELL"
    assert decision.market_structure == "BEARISH"
    assert decision.target < decision.entry_price < decision.initial_stop
    assert decision.risk_reward >= 2.0


def test_model26_ignores_the_current_unfinished_candle() -> None:
    first = _bullish_fixture()
    second = list(first)
    second[-1] = Candle("CURRENT_CHANGED", 1, 1000, 0.1, 999, 999)
    decision_a = evaluate_model26_entry(first)
    decision_b = evaluate_model26_entry(second)
    assert decision_a.direction == decision_b.direction
    assert decision_a.entry_price == decision_b.entry_price
    assert decision_a.initial_stop == decision_b.initial_stop
    assert decision_a.target == decision_b.target
    assert decision_a.closed_candle_time == decision_b.closed_candle_time


def test_model26_materializes_the_same_plan_used_by_the_robot() -> None:
    service = object.__new__(DashboardService)
    object.__setattr__(
        service,
        "mt5_market_data_service",
        SimpleNamespace(latest_forex_candles={("XAUUSD", "M5"): _bullish_fixture()}),
    )
    object.__setattr__(service, "_supplemental_m5_is_seed_only", lambda _pair: False)
    row = DashboardMT5ForexSignalRowViewModel(pair="XAUUSD", timeframe="M5")
    materialized_row, plan = service._mt5_model26_smart_money_plan(
        row,
        _fallback_plan(),
    )
    assert materialized_row.decision == "BUY"
    assert plan.status == "PLANO_VALIDO"
    assert plan.stop_management == "FIXED_STOP"
    assert plan.entry_price == materialized_row.research_plan_entry_price
    assert plan.stop == materialized_row.research_plan_stop
    assert plan.target == materialized_row.research_plan_target


def test_provider_persists_m26_identity_in_mt5_comment() -> None:
    provider = object.__new__(MT5DemoExecutionProvider)
    assert provider._model_comment(MODEL_26_ID) == "M26"


def test_robot_uses_explicit_m26_volume() -> None:
    robot = object.__new__(MT5DemoRobotService)
    robot.volume = 0.99
    signal = SimpleNamespace(operational_model=MODEL_26_ID)
    plan = SimpleNamespace(operational_model=MODEL_26_ID)
    assert robot._execution_volume(signal, plan) == 0.10


def test_shared_snapshot_reuses_m26_decision() -> None:
    service = object.__new__(DashboardService)
    object.__setattr__(
        service,
        "mt5_market_data_service",
        SimpleNamespace(latest_forex_candles={("XAUUSD", "M5"): _bullish_fixture()}),
    )
    object.__setattr__(service, "_supplemental_m5_is_seed_only", lambda _pair: False)
    object.__setattr__(
        service,
        "_mt5_entry_source_models_to_evaluate",
        lambda: (MODEL_26_ID,),
    )
    snapshot = service.get_xau_m5_operational_decision_snapshot()
    assert snapshot[(MODEL_26_ID, "XAUUSD")].ready
    assert snapshot[("__XAU_M5__", "CANDLE_COUNT")] == 201


def test_provider_blocks_m26_outside_xauusd_m5() -> None:
    provider = object.__new__(MT5DemoExecutionProvider)
    invalid = SimpleNamespace(
        operational_model=MODEL_26_ID,
        symbol="EURUSD",
        plan_snapshot={"timeframe": "M5"},
    )
    valid = SimpleNamespace(
        operational_model=MODEL_26_ID,
        symbol="XAUUSD",
        plan_snapshot={"timeframe": "M5"},
    )
    assert provider._model26_scope_preflight(valid) is None
    rejection = provider._model26_scope_preflight(invalid)
    assert rejection is not None
    assert not rejection.accepted


def test_m26_contract_is_registered_in_governance() -> None:
    marker = (
        "M26_CONTRACT=M26_SMART_MONEY_V1_20260825; "
        f"FINGERPRINT={MODEL_26_CONTRACT_FINGERPRINT}"
    )
    for path in (
        "governance/execution/PROJECT_STATUS.md",
        "governance/execution/NEXT_MISSION.md",
        "governance/programs/PROGRAM_STATUS.md",
    ):
        assert marker in open(path, encoding="utf-8").read()
