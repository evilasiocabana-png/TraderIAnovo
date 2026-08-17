from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from application.model24_xau_basket import (
    MODEL_24_ID,
    Model24BasketManager,
    evaluate_model24_rsi50_market_entry,
    model24_order_comment,
    model24_previous_candle_stop,
    model24_variant_id,
)
from application.dashboard_service import (
    DashboardService,
    MT5_MODEL_24_SOURCE_MODEL_IDS,
    MT5_OPERATIONAL_MODEL_8,
    MT5_OPERATIONAL_MODEL_24,
    MT5_OPERATIONAL_MODEL_WITH_24,
)
from application.dashboard_view_model import (
    DashboardMT5ForexSignalRowViewModel,
)
from research.mt5_research_trade_plan import MT5ResearchTradePlan
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
    operational_model_number,
)


def _buy_cross_candles(*, micro_pivot: bool = True) -> list[dict[str, float]]:
    closes = [
        100.0 + index * 0.002 + (-0.2 if index % 2 == 0 else 0.2)
        for index in range(199)
    ]
    closes.append(closes[-1] + 0.3)
    rows: list[dict[str, float]] = []
    for index, close in enumerate(closes):
        low = close - 0.1
        if index == 198 and micro_pivot:
            low = closes[index] - 0.5
        if not micro_pivot and index >= 192:
            low = 99.0 + (index - 192) * 0.05
        rows.append(
            {
                "time": float(1_700_000_000 + index * 300),
                "open": close,
                "high": close + 0.1,
                "low": low,
                "close": close,
            }
        )
    rows.append(
        {
            "time": float(1_700_000_000 + 200 * 300),
            "open": closes[-1],
            "high": closes[-1] + 0.1,
            "low": closes[-1] - 0.1,
            "close": closes[-1],
        }
    )
    return rows


def test_initial_entry_requires_micro_pivot_and_rsi50_cross() -> None:
    candles = _buy_cross_candles()
    decision = evaluate_model24_rsi50_market_entry(
        candles,
        entry_role="INITIAL",
    )

    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.previous_rsi14 is not None and decision.previous_rsi14 < 50.0
    assert decision.rsi14 is not None and decision.rsi14 > 50.0
    assert decision.entry_price is not None and decision.sma20 is not None
    assert decision.entry_price > decision.sma20
    assert decision.initial_stop == candles[-3]["low"]
    assert "INITIAL" in decision.status


def test_initial_entry_does_not_fallback_without_confirmed_micro_pivot() -> None:
    decision = evaluate_model24_rsi50_market_entry(
        _buy_cross_candles(micro_pivot=False),
        entry_role="INITIAL",
    )

    assert not decision.ready
    assert decision.status == "M24_INITIAL_AGUARDA_MICRO_PIVO_CONFIRMADO"


def test_rsi50_reentry_uses_previous_candle_extreme() -> None:
    candles = _buy_cross_candles(micro_pivot=False)
    decision = evaluate_model24_rsi50_market_entry(candles, entry_role="REENTRY")
    candidate, candle_time = model24_previous_candle_stop(candles, "BUY")

    assert decision.ready
    assert decision.initial_stop == candles[-3]["low"]
    assert candidate == candles[-2]["low"]
    assert candle_time != "N/D"


class _ExecutionStub:
    def __init__(self) -> None:
        self.positions = [
            SimpleNamespace(
                comment="TraderIA M24 S8",
                profit=1005.0,
                swap=-2.0,
                commission=-1.0,
                fee=0.0,
                symbol="XAUUSD",
                ticket=24,
                type=0,
                volume=0.1,
            ),
            SimpleNamespace(
                comment="TraderIA M23 S8",
                profit=5000.0,
                swap=0.0,
                commission=0.0,
                fee=0.0,
                symbol="XAUUSD",
                ticket=23,
                type=0,
                volume=0.1,
            ),
        ]
        self.closed: list[int] = []

    def list_open_positions(self) -> list[object]:
        return self.positions

    def close_position(self, **kwargs: object) -> object:
        self.closed.append(int(kwargs["ticket"]))
        return SimpleNamespace(accepted=True, message="ok")


def test_basket_full_exit_isolated_from_m23(tmp_path: Path) -> None:
    execution = _ExecutionStub()
    snapshot = Model24BasketManager(
        execution_service=execution,
        state_path=tmp_path / "state.json",
        audit_path=tmp_path / "audit.jsonl",
    ).evaluate_once()

    assert snapshot.status == "EXIT_SUBMITTED"
    assert execution.closed == [24]
    assert snapshot.net_result_usd == 1002.0


