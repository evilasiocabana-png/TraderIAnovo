"""Validate frozen M28 v4 contracts only on post-baseline candles."""

from __future__ import annotations

from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from application.model28_forward_validation_service import (
    FORWARD_WARMUP_CANDLES,
    _read_candles,
)
from application.xau_pattern_miner_service import pattern_miner_dataset_path
from replay.pattern_miner import PatternMinerConfig
from replay.pattern_miner.mining import PatternMiner, _PatternKey
from replay.pattern_miner.models import CandleBar, EventRecord, PatternOccurrence
from replay.pattern_miner.operational import LivePatternEngine
from scripts.analyze_model28_geometry_context import (
    ABSOLUTE_FRICTION_ATR,
    MAX_HOLDING_CANDLES,
    MIN_EXPECTANCY_R,
    MIN_OOS,
    _Aggregate,
    _context_variants,
    _metrics,
)


RESEARCH_PATH = (
    ROOT
    / ".traderia"
    / "research"
    / "model28_optimizer"
    / "geometry_context_v4.json"
)
FORWARD_ROOT = (
    ROOT / ".traderia" / "research" / "model28_forward_validation"
)
OUTPUT_PATH = (
    ROOT
    / ".traderia"
    / "research"
    / "model28_optimizer"
    / "geometry_context_v4_forward.json"
)


def _incremental_path(symbol: str) -> Path:
    return (
        FORWARD_ROOT
        / symbol
        / f"historico{symbol}_M5_incremental.csv"
    )


def _deduplicate(candles: list[CandleBar]) -> list[CandleBar]:
    ordered = sorted(candles, key=lambda item: item.timestamp)
    output: list[CandleBar] = []
    for candle in ordered:
        if output and candle.timestamp == output[-1].timestamp:
            output[-1] = candle
        else:
            output.append(candle)
    return output


def _forward_result(
    occurrence: PatternOccurrence,
    candles: list[CandleBar],
    records: list[EventRecord],
    stop_atr: float,
    rr: float,
) -> tuple[float | None, str, int] | None:
    """Resolve only mature trades; leave incomplete forward signals open."""

    entry_index = occurrence.end_index + 1
    if entry_index >= len(candles):
        return None
    atr = records[occurrence.end_index].atr14
    entry = candles[entry_index].open
    if atr is None or atr <= 0.0 or entry <= 0.0:
        return None
    direction = occurrence.direction
    stop_distance = stop_atr * atr
    target_distance = rr * stop_distance
    friction_r = ABSOLUTE_FRICTION_ATR / stop_atr
    maturity_index = entry_index + MAX_HOLDING_CANDLES
    available_end = min(len(candles), maturity_index)
    for bar_index in range(entry_index, available_end):
        bar = candles[bar_index]
        if direction > 0:
            target_hit = bar.high >= entry + target_distance
            stop_hit = bar.low <= entry - stop_distance
        else:
            target_hit = bar.low <= entry - target_distance
            stop_hit = bar.high >= entry + stop_distance
        if target_hit and stop_hit:
            return -1.0 - friction_r, "AMBIGUOUS_STOP", bar_index
        if stop_hit:
            return -1.0 - friction_r, "STOP", bar_index
        if target_hit:
            return rr - friction_r, "TARGET", bar_index
    if len(candles) < maturity_index:
        return None, "OPEN", len(candles) - 1
    exit_price = candles[maturity_index - 1].close
    marked_r = direction * (exit_price - entry) / stop_distance
    return (
        max(-1.0, min(rr, marked_r)) - friction_r,
        "TIME_EXIT",
        maturity_index - 1,
    )


