from __future__ import annotations

import math
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from application.model24_setup_contract import (
    MODEL_24_SETUP_CONTRACT_FINGERPRINT,
    MODEL_24_SETUP_CONTRACT_VERSION,
)
from application.model24_xau_basket import (
    MODEL_24_ID,
    Model24EntryDecision,
    Model24BasketManager,
    evaluate_model24_continuation,
    evaluate_model24_pending_reentry,
    evaluate_model24_reentry_opportunity,
    evaluate_model24_rsi50_market_entry,
    mark_model24_extreme_full_exit,
    mark_model24_continuation_accepted,
    mark_model24_continuation_target_exit_confirmed,
    mark_model24_market_entry_accepted,
    mark_model24_reentry_target_armed,
    model24_continuation_watch,
    model24_market_entry_role,
    model24_micro_pivot_stop,
    model24_sma20_stop_after_two_closes,
    model24_order_comment,
    model24_variant_id,
    _load_runtime_state,
    _model24_distance_atr,
    _model24_reentry_structural_target,
    _time,
)
from application.dashboard_service import (
    DashboardService,
    MT5_MODEL_24_SOURCE_MODEL_IDS,
    MT5_MODEL_25_SOURCE_MODEL_IDS,
    MT5_OPERATIONAL_MODEL_8,
    MT5_OPERATIONAL_MODEL_24,
    MT5_OPERATIONAL_MODEL_25,
    MT5_OPERATIONAL_MODEL_WITH_24,
)
from application.dashboard_view_model import (
    DashboardDemoRobotViewModel,
    DashboardMT5ForexSignalRowViewModel,
)
from research.mt5_research_trade_plan import MT5ResearchTradePlan
from domain.operational_model_policy import (
    is_active_operational_model,
    is_retired_operational_model,
    operational_model_number,
)
from domain.candle import Candle


class _M24MT5RecordWithMemoryViewData:
    data = memoryview(b"mt5")

    def __getitem__(self, field: str) -> object:
        if field == "time":
            return 1_776_211_200
        raise KeyError(field)


def test_m24_time_prefers_stable_mt5_field_over_memoryview_data() -> None:
    assert _time(_M24MT5RecordWithMemoryViewData()) == "2026-04-15T00:00:00+00:00"


