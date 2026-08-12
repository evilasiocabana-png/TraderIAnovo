"""Leitura leve dos indicadores M5 calculados nativamente pelo MetaTrader 5."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import threading
import time


NATIVE_INDICATOR_SOURCE = "MT5_NATIVE"
NATIVE_INDICATOR_FILE_NAME = "traderia_native_m5_indicators.csv"
_CACHE_LOCK = threading.RLock()
_CACHE_KEY: tuple[str, int, int] | None = None
_CACHE_ROWS: dict[str, "MT5NativeM5IndicatorSnapshot"] = {}


@dataclass(frozen=True)
class MT5NativeM5IndicatorSnapshot:
    symbol: str
    generated_at: str
    timeframe: str
    current_candle_time: str
    closed_candle_time: str
    sma20: float
    sma50: float
    previous_sma20: float
    previous_sma50: float
    rsi14: float
    previous_rsi14: float
    adx14: float
    atr14: float
    distance_atr: float
    sma50_slope_atr: float
    close: float
    high: float
    low: float
    last_swing_low: float
    last_swing_low_time: str
    last_swing_high: float
    last_swing_high_time: str
    indicator_source: str = NATIVE_INDICATOR_SOURCE


def native_indicator_file_path() -> Path:
    override = str(os.getenv("TRADERIA_MT5_NATIVE_INDICATORS_FILE", "")).strip()
    if override:
        return Path(override)
    appdata = Path(os.getenv("APPDATA", ""))
    return (
        appdata
        / "MetaQuotes"
        / "Terminal"
        / "Common"
        / "Files"
        / NATIVE_INDICATOR_FILE_NAME
    )


def load_native_m5_indicator_snapshots(
    *,
    max_file_age_seconds: float = 15.0,
    path: Path | None = None,
) -> dict[str, MT5NativeM5IndicatorSnapshot]:
    """Retorna somente o lote nativo completo e recente publicado pelo MQL5."""
    source = path or native_indicator_file_path()
    try:
        stat = source.stat()
    except OSError:
        return {}
    if max_file_age_seconds > 0 and time.time() - stat.st_mtime > max_file_age_seconds:
        return {}
    cache_key = (str(source.resolve()), int(stat.st_mtime_ns), int(stat.st_size))
    global _CACHE_KEY, _CACHE_ROWS
    with _CACHE_LOCK:
        if cache_key == _CACHE_KEY:
            return dict(_CACHE_ROWS)
        parsed: dict[str, MT5NativeM5IndicatorSnapshot] = {}
        try:
            with source.open("r", encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle, delimiter=";"):
                    snapshot = _parse_row(row)
                    if snapshot is not None:
                        parsed[snapshot.symbol] = snapshot
        except (OSError, csv.Error):
            return {}
        _CACHE_KEY = cache_key
        _CACHE_ROWS = parsed
        return dict(parsed)


def load_native_m5_indicator_snapshot(
    symbol: str,
    *,
    max_file_age_seconds: float = 15.0,
    path: Path | None = None,
) -> MT5NativeM5IndicatorSnapshot | None:
    return load_native_m5_indicator_snapshots(
        max_file_age_seconds=max_file_age_seconds,
        path=path,
    ).get(str(symbol or "").upper())


def _parse_row(row: dict[str, str]) -> MT5NativeM5IndicatorSnapshot | None:
    try:
        symbol = str(row.get("symbol") or "").upper()
        timeframe = str(row.get("timeframe") or "").upper()
        generated_epoch = int(row.get("generated_at") or 0)
        current_epoch = int(row.get("current_candle_time") or 0)
        closed_epoch = int(row.get("closed_candle_time") or 0)
        low_time = int(row.get("last_swing_low_time") or 0)
        high_time = int(row.get("last_swing_high_time") or 0)
        values = {
            name: float(row.get(name) or 0.0)
            for name in (
                "sma20", "sma50", "previous_sma20", "previous_sma50",
                "rsi14", "previous_rsi14", "adx14", "atr14",
                "distance_atr", "sma50_slope_atr", "close", "high", "low",
                "last_swing_low", "last_swing_high",
            )
        }
    except (TypeError, ValueError):
        return None
    if (
        not symbol
        or timeframe != "M5"
        or generated_epoch <= 0
        or current_epoch <= 0
        or closed_epoch <= 0
        or low_time <= 0
        or high_time <= 0
        or any(value <= 0.0 for name, value in values.items() if name not in {
            "distance_atr", "sma50_slope_atr",
        })
        or not 0.0 <= values["rsi14"] <= 100.0
        or not 0.0 <= values["previous_rsi14"] <= 100.0
    ):
        return None
    iso = lambda value: datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return MT5NativeM5IndicatorSnapshot(
        symbol=symbol,
        generated_at=iso(generated_epoch),
        timeframe=timeframe,
        current_candle_time=iso(current_epoch),
        closed_candle_time=iso(closed_epoch),
        last_swing_low_time=iso(low_time),
        last_swing_high_time=iso(high_time),
        **values,
    )
