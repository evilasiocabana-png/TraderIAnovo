from __future__ import annotations

import math
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from application.model24_xau_basket import (
    MODEL_24_ID,
    Model24BasketManager,
    evaluate_model24_pending_reentry,
    evaluate_model24_reentry_opportunity,
    evaluate_model24_rsi50_market_entry,
    mark_model24_extreme_full_exit,
    mark_model24_market_entry_accepted,
    model24_micro_pivot_stop,
    model24_order_comment,
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


def _separate_buy_cross_candles() -> list[dict[str, float]]:
    closes = [100.0]
    for index in range(1, 200):
        drift = -0.02 if index < 160 else 0.003
        closes.append(closes[-1] + drift + 0.03 * math.sin(index * 0.3))
    rows = [
        {
            "time": float(1_700_000_000 + index * 300),
            "open": close,
            "high": close + 0.1,
            "low": close - (0.5 if index == 198 else 0.1),
            "close": close,
        }
        for index, close in enumerate(closes)
    ]
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


def test_initial_entry_latches_price_and_rsi_crosses_from_different_m5() -> None:
    candles = _separate_buy_cross_candles()
    decision = evaluate_model24_rsi50_market_entry(
        candles,
        entry_role="INITIAL",
    )

    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.rsi14 is not None and decision.rsi14 > 50.0
    assert decision.entry_price is not None and decision.sma20 is not None
    assert decision.entry_price > decision.sma20
    assert decision.initial_stop == candles[-3]["low"]
    assert decision.price_cross_time != decision.rsi_cross_time
    assert decision.price_cross_time != "N/D"
    assert decision.rsi_cross_time != "N/D"
    assert "INITIAL" in decision.status


def test_initial_entry_does_not_fallback_without_confirmed_micro_pivot() -> None:
    decision = evaluate_model24_rsi50_market_entry(
        _buy_cross_candles(micro_pivot=False),
        entry_role="INITIAL",
    )

    assert not decision.ready
    assert decision.status == "M24_INITIAL_AGUARDA_MICRO_PIVO_CONFIRMADO"


def test_pending_reentry_uses_price_side_of_sma20_and_nearest_micro_pivot() -> None:
    candles = _buy_cross_candles()
    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(60.0, 59.0),
    ):
        decision = evaluate_model24_rsi50_market_entry(candles, entry_role="REENTRY")
    candidate, candle_time = model24_micro_pivot_stop(candles, "BUY")

    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.rsi14 == 60.0
    assert decision.entry_price == candles[-2]["high"]
    assert decision.initial_stop == candles[-3]["low"]
    assert candidate == candles[-3]["low"]
    assert candle_time != "N/D"


def test_pending_buy_reentry_requires_rsi_to_remain_above_50() -> None:
    candles = _buy_cross_candles()
    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(40.0, 39.0),
    ):
        decision = evaluate_model24_pending_reentry(candles)

    assert not decision.ready
    assert decision.status == "M24_REENTRY_AGUARDA_PRECO_SMA20_E_RSI50_ALINHADOS"


def test_rsi50_reentry_waits_without_confirmed_micro_pivot() -> None:
    decision = evaluate_model24_rsi50_market_entry(
        _buy_cross_candles(micro_pivot=False),
        entry_role="REENTRY",
    )

    assert not decision.ready
    assert decision.status == "M24_REENTRY_AGUARDA_MICRO_PIVO_CONFIRMADO"


def test_micro_pivot_stop_finds_confirmed_micro_top_for_sell() -> None:
    candles = [
        {"time": 1.0, "high": 100.0, "low": 98.0},
        {"time": 2.0, "high": 105.0, "low": 99.0},
        {"time": 3.0, "high": 102.0, "low": 97.0},
        {"time": 4.0, "high": 103.0, "low": 98.0},
    ]

    candidate, candle_time = model24_micro_pivot_stop(candles, "SELL")

    assert candidate == 105.0
    assert candle_time != "N/D"


def test_pending_sell_reentry_uses_low_and_nearest_previous_micro_top() -> None:
    candles = _buy_cross_candles()
    candles[-2]["close"] = 99.0
    candles[-2]["low"] = 98.8
    candles[-3]["high"] = 105.0
    with patch(
        "application.model24_xau_basket._sma",
        side_effect=(100.0, 101.0),
    ), patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(40.0, 41.0),
    ):
        decision = evaluate_model24_pending_reentry(candles)

    assert decision.ready
    assert decision.direction == "SELL"
    assert decision.entry_price == 98.8
    assert decision.initial_stop == 105.0
    assert "SELL_STOP" in decision.status


def test_micro_pivot_stop_prefers_nearest_confirmed_pivot() -> None:
    candles = [
        {"time": 1.0, "low": 100.0, "high": 102.0},
        {"time": 2.0, "low": 98.0, "high": 101.0},
        {"time": 3.0, "low": 90.0, "high": 100.0},
        {"time": 4.0, "low": 99.0, "high": 101.0},
        {"time": 5.0, "low": 98.0, "high": 102.0},
        {"time": 6.0, "low": 95.0, "high": 101.0},
        {"time": 7.0, "low": 97.0, "high": 103.0},
        {"time": 8.0, "low": 98.0, "high": 104.0},
    ]

    candidate, candle_time = model24_micro_pivot_stop(candles, "BUY")

    assert candidate == 95.0
    assert candle_time != "N/D"