def test_identity_and_comment_are_source_specific() -> None:
    variant = model24_variant_id("MODELO_20_XAU_M5_SMA_RSI_MA_DISTANCE_ATR_REENTRY_TP75")
    assert variant == f"{MODEL_24_ID}_SOURCE_M20"
    assert model24_order_comment(variant) == "TraderIA M24 S20"
    assert operational_model_number(MODEL_24_ID) == 24
    assert is_active_operational_model(variant)
    assert not is_retired_operational_model(variant)


def test_service_selects_only_the_seven_m24_sources() -> None:
    service = object.__new__(DashboardService)
    service.set_mt5_operational_model(MT5_OPERATIONAL_MODEL_24)

    assert service._mt5_operational_models_to_evaluate() == MT5_MODEL_24_SOURCE_MODEL_IDS
    assert service._mt5_model24_routing_enabled()
    assert not service._mt5_direct_routing_enabled()

    service.set_mt5_operational_models(
        list(MT5_MODEL_24_SOURCE_MODEL_IDS),
        direct_models_enabled=True,
    )
    service.set_mt5_operational_model(MT5_OPERATIONAL_MODEL_WITH_24)
    assert service.get_mt5_operational_model() == MT5_OPERATIONAL_MODEL_WITH_24
    assert service._mt5_direct_routing_enabled()


def _source_row() -> DashboardMT5ForexSignalRowViewModel:
    return DashboardMT5ForexSignalRowViewModel(
        pair="XAUUSD",
        status="OK",
        timeframe="M5",
        decision="WAIT",
        theoretical_entry_direction="WAIT",
    )


def _source_plan(**changes: object) -> MT5ResearchTradePlan:
    values = {
        "symbol": "XAUUSD",
        "timeframe": "M5",
        "direction": "WAIT",
        "entry_price": None,
        "stop": None,
        "target": None,
        "risk_reward": 0.0,
        "stop_multiplier": 0.0,
        "exit_model": "M8_EXIT",
        "exit_score": 0.0,
        "exit_candidates": 1,
        "status": "WAIT",
        "stop_management": "M8_SMA_RSI_FULL_EXIT",
        "stop_management_parameters": {},
    }
    values.update(changes)
    return MT5ResearchTradePlan(**values)


def test_service_materializes_initial_m24_without_individual_tp() -> None:
    service = object.__new__(DashboardService)
    object.__setattr__(
        service,
        "mt5_market_data_service",
        SimpleNamespace(
            latest_forex_candles={("XAUUSD", "M5"): _buy_cross_candles()}
        ),
    )

    row, plan = service._mt5_model24_variant_from_source(
        _source_row(),
        _source_plan(),
        source_operational_model=MT5_OPERATIONAL_MODEL_8,
        source_ready=False,
    )

    assert row.decision == "BUY"
    assert plan.status == "PLANO_VALIDO"
    assert plan.target == 0.0
    assert plan.stop_management_parameters["m24_entry_role"] == "INITIAL"
    assert not plan.stop_management_parameters["m24_reentry_position"]
    assert not plan.stop_management_parameters["m24_individual_target_enabled"]


def test_service_strips_structural_reentry_target_for_m24() -> None:
    candles = _buy_cross_candles()
    # Remove o cruzamento RSI50 do ultimo candle para deixar a reentrada Stop prevalecer.
    candles[-2]["close"] = candles[-3]["close"] - 0.1
    service = object.__new__(DashboardService)
    object.__setattr__(
        service,
        "mt5_market_data_service",
        SimpleNamespace(latest_forex_candles={("XAUUSD", "M5"): candles}),
    )
    source_plan = _source_plan(
        direction="BUY",
        entry_price=101.0,
        stop=99.0,
        target=105.0,
        status="PLANO_VALIDO",
        stop_management_parameters={"active_entry_order_type": "BUY_STOP"},
    )
    source_row = _source_row()
    object.__setattr__(source_row, "decision", "BUY")

    _row, plan = service._mt5_model24_variant_from_source(
        source_row,
        source_plan,
        source_operational_model=MT5_OPERATIONAL_MODEL_8,
        source_ready=True,
    )

    assert plan.target == 0.0
    assert plan.stop_management_parameters["m24_entry_role"] == "STRUCTURAL_REENTRY"
    assert plan.stop_management_parameters["m24_reentry_position"]