def test_runtime_load_sanitizes_legacy_memory_addresses(tmp_path: Path) -> None:
    state_path = tmp_path / "model24_runtime_state.json"
    state_path.write_text(
        json.dumps(
            {
                "last_initial_candle": "<memory at 0xAAA>",
                "sources": {
                    "M24_PROPRIO": {
                        "trend_side": "BUY",
                        "last_entry_candle": "<memory at 0xBBB>",
                        "last_extreme_exit_status": (
                            "M8_EXIT_RSI70_CRUZOU_PARA_BAIXO_BUY"
                        ),
                        "last_extreme_exit_candle": "<memory at 0xCCC>",
                        "last_extreme_exit_event_key": "BUY|EXIT|<memory at 0xCCC>",
                        "blocked_reentry_opportunity_key": (
                            "REENTRY|BUY|<memory at 0xDDD>"
                        ),
                        "skip_first_reentry_after_extreme": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        state_path,
    ):
        payload = _load_runtime_state()

    state = payload["sources"]["M24_PROPRIO"]
    assert payload["setup_contract_version"] == MODEL_24_SETUP_CONTRACT_VERSION
    assert (
        payload["setup_contract_fingerprint"]
        == MODEL_24_SETUP_CONTRACT_FINGERPRINT
    )
    assert payload["last_initial_candle"] == "N/D"
    assert state["last_entry_candle"] == "N/D"
    assert state["last_extreme_exit_candle"] == "N/D"
    assert state["last_extreme_exit_event_key"].endswith("|N/D")
    assert state["blocked_reentry_opportunity_key"] == ""
    assert state["skip_first_reentry_after_extreme"] is False
    persisted = json.loads(state_path.read_text(encoding="utf-8"))
    persisted_state = persisted["sources"]["M24_PROPRIO"]
    assert (
        persisted["setup_contract_version"]
        == MODEL_24_SETUP_CONTRACT_VERSION
    )
    assert (
        persisted["setup_contract_fingerprint"]
        == MODEL_24_SETUP_CONTRACT_FINGERPRINT
    )
    assert persisted_state["last_extreme_exit_candle"] == "N/D"
    assert "<memory at " not in json.dumps(persisted)


def test_sma20_stop_is_released_after_two_buy_closes_above_average() -> None:
    rows = [
        {"time": float(index), "close": float(100 + index)}
        for index in range(21)
    ]
    rows.append({"time": 21.0, "close": 121.0})

    stop, candle_time = model24_sma20_stop_after_two_closes(rows, "BUY")

    assert stop == pytest.approx(110.5)
    assert candle_time != "N/D"


def test_sma20_stop_is_released_after_two_sell_closes_below_average() -> None:
    rows = [
        {"time": float(index), "close": float(120 - index)}
        for index in range(21)
    ]
    rows.append({"time": 21.0, "close": 99.0})

    stop, candle_time = model24_sma20_stop_after_two_closes(rows, "SELL")

    assert stop == pytest.approx(109.5)
    assert candle_time != "N/D"


def test_sma20_stop_waits_until_both_closed_candles_are_favorable() -> None:
    rows = [
        {"time": float(index), "close": 100.0}
        for index in range(19)
    ]
    rows.extend(
        [
            {"time": 19.0, "close": 99.0},
            {"time": 20.0, "close": 101.0},
            {"time": 21.0, "close": 101.0},
        ]
    )

    stop, _candle_time = model24_sma20_stop_after_two_closes(rows, "BUY")

    assert stop is None


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


def _set_valid_buy_structural_close_target(
    candles: list[dict[str, float]],
) -> None:
    """Cria topo principal 2+2 cujo fechamento fica acima do BUY_STOP."""
    trigger = float(candles[-2]["high"])
    candles[-5]["close"] = trigger + 1.0
    candles[-5]["high"] = trigger + 1.1


@pytest.fixture(autouse=True)
def _legacy_scenarios_pass_the_new_distance_gate():
    """Mantem cada teste antigo focado em sua regra original."""
    with patch(
        "application.model24_xau_basket._model24_distance_atr",
        return_value=0.50,
    ):
        yield


def test_m24_distance_atr_is_absolute_and_does_not_define_direction() -> None:
    assert _model24_distance_atr(102.0, 100.0, 4.0) == 0.50
    assert _model24_distance_atr(100.0, 102.0, 4.0) == 0.50


def test_m24_blocks_entry_when_average_distance_is_below_quarter_atr() -> None:
    candles = _buy_cross_candles()
    with patch(
        "application.model24_xau_basket._model24_distance_atr",
        return_value=0.2499,
    ):
        decision = evaluate_model24_rsi50_market_entry(candles)

    assert not decision.ready
    assert decision.status == "M24_DISTANCE_ATR_BLOQUEADO"
    assert decision.distance_atr == 0.2499


def test_m24_buy_can_pass_with_sma20_below_sma50_when_distance_is_valid() -> None:
    candles = _buy_cross_candles()
    candles[-2]["open"] = candles[-2]["close"] + 0.05
    _set_valid_buy_structural_close_target(candles)
    with patch(
        "application.model24_xau_basket._sma",
        side_effect=(99.0, 101.0),
    ), patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(60.0, 59.0),
    ):
        decision = evaluate_model24_pending_reentry(candles)

    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.sma20 < decision.sma50
    assert decision.distance_atr == 0.50


def test_initial_entry_uses_price_cross_current_rsi_and_cross_candle_stop() -> None:
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
    assert decision.micro_swing_price is not None
    assert decision.initial_stop == decision.micro_swing_price - 0.01
    assert decision.price_cross_time != "N/D"
    assert decision.rsi_cross_time != "N/D"
    assert decision.price_cross_time != decision.rsi_cross_time
    assert "INITIAL" in decision.status


def test_m24_initial_requires_a_new_rsi_cross_but_not_micro_pivot() -> None:
    candles = _buy_cross_candles(micro_pivot=False)

    with patch(
        "application.model24_xau_basket._wilder_rsi",
        return_value=60.0,
    ):
        decision = evaluate_model24_rsi50_market_entry(
            candles,
            entry_role="INITIAL",
        )

    assert not decision.ready
    assert decision.direction == "WAIT"
    assert decision.status == (
        "M24_INITIAL_AGUARDA_CRUZAMENTOS_PRECO_SMA20_E_RSI50"
    )
    assert decision.rsi_cross_time == "N/D"


def test_m24_initial_accepts_distance_exactly_quarter_atr() -> None:
    with patch(
        "application.model24_xau_basket._model24_distance_atr",
        return_value=0.25,
    ):
        decision = evaluate_model24_rsi50_market_entry(
            _separate_buy_cross_candles(),
            entry_role="INITIAL",
        )

    assert decision.ready
    assert decision.distance_atr == 0.25
    assert decision.price_cross_time != decision.rsi_cross_time


def test_initial_entry_accepts_canonical_candle_with_portuguese_fields() -> None:
    rows = [
        Candle(
            data=str(row["time"]),
            abertura=row["open"],
            maxima=row["high"],
            minima=row["low"],
            fechamento=row["close"],
            volume=1,
        )
        for row in _separate_buy_cross_candles()
    ]

    decision = evaluate_model24_rsi50_market_entry(rows)

    assert decision.ready
    assert decision.direction == "BUY"
    assert decision.status != "M24_DADOS_INVALIDOS"
    assert decision.closed_candle_time != "N/D"


def test_initial_entry_uses_cross_candle_even_without_confirmed_micro_pivot() -> None:
    decision = evaluate_model24_rsi50_market_entry(
        _buy_cross_candles(micro_pivot=False),
        entry_role="INITIAL",
    )

    assert decision.ready
    assert decision.status == "M24_INITIAL_BUY_PRECO_SMA20_RSI50_MERCADO_PRONTA"


def test_pending_reentry_uses_last_closed_candle_for_trigger_and_stop() -> None:
    candles = _buy_cross_candles()
    candles[-2]["open"] = candles[-2]["close"] + 0.05
    _set_valid_buy_structural_close_target(candles)
    target_candle = max(candles[-7:-2], key=lambda row: row["high"])
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
    assert candidate is not None
    assert decision.initial_stop == candidate - 0.01
    assert decision.structural_target_price == target_candle["close"]
    assert decision.structural_target_price > decision.entry_price
    assert candidate == candles[-3]["low"]
    assert candle_time != "N/D"


def test_pending_reentry_waits_without_structural_target() -> None:
    candles = _buy_cross_candles()
    candles[-2]["open"] = candles[-2]["close"] + 0.05

    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(60.0, 59.0),
    ), patch(
        "application.model24_xau_basket._model24_reentry_structural_target",
        return_value=(None, "N/D"),
    ):
        decision = evaluate_model24_pending_reentry(candles)

    assert not decision.ready
    assert decision.direction == "BUY"
    assert decision.entry_price == candles[-2]["high"]
    assert decision.structural_target_price is None
    assert decision.status == "M24_REENTRY_AGUARDA_ALVO_ESTRUTURAL_VALIDO"


@pytest.mark.parametrize(
    ("side", "current_rsi", "previous_rsi"),
    (("BUY", 75.0, 69.0), ("SELL", 25.0, 31.0)),
)
def test_continuation_enters_after_confirmed_reentry_tp_with_extreme_rsi(
    side: str,
    current_rsi: float,
    previous_rsi: float,
) -> None:
    candles = _buy_cross_candles()
    if side == "SELL":
        candles = [
            {
                **row,
                "open": 200.0 - row["open"],
                "high": 200.0 - row["low"],
                "low": 200.0 - row["high"],
                "close": 200.0 - row["close"],
            }
            for row in candles
        ]
    current_close = float(candles[-2]["close"])
    target = current_close - 0.10 if side == "BUY" else current_close + 0.10

    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(current_rsi, previous_rsi),
    ):
        decision = evaluate_model24_continuation(
            candles,
            watch={"side": side, "target_price": target},
            target_exit_confirmed=True,
        )

    assert decision.ready
    assert decision.direction == side
    assert "CONTINUATION" in decision.status
    assert decision.entry_price == current_close
    assert decision.structural_target_price is None
    previous_candle = candles[-2]
    if side == "BUY":
        assert decision.micro_swing_price == previous_candle["low"]
        assert decision.initial_stop == pytest.approx(
            previous_candle["low"] - 0.01
        )
    else:
        assert decision.micro_swing_price == previous_candle["high"]
        assert decision.initial_stop == pytest.approx(
            previous_candle["high"] + 0.01
        )


def test_continuation_fails_closed_until_mt5_confirms_tp_exit() -> None:
    candles = _buy_cross_candles()
    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(75.0, 69.0),
    ):
        decision = evaluate_model24_continuation(
            candles,
            watch={
                "side": "BUY",
                "target_price": float(candles[-2]["close"]) - 0.10,
            },
            target_exit_confirmed=False,
        )

    assert not decision.ready
    assert decision.status == "M24_CONTINUATION_AGUARDA_FECHAMENTO_TP_CONFIRMADO"