def test_first_reentry_after_extreme_exit_is_skipped_on_both_sides(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "model24_runtime_state.json"
    cases = (
        (
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY",
        ),
        (
            "MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR",
            "SELL",
            "M8_EXIT_RSI30_CRUZOU_PARA_CIMA_SELL",
        ),
    )
    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        state_path,
    ):
        for source, side, exit_status in cases:
            mark_model24_market_entry_accepted(source, side, "entrada-inicial")
            mark_model24_extreme_full_exit(
                source,
                side,
                exit_status,
                "saida-extrema",
            )

            first = evaluate_model24_reentry_opportunity(
                source,
                side,
                f"REENTRY|{side}|candle-1|MARKET",
            )
            repeated = evaluate_model24_reentry_opportunity(
                source,
                side,
                f"REENTRY|{side}|candle-1|MARKET",
            )
            second = evaluate_model24_reentry_opportunity(
                source,
                side,
                f"REENTRY|{side}|candle-2|MARKET",
            )

            assert not first.allowed
            assert first.status == "M24_REENTRY_PRIMEIRA_OPORTUNIDADE_IGNORADA"
            assert not repeated.allowed
            assert second.allowed
            assert second.status == "M24_REENTRY_SEGUNDA_OPORTUNIDADE_LIBERADA"


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


def test_basket_state_write_retries_short_windows_lock(tmp_path: Path) -> None:
    execution = _ExecutionStub()
    execution.positions = []
    state_path = tmp_path / "state.json"
    real_replace = os.replace
    attempts = 0

    def flaky_replace(source: object, target: object) -> None:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError(5, "arquivo temporariamente ocupado")
        real_replace(source, target)

    with patch("application.model24_xau_basket.os.replace", side_effect=flaky_replace):
        snapshot = Model24BasketManager(
            execution_service=execution,
            state_path=state_path,
            audit_path=tmp_path / "audit.jsonl",
        ).evaluate_once()

    assert snapshot.status == "WAITING_NEW_ROUND"
    assert attempts == 2
    assert state_path.exists()


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


def test_service_materializes_initial_m24_without_individual_tp(
    tmp_path: Path,
) -> None:
    service = object.__new__(DashboardService)
    object.__setattr__(
        service,
        "mt5_market_data_service",
        SimpleNamespace(
            latest_forex_candles={("XAUUSD", "M5"): _buy_cross_candles()}
        ),
    )

    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        tmp_path / "runtime.json",
    ):
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


def test_service_builds_pending_reentry_from_price_above_sma20(tmp_path: Path) -> None:
    candles = _buy_cross_candles()
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

    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        tmp_path / "runtime.json",
    ):
        mark_model24_market_entry_accepted(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "entrada-inicial",
        )
        _row, plan = service._mt5_model24_variant_from_source(
            source_row,
            source_plan,
            source_operational_model=MT5_OPERATIONAL_MODEL_8,
            source_ready=False,
        )

    assert plan.target == 0.0
    assert plan.entry_price == candles[-2]["high"]
    assert plan.stop == candles[-3]["low"]
    assert plan.stop_management_parameters["active_entry_order_type"] == "BUY_STOP"
    assert plan.stop_management_parameters["m24_entry_role"] == "REENTRY"
    assert plan.stop_management_parameters["m24_reentry_position"]
    assert plan.stop_management_parameters["m24_micro_pivot_stop_enabled"]


def test_service_blocks_pending_reentry_without_micro_pivot(tmp_path: Path) -> None:
    candles = _buy_cross_candles(micro_pivot=False)
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

    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        tmp_path / "runtime.json",
    ):
        mark_model24_market_entry_accepted(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "entrada-inicial",
        )
        _row, plan = service._mt5_model24_variant_from_source(
            _source_row(),
            source_plan,
            source_operational_model=MT5_OPERATIONAL_MODEL_8,
            source_ready=False,
        )

    assert plan.direction == "WAIT"
    assert plan.status == "M24_REENTRY_AGUARDA_MICRO_PIVO_CONFIRMADO"
    assert plan.stop is None


def test_service_keeps_first_post_extreme_reentry_blocked_until_new_m5(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "model24_runtime_state.json"
    candles = _buy_cross_candles()
    service = object.__new__(DashboardService)
    object.__setattr__(
        service,
        "mt5_market_data_service",
        SimpleNamespace(latest_forex_candles={("XAUUSD", "M5"): candles}),
    )
    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        state_path,
    ):
        mark_model24_market_entry_accepted(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "entrada-inicial",
        )
        mark_model24_extreme_full_exit(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY",
            "saida-extrema",
        )

        _row, first = service._mt5_model24_variant_from_source(
            _source_row(),
            _source_plan(),
            source_operational_model=MT5_OPERATIONAL_MODEL_8,
            source_ready=False,
        )
        _row, repeated = service._mt5_model24_variant_from_source(
            _source_row(),
            _source_plan(),
            source_operational_model=MT5_OPERATIONAL_MODEL_8,
            source_ready=False,
        )
        for candle in candles:
            candle["time"] += 300.0
        _row, second = service._mt5_model24_variant_from_source(
            _source_row(),
            _source_plan(),
            source_operational_model=MT5_OPERATIONAL_MODEL_8,
            source_ready=False,
        )

    assert first.status == "M24_REENTRY_PRIMEIRA_OPORTUNIDADE_IGNORADA"
    assert repeated.status == "M24_REENTRY_PRIMEIRA_OPORTUNIDADE_IGNORADA"
    assert second.status == "PLANO_VALIDO"
    assert second.direction == "BUY"
