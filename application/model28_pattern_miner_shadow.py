"""Model 28 adaptive pattern runtime and Demo execution contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from domain.operational_pattern import ShadowSignalResult, SignalCandidate
from replay.pattern_miner import PatternMinerConfig
from replay.pattern_miner.models import CandleBar, EventRecord

from replay.pattern_miner.operational import (
    MODEL_28_CONTRACT_VERSION,
    MODEL_28_EXECUTION_MODE,
    MODEL_28_ID,
    MODEL_28_SHORT_NAME,
    MODEL_28_SOURCE,
    LivePatternEngine,
    OperationalPatternStore,
    ShadowSignalJournal,
)

MODEL_28_ALPHA_ID = "ALPHA028_PATTERN_MINER_PROMOTED"
MODEL_28_BETA_ID = "BETA028_REPLAY_DERIVED_FIXED_RISK"
MODEL_28_COMMENT = "TraderIA M28 ADAPTIVE"
MODEL_28_VOLUME = 0.04
MODEL_28_STOP_MANAGEMENT = "M28_FIXED_PATTERN_GEOMETRY"
MODEL_28_SYMBOL = "XAUUSD"
MODEL_28_TIMEFRAME = "M5"
DEFAULT_MODEL_28_REGISTRY_PATH = (
    Path(__file__).resolve().parents[1]
    / ".traderia"
    / "research"
    / "historicoXAU"
    / "model28_operational_patterns.json"
)
DEFAULT_MODEL_28_SHADOW_JOURNAL_PATH = (
    DEFAULT_MODEL_28_REGISTRY_PATH.parent / "model28_shadow_signals.json"
)


@dataclass(frozen=True, slots=True)
class Model28LiveSelection:
    """Current replay-validated setup selected from the live closed candle."""

    versioned_id: str
    pattern_id: str
    direction: str
    selected_at: str
    confidence: float
    validation_performance: float
    oos_performance: float
    valid_until_index: int
    occurrence_id: str
    symbol: str
    timeframe: str
    entry_reference: float
    stop_reference: float
    target_reference: float
    reason: str


class Model28ShadowRuntime:
    """Consume live closed candles and expose the strongest executable setup."""

    def __init__(
        self,
        registry_path: str | Path = DEFAULT_MODEL_28_REGISTRY_PATH,
        journal_path: str | Path = DEFAULT_MODEL_28_SHADOW_JOURNAL_PATH,
        config: PatternMinerConfig | None = None,
    ) -> None:
        self.store = OperationalPatternStore(registry_path)
        self.journal = ShadowSignalJournal(journal_path)
        specs = self.store.load()
        self.config = config or PatternMinerConfig()
        self._engines: dict[tuple[str, str], LivePatternEngine] = {}
        self._selections: dict[tuple[str, str], Model28LiveSelection] = {}
        for key in {
            (str(item.symbol).upper(), str(item.timeframe).upper())
            for item in specs
        }:
            self._engine_for(*key, specs=specs)
        self.engine = self._engine_for(MODEL_28_SYMBOL, MODEL_28_TIMEFRAME, specs)
        self._spec_signature = self._signature(specs)

    def refresh_specs(self) -> None:
        specs = self.store.load()
        signature = self._signature(specs)
        if signature == self._spec_signature:
            return
        active_keys = {
            (str(item.symbol).upper(), str(item.timeframe).upper())
            for item in specs
        }
        for key in active_keys:
            engine = self._engine_for(*key, specs=specs)
            engine.tracker.set_specs(self._specs_for_market(specs, *key))
        for key, engine in self._engines.items():
            if key not in active_keys:
                engine.tracker.set_specs(())
        self._spec_signature = signature

    def has_active_specs(self) -> bool:
        self.refresh_specs()
        return any(engine.tracker.specs for engine in self._engines.values())

    def active_markets(self) -> tuple[tuple[str, str], ...]:
        """Markets with promoted and running M28 contracts."""

        self.refresh_specs()
        return tuple(
            sorted(
                key
                for key, engine in self._engines.items()
                if engine.tracker.specs
            )
        )

    def live_selection(
        self,
        symbol: str | None = None,
        timeframe: str = MODEL_28_TIMEFRAME,
    ) -> Model28LiveSelection | None:
        if symbol:
            return self._selections.get((symbol.upper(), timeframe.upper()))
        if not self._selections:
            return None
        return max(self._selections.values(), key=lambda item: item.selected_at)

    def synchronize_mt5_closed_candles(
        self,
        rows: Sequence[object],
        *,
        symbol: str = MODEL_28_SYMBOL,
        timeframe: str = MODEL_28_TIMEFRAME,
    ) -> Model28LiveSelection | None:
        """Consume only chronological M5 candles not seen by this live runtime."""

        self.refresh_specs()
        key = (symbol.upper(), timeframe.upper())
        engine = self._engines.get(key)
        if engine is None or not engine.tracker.specs:
            self._selections.pop(key, None)
            return None
        parsed = sorted(
            (_candle_bar_from_mt5(row, index) for index, row in enumerate(rows)),
            key=lambda candle: candle.timestamp,
        )
        deduplicated: list[CandleBar] = []
        for candle in parsed:
            if deduplicated and candle.timestamp == deduplicated[-1].timestamp:
                deduplicated[-1] = candle
            else:
                deduplicated.append(candle)
        last_timestamp = (
            engine.candles[-1].timestamp if engine.candles else None
        )
        incoming = [
            candle
            for candle in deduplicated
            if last_timestamp is None or candle.timestamp > last_timestamp
        ]
        bootstrap = not engine.candles
        for candle in incoming:
            if bootstrap:
                record, signals = engine.consume_closed_candle(candle)
            else:
                self.journal.evaluate(candle, symbol=key[0])
                record, signals = engine.consume_closed_candle(candle)
                if signals:
                    self.journal.record(signals)
            self._update_selection(record, signals, key=key)
            bootstrap = False
        return self._selections.get(key)

    def consume_closed_candle(
        self,
        candle: CandleBar,
    ) -> tuple[EventRecord, tuple[SignalCandidate, ...]]:
        self.journal.evaluate(candle, symbol=MODEL_28_SYMBOL)
        record, signals = self.engine.consume_closed_candle(candle)
        if signals:
            self.journal.record(signals)
        self._update_selection(record, signals)
        return record, signals

    def shadow_results(self) -> tuple[ShadowSignalResult, ...]:
        return self.journal.load()

    def _update_selection(
        self,
        record: EventRecord,
        signals: tuple[SignalCandidate, ...],
        *,
        key: tuple[str, str] = (MODEL_28_SYMBOL, MODEL_28_TIMEFRAME),
    ) -> None:
        current = self._selections.get(key)
        if (
            current is not None
            and record.index > current.valid_until_index
        ):
            self._selections.pop(key, None)
        if not signals:
            return
        engine = self._engines[key]
        specs = {
            item.versioned_id: item for item in engine.tracker.specs
        }

        def evidence(signal: SignalCandidate) -> tuple[float, float, float, int]:
            spec = specs.get(f"{signal.setup_id}_v{signal.setup_version}")
            validation = _metric(spec.validation_metrics, "performance") if spec else 0.0
            oos = _metric(spec.oos_metrics, "performance") if spec else 0.0
            occurrences = int(spec.minimum_occurrences) if spec else 0
            return (float(signal.confidence), min(validation, oos), oos, occurrences)

        selected = max(signals, key=evidence)
        spec = specs[f"{selected.setup_id}_v{selected.setup_version}"]
        validation = _metric(spec.validation_metrics, "performance")
        oos = _metric(spec.oos_metrics, "performance")
        self._selections[key] = Model28LiveSelection(
            versioned_id=spec.versioned_id,
            pattern_id=spec.pattern_id,
            direction=selected.direction,
            selected_at=selected.datetime.isoformat(),
            confidence=float(selected.confidence),
            validation_performance=validation,
            oos_performance=oos,
            valid_until_index=record.index + spec.max_distance_between_events,
            occurrence_id=selected.pattern_occurrence_id,
            symbol=selected.symbol,
            timeframe=selected.timeframe,
            entry_reference=float(selected.entry_reference),
            stop_reference=float(selected.stop_reference),
            target_reference=float(selected.target_reference),
            reason=(
                "Padrao causal concluido no candle M5 fechado; escolhido entre "
                f"{len(signals)} candidato(s) por score, validacao e OOS."
            ),
        )

    def _engine_for(
        self,
        symbol: str,
        timeframe: str,
        specs: Sequence[object],
    ) -> LivePatternEngine:
        key = (symbol.upper(), timeframe.upper())
        engine = self._engines.get(key)
        if engine is None:
            engine = LivePatternEngine(
                self.config,
                self._specs_for_market(specs, *key),
            )
            self._engines[key] = engine
        return engine

    @staticmethod
    def _specs_for_market(
        specs: Sequence[object],
        symbol: str,
        timeframe: str,
    ) -> tuple[object, ...]:
        return tuple(
            item
            for item in specs
            if str(getattr(item, "symbol", "")).upper() == symbol.upper()
            and str(getattr(item, "timeframe", "")).upper() == timeframe.upper()
        )

    @staticmethod
    def _signature(specs: Sequence[object]) -> tuple[tuple[str, str], ...]:
        return tuple(
            (str(getattr(item, "versioned_id", "")), str(getattr(getattr(item, "shadow_status", None), "value", "")))
            for item in specs
        )


def model28_parameters() -> dict[str, object]:
    return {
        "model_id": MODEL_28_ID,
        "short_name": MODEL_28_SHORT_NAME,
        "source": MODEL_28_SOURCE,
        "contract_version": MODEL_28_CONTRACT_VERSION,
        "execution_mode": MODEL_28_EXECUTION_MODE,
        "manual_promotion_required": True,
        "shadow_required_before_active": True,
        "execution_volume": MODEL_28_VOLUME,
        "can_send_orders": True,
        "real_account_allowed": False,
        "active_entry_order_type": "MARKET",
        "active_signal_kind": "ADAPTIVE_PATTERN",
        "stop_management": MODEL_28_STOP_MANAGEMENT,
        "live_adaptive_selection": True,
        "live_source": "MULTI_MARKET_M5_CLOSED_CANDLES",
    }


def _metric(rows: Sequence[tuple[str, float]], name: str) -> float:
    return float(dict(rows).get(name, 0.0) or 0.0)


def _candle_bar_from_mt5(row: object, index: int) -> CandleBar:
    timestamp = _timestamp(_row_value(row, "data", "time", "timestamp"))
    return CandleBar(
        index=index,
        timestamp=timestamp,
        open=float(_row_value(row, "abertura", "open")),
        high=float(_row_value(row, "maxima", "high")),
        low=float(_row_value(row, "minima", "low")),
        close=float(_row_value(row, "fechamento", "close")),
        volume=float(_row_value(row, "volume", "tick_volume", default=0.0)),
        spread=float(_row_value(row, "spread", default=0.0)),
        real_volume=float(_row_value(row, "real_volume", default=0.0)),
    )


def _row_value(row: object, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(row, Mapping) and name in row:
            return row[name]
        dtype_names = getattr(getattr(row, "dtype", None), "names", ()) or ()
        if name in dtype_names:
            return row[name]  # type: ignore[index]
        if hasattr(row, name):
            return getattr(row, name)
    if default is not None:
        return default
    raise ValueError(f"Campo MT5 ausente: {names[0]}")


def _timestamp(value: object) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    normalized = str(value or "").strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        parsed = datetime.strptime(normalized, "%Y-%m-%d %H:%M:%S")
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