def test_continuation_watch_is_armed_and_consumed_persistently(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "model24_runtime_state.json"
    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        state_path,
    ):
        mark_model24_reentry_target_armed(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            3500.0,
            "topo-anterior",
            "reentry-aceita",
        )
        armed = model24_continuation_watch(MT5_OPERATIONAL_MODEL_8)
        mark_model24_continuation_target_exit_confirmed(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            3500.0,
        )
        confirmed = model24_continuation_watch(MT5_OPERATIONAL_MODEL_8)
        mark_model24_continuation_accepted(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "continuation-aceita",
        )
        consumed = model24_continuation_watch(MT5_OPERATIONAL_MODEL_8)

    assert armed["side"] == "BUY"
    assert armed["target_price"] == 3500.0
    assert not armed["target_exit_confirmed"]
    assert confirmed["target_exit_confirmed"]
    assert consumed == {}


def test_pending_buy_reentry_requires_rsi_to_remain_above_50() -> None:
    candles = _buy_cross_candles()
    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(40.0, 39.0),
    ):
        decision = evaluate_model24_pending_reentry(candles)

    assert not decision.ready
    assert decision.status == "M24_REENTRY_AGUARDA_PRECO_SMA20_E_FAIXA_RSI"


def test_rsi50_reentry_waits_without_confirmed_micro_pivot_for_stop() -> None:
    candles = _buy_cross_candles(micro_pivot=False)
    candles[-2]["open"] = candles[-2]["close"] + 0.05
    _set_valid_buy_structural_close_target(candles)
    decision = evaluate_model24_rsi50_market_entry(
        candles,
        entry_role="REENTRY",
    )

    assert not decision.ready
    assert decision.status == "M24_REENTRY_AGUARDA_MICRO_PIVO_1X1"


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