def _analyze_contract(contract: dict[str, object]) -> dict[str, object]:
    symbol = str(contract["symbol"])
    original = _read_candles(
        pattern_miner_dataset_path(symbol),
        tail=FORWARD_WARMUP_CANDLES,
    )
    incremental = _read_candles(_incremental_path(symbol))
    combined = _deduplicate([*original, *incremental])
    if not original or not incremental:
        return {
            "symbol": symbol,
            "pattern_id": contract["pattern_id"],
            "status": "MISSING_FORWARD_DATA",
            "incremental_candles": len(incremental),
        }

    incremental_start = min(item.timestamp for item in incremental)
    engine = LivePatternEngine(PatternMinerConfig(), ())
    for candle in combined:
        engine.consume_closed_candle(candle)
    first_incremental_index = next(
        index
        for index, candle in enumerate(engine.candles)
        if candle.timestamp >= incremental_start
    )
    direction = 1 if str(contract["direction"]).upper() == "BUY" else -1
    key = _PatternKey(
        sequence=tuple(str(item) for item in contract["events"]),
        gaps=tuple(str(item) for item in contract["gaps"]),
        direction=direction,
    )
    if key.pattern_id != str(contract["pattern_id"]):
        raise RuntimeError(
            f"Contrato {symbol} inconsistente: {contract['pattern_id']} != {key.pattern_id}"
        )
    miner = PatternMiner(PatternMinerConfig())
    tokens = miner._event_stream(engine.records)
    occurrences = miner._collect_occurrences(
        tokens,
        {key},
        first_incremental_index,
        first_incremental_index,
    ).get(key, ())
    selected_context = tuple(
        (str(name), str(value))
        for name, value in dict(contract["context"]).items()
    )
    matched = [
        occurrence
        for occurrence in occurrences
        if occurrence.end_index >= first_incremental_index
        and selected_context
        in _context_variants(
            engine.records[occurrence.end_index],
            occurrence.direction,
        )
    ]
    aggregate = _Aggregate()
    open_signals = 0
    overlap_skipped = 0
    occupied_until = -1
    for occurrence in matched:
        if occurrence.end_index + 1 <= occupied_until:
            overlap_skipped += 1
            continue
        result = _forward_result(
            occurrence,
            engine.candles,
            engine.records,
            float(contract["stop_atr"]),
            float(contract["rr"]),
        )
        if result is None:
            continue
        value, status, exit_index = result
        occupied_until = exit_index
        if value is None:
            open_signals += 1
        else:
            aggregate.add(value, status)
    metrics = _metrics(aggregate)
    enough = int(metrics["trades"]) >= MIN_OOS
    approved = (
        enough
        and float(metrics["expectancy_r"]) >= MIN_EXPECTANCY_R
        and float(metrics["lower_80_expectancy_r"]) > 0.0
    )
    status = (
        "FORWARD_APPROVED"
        if approved
        else "FORWARD_REJECTED"
        if enough
        else "INSUFFICIENT_FORWARD_SAMPLE"
    )
    return {
        "symbol": symbol,
        "pattern_id": contract["pattern_id"],
        "direction": contract["direction"],
        "context": contract["context"],
        "stop_atr": contract["stop_atr"],
        "rr": contract["rr"],
        "incremental_candles": len(incremental),
        "incremental_start": incremental[0].timestamp.isoformat(),
        "incremental_end": incremental[-1].timestamp.isoformat(),
        "signals": len(matched),
        "resolved": int(metrics["trades"]),
        "open": open_signals,
        "overlap_skipped": overlap_skipped,
        "metrics": metrics,
        "status": status,
        "approved": approved,
    }


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    temporary.replace(path)


def main() -> int:
    research = json.loads(RESEARCH_PATH.read_text(encoding="utf-8"))
    contracts = list(research.get("approved_contracts", ()) or ())
    markets: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []
    for index, source in enumerate(contracts, start=1):
        contract = dict(source)
        symbol = str(contract.get("symbol", "N/D"))
        try:
            result = _analyze_contract(contract)
            markets.append(result)
            metrics = dict(result.get("metrics", {}) or {})
            print(
                f"[{index:02d}/{len(contracts)}] {symbol}: "
                f"{result.get('resolved', 0)} resolvidos, "
                f"E={float(metrics.get('expectancy_r', 0.0)):+.4f}R, "
                f"{result['status']}",
                flush=True,
            )
        except Exception as exc:
            failures.append({"symbol": symbol, "error": str(exc)})
            print(f"[{index:02d}/{len(contracts)}] {symbol}: FALHA - {exc}", flush=True)
        finally:
            gc.collect()
    approved = [item for item in markets if item.get("approved")]
    payload = {
        "schema_version": "model28-geometry-context-v4-forward-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_research": str(RESEARCH_PATH),
        "execution_registry_changed": False,
        "policy": {
            "data": "ONLY_POST_FROZEN_100K_BASELINE",
            "minimum_resolved_trades": MIN_OOS,
            "minimum_expectancy_r": MIN_EXPECTANCY_R,
            "positive_lower_80_bound_required": True,
            "open_signals_are_excluded": True,
            "one_open_trade_per_contract": True,
        },
        "contracts_tested": len(contracts),
        "forward_approved": len(approved),
        "markets": markets,
        "failures": failures,
    }
    _write_json(OUTPUT_PATH, payload)
    print(
        f"Concluido: {len(approved)}/{len(contracts)} aprovados no forward. "
        "Registro operacional preservado.",
        flush=True,
    )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
