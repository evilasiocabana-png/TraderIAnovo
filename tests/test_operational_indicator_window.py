from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from application.model8_xau_m5_sma_rsi_reentry import evaluate_model8_entry
from application.mt5_market_data_service import MT5MarketDataService
from application.operational_indicator_window import (
    OPERATIONAL_INDICATOR_CLOSED_CANDLES,
    OPERATIONAL_INDICATOR_RAW_CANDLES,
    operational_closed_window,
)
from domain.candle import Candle


def _candles() -> list[Candle]:
    start = datetime(2026, 8, 12, tzinfo=timezone.utc)
    rows: list[Candle] = []
    for index in range(OPERATIONAL_INDICATOR_RAW_CANDLES):
        close = 100.0 + index * 0.1
        rows.append(
            Candle(
                data=(start + timedelta(minutes=5 * index)).isoformat(),
                abertura=close,
                maxima=close + 0.2,
                minima=close - 0.2,
                fechamento=close,
                volume=10,
            )
        )
    return rows


def test_window_exposes_exactly_200_closed_candles() -> None:
    rows = _candles()

    closed = operational_closed_window(rows)

    assert len(rows) == OPERATIONAL_INDICATOR_RAW_CANDLES
    assert len(closed) == OPERATIONAL_INDICATOR_CLOSED_CANDLES
    assert closed[-1] == rows[-2]


def test_forming_candle_changes_do_not_change_indicator_decision() -> None:
    rows = _candles()
    changed_current = [
        *rows[:-1],
        Candle(
            data=rows[-1].data,
            abertura=1.0,
            maxima=999.0,
            minima=0.1,
            fechamento=1.0,
            volume=9999,
        ),
    ]

    first = evaluate_model8_entry(rows)
    second = evaluate_model8_entry(changed_current)

    assert first.closed_candle_time == second.closed_candle_time
    assert first.direction == second.direction
    assert first.sma20 == second.sma20
    assert first.sma50 == second.sma50
    assert first.rsi14 == second.rsi14


def test_cache_replaces_current_and_slides_only_on_new_candle() -> None:
    rows = _candles()
    service = MT5MarketDataService(provider=SimpleNamespace())
    service.latest_forex_candles[("XAUUSD", "M5")] = rows
    replacement = Candle(
        data=rows[-1].data,
        abertura=rows[-1].abertura,
        maxima=rows[-1].maxima + 1.0,
        minima=rows[-1].minima,
        fechamento=rows[-1].fechamento + 0.5,
        volume=20,
    )

    service._merge_forex_candle_cache("XAUUSD", "M5", [replacement], limit=500)

    same_candle_window = service.latest_forex_candles[("XAUUSD", "M5")]
    assert len(same_candle_window) == OPERATIONAL_INDICATOR_RAW_CANDLES
    assert same_candle_window[0] == rows[0]
    assert same_candle_window[-1] == replacement

    next_time = datetime.fromisoformat(rows[-1].data) + timedelta(minutes=5)
    next_candle = Candle(
        data=next_time.isoformat(),
        abertura=121.0,
        maxima=121.2,
        minima=120.8,
        fechamento=121.1,
        volume=10,
    )
    service._merge_forex_candle_cache("XAUUSD", "M5", [next_candle], limit=500)

    shifted = service.latest_forex_candles[("XAUUSD", "M5")]
    assert len(shifted) == OPERATIONAL_INDICATOR_RAW_CANDLES
    assert shifted[0] == rows[1]
    assert shifted[-2] == replacement
    assert shifted[-1] == next_candle