def test_pending_sell_reentry_uses_last_closed_low_and_high_for_stop() -> None:
    candles = _buy_cross_candles()
    candles[-2]["close"] = 99.0
    candles[-2]["open"] = 98.9
    candles[-2]["low"] = 98.8
    candles[-3]["high"] = 105.0
    candles[-4]["low"] = 98.0
    candles[-4]["close"] = 98.2
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
    assert decision.initial_stop == candles[-3]["high"] + 0.01
    assert decision.structural_target_price == 98.2
    assert "SELL_STOP" in decision.status


def test_reentry_target_uses_close_of_confirmed_micro_bottom_not_its_low() -> None:
    rows = [
        {"time": index, "high": high, "low": low, "close": close}
        for index, (high, low, close) in enumerate(
            (
                (110.0, 105.0, 107.0),
                (108.0, 102.0, 104.0),
                (106.0, 100.0, 103.0),
                (107.0, 101.0, 105.0),
                (109.0, 103.0, 108.0),
                (111.0, 105.0, 110.0),
                (110.0, 104.0, 106.0),
                (109.0, 103.0, 105.0),
            )
        )
    ]

    target, target_time = _model24_reentry_structural_target(
        rows,
        "SELL",
        108.0,
    )

    assert target == 103.0
    assert target != 100.0
    assert target_time != "N/D"


