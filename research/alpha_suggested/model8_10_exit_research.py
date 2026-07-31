"""Replay research for the fixed stop and target of models M8-M10.

The module is intentionally isolated from the light Forex runtime. It reads the
local 5,000-candle database, evaluates the exact M2 trend-pullback entry and
writes one compact artifact for the Replay tab.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd


PAIRS = (
    "AUDUSD",
    "EURJPY",
    "EURUSD",
    "GBPUSD",
    "NZDUSD",
    "USDCAD",
    "USDCHF",
    "USDJPY",
)
MODEL_SPECS: dict[str, dict[str, str]] = {
    "M8": {
        "model_id": "MODELO_8_TREND_PULLBACK_H1_M5",
        "entry_timeframe": "M5",
        "context_timeframe": "H1",
    },
    "M9": {
        "model_id": "MODELO_9_TREND_PULLBACK_M15_M1",
        "entry_timeframe": "M1",
        "context_timeframe": "M15",
    },
    "M10": {
        "model_id": "MODELO_10_TREND_PULLBACK_D1_M15",
        "entry_timeframe": "M15",
        "context_timeframe": "D1",
    },
}
STOP_FACTORS = (0.75, 1.0, 1.25, 1.5, 2.0, 2.5)
RISK_REWARDS = (1.0, 1.5, 2.0, 2.5, 3.0)
MINIMUM_DISTANCE_PERCENT = 0.0005
MINIMUM_RANKING_TRADES = 5
TIMEFRAME_MINUTES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}


@dataclass(frozen=True)
class TradeResult:
    pair: str
    entry_index: int
    exit_index: int
    direction: str
    entry_time: str
    exit_time: str
    entry_price: float
    stop: float
    target: float
    exit_price: float
    outcome: str
    result_r: float


def run_research(
    database_path: Path,
    output_path: Path,
    *,
    candle_limit: int = 5000,
) -> dict[str, Any]:
    """Run the full grid and persist a reproducible Replay artifact."""
    database_path = database_path.resolve()
    if not database_path.exists():
        raise FileNotFoundError(f"Banco historico nao encontrado: {database_path}")
    dataset_hash = hashlib.sha256(database_path.read_bytes()).hexdigest()
    models: dict[str, Any] = {}
    for model_label, spec in MODEL_SPECS.items():
        pair_payloads: dict[str, Any] = {}
        aggregate: dict[tuple[float, float], list[dict[str, float]]] = {
            (stop, rr): [] for stop in STOP_FACTORS for rr in RISK_REWARDS
        }
        for pair in PAIRS:
            entry = load_market(
                database_path,
                pair,
                spec["entry_timeframe"],
                candle_limit,
            )
            context = load_market(
                database_path,
                pair,
                spec["context_timeframe"],
                candle_limit,
            )
            if context.empty and spec["context_timeframe"] == "D1":
                context = _resample_daily(
                    load_market(database_path, pair, "H1", candle_limit)
                )
            signals = build_signals(entry, context, spec)
            ranking: list[dict[str, Any]] = []
            for stop_factor in STOP_FACTORS:
                for risk_reward in RISK_REWARDS:
                    trades = replay_trades(
                        entry,
                        signals,
                        pair=pair,
                        stop_factor=stop_factor,
                        risk_reward=risk_reward,
                    )
                    metrics = calculate_metrics(trades)
                    row = {
                        "stop_factor": stop_factor,
                        "risk_reward": risk_reward,
                        **metrics,
                    }
                    ranking.append(row)
                    aggregate[(stop_factor, risk_reward)].append(metrics)
            ranking.sort(key=_ranking_key, reverse=True)
            winner = ranking[0]
            pair_payloads[pair] = {
                "pair": pair,
                "entry_timeframe": spec["entry_timeframe"],
                "context_timeframe": spec["context_timeframe"],
                "candles": len(entry.index),
                "context_candles": len(context.index),
                "first_candle": _timestamp_text(entry.index[0]),
                "last_candle": _timestamp_text(entry.index[-1]),
                "signal_count": int(signals["direction"].ne(0).sum()),
                "winner": winner,
                "ranking": ranking,
            }
        aggregate_ranking = [
            {
                "stop_factor": stop,
                "risk_reward": rr,
                **aggregate_metrics(metrics),
            }
            for (stop, rr), metrics in aggregate.items()
        ]
        aggregate_ranking.sort(key=_ranking_key, reverse=True)
        models[model_label] = {
            **spec,
            "entry_rule": "M2_TREND_PULLBACK_EXACT",
            "stop_grid_atr": list(STOP_FACTORS),
            "target_grid_rr": list(RISK_REWARDS),
            "global_winner": aggregate_ranking[0],
            "aggregate_ranking": aggregate_ranking,
            "pairs": pair_payloads,
        }
    payload = {
        "schema_version": "1.0",
        "status": "RESEARCH_ONLY_NOT_PROMOTED",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "database_path": str(database_path),
        "database_sha256": dataset_hash,
        "candle_limit": candle_limit,
        "execution": {
            "entry": "NEXT_CANDLE_OPEN_AFTER_CLOSED_CONFIRMATION",
            "same_candle_collision": "STOP_FIRST_CONSERVATIVE",
            "overlap": "ONE_POSITION_PER_MODEL_AND_PAIR",
            "open_trade_at_end": "MARK_TO_MARKET_EXCLUDED_FROM_CLOSED_METRICS",
            "costs": "GROSS_WITHOUT_SPREAD_COMMISSION_SWAP",
            "minimum_ranking_trades": MINIMUM_RANKING_TRADES,
        },
        "models": models,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(f"{output_path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temporary.replace(output_path)
    return payload


def load_market(
    database_path: Path,
    pair: str,
    timeframe: str,
    candle_limit: int,
) -> pd.DataFrame:
    """Load an immutable chronological window from the local MT5 database."""
    uri = f"file:{database_path.as_posix()}?mode=ro&immutable=1"
    with sqlite3.connect(uri, uri=True, timeout=10.0) as connection:
        rows = connection.execute(
            """
            SELECT candle_time, open, high, low, close, volume
            FROM (
                SELECT candle_time, open, high, low, close, volume
                FROM mt5_history_candles
                WHERE pair = ? AND timeframe = ?
                ORDER BY candle_time DESC
                LIMIT ?
            )
            ORDER BY candle_time ASC
            """,
            (pair, timeframe, max(int(candle_limit), 1)),
        ).fetchall()
    if not rows:
        return pd.DataFrame(columns=("open", "high", "low", "close", "volume"))
    frame = pd.DataFrame(
        rows,
        columns=("timestamp", "open", "high", "low", "close", "volume"),
    )
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.drop_duplicates("timestamp").set_index("timestamp").sort_index()
    return frame.astype(
        {"open": float, "high": float, "low": float, "close": float, "volume": float}
    )


def build_signals(
    entry: pd.DataFrame,
    context: pd.DataFrame,
    spec: dict[str, str],
) -> pd.DataFrame:
    """Vectorize the exact runtime M2 signal without future information."""
    if entry.empty or context.empty:
        return pd.DataFrame(index=entry.index, data={"direction": 0, "atr": np.nan})
    entry_features = _indicators(entry, fast=9, slow=21)
    context_features = _indicators(context, fast=20, slow=50)
    entry_minutes = TIMEFRAME_MINUTES[spec["entry_timeframe"]]
    context_minutes = TIMEFRAME_MINUTES[spec["context_timeframe"]]
    entry_features = entry_features.copy()
    context_features = context_features.copy()
    entry_features["close_time"] = entry_features.index + pd.to_timedelta(
        entry_minutes, unit="m"
    )
    context_features["context_close_time"] = context_features.index + pd.to_timedelta(
        context_minutes, unit="m"
    )
    merged = pd.merge_asof(
        entry_features.reset_index().sort_values("close_time"),
        context_features[
            ["context_close_time", "ema20", "ema50"]
        ].sort_values("context_close_time"),
        left_on="close_time",
        right_on="context_close_time",
        direction="backward",
        suffixes=("", "_context"),
    ).set_index("timestamp")
    previous = merged.shift(1)
    band_low = np.minimum(previous["ema9"], previous["ema21"])
    band_high = np.maximum(previous["ema9"], previous["ema21"])
    touched = (previous["low"] <= band_high) & (previous["high"] >= band_low)
    adx_ok = merged["adx"] > 20.0
    buy = (
        (merged["ema20"] > merged["ema50"])
        & (merged["ema9"] > merged["ema21"])
        & adx_ok
        & touched
        & (merged["close"] > merged["open"])
        & (merged["close"] > merged["ema9"])
    )
    sell = (
        (merged["ema20"] < merged["ema50"])
        & (merged["ema9"] < merged["ema21"])
        & adx_ok
        & touched
        & (merged["close"] < merged["open"])
        & (merged["close"] < merged["ema9"])
    )
    return pd.DataFrame(
        {
            "direction": np.select((buy, sell), (1, -1), default=0).astype(int),
            "atr": merged["atr"].astype(float),
        },
        index=merged.index,
    )


def replay_trades(
    entry: pd.DataFrame,
    signals: pd.DataFrame,
    *,
    pair: str = "",
    stop_factor: float,
    risk_reward: float,
) -> list[TradeResult]:
    """Replay sequentially, allowing only one open position per model/pair."""
    trades: list[TradeResult] = []
    next_available = 1
    opens = entry["open"].to_numpy(dtype=float)
    highs = entry["high"].to_numpy(dtype=float)
    lows = entry["low"].to_numpy(dtype=float)
    directions = signals["direction"].to_numpy(dtype=int)
    atrs = signals["atr"].to_numpy(dtype=float)
    signal_indexes = np.flatnonzero(directions != 0)
    for confirmation_index in signal_indexes:
        confirmation_index = int(confirmation_index)
        if confirmation_index >= len(entry.index) - 1:
            break
        if confirmation_index < next_available:
            continue
        direction = int(directions[confirmation_index])
        atr = float(atrs[confirmation_index])
        if direction == 0 or not math.isfinite(atr) or atr <= 0:
            continue
        entry_index = confirmation_index + 1
        entry_price = float(opens[entry_index])
        distance = max(
            atr * float(stop_factor),
            abs(entry_price) * MINIMUM_DISTANCE_PERCENT,
        )
        multiplier = 1.0 if direction > 0 else -1.0
        stop = entry_price - multiplier * distance
        target = entry_price + multiplier * distance * float(risk_reward)
        future_highs = highs[entry_index:]
        future_lows = lows[entry_index:]
        stop_hits = future_lows <= stop if direction > 0 else future_highs >= stop
        target_hits = future_highs >= target if direction > 0 else future_lows <= target
        hit_offsets = np.flatnonzero(stop_hits | target_hits)
        if not len(hit_offsets):
            break
        exit_index = entry_index + int(hit_offsets[0])
        offset = int(hit_offsets[0])
        # With OHLC data the intrabar order is unknown; stop-first is safer.
        outcome = "STOP" if bool(stop_hits[offset]) else "TARGET"
        exit_price = stop if outcome == "STOP" else target
        result_r = -1.0 if outcome == "STOP" else float(risk_reward)
        closed = TradeResult(
            pair=pair,
            entry_index=entry_index,
            exit_index=exit_index,
            direction="BUY" if direction > 0 else "SELL",
            entry_time=_timestamp_text(entry.index[entry_index]),
            exit_time=_timestamp_text(entry.index[exit_index]),
            entry_price=entry_price,
            stop=stop,
            target=target,
            exit_price=exit_price,
            outcome=outcome,
            result_r=result_r,
        )
        trades.append(closed)
        next_available = closed.exit_index + 1
    return trades


def calculate_metrics(trades: Iterable[TradeResult]) -> dict[str, Any]:
    values = [float(item.result_r) for item in trades]
    sample = len(values)
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = abs(sum(value for value in values if value < 0))
    net_r = sum(values)
    equity = np.cumsum(values, dtype=float) if values else np.asarray([], dtype=float)
    running_peak = np.maximum.accumulate(np.insert(equity, 0, 0.0))
    equity_with_zero = np.insert(equity, 0, 0.0)
    max_drawdown = float(np.max(running_peak - equity_with_zero)) if values else 0.0
    return {
        "trades": sample,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / sample) if sample else 0.0,
        "profit_factor": (
            gross_profit / gross_loss
            if gross_loss > 0
            else (999.0 if gross_profit > 0 else 0.0)
        ),
        "expectancy_r": (net_r / sample) if sample else 0.0,
        "net_r": net_r,
        "gross_profit_r": gross_profit,
        "gross_loss_r": gross_loss,
        "max_drawdown_r": max_drawdown,
        "eligible": sample >= MINIMUM_RANKING_TRADES,
    }


def aggregate_metrics(rows: Iterable[dict[str, float]]) -> dict[str, Any]:
    values = list(rows)
    trades = sum(int(row["trades"]) for row in values)
    wins = sum(int(row["wins"]) for row in values)
    losses = sum(int(row["losses"]) for row in values)
    net_r = sum(float(row["net_r"]) for row in values)
    gross_profit = sum(float(row["gross_profit_r"]) for row in values)
    gross_loss = sum(float(row["gross_loss_r"]) for row in values)
    return {
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / trades) if trades else 0.0,
        "profit_factor": (
            gross_profit / gross_loss
            if gross_loss > 0
            else (999.0 if wins > 0 else 0.0)
        ),
        "expectancy_r": (net_r / trades) if trades else 0.0,
        "net_r": net_r,
        "gross_profit_r": gross_profit,
        "gross_loss_r": gross_loss,
        "max_drawdown_r": sum(float(row["max_drawdown_r"]) for row in values),
        "eligible": trades >= MINIMUM_RANKING_TRADES,
    }


def _ranking_key(row: dict[str, Any]) -> tuple[float, ...]:
    return (
        1.0 if bool(row.get("eligible")) else 0.0,
        float(row.get("net_r", 0.0)),
        float(row.get("expectancy_r", 0.0)),
        float(row.get("profit_factor", 0.0)),
        -float(row.get("max_drawdown_r", 0.0)),
        float(row.get("trades", 0.0)),
    )


def _indicators(frame: pd.DataFrame, *, fast: int, slow: int) -> pd.DataFrame:
    result = frame.copy()
    for period in {fast, slow}:
        result[f"ema{period}"] = result["close"].ewm(
            span=period, adjust=False, min_periods=period
        ).mean()
    previous_close = result["close"].shift(1)
    true_range = pd.concat(
        (
            (result["high"] - result["low"]).abs(),
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs(),
        ),
        axis=1,
    ).max(axis=1)
    result["atr"] = true_range.ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    upward = result["high"].diff()
    downward = -result["low"].diff()
    plus_dm = pd.Series(
        np.where((upward > downward) & (upward > 0), upward, 0.0),
        index=result.index,
    )
    minus_dm = pd.Series(
        np.where((downward > upward) & (downward > 0), downward, 0.0),
        index=result.index,
    )
    smoothed_range = true_range.ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    plus_di = 100 * plus_dm.ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean() / smoothed_range
    minus_di = 100 * minus_dm.ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean() / smoothed_range
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    result["adx"] = dx.ewm(
        alpha=1 / 14, adjust=False, min_periods=14
    ).mean()
    return result


def _resample_daily(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return frame
    return (
        frame.resample("1D")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            }
        )
        .dropna(subset=("open", "high", "low", "close"))
    )


def _timestamp_text(value: object) -> str:
    return pd.Timestamp(value).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--candles", type=int, default=5000)
    args = parser.parse_args()
    result = run_research(args.database, args.output, candle_limit=args.candles)
    summary = {
        label: model["global_winner"]
        for label, model in result["models"].items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
