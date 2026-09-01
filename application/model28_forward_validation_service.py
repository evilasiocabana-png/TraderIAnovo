"""Forward validation of Replay-promoted M28 patterns against MT5 execution."""

from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from application.xau_pattern_miner_service import (
    DEFAULT_OPERATIONAL_PATTERN_STORE_PATH,
    pattern_miner_dataset_path,
)
from domain.operational_pattern import (
    OperationalPatternSpec,
    OperationalPatternStatus,
    ShadowStatus,
    SignalCandidate,
)
from replay.pattern_miner import PatternMinerConfig
from replay.pattern_miner.models import CandleBar
from replay.pattern_miner.operational import (
    MODEL_28_CONTRACT_VERSION,
    LivePatternEngine,
    OperationalPatternStore,
)


MODEL_28_ID = "MODELO_28_PATTERN_MINER_SHADOW"
MODEL_28_TIMEFRAME = "M5"
MODEL_28_TIMEFRAME_VALUE = 5
FORWARD_WARMUP_CANDLES = 200
CSV_FIELDS = (
    "datetime",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "spread",
    "real_volume",
    "is_closed",
)
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORWARD_ROOT = (
    DEFAULT_PROJECT_ROOT / ".traderia" / "research" / "model28_forward_validation"
)
DEFAULT_EXECUTION_LOG_PATH = DEFAULT_PROJECT_ROOT / ".traderia" / "mt5_demo_execution.jsonl"
DEFAULT_TRADE_AUDIT_SNAPSHOT_PATH = (
    DEFAULT_PROJECT_ROOT / ".traderia" / "runtime" / "mt5_trade_audit_report.json"
)
DEFAULT_OPERATIONAL_AVAILABILITY_PATH = (
    DEFAULT_PROJECT_ROOT
    / ".traderia"
    / "runtime"
    / "model28_operational_availability.jsonl"
)
BRAZIL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
MODEL28_COMPARISON_START_BRT = datetime(
    2026,
    8,
    30,
    19,
    0,
    tzinfo=BRAZIL_TIMEZONE,
)
MODEL28_COMPARISON_START_UTC = MODEL28_COMPARISON_START_BRT.astimezone(timezone.utc)
AVAILABILITY_HEARTBEAT_SECONDS = 30.0
AVAILABILITY_MATCH_BEFORE_SECONDS = 30.0
AVAILABILITY_MATCH_AFTER_SECONDS = 90.0
BROKER_CLOCK_OFFSET_MAX_HOURS = 12
BROKER_CLOCK_OFFSET_TOLERANCE_SECONDS = 120.0
ATR_GEOMETRY_RELATIVE_TOLERANCE = 0.02
MATCHED_COMPARISON_STATUSES = frozenset({"CONFERE", "CONFERE_TOLERANCIA_ATR"})

_AVAILABILITY_WRITE_LOCK = threading.Lock()
_AVAILABILITY_LAST_SIGNATURE: tuple[object, ...] | None = None
_AVAILABILITY_LAST_MONOTONIC = 0.0


def record_model28_operational_heartbeat(
    *,
    online: bool,
    model_selected: bool,
    cycle_completed: bool,
    ready_symbols: Sequence[str] = (),
    status: str = "N/D",
    message: str = "",
    observed_at: datetime | None = None,
    path: str | Path = DEFAULT_OPERATIONAL_AVAILABILITY_PATH,
) -> None:
    """Persist one lightweight proof that M28 could evaluate a live candle."""

    global _AVAILABILITY_LAST_MONOTONIC, _AVAILABILITY_LAST_SIGNATURE
    symbols = tuple(sorted({str(item).strip().upper() for item in ready_symbols if item}))
    active = bool(online and model_selected and cycle_completed and symbols)
    signature = (
        active,
        bool(online),
        bool(model_selected),
        bool(cycle_completed),
        symbols,
        str(status),
    )
    monotonic = time.monotonic()
    with _AVAILABILITY_WRITE_LOCK:
        if (
            signature == _AVAILABILITY_LAST_SIGNATURE
            and monotonic - _AVAILABILITY_LAST_MONOTONIC
            < AVAILABILITY_HEARTBEAT_SECONDS
        ):
            return
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "m28-operational-availability-v1",
            "observed_at": _as_utc(observed_at or datetime.now(timezone.utc)).isoformat(),
            "active": active,
            "robot_online": bool(online),
            "model28_selected": bool(model_selected),
            "cycle_completed": bool(cycle_completed),
            "ready_symbols": list(symbols),
            "status": str(status or "N/D"),
            "message": str(message or "")[:500],
        }
        with target.open("a", encoding="utf-8") as output:
            output.write(json.dumps(payload, ensure_ascii=True) + "\n")
        _AVAILABILITY_LAST_SIGNATURE = signature
        _AVAILABILITY_LAST_MONOTONIC = monotonic