def test_reentry_target_prefers_latest_profitable_micro_bottom() -> None:
    rows = [
        {"time": index, "high": 120.0 + index, "low": 110.0 + index, "close": 115.0 + index}
        for index in range(12)
    ]
    rows[2].update({"low": 90.0, "close": 95.0})
    rows[7].update({"low": 97.0, "close": 99.0})
    rows[6].update({"low": 101.0, "close": 103.0})
    rows[8].update({"low": 100.0, "close": 102.0})

    target, _ = _model24_reentry_structural_target(rows, "SELL", 110.0)

    assert target == 99.0


def test_reentry_buy_target_uses_close_of_latest_micro_top() -> None:
    rows = [
        {"time": index, "high": high, "low": 90.0, "close": close}
        for index, (high, close) in enumerate(
            ((100.0, 98.0), (105.0, 103.0), (102.0, 101.0), (104.0, 102.0))
        )
    ]

    target, target_time = _model24_reentry_structural_target(rows, "BUY", 101.0)

    assert target == 103.0
    assert target != 105.0
    assert target_time != "N/D"


def test_reentry_target_does_not_skip_invalid_latest_micro_top() -> None:
    rows = [
        {"time": "1", "high": 100.0, "low": 95.0, "close": 98.0},
        {"time": "2", "high": 110.0, "low": 97.0, "close": 108.0},
        {"time": "3", "high": 105.0, "low": 96.0, "close": 103.0},
        {"time": "4", "high": 107.0, "low": 98.0, "close": 104.0},
        {"time": "5", "high": 109.0, "low": 99.0, "close": 105.0},
        {"time": "6", "high": 106.0, "low": 98.0, "close": 103.0},
    ]

    target, target_time = _model24_reentry_structural_target(rows, "BUY", 106.0)

    assert target is None
    assert target_time == "N/D"


def test_pending_reentry_waits_until_buy_correction_exists() -> None:
    candles = _buy_cross_candles()
    for row in candles[-6:-1]:
        row["open"] = row["close"] - 0.05
    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(60.0, 59.0),
    ):
        decision = evaluate_model24_pending_reentry(candles)

    assert not decision.ready
    assert decision.direction == "BUY"
    assert decision.status == "M24_REENTRY_AGUARDA_CORRECAO_M5"


def test_pending_reentry_moves_trigger_to_each_new_closed_candle() -> None:
    first_rows = _buy_cross_candles()
    first_rows[-2]["open"] = first_rows[-2]["close"] + 0.05
    _set_valid_buy_structural_close_target(first_rows)
    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(60.0, 59.0),
    ):
        first = evaluate_model24_pending_reentry(first_rows)

    second_rows = list(first_rows)
    previous_current = dict(second_rows[-1])
    previous_current.update(
        {
            "open": first_rows[-2]["close"],
            "close": first_rows[-2]["close"] + 0.02,
            "high": first_rows[-2]["high"] + 0.07,
            "low": first_rows[-2]["low"] + 0.01,
        }
    )
    second_rows[-1] = previous_current
    second_rows.append(
        {
            "time": previous_current["time"] + 300.0,
            "open": previous_current["close"],
            "high": previous_current["close"] + 0.1,
            "low": previous_current["close"] - 0.1,
            "close": previous_current["close"],
        }
    )
    with patch(
        "application.model24_xau_basket._wilder_rsi",
        side_effect=(61.0, 60.0),
    ):
        second = evaluate_model24_pending_reentry(second_rows)

    assert first.ready and second.ready
    assert second.closed_candle_time != first.closed_candle_time
    assert second.entry_price == previous_current["high"]
    assert second.entry_price != first.entry_price


