"""Model 28 adaptive pattern runtime and Demo execution contract."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from domain.operational_pattern import (
    OperationalPatternSpec,
    OperationalPatternStatus,
    ShadowSignalResult,
    ShadowStatus,
    SignalCandidate,
)
from replay.pattern_miner import PatternMinerConfig
from replay.pattern_miner.models import CandleBar, EventRecord

from replay.pattern_miner.operational import (
    MODEL_28_CONTRACT_VERSION,
    MODEL_28_ENTRY_RULE,
    MODEL_28_EXECUTION_MODE,
    MODEL_28_ID,
    MODEL_28_SHORT_NAME,
    MODEL_28_SOURCE,
    LivePatternEngine,
    OperationalPatternStore,
    ShadowSignalJournal,
)

MODEL_28_ALPHA_ID = "ALPHA028_PATTERN_MINER_PROMOTED"
MODEL_28_BETA_ID = "BETA028_REPLAY_DERIVED_EMPIRICAL_CONTRACT"
MODEL_28_COMMENT = "TraderIA M28 ADAPTIVE"
MODEL_28_VOLUME = 0.11
MODEL_28_STOP_MANAGEMENT = "M28_EMPIRICAL_PATTERN_CONTRACT"
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
DEFAULT_MODEL_28_RESEARCH_REPORT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".traderia"
    / "research"
    / "model28_optimizer"
    / "empirical_pattern_contracts_v6.json"
)
MODEL_28_RESEARCH_SCHEMA_V6 = "model28-empirical-pattern-contracts-v6-research"
MODEL_28_VALIDATED_TIER = "VALIDATED"
MODEL_28_EXPLORATION_TIER = "EXPLORATION_DEMO"


def synchronize_model28_replay_contracts(
    *,
    registry_path: str | Path = DEFAULT_MODEL_28_REGISTRY_PATH,
    report_path: str | Path = DEFAULT_MODEL_28_RESEARCH_REPORT_PATH,
    config: PatternMinerConfig | None = None,
) -> tuple[OperationalPatternSpec, ...]:
    """Activate the validated/exploratory Demo portfolio built from each 100k Replay."""

    path = Path(report_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return ()
    schema = str(payload.get("schema_version", ""))
    if schema != MODEL_28_RESEARCH_SCHEMA_V6:
        return ()

    miner_config = config or PatternMinerConfig()
    contract_field = "operational_contracts"
    total_field = "operational_total"
    source_contracts = tuple(payload.get(contract_field, ()) or ())
    try:
        declared_total = int(payload.get(total_field, len(source_contracts)))
    except (TypeError, ValueError):
        return ()
    if declared_total != len(source_contracts) or not source_contracts:
        return ()
    candidate_rows = [
        _spec_from_replay_contract(source, config=miner_config, report_schema=schema)
        if isinstance(source, Mapping)
        else None
        for source in source_contracts
    ]
    if any(candidate is None for candidate in candidate_rows):
        return ()
    candidates = tuple(candidate for candidate in candidate_rows if candidate is not None)
    store = OperationalPatternStore(registry_path)
    original = store.load()
    existing = list(original)
    synchronized: list[OperationalPatternSpec] = []

    for candidate in candidates:
        same_setup = [item for item in existing if item.setup_id == candidate.setup_id]
        current_index = next(
            (
                index
                for index in range(len(existing) - 1, -1, -1)
                if existing[index].setup_id == candidate.setup_id
                if _replay_contract_signature(existing[index])
                == _replay_contract_signature(candidate)
            ),
            None,
        )
        if current_index is None:
            version = max((item.version for item in same_setup), default=0) + 1
            current = replace(candidate, version=version)
            existing.append(current)
        else:
            current = existing[current_index]
            if (
                current.status != OperationalPatternStatus.OPERATIONAL_CANDIDATE
                or current.shadow_status != ShadowStatus.RUNNING
            ):
                current = replace(
                    current,
                    status=OperationalPatternStatus.OPERATIONAL_CANDIDATE,
                    shadow_status=ShadowStatus.RUNNING,
                )
                existing[current_index] = current
        synchronized.append(current)

    active_ids = {item.versioned_id for item in synchronized}
    for index, item in enumerate(existing):
        if (
            str(item.contract_version).startswith("M28_PATTERN_BRIDGE_")
            and item.versioned_id not in active_ids
            and (
                item.status != OperationalPatternStatus.DISABLED
                or item.shadow_status != ShadowStatus.OFF
            )
        ):
            existing[index] = replace(
                item,
                status=OperationalPatternStatus.DISABLED,
                shadow_status=ShadowStatus.OFF,
            )

    if tuple(existing) != original:
        store.save(existing)
    return tuple(synchronized)


@dataclass(frozen=True, slots=True)
class Model28LiveSelection:
    """Current 100k-ranked setup selected from the live closed candle."""

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
    evidence_tier: str = MODEL_28_VALIDATED_TIER
    adaptive_rank: int = 0
    pattern_family: str = ""
    selection_score: float = 0.0
    repeat_position: int = 1
    repeat_limit: int = 1
    repeat_probability: float = 0.0
    repeat_basis: str = "FIRST_OCCURRENCE_ONLY"
    entry_rule: str = MODEL_28_ENTRY_RULE
    stop_rule: str = ""
    target_rule: str = ""
    expiration_rule: str = ""
    max_holding_candles: int = 100
    cost_rule: str = ""
    stop_atr: float = 0.0
    target_atr: float = 0.0
    geometry_method: str = ""


class Model28ShadowRuntime:
    """Consume live closed candles and expose the strongest executable setup."""

    def __init__(
        self,
        registry_path: str | Path = DEFAULT_MODEL_28_REGISTRY_PATH,
        journal_path: str | Path = DEFAULT_MODEL_28_SHADOW_JOURNAL_PATH,
        config: PatternMinerConfig | None = None,
        research_report_path: str | Path | None = None,
        auto_activate_replay_contracts: bool | None = None,
    ) -> None:
        self.store = OperationalPatternStore(registry_path)
        self.journal = ShadowSignalJournal(journal_path)
        self.config = config or PatternMinerConfig()
        registry_is_default = (
            Path(registry_path).resolve() == DEFAULT_MODEL_28_REGISTRY_PATH.resolve()
        )
        self._auto_activate_replay_contracts = (
            registry_is_default or research_report_path is not None
            if auto_activate_replay_contracts is None
            else bool(auto_activate_replay_contracts)
        )
        self._research_report_path = (
            Path(research_report_path)
            if research_report_path is not None
            else DEFAULT_MODEL_28_RESEARCH_REPORT_PATH
        )
        self._research_report_mtime_ns: int | None = None
        self._synchronize_replay_registry()
        specs = tuple(
            item
            for item in self.store.load()
            if _is_empirical_spec(item, self.config)
        )
        self._engines: dict[tuple[str, str], LivePatternEngine] = {}
        self._selections: dict[tuple[str, str], Model28LiveSelection] = {}
        self._latest_records: dict[tuple[str, str], EventRecord] = {}
        for key in {
            (str(item.symbol).upper(), str(item.timeframe).upper())
            for item in specs
        }:
            self._engine_for(*key, specs=specs)
        self.engine = self._engine_for(MODEL_28_SYMBOL, MODEL_28_TIMEFRAME, specs)
        self._spec_signature = self._signature(specs)

    def refresh_specs(self) -> None:
        self._synchronize_replay_registry()
        specs = tuple(
            item
            for item in self.store.load()
            if _is_empirical_spec(item, self.config)
        )
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

    def _synchronize_replay_registry(self) -> None:
        if not self._auto_activate_replay_contracts:
            return
        try:
            mtime_ns = self._research_report_path.stat().st_mtime_ns
        except OSError:
            return
        if mtime_ns == self._research_report_mtime_ns:
            return
        synchronize_model28_replay_contracts(
            registry_path=self.store.path,
            report_path=self._research_report_path,
            config=self.config,
        )
        self._research_report_mtime_ns = mtime_ns

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

    def latest_record(
        self,
        symbol: str,
        timeframe: str = MODEL_28_TIMEFRAME,
    ) -> EventRecord | None:
        """Return the latest causal record already computed by the shared M5 pass."""

        return self._latest_records.get((symbol.upper(), timeframe.upper()))

    def record_history(
        self,
        symbol: str,
        timeframe: str = MODEL_28_TIMEFRAME,
    ) -> tuple[EventRecord, ...]:
        """Expose the bounded live record history without another MT5 read."""

        engine = self._engines.get((symbol.upper(), timeframe.upper()))
        return tuple(engine.records) if engine is not None else ()

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
            self._latest_records[key] = record
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
        self._latest_records[(MODEL_28_SYMBOL, MODEL_28_TIMEFRAME)] = record
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
        active_signals = tuple(
            signal
            for signal in signals
            if f"{signal.setup_id}_v{signal.setup_version}" in specs
        )
        if not active_signals:
            return
        journal_rows = self.journal.load()
        repeat_positions: dict[str, int] = {}
        eligible_signals: list[SignalCandidate] = []
        for signal in active_signals:
            versioned_id = f"{signal.setup_id}_v{signal.setup_version}"
            spec = specs[versioned_id]
            position = self._repeat_position(signal, spec, journal_rows)
            repeat_positions[signal.pattern_occurrence_id] = position
            if position <= max(int(spec.repeat_limit), 1):
                eligible_signals.append(signal)
        if not eligible_signals:
            return

        def evidence(signal: SignalCandidate) -> tuple[int, float, float, float, int]:
            spec = specs.get(f"{signal.setup_id}_v{signal.setup_version}")
            validation = _metric(spec.validation_metrics, "performance") if spec else 0.0
            oos = _metric(spec.oos_metrics, "performance") if spec else 0.0
            occurrences = int(spec.minimum_occurrences) if spec else 0
            tier = str(getattr(spec, "evidence_tier", ""))
            tier_priority = 1 if tier == MODEL_28_VALIDATED_TIER else 0
            selection_score = float(getattr(spec, "selection_score", 0.0) or 0.0)
            return (
                tier_priority,
                selection_score,
                float(signal.confidence),
                min(validation, oos),
                occurrences,
            )

        selected = max(eligible_signals, key=evidence)
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
            valid_until_index=record.index,
            occurrence_id=selected.pattern_occurrence_id,
            symbol=selected.symbol,
            timeframe=selected.timeframe,
            entry_reference=float(selected.entry_reference),
            stop_reference=float(selected.stop_reference),
            target_reference=float(selected.target_reference),
            evidence_tier=spec.evidence_tier,
            adaptive_rank=spec.adaptive_rank,
            pattern_family=spec.pattern_family,
            selection_score=spec.selection_score,
            repeat_position=repeat_positions[selected.pattern_occurrence_id],
            repeat_limit=spec.repeat_limit,
            repeat_probability=spec.repeat_probability,
            repeat_basis=spec.repeat_basis,
            entry_rule=spec.entry_rule,
            stop_rule=spec.stop_rule,
            target_rule=spec.target_rule,
            expiration_rule=spec.expiration_rule,
            max_holding_candles=spec.max_holding_candles,
            cost_rule=spec.cost_rule,
            stop_atr=spec.stop_atr,
            target_atr=spec.target_atr,
            geometry_method=spec.geometry_method,
            reason=(
                "Padrao causal identificado no candle M5 fechado; contrato empirico "
                "aprendido nas 100 mil velas e escolhido entre "
                f"{len(eligible_signals)} candidato(s) elegivel(is) por tier e "
                f"ranking. Repeticao {repeat_positions[selected.pattern_occurrence_id]}"
                f"/{spec.repeat_limit} sustentada pelo historico."
            ),
        )

    @staticmethod
    def _repeat_position(
        signal: SignalCandidate,
        spec: OperationalPatternSpec,
        rows: Sequence[ShadowSignalResult],
    ) -> int:
        """Count the current occurrence inside the persisted same-pattern episode."""

        window = timedelta(minutes=5 * max(int(spec.repeat_window_candles), 1))
        previous: list[datetime] = []
        for item in rows:
            if (
                item.pattern_occurrence_id == signal.pattern_occurrence_id
                or item.setup_id != signal.setup_id
                or int(item.setup_version) != int(signal.setup_version)
                or item.symbol.upper() != signal.symbol.upper()
                or item.timeframe.upper() != signal.timeframe.upper()
            ):
                continue
            try:
                opened_at = datetime.fromisoformat(item.opened_at.replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            if opened_at.tzinfo is None:
                opened_at = opened_at.replace(tzinfo=timezone.utc)
            if opened_at < signal.datetime:
                previous.append(opened_at.astimezone(timezone.utc))
        position = 1
        anchor = signal.datetime.astimezone(timezone.utc)
        for opened_at in sorted(previous, reverse=True):
            gap = anchor - opened_at
            if gap > window:
                break
            position += 1
            anchor = opened_at
        return position

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
        "manual_promotion_required": False,
        "automatic_replay_promotion": True,
        "adaptive_demo_portfolio": True,
        "pattern_specific_empirical_contracts": True,
        "universal_stop_target_grid": False,
        "exploration_contracts_can_send_demo": True,
        "shadow_required_before_active": False,
        "forward_validation_blocks_demo": False,
        "execution_volume": MODEL_28_VOLUME,
        "can_send_orders": True,
        "real_account_allowed": False,
        "active_entry_order_type": "MARKET",
        "active_signal_kind": "ADAPTIVE_PATTERN",
        "stop_management": MODEL_28_STOP_MANAGEMENT,
        "live_adaptive_selection": True,
        "live_source": "MULTI_MARKET_M5_CLOSED_CANDLES",
        "first_occurrence_always_eligible": True,
        "repeat_limit_is_historical": True,
        "historical_cost_rule": "RECORDED_ENTRY_SPREAD_ONLY",
    }


def _metric(rows: Sequence[tuple[str, float]], name: str) -> float:
    return float(dict(rows).get(name, 0.0) or 0.0)


def _spec_from_replay_contract(
    source: Mapping[str, Any],
    *,
    config: PatternMinerConfig,
    report_schema: str = MODEL_28_RESEARCH_SCHEMA_V6,
) -> OperationalPatternSpec | None:
    evidence_tier = str(
        source.get(
            "operational_tier",
            MODEL_28_VALIDATED_TIER if source.get("approved") is True else "",
        )
    ).strip().upper()
    if evidence_tier not in {MODEL_28_VALIDATED_TIER, MODEL_28_EXPLORATION_TIER}:
        return None
    if evidence_tier == MODEL_28_VALIDATED_TIER and source.get("approved") is not True:
        return None
    symbol = str(source.get("symbol", "")).strip().upper()
    pattern_id = str(source.get("pattern_id", "")).strip().upper()
    direction = str(source.get("direction", "")).strip().upper()
    events = tuple(str(item) for item in source.get("events", ()) or ())
    gaps = tuple(str(item) for item in source.get("gaps", ()) or ())
    if (
        not symbol
        or not pattern_id
        or direction not in {"BUY", "SELL"}
        or not 2 <= len(events) <= 5
        or len(gaps) != len(events) - 1
    ):
        return None

    split_rows = {
        name: dict(source.get(name, {}) or {})
        for name in ("discovery", "validation", "oos")
    }
    total_occurrences = sum(
        int(metrics.get("trades", 0) or 0) for metrics in split_rows.values()
    )
    minimum_total = (
        int(config.operational_min_occurrences)
        if evidence_tier == MODEL_28_VALIDATED_TIER
        else 60
    )
    if total_occurrences < minimum_total:
        return None
    splits_to_gate = (
        tuple(split_rows.values())
        if evidence_tier == MODEL_28_VALIDATED_TIER
        else (split_rows["discovery"],)
    )
    for metrics in splits_to_gate:
        if (
            float(metrics.get("expectancy_r", 0.0) or 0.0)
            < float(config.operational_min_split_expectancy_r)
            or float(metrics.get("lower_80_expectancy_r", 0.0) or 0.0) <= 0.0
        ):
            return None

    try:
        stop_atr = float(source.get("stop_atr", 0.0) or 0.0)
        target_atr = float(source.get("target_atr", 0.0) or 0.0)
        max_holding_candles = int(source.get("max_holding_candles", 0) or 0)
        robust_floor = float(source.get("robust_floor_r", 0.0) or 0.0)
        selection_score = float(source.get("adaptive_score", robust_floor) or 0.0)
        selection_confidence = float(
            source.get("selection_confidence", max(robust_floor, 0.01)) or 0.01
        )
        adaptive_rank = int(source.get("adaptive_rank", 0) or 0)
        repeat_limit = int(source.get("repeat_limit", 1) or 1)
        repeat_window_candles = int(
            source.get("repeat_window_candles", 100) or 100
        )
        repeat_probability = float(source.get("repeat_probability", 0.0) or 0.0)
    except (TypeError, ValueError):
        return None
    if stop_atr <= 0.0 or target_atr <= 0.0 or max_holding_candles <= 0:
        return None
    if evidence_tier == MODEL_28_VALIDATED_TIER and robust_floor <= 0.0:
        return None
    selection_confidence = max(0.01, min(selection_confidence, 0.99))
    repeat_limit = max(1, min(repeat_limit, 5))
    repeat_window_candles = max(1, repeat_window_candles)
    repeat_probability = max(0.0, min(repeat_probability, 1.0))
    repeat_basis = str(
        source.get("repeat_basis", "FIRST_OCCURRENCE_ONLY")
    ).strip().upper()
    repeat_statistics = _replay_repeat_statistics(source)
    pattern_family = str(source.get("pattern_family", pattern_id)).strip().upper()
    entry_rule = str(source.get("entry_rule", "")).strip().upper()
    stop_rule = str(source.get("stop_rule", "")).strip().upper()
    target_rule = str(source.get("target_rule", "")).strip().upper()
    expiration_rule = str(source.get("expiration_rule", "")).strip().upper()
    geometry_method = str(source.get("geometry_method", "")).strip().upper()
    cost_rule = str(source.get("cost_rule", "")).strip().upper()
    if (
        entry_rule != MODEL_28_ENTRY_RULE
        or not stop_rule.startswith("DISCOVERY_MAE_Q")
        or not target_rule.startswith("DISCOVERY_MFE_Q")
        or not expiration_rule.startswith("FULL_EXIT_AFTER_")
        or geometry_method != "PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE"
        or cost_rule != "RECORDED_ENTRY_SPREAD_ONLY"
    ):
        return None
    geometry_statistics = _replay_geometry_statistics(source)

    raw_context = source.get("context", {}) or {}
    if not isinstance(raw_context, Mapping):
        return None
    context_filters = (("warmup_complete", True),) + tuple(
        (str(name), value)
        for name, value in sorted(raw_context.items(), key=lambda item: str(item[0]))
    )
    fingerprint_payload = {
        "schema": MODEL_28_CONTRACT_VERSION,
        "symbol": symbol,
        "pattern_id": pattern_id,
        "direction": direction,
        "events": events,
        "gaps": gaps,
        "context": dict(raw_context),
        "stop_atr": stop_atr,
        "target_atr": target_atr,
        "max_holding_candles": max_holding_candles,
        "entry_rule": entry_rule,
        "stop_rule": stop_rule,
        "target_rule": target_rule,
        "expiration_rule": expiration_rule,
        "geometry_method": geometry_method,
        "cost_rule": cost_rule,
        "geometry_statistics": geometry_statistics,
        "splits": split_rows,
        "evidence_tier": evidence_tier,
        "adaptive_rank": adaptive_rank,
        "pattern_family": pattern_family,
        "selection_score": selection_score,
        "repeat_limit": repeat_limit,
        "repeat_window_candles": repeat_window_candles,
        "repeat_probability": repeat_probability,
        "repeat_basis": repeat_basis,
        "repeat_statistics": repeat_statistics,
        "report_schema": report_schema,
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            fingerprint_payload,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]
    return OperationalPatternSpec.created_now(
        setup_id=f"{symbol}_M28_{pattern_id.replace('-', '_')}",
        pattern_id=pattern_id,
        version=1,
        symbol=symbol,
        timeframe=MODEL_28_TIMEFRAME,
        direction=direction,
        event_sequence=events,
        event_gap_buckets=gaps,
        max_distance_between_events=config.max_event_distance,
        context_filters=context_filters,
        entry_rule=entry_rule,
        stop_rule=stop_rule,
        target_rule=target_rule,
        target_atr=target_atr,
        expiration_rule=expiration_rule,
        minimum_score=selection_confidence,
        minimum_occurrences=total_occurrences,
        discovery_metrics=_replay_split_metrics(split_rows["discovery"]),
        validation_metrics=_replay_split_metrics(split_rows["validation"]),
        oos_metrics=_replay_split_metrics(split_rows["oos"]),
        status=OperationalPatternStatus.OPERATIONAL_CANDIDATE,
        shadow_status=ShadowStatus.RUNNING,
        source_cache_key=f"100k-empirical:{fingerprint}",
        stop_atr=stop_atr,
        contract_version=MODEL_28_CONTRACT_VERSION,
        evidence_tier=evidence_tier,
        adaptive_rank=adaptive_rank,
        pattern_family=pattern_family,
        selection_score=selection_score,
        repeat_limit=repeat_limit,
        repeat_window_candles=repeat_window_candles,
        repeat_probability=repeat_probability,
        repeat_basis=repeat_basis,
        repeat_statistics=repeat_statistics,
        max_holding_candles=max_holding_candles,
        cost_rule=cost_rule,
        geometry_method=geometry_method,
        geometry_statistics=geometry_statistics,
    )


def _replay_repeat_statistics(source: Mapping[str, Any]) -> tuple[tuple[str, float], ...]:
    """Flatten the persisted recurrence evidence into the immutable contract."""

    analysis = source.get("repeat_analysis", {}) or {}
    if not isinstance(analysis, Mapping):
        return ()
    profile = analysis.get("all", {}) or {}
    if not isinstance(profile, Mapping):
        return ()
    length_counts = profile.get("length_counts", {}) or {}
    positions = profile.get("positions", {}) or {}
    if not isinstance(length_counts, Mapping) or not isinstance(positions, Mapping):
        return ()
    rows: list[tuple[str, float]] = [
        ("episodes", float(profile.get("episodes", 0) or 0)),
        ("isolated", float(length_counts.get("1", 0) or 0)),
        ("pairs", float(length_counts.get("2", 0) or 0)),
        ("triples", float(length_counts.get("3", 0) or 0)),
        ("four", float(length_counts.get("4", 0) or 0)),
        ("five_plus", float(length_counts.get("5_plus", 0) or 0)),
        ("modal_length", float(profile.get("modal_repeat_count", 1) or 1)),
        ("median_length", float(profile.get("median_repeat_count", 1) or 1)),
        (
            "pair_or_more_probability",
            float(profile.get("pair_or_more_probability", 0.0) or 0.0),
        ),
        (
            "triple_or_more_probability",
            float(profile.get("triple_or_more_probability", 0.0) or 0.0),
        ),
    ]
    for position in range(1, 6):
        metrics = positions.get(str(position), {}) or {}
        if not isinstance(metrics, Mapping):
            metrics = {}
        prefix = f"position_{position}"
        rows.extend(
            (
                (f"{prefix}_trades", float(metrics.get("trades", 0) or 0)),
                (
                    f"{prefix}_expectancy_r",
                    float(metrics.get("expectancy_r", 0.0) or 0.0),
                ),
                (
                    f"{prefix}_lower_80_expectancy_r",
                    float(metrics.get("lower_80_expectancy_r", 0.0) or 0.0),
                ),
                (
                    f"{prefix}_reach_probability",
                    float(metrics.get("reach_probability", 0.0) or 0.0),
                ),
                (
                    f"{prefix}_continuation_probability",
                    float(metrics.get("continuation_probability", 0.0) or 0.0),
                ),
            )
        )
    return tuple(rows)


def _replay_geometry_statistics(
    source: Mapping[str, Any],
) -> tuple[tuple[str, float], ...]:
    """Keep the empirical derivation auditable inside the immutable contract."""

    discovery = source.get("discovery", {}) or {}
    validation = source.get("validation", {}) or {}
    oos = source.get("oos", {}) or {}
    if not all(isinstance(item, Mapping) for item in (discovery, validation, oos)):
        return ()
    return (
        ("stop_quantile", float(source.get("stop_quantile", 0.0) or 0.0)),
        ("target_quantile", float(source.get("target_quantile", 0.0) or 0.0)),
        ("stop_atr", float(source.get("stop_atr", 0.0) or 0.0)),
        ("target_atr", float(source.get("target_atr", 0.0) or 0.0)),
        (
            "max_holding_candles",
            float(source.get("max_holding_candles", 0) or 0),
        ),
        (
            "discovery_mean_recorded_cost_r",
            float(discovery.get("mean_recorded_cost_r", 0.0) or 0.0),
        ),
        (
            "validation_mean_recorded_cost_r",
            float(validation.get("mean_recorded_cost_r", 0.0) or 0.0),
        ),
        (
            "oos_mean_recorded_cost_r",
            float(oos.get("mean_recorded_cost_r", 0.0) or 0.0),
        ),
    )


def _replay_split_metrics(metrics: Mapping[str, Any]) -> tuple[tuple[str, float], ...]:
    expectancy = float(metrics.get("expectancy_r", 0.0) or 0.0)
    return (
        ("performance", expectancy),
        ("horizon_return_atr", expectancy),
        ("lower_80_expectancy_r", float(metrics.get("lower_80_expectancy_r", 0.0) or 0.0)),
        ("trades", float(metrics.get("trades", 0) or 0)),
        ("win_rate", float(metrics.get("win_rate", 0.0) or 0.0)),
        (
            "mean_recorded_cost_r",
            float(metrics.get("mean_recorded_cost_r", 0.0) or 0.0),
        ),
    )


def _replay_contract_signature(spec: OperationalPatternSpec) -> tuple[object, ...]:
    return (
        spec.pattern_id,
        spec.symbol,
        spec.timeframe,
        spec.direction,
        spec.event_sequence,
        spec.event_gap_buckets,
        spec.max_distance_between_events,
        spec.context_filters,
        spec.entry_rule,
        spec.stop_rule,
        spec.target_rule,
        spec.target_atr,
        spec.expiration_rule,
        spec.minimum_score,
        spec.minimum_occurrences,
        spec.discovery_metrics,
        spec.validation_metrics,
        spec.oos_metrics,
        spec.source_cache_key,
        spec.stop_atr,
        spec.contract_version,
        spec.evidence_tier,
        spec.adaptive_rank,
        spec.pattern_family,
        spec.selection_score,
        spec.repeat_limit,
        spec.repeat_window_candles,
        spec.repeat_probability,
        spec.repeat_basis,
        spec.repeat_statistics,
        spec.max_holding_candles,
        spec.cost_rule,
        spec.geometry_method,
        spec.geometry_statistics,
    )


def _is_empirical_spec(item: object, config: PatternMinerConfig) -> bool:
    """Accept only v6 Pattern IDs with Replay-learned operational contracts."""

    if str(getattr(item, "contract_version", "")) != MODEL_28_CONTRACT_VERSION:
        return False
    if str(getattr(item, "entry_rule", "")) != MODEL_28_ENTRY_RULE:
        return False
    tier = str(getattr(item, "evidence_tier", "")).upper()
    if tier not in {MODEL_28_VALIDATED_TIER, MODEL_28_EXPLORATION_TIER}:
        return False
    required_occurrences = (
        int(config.operational_min_occurrences)
        if tier == MODEL_28_VALIDATED_TIER
        else 60
    )
    if int(getattr(item, "minimum_occurrences", 0) or 0) < required_occurrences:
        return False
    if not str(getattr(item, "source_cache_key", "")).startswith("100k-empirical:"):
        return False
    if str(getattr(item, "geometry_method", "")) != "PATTERN_DISCOVERY_EMPIRICAL_MAE_MFE":
        return False
    if str(getattr(item, "cost_rule", "")) != "RECORDED_ENTRY_SPREAD_ONLY":
        return False
    if float(getattr(item, "stop_atr", 0.0) or 0.0) <= 0.0:
        return False
    if float(getattr(item, "target_atr", 0.0) or 0.0) <= 0.0:
        return False
    if int(getattr(item, "max_holding_candles", 0) or 0) <= 0:
        return False
    if int(getattr(item, "repeat_limit", 0) or 0) < 1:
        return False
    if int(getattr(item, "repeat_window_candles", 0) or 0) < 1:
        return False
    for attribute in ("discovery_metrics", "validation_metrics", "oos_metrics"):
        metrics = dict(getattr(item, attribute, ()) or ())
        if "horizon_return_atr" not in metrics:
            return False
        if tier == MODEL_28_VALIDATED_TIER and float(
            metrics.get("performance", 0.0) or 0.0
        ) < float(config.operational_min_split_expectancy_r):
            return False
    discovery = dict(getattr(item, "discovery_metrics", ()) or ())
    if float(discovery.get("performance", 0.0) or 0.0) <= 0.0:
        return False
    return True


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