class Model28ForwardValidationService:
    """Keep original Replay datasets frozen and validate only later M5 candles."""

    def __init__(
        self,
        market_data_provider: object,
        *,
        markets: Sequence[str],
        forward_root: str | Path = DEFAULT_FORWARD_ROOT,
        operational_store_path: str | Path = DEFAULT_OPERATIONAL_PATTERN_STORE_PATH,
        execution_log_path: str | Path = DEFAULT_EXECUTION_LOG_PATH,
        trade_audit_snapshot_path: str | Path = DEFAULT_TRADE_AUDIT_SNAPSHOT_PATH,
        availability_path: str | Path = DEFAULT_OPERATIONAL_AVAILABILITY_PATH,
        original_path_resolver: Callable[[str], Path] = pattern_miner_dataset_path,
    ) -> None:
        self.provider = market_data_provider
        self.markets = tuple(dict.fromkeys(str(item).strip().upper() for item in markets))
        self.forward_root = Path(forward_root)
        self.operational_store_path = Path(operational_store_path)
        self.execution_log_path = Path(execution_log_path)
        self.trade_audit_snapshot_path = Path(trade_audit_snapshot_path)
        self.availability_path = Path(availability_path)
        self.original_path_resolver = original_path_resolver
        self.manifest_path = self.forward_root / "manifest.json"
        self.report_path = self.forward_root / "comparison_report.json"

    def load_report(self) -> dict[str, Any]:
        """Load the last persisted report without contacting MT5 or recalculating Replay."""

        payload = _read_json(self.report_path)
        if payload.get("comparison_start_brt") == MODEL28_COMPARISON_START_BRT.isoformat():
            return payload
        manifest = _read_json(self.manifest_path)
        markets = list(payload.get("markets", []) or manifest.get("markets", []) or [])
        return self._empty_report(markets or self._uninitialized_market_status_rows())

    def update(
        self,
        *,
        now: datetime | None = None,
        progress_callback: Callable[[int, int, str], None] | None = None,
    ) -> dict[str, Any]:
        """Download only post-cutoff closed candles and rebuild the persisted audit."""

        current = _as_utc(now or datetime.now(timezone.utc))
        closed_boundary = _floor_m5(current)
        statuses = self._market_status_rows()
        clock_offsets = self._download_clock_offsets(statuses, current=current)
        manifest = _read_json(self.manifest_path)
        rebuild_clock_normalization = (
            manifest.get("broker_clock_policy")
            != "REQUEST_SHIFT_AND_NORMALIZE_TO_UTC_V1"
        )
        starts = {
            row["symbol"]: (
                None
                if rebuild_clock_normalization
                else _parse_timestamp(row["last_incremental_candle"])
            )
            or _parse_timestamp(row["original_cutoff"])
            for row in statuses
        }
        starts = {
            symbol: value + timedelta(minutes=5)
            for symbol, value in starts.items()
            if value is not None and value + timedelta(minutes=5) < closed_boundary
        }
        downloaded: dict[str, Mapping[str, Any]] = {}
        if starts:
            getter = getattr(self.provider, "get_research_range", None)
            if not callable(getter):
                raise RuntimeError("Provider MT5 nao oferece leitura historica por intervalo.")
            symbols_by_window: dict[tuple[timedelta, datetime], list[str]] = {}
            for symbol, start in starts.items():
                offset = _clock_offset_for_symbol(clock_offsets, symbol)
                symbols_by_window.setdefault((offset, start), []).append(symbol)
            for (offset, start), symbols in symbols_by_window.items():
                batch = getter(
                    symbols,
                    MODEL_28_TIMEFRAME_VALUE,
                    start + offset,
                    closed_boundary + offset,
                )
                downloaded.update(dict(batch or {}))

        total = len(statuses)
        for index, row in enumerate(statuses, start=1):
            symbol = str(row["symbol"])
            if progress_callback:
                progress_callback(index, total, symbol)
            start = starts.get(symbol)
            if start is None:
                row["status"] = "SEM_NOVAS_VELAS"
                row["new_candles"] = 0
                continue
            if symbol not in downloaded:
                row["status"] = "FALHA_LEITURA_MT5"
                row["new_candles"] = 0
                continue
            source = dict(downloaded.get(symbol, {}) or {})
            if not source.get("exists", True) or not source.get("selected", True):
                row["status"] = "ATIVO_INDISPONIVEL_MT5"
                row["new_candles"] = 0
                continue
            offset = _clock_offset_for_symbol(clock_offsets, symbol)
            candles = [
                normalized
                for candle in list(source.get("candles", []) or [])
                for normalized in (_normalized_provider_candle(candle, offset),)
                if start <= normalized.timestamp < closed_boundary
            ]
            added = self._merge_incremental(symbol, candles)
            row["new_candles"] = added
            row["status"] = "ATUALIZADO" if added else "SEM_NOVAS_VELAS"

        statuses = self._market_status_rows(previous=statuses)
        generated_at = current.isoformat()
        manifest = {
            "schema_version": "m28-forward-manifest-v1",
            "generated_at": generated_at,
            "timeframe": MODEL_28_TIMEFRAME,
            "original_datasets_policy": "FROZEN_READ_ONLY",
            "incremental_policy": "BUTTON_ONLY_CLOSED_CANDLES",
            "broker_clock_policy": "REQUEST_SHIFT_AND_NORMALIZE_TO_UTC_V1",
            "broker_clock_offsets_hours": {
                symbol: round(offset.total_seconds() / 3600.0, 3)
                for symbol, offset in clock_offsets.items()
                if symbol != "*"
            },
            "markets": statuses,
        }
        _atomic_json_write(self.manifest_path, manifest)
        report = self._build_report(statuses, generated_at=generated_at)
        _atomic_json_write(self.report_path, report)
        return report

    def _build_report(
        self,
        statuses: list[dict[str, Any]],
        *,
        generated_at: str,
    ) -> dict[str, Any]:
        specs = tuple(
            item
            for item in OperationalPatternStore(self.operational_store_path).load()
            if item.contract_version == MODEL_28_CONTRACT_VERSION
            and item.status == OperationalPatternStatus.OPERATIONAL_CANDIDATE
            and item.shadow_status == ShadowStatus.RUNNING
        )
        actual_unbounded = self._actual_m28_attempts(statuses)
        broker_clock_offsets = _broker_clock_offsets(actual_unbounded)
        expected_all: list[dict[str, Any]] = []
        incremental_by_symbol: dict[str, list[CandleBar]] = {}
        for status in statuses:
            symbol = str(status["symbol"])
            incremental_by_symbol[symbol] = _read_candles(self._incremental_path(symbol))
            expected_all.extend(
                self._theoretical_signals(
                    symbol,
                    specs,
                    # Incremental candles are persisted in physical UTC. Only
                    # live execution records still need broker-clock correction.
                    clock_offset=timedelta(),
                )
            )
        expected = [
            row for row in expected_all if _signal_is_in_comparison_period(row)
        ]
        actual_unbounded = [
            _with_operational_candle_time(
                row,
                _clock_offset_for_symbol(
                    broker_clock_offsets,
                    str(row.get("symbol", "")),
                ),
            )
            for row in actual_unbounded
        ]
        actual_all = [
            row for row in actual_unbounded if _signal_is_in_comparison_period(row)
        ]
        availability_all = _read_operational_availability(self.availability_path)
        availability = [
            row
            for row in availability_all
            if (
                _parse_timestamp(row.get("observed_at"))
                or datetime.min.replace(tzinfo=timezone.utc)
            )
            >= MODEL28_COMPARISON_START_UTC
        ]
        expected_active = [
            row for row in expected if _signal_has_active_observation(row, availability)
        ]
        actual_active = [
            row for row in actual_all if _signal_has_active_observation(row, availability)
        ]
        comparisons = _compare_signals(expected_active, actual_active)
        chart_day = _as_utc(
            _parse_timestamp(generated_at) or datetime.now(timezone.utc)
        ).astimezone(BRAZIL_TIMEZONE).date().isoformat()
        theoretical_curve = _theoretical_result_curve(
            expected_active,
            incremental_by_symbol,
            chart_day=chart_day,
        )
        symbol_costs = self._symbol_costs(statuses)
        comparisons = _with_projected_financials(comparisons, symbol_costs)
        active_tickets = {
            str(row.get("ticket"))
            for row in actual_active
            if row.get("ticket") not in {None, "", 0, "0", "N/D"}
        }
        realized_curve = _realized_mt5_curve(
            self.trade_audit_snapshot_path,
            chart_day=chart_day,
            symbol_costs=symbol_costs,
            allowed_tickets=active_tickets,
        )
        matched_theoretical_curve, matched_realized_curve = _matched_result_curves(
            comparisons,
            theoretical_curve,
            realized_curve,
        )
        counts = {
            "matches": sum(
                row["comparison_status"] in MATCHED_COMPARISON_STATUSES
                for row in comparisons
            ),
            "divergences": sum(
                row["comparison_status"]
                not in {*MATCHED_COMPARISON_STATUSES, "AGUARDANDO_EXECUCAO"}
                for row in comparisons
            ),
            "waiting": sum(
                row["comparison_status"] == "AGUARDANDO_EXECUCAO"
                for row in comparisons
            ),
        }
        return {
            "schema_version": "m28-forward-comparison-v5-empirical-contracts",
            "generated_at": generated_at,
            "model": "M28",
            "timeframe": MODEL_28_TIMEFRAME,
            "comparison_start_brt": MODEL28_COMPARISON_START_BRT.isoformat(),
            "comparison_start_utc": MODEL28_COMPARISON_START_UTC.isoformat(),
            "original_datasets_policy": "FROZEN_READ_ONLY",
            "incremental_policy": "BUTTON_ONLY_CLOSED_CANDLES",
            "markets": statuses,
            "total_incremental_candles": sum(
                int(row.get("incremental_candles", 0) or 0) for row in statuses
            ),
            "comparison_scope": "ONLY_OBSERVED_OPERATIONAL_WINDOWS",
            "broker_clock_offsets_hours": {
                symbol: round(offset.total_seconds() / 3600.0, 3)
                for symbol, offset in broker_clock_offsets.items()
                if symbol != "*"
            },
            "broker_clock_offset_fallback_hours": round(
                broker_clock_offsets.get("*", timedelta()).total_seconds() / 3600.0,
                3,
            ),
            "availability_tracking_started_at": (
                str(availability[0].get("observed_at", "N/D"))
                if availability
                else "N/D"
            ),
            "availability_observations": len(availability),
            "active_availability_observations": sum(
                bool(row.get("active")) for row in availability
            ),
            "theoretical_signals_total": len(expected),
            "theoretical_signals_excluded_before_start": len(expected_all) - len(expected),
            "theoretical_signals_excluded_inactive": len(expected) - len(expected_active),
            "theoretical_signals": len(expected_active),
            "actual_attempts_total": len(actual_all),
            "actual_attempts_excluded_before_start": len(actual_unbounded) - len(actual_all),
            "actual_attempts_excluded_inactive": len(actual_all) - len(actual_active),
            "actual_attempts": len(actual_active),
            "chart_day": chart_day,
            "theoretical_curve": theoretical_curve,
            "realized_curve": realized_curve,
            "theoretical_resolved": len(theoretical_curve),
            "actual_closed_trades": len(realized_curve),
            "matched_closed_trades": len(matched_realized_curve),
            "matched_theoretical_curve": matched_theoretical_curve,
            "matched_realized_curve": matched_realized_curve,
            **counts,
            "comparisons": comparisons,
        }

    def _theoretical_signals(
        self,
        symbol: str,
        all_specs: Sequence[OperationalPatternSpec],
        *,
        clock_offset: timedelta = timedelta(),
    ) -> list[dict[str, Any]]:
        specs = tuple(
            item
            for item in all_specs
            if item.symbol.upper() == symbol
            and item.timeframe.upper() == MODEL_28_TIMEFRAME
        )
        incremental = _read_candles(self._incremental_path(symbol))
        if not specs or not incremental:
            return []
        original = _read_candles(
            self.original_path_resolver(symbol),
            tail=FORWARD_WARMUP_CANDLES,
        )
        engine = LivePatternEngine(PatternMinerConfig(), specs)
        for candle in original:
            engine.consume_closed_candle(candle)
        spec_by_id = {item.versioned_id: item for item in engine.tracker.specs}
        repeat_states: dict[str, tuple[datetime, int]] = {}
        rows: list[dict[str, Any]] = []
        pending: tuple[SignalCandidate, OperationalPatternSpec, int] | None = None
        for candle in incremental:
            if pending is not None:
                selected, spec, repeat_position = pending
                reference_entry = float(selected.entry_reference)
                stop_distance = abs(reference_entry - float(selected.stop_reference))
                target_distance = abs(float(selected.target_reference) - reference_entry)
                entry = float(candle.open)
                if selected.direction == "BUY":
                    stop = entry - stop_distance
                    target = entry + target_distance
                else:
                    stop = entry + stop_distance
                    target = entry - target_distance
                rows.append(
                    _with_operational_candle_time(
                        {
                            "symbol": symbol,
                            "candle_time": selected.datetime.isoformat(),
                            "entry_time": candle.timestamp.isoformat(),
                            "pattern_id": spec.pattern_id,
                            "pattern_versioned_id": spec.versioned_id,
                            "pattern_occurrence_id": selected.pattern_occurrence_id,
                            "direction": selected.direction,
                            "entry": entry,
                            "stop": stop,
                            "target": target,
                            "reference_entry": reference_entry,
                            "stop_distance": stop_distance,
                            "target_distance": target_distance,
                            "entry_spread_points": float(candle.spread or 0.0),
                            "entry_rule": spec.entry_rule,
                            "stop_rule": spec.stop_rule,
                            "target_rule": spec.target_rule,
                            "expiration_rule": spec.expiration_rule,
                            "max_holding_candles": int(spec.max_holding_candles),
                            "cost_rule": spec.cost_rule,
                            "confidence": float(selected.confidence),
                            "evidence_tier": str(spec.evidence_tier),
                            "adaptive_rank": int(spec.adaptive_rank or 0),
                            "repeat_position": repeat_position,
                            "repeat_limit": int(spec.repeat_limit or 1),
                            "repeat_probability": float(spec.repeat_probability or 0.0),
                            "pattern_family": str(spec.pattern_family),
                            "selection_score": float(spec.selection_score or 0.0),
                        },
                        clock_offset,
                    )
                )
                pending = None
            _record, signals = engine.consume_closed_candle(candle)
            if not signals:
                continue
            repeat_positions: dict[str, int] = {}
            eligible: list[SignalCandidate] = []
            for signal in signals:
                versioned_id = f"{signal.setup_id}_v{signal.setup_version}"
                spec = spec_by_id.get(versioned_id)
                if spec is None:
                    continue
                position = _advance_repeat_position(signal, spec, repeat_states)
                repeat_positions[signal.pattern_occurrence_id] = position
                if position <= max(int(spec.repeat_limit), 1):
                    eligible.append(signal)
            if not eligible:
                continue
            selected = max(
                eligible,
                key=lambda signal: _signal_evidence(signal, spec_by_id),
            )
            spec = spec_by_id.get(f"{selected.setup_id}_v{selected.setup_version}")
            if spec is not None:
                pending = (
                    selected,
                    spec,
                    int(repeat_positions.get(selected.pattern_occurrence_id, 1)),
                )
        return rows

    def _actual_m28_attempts(
        self,
        statuses: Sequence[Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        if not self.execution_log_path.exists():
            return []
        cutoffs = {
            str(row["symbol"]): _parse_timestamp(row.get("original_cutoff"))
            for row in statuses
        }
        grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        with self.execution_log_path.open("r", encoding="utf-8", errors="ignore") as source:
            for line in source:
                if MODEL_28_ID not in line:
                    continue
                try:
                    record = json.loads(line)
                except (TypeError, json.JSONDecodeError):
                    continue
                if str(record.get("operational_model", "")) != MODEL_28_ID:
                    continue
                plan = dict(record.get("plan_snapshot", {}) or {})
                parameters = dict(plan.get("stop_management_parameters", {}) or {})
                symbol = str(record.get("symbol", plan.get("symbol", ""))).upper()
                candle_time = _parse_timestamp(plan.get("candle_time"))
                cutoff = cutoffs.get(symbol)
                if candle_time is None or cutoff is None or candle_time <= cutoff:
                    continue
                pattern_id = str(parameters.get("pattern_id", "N/D"))
                direction = str(record.get("side", plan.get("direction", "N/D"))).upper()
                key = (symbol, candle_time.isoformat(), pattern_id, direction)
                normalized = {
                    "symbol": symbol,
                    "candle_time": candle_time.isoformat(),
                    "pattern_id": pattern_id,
                    "pattern_versioned_id": str(
                        parameters.get("pattern_versioned_id", "N/D")
                    ),
                    "pattern_occurrence_id": str(
                        parameters.get("pattern_occurrence_id", "N/D")
                    ),
                    "direction": direction,
                    "entry": _float(plan.get("entry_price", record.get("entry_price"))),
                    "stop": _float(plan.get("initial_stop", record.get("stop"))),
                    "target": _float(plan.get("target", record.get("target"))),
                    "quantity": _float(record.get("quantity")),
                    "executed_price": _float(record.get("executed_price")),
                    "accepted": bool(record.get("accepted")),
                    "status": str(record.get("status", "N/D")),
                    "message": str(record.get("message", "N/D")),
                    "ticket": record.get("ticket"),
                    "attempted_at": str(record.get("timestamp", "N/D")),
                }
                previous = grouped.get(key)
                if previous is None or (normalized["accepted"] and not previous["accepted"]):
                    grouped[key] = normalized
        return sorted(grouped.values(), key=lambda row: str(row["candle_time"]))

    def _market_status_rows(
        self,
        *,
        previous: Sequence[Mapping[str, Any]] = (),
    ) -> list[dict[str, Any]]:
        previous_by_symbol = {str(row.get("symbol")): dict(row) for row in previous}
        rows: list[dict[str, Any]] = []
        for symbol in self.markets:
            original_path = self.original_path_resolver(symbol)
            incremental_path = self._incremental_path(symbol)
            original_last, original_count = _csv_last_timestamp_and_count(
                original_path,
                frozen=True,
            )
            incremental_last, incremental_count = _csv_last_timestamp_and_count(
                incremental_path
            )
            prior = previous_by_symbol.get(symbol, {})
            rows.append(
                {
                    "symbol": symbol,
                    "timeframe": MODEL_28_TIMEFRAME,
                    "original_path": str(original_path),
                    "original_cutoff": _iso(original_last),
                    "original_candles": original_count,
                    "incremental_path": str(incremental_path),
                    "last_incremental_candle": _iso(incremental_last),
                    "incremental_candles": incremental_count,
                    "new_candles": int(prior.get("new_candles", 0) or 0),
                    "status": str(prior.get("status", "AGUARDANDO_ATUALIZACAO")),
                }
            )
        return rows

    def _uninitialized_market_status_rows(self) -> list[dict[str, Any]]:
        """Build the first screen instantly, without scanning the frozen datasets."""

        return [
            {
                "symbol": symbol,
                "timeframe": MODEL_28_TIMEFRAME,
                "original_path": str(self.original_path_resolver(symbol)),
                "original_cutoff": "N/D",
                "original_candles": 0,
                "incremental_path": str(self._incremental_path(symbol)),
                "last_incremental_candle": "N/D",
                "incremental_candles": 0,
                "new_candles": 0,
                "status": "CLIQUE_EM_ATUALIZAR_DADOS",
            }
            for symbol in self.markets
        ]

    def _incremental_path(self, symbol: str) -> Path:
        return self.forward_root / symbol / f"historico{symbol}_M5_incremental.csv"

    def _merge_incremental(self, symbol: str, candles: Iterable[object]) -> int:
        path = self._incremental_path(symbol)
        existing = {candle.timestamp: candle for candle in _read_candles(path)}
        before = len(existing)
        changed = False
        for source in candles:
            timestamp = _candle_timestamp(source)
            normalized = CandleBar(
                index=0,
                timestamp=timestamp,
                open=float(_value(source, "abertura", "open")),
                high=float(_value(source, "maxima", "high")),
                low=float(_value(source, "minima", "low")),
                close=float(_value(source, "fechamento", "close")),
                volume=float(_value(source, "volume", "tick_volume", default=0.0)),
                spread=float(_value(source, "spread", default=0.0)),
                real_volume=float(_value(source, "real_volume", default=0.0)),
            )
            if existing.get(timestamp) != normalized:
                existing[timestamp] = normalized
                changed = True
        if changed:
            _atomic_csv_write(path, sorted(existing.values(), key=lambda item: item.timestamp))
        return len(existing) - before

    def _download_clock_offsets(
        self,
        statuses: Sequence[Mapping[str, Any]],
        *,
        current: datetime,
    ) -> dict[str, timedelta]:
        """Resolve the server clock before requesting an MT5 historical range."""

        offsets = _broker_clock_offsets(self._actual_m28_attempts(statuses))
        fallback = offsets.get("*")
        if fallback is None:
            fallback = _provider_clock_offset(self.provider, current=current)
        fallback = fallback or timedelta()
        output = {
            str(row.get("symbol", "")).upper(): offsets.get(
                str(row.get("symbol", "")).upper(),
                fallback,
            )
            for row in statuses
        }
        output["*"] = fallback
        return output

    def _empty_report(self, statuses: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "schema_version": "m28-forward-comparison-v5-empirical-contracts",
            "generated_at": "N/D",
            "model": "M28",
            "timeframe": MODEL_28_TIMEFRAME,
            "comparison_start_brt": MODEL28_COMPARISON_START_BRT.isoformat(),
            "comparison_start_utc": MODEL28_COMPARISON_START_UTC.isoformat(),
            "original_datasets_policy": "FROZEN_READ_ONLY",
            "incremental_policy": "BUTTON_ONLY_CLOSED_CANDLES",
            "markets": statuses,
            "total_incremental_candles": sum(
                int(row.get("incremental_candles", 0) or 0) for row in statuses
            ),
            "theoretical_signals": 0,
            "theoretical_signals_total": 0,
            "theoretical_signals_excluded_before_start": 0,
            "theoretical_signals_excluded_inactive": 0,
            "actual_attempts": 0,
            "actual_attempts_total": 0,
            "actual_attempts_excluded_before_start": 0,
            "actual_attempts_excluded_inactive": 0,
            "comparison_scope": "ONLY_OBSERVED_OPERATIONAL_WINDOWS",
            "broker_clock_offsets_hours": {},
            "broker_clock_offset_fallback_hours": 0.0,
            "availability_tracking_started_at": "N/D",
            "availability_observations": 0,
            "active_availability_observations": 0,
            "chart_day": "N/D",
            "theoretical_curve": [],
            "realized_curve": [],
            "theoretical_resolved": 0,
            "actual_closed_trades": 0,
            "matched_closed_trades": 0,
            "matched_theoretical_curve": [],
            "matched_realized_curve": [],
            "matches": 0,
            "divergences": 0,
            "waiting": 0,
            "comparisons": [],
        }

    def _symbol_costs(
        self,
        statuses: Sequence[Mapping[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        """Capture contract metadata only during the explicit update operation."""

        getter = getattr(self.provider, "get_symbol_cost_data", None)
        if not callable(getter):
            return {}
        output: dict[str, dict[str, Any]] = {}
        for status in statuses:
            symbol = str(status.get("symbol", "")).upper()
            try:
                payload = dict(getter(symbol) or {})
            except (OSError, RuntimeError, ValueError, TypeError):
                continue
            tick_size = _float(payload.get("tick_size"))
            tick_value = _float(payload.get("tick_value"))
            if tick_size and tick_size > 0 and tick_value and tick_value > 0:
                output[symbol] = {
                    "tick_size": tick_size,
                    "tick_value": tick_value,
                }
        return output


def _theoretical_result_curve(
    signals: Sequence[Mapping[str, Any]],
    candles_by_symbol: Mapping[str, Sequence[CandleBar]],
    *,
    chart_day: str,
) -> list[dict[str, Any]]:
    """Resolve the same empirical barriers, cost and horizon used by Replay v6."""

    resolved: list[dict[str, Any]] = []
    for signal in signals:
        symbol = str(signal.get("symbol", "")).upper()
        signal_time = _parse_timestamp(signal.get("candle_time"))
        entry_time = _parse_timestamp(signal.get("entry_time"))
        operational_signal_time = _operational_candle_timestamp(signal)
        entry = _float(signal.get("entry"))
        stop = _float(signal.get("stop"))
        target = _float(signal.get("target"))
        direction = str(signal.get("direction", "")).upper()
        if None in {
            signal_time,
            entry_time,
            operational_signal_time,
            entry,
            stop,
            target,
        }:
            continue
        risk = abs(float(entry) - float(stop))
        if risk <= 0.0:
            continue
        reward_r = abs(float(target) - float(entry)) / risk
        try:
            max_holding_candles = int(signal.get("max_holding_candles", 0) or 0)
        except (TypeError, ValueError):
            max_holding_candles = 0
        if max_holding_candles <= 0:
            continue
        spread_points = max(float(signal.get("entry_spread_points", 0.0) or 0.0), 0.0)
        spread_price = spread_points * _historical_spread_point_size(symbol)
        cost_r = spread_price / risk
        bars_seen = 0
        for candle in candles_by_symbol.get(symbol, ()):
            if candle.timestamp < entry_time:
                continue
            bars_seen += 1
            if direction in {"BUY", "COMPRAR"}:
                stop_hit = candle.low <= float(stop)
                target_hit = candle.high >= float(target)
            elif direction in {"SELL", "VENDER"}:
                stop_hit = candle.high >= float(stop)
                target_hit = candle.low <= float(target)
            else:
                break
            outcome = ""
            result_r: float | None = None
            if stop_hit:
                # OHLC does not reveal intrabar order; simultaneous touches are conservative.
                result_r = -1.0 - cost_r
                outcome = "AMBIGUOUS_STOP" if target_hit else "STOP"
            elif target_hit:
                result_r = reward_r - cost_r
                outcome = "TARGET"
            elif bars_seen >= max_holding_candles:
                marked_r = (
                    (float(candle.close) - float(entry)) / risk
                    if direction in {"BUY", "COMPRAR"}
                    else (float(entry) - float(candle.close)) / risk
                )
                result_r = max(-1.0, min(reward_r, marked_r)) - cost_r
                outcome = "TIME_EXIT"
            if result_r is None:
                continue
            exit_time = _as_utc(candle.timestamp) - _signal_clock_offset(signal)
            if exit_time.astimezone(BRAZIL_TIMEZONE).date().isoformat() == chart_day:
                resolved.append(
                    {
                        "time": exit_time.isoformat(),
                        "signal_time": operational_signal_time.isoformat(),
                        "symbol": symbol,
                        "pattern_id": str(signal.get("pattern_id", "N/D")),
                        "pattern_occurrence_id": str(
                            signal.get("pattern_occurrence_id", "N/D")
                        ),
                        "direction": direction,
                        "outcome": outcome,
                        "result_r": round(float(result_r), 6),
                        "cost_r": round(float(cost_r), 6),
                        "bars_held": bars_seen,
                    }
                )
            break

    cumulative = 0.0
    curve: list[dict[str, Any]] = []
    for row in sorted(resolved, key=lambda item: str(item["time"])):
        cumulative += float(row["result_r"])
        curve.append({**row, "cumulative_r": round(cumulative, 6)})
    return curve


def _historical_spread_point_size(symbol: str) -> float:
    """Use the same MT5 spread-to-price conversion as the 100k research."""

    normalized = str(symbol or "").upper()
    if normalized.endswith("JPY"):
        return 0.001
    if normalized in {"XAUUSD", "BTCUSD"}:
        return 0.01
    return 0.00001


def _realized_mt5_curve(
    snapshot_path: Path,
    *,
    chart_day: str,
    symbol_costs: Mapping[str, Mapping[str, Any]] | None = None,
    allowed_tickets: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Build M28 net realized P/L from the persisted audit, without reading Replay."""

    payload = _read_json(snapshot_path)
    unique: dict[str, dict[str, Any]] = {}
    for source in list(payload.get("rows", []) or []):
        row = dict(source or {})
        plan = dict(row.get("plan_snapshot", {}) or {})
        model = str(row.get("operational_model") or plan.get("operational_model") or "")
        if model != MODEL_28_ID:
            continue
        if str(row.get("operation_status", "")).upper() != "FECHADA/HISTORICO":
            continue
        closed_at = _parse_timestamp(row.get("mt5_time"))
        if closed_at is None:
            continue
        if closed_at.astimezone(BRAZIL_TIMEZONE).date().isoformat() != chart_day:
            continue
        ticket = str(row.get("mt5_ticket") or row.get("local_ticket") or "")
        if not ticket:
            continue
        if allowed_tickets is not None and ticket not in allowed_tickets:
            continue
        realized = float(_float(row.get("mt5_realized_profit")) or 0.0)
        commission = float(_float(row.get("mt5_commission")) or 0.0)
        swap = float(_float(row.get("mt5_swap")) or 0.0)
        fee = float(_float(row.get("mt5_fee")) or 0.0)
        symbol = str(row.get("symbol", "N/D")).upper()
        entry = _float(row.get("entry_price"))
        stop = _float(row.get("stop"))
        quantity = _float(row.get("quantity"))
        contract = dict((symbol_costs or {}).get(symbol, {}) or {})
        tick_size = _float(contract.get("tick_size"))
        tick_value = _float(contract.get("tick_value"))
        risk_usd = None
        if (
            entry is not None
            and stop is not None
            and quantity is not None
            and quantity > 0
            and tick_size is not None
            and tick_size > 0
            and tick_value is not None
            and tick_value > 0
        ):
            risk_usd = abs(entry - stop) / tick_size * tick_value * quantity
        result_usd = realized + commission + swap + fee
        result_r = result_usd / risk_usd if risk_usd and risk_usd > 0 else None
        unique[ticket] = {
            "time": _as_utc(closed_at).isoformat(),
            "symbol": symbol,
            "ticket": ticket,
            "gross_usd": round(realized, 6),
            "costs_usd": round(commission + swap + fee, 6),
            "result_usd": round(result_usd, 6),
            "risk_usd": round(risk_usd, 6) if risk_usd is not None else None,
            "result_r": round(result_r, 6) if result_r is not None else None,
        }

    cumulative = 0.0
    cumulative_r = 0.0
    curve: list[dict[str, Any]] = []
    for row in sorted(unique.values(), key=lambda item: str(item["time"])):
        cumulative += float(row["result_usd"])
        result_r = row.get("result_r")
        if result_r is not None:
            cumulative_r += float(result_r)
        curve.append(
            {
                **row,
                "cumulative_usd": round(cumulative, 6),
                "cumulative_r": round(cumulative_r, 6),
            }
        )
    return curve


def _matched_result_curves(
    comparisons: Sequence[Mapping[str, Any]],
    theoretical_curve: Sequence[Mapping[str, Any]],
    realized_curve: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Align only confirmed tickets while preserving independent exit timestamps."""

    theoretical_by_key: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    for source in theoretical_curve:
        row = dict(source)
        key = (
            str(row.get("symbol", "")),
            str(row.get("signal_time", "")),
            str(row.get("pattern_id", "")),
            str(row.get("direction", "")),
        )
        theoretical_by_key.setdefault(key, []).append(row)
    realized_by_ticket = {
        str(row.get("ticket")): dict(row)
        for row in realized_curve
        if row.get("result_r") is not None
    }
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for comparison in comparisons:
        if str(comparison.get("comparison_status")) not in MATCHED_COMPARISON_STATUSES:
            continue
        ticket = str(comparison.get("ticket") or "")
        realized = realized_by_ticket.get(ticket)
        key = (
            str(comparison.get("symbol", "")),
            str(comparison.get("candle_time", "")),
            str(comparison.get("pattern_id", "")),
            str(comparison.get("direction", "")),
        )
        candidates = theoretical_by_key.get(key, [])
        if realized is None or not candidates:
            continue
        theoretical = candidates.pop(0)
        pairs.append((theoretical, realized))

    theoretical_output: list[dict[str, Any]] = []
    theoretical_total = 0.0
    for theoretical, realized in sorted(pairs, key=lambda pair: str(pair[0].get("time", ""))):
        theoretical_total += float(theoretical.get("result_r", 0.0) or 0.0)
        theoretical_output.append(
            {
                **theoretical,
                "ticket": str(realized.get("ticket", "N/D")),
                "cumulative_r": round(theoretical_total, 6),
            }
        )

    realized_output: list[dict[str, Any]] = []
    realized_total = 0.0
    for theoretical, realized in sorted(pairs, key=lambda pair: str(pair[1].get("time", ""))):
        realized_total += float(realized.get("result_r", 0.0) or 0.0)
        realized_output.append(
            {
                **realized,
                "pattern_id": str(theoretical.get("pattern_id", "N/D")),
                "cumulative_r": round(realized_total, 6),
            }
        )
    return theoretical_output, realized_output


def _compare_signals(
    expected: Sequence[Mapping[str, Any]],
    actual: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    remaining = list(actual)
    rows: list[dict[str, Any]] = []
    for theoretical in expected:
        match_index = _matching_actual_index(theoretical, remaining)
        executed = remaining.pop(match_index) if match_index is not None else None
        if executed is None:
            status = "AGUARDANDO_EXECUCAO"
            reason = "Sinal teorico M28 encontrado, sem tentativa correspondente no log MT5."
        elif not bool(executed.get("accepted")):
            status = "REJEITADO_MT5"
            reason = str(executed.get("message", "Tentativa rejeitada pelo MT5."))
        elif _geometry_matches(theoretical, executed):
            status = "CONFERE"
            reason = "Padrao, lado, candle, entrada, SL e TP conferem."
        elif _geometry_matches_with_atr_tolerance(theoretical, executed):
            status = "CONFERE_TOLERANCIA_ATR"
            reason = (
                "Padrao, lado, candle e entrada conferem; SL/TP ficaram dentro "
                "da tolerancia de 2% da distancia ATR entre Replay e motor ao vivo."
            )
        else:
            status = "DIVERGE_GEOMETRIA"
            reason = "A tentativa MT5 nao preservou entrada, SL ou TP teoricos."
        rows.append(_comparison_row(theoretical, executed, status, reason))
    for executed in remaining:
        rows.append(
            _comparison_row(
                None,
                executed,
                "SEM_SINAL_FORWARD",
                "Houve tentativa M28 sem sinal correspondente na reconstrucao pos-corte.",
            )
        )
    return sorted(rows, key=lambda row: str(row.get("candle_time", "")), reverse=True)


def _read_operational_availability(path: Path) -> list[dict[str, Any]]:
    """Read compact cycle proofs; malformed or partial lines are ignored."""

    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as source:
            for line in source:
                try:
                    payload = json.loads(line)
                except (TypeError, json.JSONDecodeError):
                    continue
                observed_at = _parse_timestamp(payload.get("observed_at"))
                if observed_at is None:
                    continue
                rows.append(
                    {
                        **dict(payload),
                        "observed_at": observed_at.isoformat(),
                        "ready_symbols": [
                            str(item).strip().upper()
                            for item in list(payload.get("ready_symbols", []) or [])
                            if str(item).strip()
                        ],
                    }
                )
    except OSError:
        return []
    return sorted(rows, key=lambda row: str(row["observed_at"]))


def _broker_clock_offsets(
    attempts: Sequence[Mapping[str, Any]],
) -> dict[str, timedelta]:
    """Infer the broker candle clock from accepted attempts near an M5 close."""

    candidates_by_symbol: dict[str, list[int]] = {}
    all_candidates: list[int] = []
    for row in attempts:
        if not bool(row.get("accepted")):
            continue
        candle_time = _parse_timestamp(
            row.get("source_candle_time", row.get("candle_time"))
        )
        attempted_at = _parse_timestamp(row.get("attempted_at"))
        if candle_time is None or attempted_at is None:
            continue
        drift_seconds = (
            candle_time
            + timedelta(minutes=MODEL_28_TIMEFRAME_VALUE)
            - attempted_at
        ).total_seconds()
        rounded_hours = int(round(drift_seconds / 3600.0))
        rounded_seconds = rounded_hours * 3600
        if abs(rounded_hours) > BROKER_CLOCK_OFFSET_MAX_HOURS:
            continue
        if abs(drift_seconds - rounded_seconds) > BROKER_CLOCK_OFFSET_TOLERANCE_SECONDS:
            continue
        symbol = str(row.get("symbol", "")).strip().upper()
        if not symbol:
            continue
        candidates_by_symbol.setdefault(symbol, []).append(rounded_hours)
        all_candidates.append(rounded_hours)

    offsets = {
        symbol: timedelta(hours=_most_common_integer(values))
        for symbol, values in candidates_by_symbol.items()
        if values
    }
    if all_candidates:
        offsets["*"] = timedelta(hours=_most_common_integer(all_candidates))
    return offsets


def _most_common_integer(values: Sequence[int]) -> int:
    counts: dict[int, int] = {}
    for value in values:
        counts[int(value)] = counts.get(int(value), 0) + 1
    return max(counts, key=lambda value: (counts[value], -abs(value)))


def _clock_offset_for_symbol(
    offsets: Mapping[str, timedelta],
    symbol: str,
) -> timedelta:
    return offsets.get(str(symbol).strip().upper(), offsets.get("*", timedelta()))


def _with_operational_candle_time(
    source: Mapping[str, Any],
    clock_offset: timedelta,
) -> dict[str, Any]:
    row = dict(source)
    raw_time = _parse_timestamp(row.get("source_candle_time", row.get("candle_time")))
    if raw_time is None:
        return row
    operational_time = raw_time - clock_offset
    row["source_candle_time"] = raw_time.isoformat()
    row["operational_candle_time"] = operational_time.isoformat()
    row["broker_clock_offset_hours"] = round(
        clock_offset.total_seconds() / 3600.0,
        3,
    )
    return row


def _signal_clock_offset(signal: Mapping[str, Any]) -> timedelta:
    try:
        return timedelta(hours=float(signal.get("broker_clock_offset_hours", 0.0) or 0.0))
    except (TypeError, ValueError):
        return timedelta()


def _operational_candle_timestamp(signal: Mapping[str, Any]) -> datetime | None:
    explicit = _parse_timestamp(signal.get("operational_candle_time"))
    if explicit is not None:
        return explicit
    raw_time = _parse_timestamp(
        signal.get("source_candle_time", signal.get("candle_time"))
    )
    if raw_time is None:
        return None
    return raw_time - _signal_clock_offset(signal)


def _signal_has_active_observation(
    signal: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
) -> bool:
    """Require live proof around the close of the signal's M5 candle."""

    candle_time = _operational_candle_timestamp(signal)
    if candle_time is None:
        return False
    expected_close = candle_time + timedelta(minutes=MODEL_28_TIMEFRAME_VALUE)
    lower = expected_close - timedelta(seconds=AVAILABILITY_MATCH_BEFORE_SECONDS)
    upper = expected_close + timedelta(seconds=AVAILABILITY_MATCH_AFTER_SECONDS)
    symbol = str(signal.get("symbol", "")).strip().upper()
    for observation in observations:
        if not bool(observation.get("active")):
            continue
        observed_at = _parse_timestamp(observation.get("observed_at"))
        if observed_at is None or observed_at < lower or observed_at > upper:
            continue
        ready = {
            str(item).strip().upper()
            for item in list(observation.get("ready_symbols", []) or [])
        }
        if symbol in ready:
            return True
    return False


def _signal_is_in_comparison_period(signal: Mapping[str, Any]) -> bool:
    """Include the M5 candle whose close is at or after the fixed BRT baseline."""

    candle_time = _operational_candle_timestamp(signal)
    if candle_time is None:
        return False
    signal_available_at = candle_time + timedelta(minutes=MODEL_28_TIMEFRAME_VALUE)
    return signal_available_at >= MODEL28_COMPARISON_START_UTC


def _matching_actual_index(
    expected: Mapping[str, Any],
    actual: Sequence[Mapping[str, Any]],
) -> int | None:
    expected_occurrence = str(expected.get("pattern_occurrence_id", ""))
    for index, row in enumerate(actual):
        if expected_occurrence and expected_occurrence == str(row.get("pattern_occurrence_id", "")):
            return index
    expected_time = _operational_candle_timestamp(expected)
    for index, row in enumerate(actual):
        actual_time = _operational_candle_timestamp(row)
        if (
            str(expected.get("symbol")) == str(row.get("symbol"))
            and str(expected.get("pattern_id")) == str(row.get("pattern_id"))
            and str(expected.get("direction")) == str(row.get("direction"))
            and expected_time is not None
            and actual_time is not None
            and abs((actual_time - expected_time).total_seconds()) <= 300
        ):
            return index
    return None


def _comparison_row(
    expected: Mapping[str, Any] | None,
    actual: Mapping[str, Any] | None,
    status: str,
    reason: str,
) -> dict[str, Any]:
    theoretical = dict(expected or {})
    executed = dict(actual or {})
    return {
        "symbol": theoretical.get("symbol", executed.get("symbol", "N/D")),
        "candle_time": theoretical.get(
            "operational_candle_time",
            executed.get("operational_candle_time", "N/D"),
        ),
        "source_candle_time": theoretical.get(
            "source_candle_time",
            theoretical.get(
                "candle_time",
                executed.get("source_candle_time", executed.get("candle_time", "N/D")),
            ),
        ),
        "broker_clock_offset_hours": theoretical.get(
            "broker_clock_offset_hours",
            executed.get("broker_clock_offset_hours", 0.0),
        ),
        "pattern_id": theoretical.get("pattern_id", executed.get("pattern_id", "N/D")),
        "direction": theoretical.get("direction", executed.get("direction", "N/D")),
        "theoretical_entry": theoretical.get("entry"),
        "theoretical_stop": theoretical.get("stop"),
        "theoretical_target": theoretical.get("target"),
        "mt5_entry_plan": executed.get("entry"),
        "mt5_executed_price": executed.get("executed_price"),
        "mt5_stop": executed.get("stop"),
        "mt5_target": executed.get("target"),
        "mt5_quantity": executed.get("quantity"),
        "ticket": executed.get("ticket"),
        "mt5_attempted_at": executed.get("attempted_at", "N/D"),
        "mt5_status": executed.get("status", "NAO_ENVIADO"),
        "comparison_status": status,
        "reason": reason,
    }


def _with_projected_financials(
    comparisons: Sequence[Mapping[str, Any]],
    symbol_costs: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Attach the gross TP projection to each attempted M28 order."""

    output: list[dict[str, Any]] = []
    for source in comparisons:
        row = dict(source)
        symbol = str(row.get("symbol", "")).upper()
        contract = dict(symbol_costs.get(symbol, {}) or {})
        entry = _float(row.get("mt5_executed_price"))
        if entry is None:
            entry = _float(row.get("mt5_entry_plan"))
        target = _float(row.get("mt5_target"))
        quantity = _float(row.get("mt5_quantity"))
        tick_size = _float(contract.get("tick_size"))
        tick_value = _float(contract.get("tick_value"))
        projected = None
        if (
            entry is not None
            and target is not None
            and quantity is not None
            and quantity > 0.0
            and tick_size is not None
            and tick_size > 0.0
            and tick_value is not None
            and tick_value > 0.0
        ):
            projected = abs(target - entry) / tick_size * tick_value * quantity
        row["projected_profit_usd"] = (
            round(projected, 6) if projected is not None else None
        )
        output.append(row)
    return output


def _geometry_matches(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> bool:
    return all(
        _prices_close(_float(expected.get(name)), _float(actual.get(name)))
        for name in ("entry", "stop", "target")
    )


def _geometry_matches_with_atr_tolerance(
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
) -> bool:
    expected_entry = _float(expected.get("entry"))
    actual_entry = _float(actual.get("entry"))
    if not _prices_close(expected_entry, actual_entry):
        return False
    if expected_entry is None or actual_entry is None:
        return False
    expected_stop = _float(expected.get("stop"))
    actual_stop = _float(actual.get("stop"))
    expected_target = _float(expected.get("target"))
    actual_target = _float(actual.get("target"))
    if None in {expected_stop, actual_stop, expected_target, actual_target}:
        return False
    expected_risk = abs(expected_entry - float(expected_stop))
    actual_risk = abs(actual_entry - float(actual_stop))
    expected_reward = abs(float(expected_target) - expected_entry)
    actual_reward = abs(float(actual_target) - actual_entry)
    return (
        _relative_distance_matches(expected_risk, actual_risk)
        and _relative_distance_matches(expected_reward, actual_reward)
    )


def _relative_distance_matches(left: float, right: float) -> bool:
    scale = max(abs(left), abs(right))
    if scale <= 0.0:
        return left == right
    return abs(left - right) / scale <= ATR_GEOMETRY_RELATIVE_TOLERANCE


def _prices_close(left: float | None, right: float | None) -> bool:
    if left is None or right is None:
        return left is right
    return abs(left - right) <= max(1e-8, abs(left) * 1e-7)


def _signal_evidence(
    signal: SignalCandidate,
    specs: Mapping[str, OperationalPatternSpec],
) -> tuple[int, float, float, float, int]:
    spec = specs.get(f"{signal.setup_id}_v{signal.setup_version}")
    if spec is None:
        return (0, 0.0, float(signal.confidence), 0.0, 0)
    validation = float(dict(spec.validation_metrics).get("performance", 0.0) or 0.0)
    oos = float(dict(spec.oos_metrics).get("performance", 0.0) or 0.0)
    tier_priority = int(str(spec.evidence_tier).upper() == "VALIDATED")
    return (
        tier_priority,
        float(spec.selection_score),
        float(signal.confidence),
        min(validation, oos),
        spec.minimum_occurrences,
    )


def _advance_repeat_position(
    signal: SignalCandidate,
    spec: OperationalPatternSpec,
    states: dict[str, tuple[datetime, int]],
) -> int:
    """Apply the same time-bounded recurrence episode used by the live runtime."""

    key = spec.versioned_id
    current = signal.datetime.astimezone(timezone.utc)
    previous = states.get(key)
    window = timedelta(minutes=5 * max(int(spec.repeat_window_candles), 1))
    position = (
        previous[1] + 1
        if previous is not None and current - previous[0] <= window
        else 1
    )
    states[key] = (current, position)
    return position


def _read_candles(path: Path, *, tail: int | None = None) -> list[CandleBar]:
    if not path.exists():
        return []
    if tail:
        header, data_lines = _csv_tail(path, tail)
        reader: Iterable[Mapping[str, str]] = csv.DictReader([header, *data_lines])
    else:
        source = path.open("r", encoding="utf-8-sig", newline="")
        reader = csv.DictReader(source)
    target: list[CandleBar] = []
    try:
        for row in reader:
            if str(row.get("is_closed", "1")).strip().lower() not in {"1", "true", "sim", "yes"}:
                continue
            timestamp = _parse_timestamp(row.get("datetime"))
            if timestamp is None:
                continue
            target.append(
                CandleBar(
                    index=0,
                    timestamp=timestamp,
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    volume=float(row.get("volume", 0.0) or 0.0),
                    spread=float(row.get("spread", 0.0) or 0.0),
                    real_volume=float(row.get("real_volume", 0.0) or 0.0),
                )
            )
    finally:
        if not tail:
            source.close()
    return list(target)


def _csv_last_timestamp_and_count(
    path: Path,
    *,
    frozen: bool = False,
) -> tuple[datetime | None, int]:
    if not path.exists():
        return None, 0
    header, data_lines = _csv_tail(path, 1)
    if not data_lines:
        return None, 0
    row = next(csv.DictReader([header, *data_lines]), {})
    last = _parse_timestamp(row.get("datetime"))
    count = _known_csv_count(path, frozen=frozen)
    return last, count


def _csv_tail(path: Path, quantity: int) -> tuple[str, list[str]]:
    """Read a CSV header and its last non-empty rows without scanning the file."""

    with path.open("r", encoding="utf-8-sig", newline="") as source:
        header = source.readline().rstrip("\r\n")
    if not header or quantity <= 0:
        return header, []
    with path.open("rb") as source:
        source.seek(0, os.SEEK_END)
        position = source.tell()
        chunks: list[bytes] = []
        newline_count = 0
        while position > 0 and newline_count <= quantity + 1:
            size = min(8192, position)
            position -= size
            source.seek(position)
            chunk = source.read(size)
            chunks.append(chunk)
            newline_count += chunk.count(b"\n")
    text = b"".join(reversed(chunks)).decode("utf-8-sig", errors="ignore")
    lines = [line for line in text.splitlines() if line.strip()]
    if position == 0 and lines and lines[0].lstrip("\ufeff") == header:
        lines = lines[1:]
    return header, lines[-quantity:]


def _known_csv_count(path: Path, *, frozen: bool) -> int:
    """Use persisted Replay metadata for frozen files and cheap counting for deltas."""

    if frozen:
        summary = _read_json(path.parent / "pattern_miner_summary.json")
        try:
            return int(summary.get("total_candles", 0) or 0)
        except (TypeError, ValueError):
            return 0
    with path.open("rb") as source:
        return max(sum(chunk.count(b"\n") for chunk in iter(lambda: source.read(65536), b"")) - 1, 0)


def _atomic_csv_write(path: Path, candles: Sequence[CandleBar]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for candle in candles:
            writer.writerow(
                {
                    "datetime": candle.timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume,
                    "spread": candle.spread,
                    "real_volume": candle.real_volume,
                    "is_closed": 1,
                }
            )
    _replace_with_retry(temporary, path)


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    _replace_with_retry(temporary, path)


def _replace_with_retry(source: Path, target: Path) -> None:
    for attempt in range(20):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 19:
                target.write_bytes(source.read_bytes())
                source.unlink(missing_ok=True)
                return
            import time

            time.sleep(0.1)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return dict(payload) if isinstance(payload, dict) else {}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {}


def _value(source: object, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(source, Mapping) and name in source:
            return source[name]
        if hasattr(source, name):
            return getattr(source, name)
    return default


def _candle_timestamp(source: object) -> datetime:
    value = _value(source, "data", "datetime", "timestamp", "time")
    parsed = _parse_timestamp(value)
    if parsed is None:
        raise ValueError("Candle MT5 sem timestamp valido.")
    return parsed


def _normalized_provider_candle(
    source: object,
    clock_offset: timedelta,
) -> CandleBar:
    """Convert a broker-clock candle into the physical UTC timeline."""

    return CandleBar(
        index=0,
        timestamp=_candle_timestamp(source) - clock_offset,
        open=float(_value(source, "abertura", "open")),
        high=float(_value(source, "maxima", "high")),
        low=float(_value(source, "minima", "low")),
        close=float(_value(source, "fechamento", "close")),
        volume=float(_value(source, "volume", "tick_volume", default=0.0)),
        spread=float(_value(source, "spread", default=0.0)),
        real_volume=float(_value(source, "real_volume", default=0.0)),
    )


def _provider_clock_offset(
    provider: object,
    *,
    current: datetime,
) -> timedelta | None:
    """Infer an integer-hour server offset from the latest MT5 tick clock."""

    getter = getattr(provider, "get_server_time", None)
    if not callable(getter):
        return None
    try:
        server_time = _parse_timestamp(getter("EURUSD"))
    except (OSError, RuntimeError, TypeError, ValueError):
        return None
    if server_time is None:
        return None
    drift_seconds = (server_time - _as_utc(current)).total_seconds()
    rounded_hours = int(round(drift_seconds / 3600.0))
    if abs(rounded_hours) > BROKER_CLOCK_OFFSET_MAX_HOURS:
        return None
    # A last tick can lag briefly, but a valid server offset remains close to
    # an integer hour. Larger drifts usually mean that the market is closed.
    if abs(drift_seconds - rounded_hours * 3600) > 30 * 60:
        return None
    return timedelta(hours=rounded_hours)


def _parse_timestamp(value: object) -> datetime | None:
    if value in (None, "", "N/D"):
        return None
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    normalized = str(value).strip().replace("Z", "+00:00")
    for parser in (
        datetime.fromisoformat,
        lambda item: datetime.strptime(item, "%Y-%m-%d %H:%M:%S"),
        lambda item: datetime.strptime(item, "%d/%m/%Y %H:%M"),
    ):
        try:
            return _as_utc(parser(normalized))
        except ValueError:
            continue
    return None


def _as_utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _floor_m5(value: datetime) -> datetime:
    normalized = _as_utc(value).replace(second=0, microsecond=0)
    return normalized - timedelta(minutes=normalized.minute % 5)


def _float(value: object) -> float | None:
    if value in (None, "", "N/D"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _iso(value: datetime | None) -> str:
    return value.isoformat() if value is not None else "N/D"