def test_model24_initial_direction_alternates_globally_between_sources(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "model24_runtime_state.json"
    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        state_path,
    ):
        assert model24_market_entry_role(MT5_OPERATIONAL_MODEL_8, "BUY") == "INITIAL"
        mark_model24_market_entry_accepted(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "candle-buy",
        )

        assert model24_market_entry_role("MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR", "BUY") == "REENTRY"
        assert model24_market_entry_role("MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR", "SELL") == "INITIAL"
        mark_model24_market_entry_accepted(
            "MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR",
            "SELL",
            "candle-sell",
        )
        assert model24_market_entry_role(MT5_OPERATIONAL_MODEL_8, "SELL") == "REENTRY"
        assert model24_market_entry_role(MT5_OPERATIONAL_MODEL_8, "BUY") == "INITIAL"


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


def test_first_reentry_after_extreme_exit_is_released_on_both_sides(
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

            assert first.allowed
            assert first.status == "M24_REENTRY_LIBERADA_SEM_DESCARTE_POS_EXTREMO"
            assert repeated.allowed
            assert second.allowed
            assert second.status == "M24_REENTRY_LIBERADA_SEM_DESCARTE_POS_EXTREMO"


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


def test_identity_and_comment_are_standalone_for_new_m24_orders() -> None:
    variant = model24_variant_id("MODELO_20_XAU_M5_SMA_RSI_MA_DISTANCE_ATR_REENTRY_TP75")
    assert variant == MODEL_24_ID
    assert model24_order_comment(variant) == "TraderIA M24"
    assert model24_order_comment(f"{MODEL_24_ID}_SOURCE_M20") == "TraderIA M24 S20"
    assert operational_model_number(MODEL_24_ID) == 24
    assert is_active_operational_model(variant)
    assert not is_retired_operational_model(variant)


def test_service_selects_only_the_standalone_m24_route() -> None:
    service = object.__new__(DashboardService)
    service.set_mt5_operational_model(MT5_OPERATIONAL_MODEL_24)

    assert service._mt5_operational_models_to_evaluate() == MT5_MODEL_24_SOURCE_MODEL_IDS
    assert MT5_MODEL_24_SOURCE_MODEL_IDS == (MODEL_24_ID,)
    assert service._mt5_model24_routing_enabled()
    assert not service._mt5_direct_routing_enabled()

    service.set_mt5_operational_models(
        list(MT5_MODEL_24_SOURCE_MODEL_IDS),
        direct_models_enabled=True,
    )
    service.set_mt5_operational_model(MT5_OPERATIONAL_MODEL_WITH_24)
    assert service.get_mt5_operational_model() == MT5_OPERATIONAL_MODEL_WITH_24
    assert service._mt5_direct_routing_enabled()


def test_m24_waiting_diagnostic_has_priority_over_generic_batch_wait() -> None:
    m24_waiting = DashboardDemoRobotViewModel(
        status="ARMED_WAITING",
        model="M24",
        result_status="M24_DISTANCE_ATR_BLOQUEADO",
    )
    generic_waiting = DashboardDemoRobotViewModel(
        status="AGUARDANDO_PLANO",
        model="TREND_PULLBACK",
        selected_pair="BTCUSD",
    )

    selected = DashboardService._preferred_demo_cycle_status(
        last_executed=None,
        last_model24_waiting=m24_waiting,
        last_waiting=generic_waiting,
        default_waiting=DashboardDemoRobotViewModel(),
    )

    assert selected is m24_waiting
    assert selected.result_status == "M24_DISTANCE_ATR_BLOQUEADO"


def test_model25_is_exclusive_and_expands_to_its_xau_sources() -> None:
    service = object.__new__(DashboardService)
    service.set_mt5_operational_model(MT5_OPERATIONAL_MODEL_25)

    assert service._mt5_operational_models_to_evaluate() == MT5_MODEL_25_SOURCE_MODEL_IDS
    assert not service._mt5_model24_routing_enabled()
    assert service._mt5_model25_routing_enabled()
    assert not service._mt5_direct_routing_enabled()


def test_m24_does_not_require_valid_h1_research_plan_before_its_own_route() -> None:
    service = object.__new__(DashboardService)

    assert not service._mt5_requires_valid_base_research_plan(
        [MT5_OPERATIONAL_MODEL_8],
        basket24_mode=True,
    )
    assert service._mt5_requires_valid_base_research_plan(
        [],
        basket24_mode=False,
    )


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


def test_service_materializes_initial_m24_with_fixed_point_two_five_tp(
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
    assert plan.target == round(float(plan.entry_price) + 0.25, 2)
    assert plan.stop_management_parameters["m24_entry_role"] == "INITIAL"
    assert not plan.stop_management_parameters["m24_reentry_position"]
    assert plan.stop_management_parameters["m24_individual_target_enabled"]
    assert plan.stop_management_parameters["m24_target_distance"] == 0.25
    assert not plan.stop_management_parameters["m24_micro_pivot_stop_enabled"]
    assert not plan.stop_management_parameters[
        "m24_initial_micro_pivot_trailing_enabled"
    ]
    assert plan.stop_management_parameters["m24_initial_sma20_trailing_enabled"]
    assert (
        plan.stop_management_parameters["m24_setup_contract_version"]
        == MODEL_24_SETUP_CONTRACT_VERSION
    )
    assert (
        plan.stop_management_parameters["m24_setup_contract_fingerprint"]
        == MODEL_24_SETUP_CONTRACT_FINGERPRINT
    )
    assert (
        plan.stop_management_parameters["m24_initial_stop_source"]
        == "SMA20_PRICE_CROSS_CANDLE_EXTREME_PLUS_1_PIP"
    )


def test_service_materializes_continuation_market_with_point_four_lot(
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
    object.__setattr__(
        service,
        "demo_robot_execution_service",
        SimpleNamespace(
            model24_reentry_target_exit_confirmed=lambda **_kwargs: True
        ),
    )
    waiting = Model24EntryDecision(
        status="M24_AGUARDA",
        reason="aguarda",
    )
    ready = Model24EntryDecision(
        direction="BUY",
        status="M24_CONTINUATION_BUY_RSI_EXTREMO_MERCADO_PRONTA",
        reason="continuacao pronta",
        closed_candle_time="2026-08-19T12:00:00+00:00",
        entry_price=101.0,
        initial_stop=99.5,
        rsi14=75.0,
        micro_swing_price=99.51,
        micro_swing_time="2026-08-19T11:55:00+00:00",
    )
    state_path = tmp_path / "runtime.json"
    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        state_path,
    ):
        mark_model24_market_entry_accepted(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "initial-aceita",
        )
        mark_model24_reentry_target_armed(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            100.5,
            "topo-anterior",
            "reentry-aceita",
        )
        with patch(
            "application.dashboard_service.evaluate_model24_rsi50_market_entry",
            return_value=waiting,
        ), patch(
            "application.dashboard_service.evaluate_model24_pending_reentry",
            return_value=waiting,
        ), patch(
            "application.dashboard_service.evaluate_model24_continuation",
            return_value=ready,
        ):
            row, plan = service._mt5_model24_variant_from_source(
                _source_row(),
                _source_plan(),
                source_operational_model=MT5_OPERATIONAL_MODEL_8,
                source_ready=False,
            )

    parameters = plan.stop_management_parameters
    assert row.decision == "BUY"
    assert plan.status == "PLANO_VALIDO"
    assert plan.target == 101.13
    assert parameters["m24_entry_role"] == "CONTINUATION"
    assert parameters["active_entry_order_type"] == "MARKET"
    assert parameters["execution_volume"] == 0.40
    assert parameters["m24_continuation_position"]
    assert not parameters["m24_initial_sma20_trailing_enabled"]
    assert parameters["m24_individual_target_enabled"]
    assert parameters["m24_target_distance"] == 0.13
    assert parameters["m24_continuation_previous_candle_stop_enabled"]


def test_m24_source_cannot_add_adx_or_sma_slope_filter(tmp_path: Path) -> None:
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
    ), patch(
        "application.dashboard_service.evaluate_xau_trend_filter_entry",
        side_effect=AssertionError("M24 nao deve herdar filtro da fonte"),
    ):
        row, plan = service._mt5_model24_variant_from_source(
            _source_row(),
            _source_plan(),
            source_operational_model=MT5_MODEL_24_SOURCE_MODEL_IDS[-1],
            source_ready=False,
        )

    assert row.decision == "BUY"
    assert plan.status == "PLANO_VALIDO"
    assert plan.stop_management_parameters["m24_filter_status"] == (
        "M24_CRUZAMENTOS_PRECO_RSI_E_DISTANCIA_ATR"
    )


def test_service_normalizes_non_xau_transport_row_to_standalone_xau_route(
    tmp_path: Path,
) -> None:
    service = object.__new__(DashboardService)
    row = _source_row()
    object.__setattr__(row, "pair", "EURUSD")
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
        transformed_row, plan = service._mt5_model24_variant_from_source(
            row,
            _source_plan(symbol="EURUSD"),
            source_operational_model=MT5_OPERATIONAL_MODEL_8,
            source_ready=False,
        )

    assert transformed_row.pair == "XAUUSD"
    assert transformed_row.timeframe == "M5"
    assert transformed_row.decision == "BUY"
    assert plan.symbol == "XAUUSD"
    assert plan.timeframe == "M5"
    assert plan.status == "PLANO_VALIDO"


def test_service_builds_pending_reentry_from_price_above_sma20(tmp_path: Path) -> None:
    candles = _buy_cross_candles()
    candles[-2]["open"] = candles[-2]["close"] + 0.05
    _set_valid_buy_structural_close_target(candles)
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

    assert plan.target is not None and plan.target > plan.entry_price
    assert plan.entry_price == candles[-2]["high"]
    micro_bottom, _ = model24_micro_pivot_stop(candles, "BUY")
    assert micro_bottom is not None
    assert plan.stop == micro_bottom - 0.01
    assert plan.stop_management_parameters["active_entry_order_type"] == "BUY_STOP"
    assert plan.stop_management_parameters["m24_entry_role"] == "REENTRY"
    assert plan.stop_management_parameters["m24_reentry_position"]
    assert plan.stop_management_parameters["m24_micro_pivot_stop_enabled"]
    assert plan.stop_management_parameters["m24_individual_target_enabled"]
    assert plan.stop_management_parameters["m24_structural_target_price"] == plan.target


def test_service_blocks_m24_reentry_without_structural_target(
    tmp_path: Path,
) -> None:
    candles = _buy_cross_candles()
    candles[-2]["open"] = candles[-2]["close"] + 0.05
    service = object.__new__(DashboardService)
    object.__setattr__(
        service,
        "mt5_market_data_service",
        SimpleNamespace(latest_forex_candles={("XAUUSD", "M5"): candles}),
    )

    with patch(
        "application.model24_xau_basket.MODEL_24_RUNTIME_STATE_PATH",
        tmp_path / "runtime.json",
    ), patch(
        "application.model24_xau_basket._model24_reentry_structural_target",
        return_value=(None, "N/D"),
    ):
        mark_model24_market_entry_accepted(
            MT5_OPERATIONAL_MODEL_8,
            "BUY",
            "entrada-inicial",
        )
        _row, plan = service._mt5_model24_variant_from_source(
            _source_row(),
            _source_plan(direction="BUY"),
            source_operational_model=MT5_OPERATIONAL_MODEL_8,
            source_ready=False,
        )

    assert plan.status == "M24_REENTRY_AGUARDA_ALVO_ESTRUTURAL_VALIDO"
    assert plan.direction == "WAIT"
    assert plan.target is None


def test_service_waits_for_pending_reentry_without_micro_pivot(tmp_path: Path) -> None:
    candles = _buy_cross_candles(micro_pivot=False)
    candles[-2]["open"] = candles[-2]["close"] + 0.05
    _set_valid_buy_structural_close_target(candles)
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
    assert plan.status == "M24_REENTRY_AGUARDA_MICRO_PIVO_1X1"


def test_service_releases_first_post_extreme_reentry_immediately(
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "model24_runtime_state.json"
    candles = _buy_cross_candles()
    candles[-2]["open"] = candles[-2]["close"] + 0.05
    _set_valid_buy_structural_close_target(candles)
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

    assert first.status == "PLANO_VALIDO"
    assert first.direction == "BUY"
    assert repeated.status == "PLANO_VALIDO"
    assert repeated.direction == "BUY"
    assert second.status == "PLANO_VALIDO"
    assert second.direction == "BUY"
