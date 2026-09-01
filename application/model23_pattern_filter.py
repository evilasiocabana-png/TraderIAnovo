"""Offline replay and lightweight execution filter for Model 23 signals.

The heavy analysis joins closed M23 trades to the last causal M5 EventRecord
available before entry. Runtime evaluation only reads the persisted rule file.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import pickle
from typing import Any, Iterable, Mapping, Sequence

from application.model23_basket_accumulator import model23_entry_type
from replay.pattern_miner.models import EventRecord


MODEL_23_PATTERN_FILTER_SCHEMA = "m23-pattern-filter-v5"
MODEL_23_PATTERN_FILTER_MODE = "INDIVIDUAL_BLOCK_ONLY"
# Kept only so old report readers/tests can identify the retired portfolio scope.
MODEL_23_PATTERN_FILTER_ALL_SOURCES = "ALL_SOURCES"
MODEL_23_PATTERN_FILTER_PATH = (
    Path(".traderia") / "research" / "m23_pattern_filter" / "report.json"
)
MODEL_23_PATTERN_FILTER_MIN_SAMPLES = 20
_MAJOR_EVENT_PREFIXES = (
    "BOS_",
    "CHOCH_",
    "SWEEP_",
    "FVG_",
    "DISPLACEMENT_",
    "ORDER_BLOCK_",
)


@dataclass(frozen=True, slots=True)
class M23PatternContext:
    """Causal context frozen at or before one signal timestamp."""

    trend_alignment: str
    structure_alignment: str
    rsi_zone: str
    adx_zone: str
    atr_regime: str
    session: str
    latest_event: str

    @property
    def signature(self) -> str:
        return "|".join(
            (
                self.trend_alignment,
                self.structure_alignment,
                self.rsi_zone,
                self.adx_zone,
                self.atr_regime,
                self.session,
                self.latest_event,
            )
        )


@dataclass(frozen=True, slots=True)
class M23PatternSample:
    source_model: str
    symbol: str
    entry_type: str
    entry_setup: str
    direction: str
    timestamp: str
    net_result: float
    split: str
    pattern_id: str
    context: M23PatternContext


@dataclass(frozen=True, slots=True)
class M23PatternRule:
    rule_id: str
    source_model: str
    symbol: str
    entry_type: str
    direction: str
    pattern_scope: str
    pattern_value: str
    pattern_id: str
    signature: str
    decision: str
    samples: int
    wins: int
    win_rate: float
    net_result: float
    expectancy: float
    discovery_expectancy: float
    validation_expectancy: float
    oos_expectancy: float


@dataclass(frozen=True, slots=True)
class M23PatternFilterDecision:
    decision: str = "NO_EVIDENCE"
    rule_id: str = "N/D"
    pattern_id: str = "N/D"
    reason: str = "Filtro M23 ainda sem evidencia aplicavel."
    samples: int = 0
    validation_expectancy: float = 0.0
    oos_expectancy: float = 0.0


@dataclass(frozen=True, slots=True)
class M23PatternFilterReport:
    generated_at: str
    source_rows: int
    eligible_rows: int
    contextualized_rows: int
    ignored_legacy_rows: int
    rules: tuple[M23PatternRule, ...]
    samples: tuple[M23PatternSample, ...]
    schema_version: str = MODEL_23_PATTERN_FILTER_SCHEMA
    mode: str = MODEL_23_PATTERN_FILTER_MODE

    @property
    def approve_rules(self) -> int:
        return sum(rule.decision == "APPROVE" for rule in self.rules)

    @property
    def block_rules(self) -> int:
        return sum(rule.decision == "BLOCK" for rule in self.rules)


class M23PatternFilterService:
    """Build and query an out-of-sample-aware filter for M23 source signals."""

    def __init__(self, report_path: str | Path = MODEL_23_PATTERN_FILTER_PATH) -> None:
        self.report_path = Path(report_path)
        self._cached_report: M23PatternFilterReport | None = None
        self._cached_mtime_ns = -1

    def analyze(
        self,
        audit_rows: Sequence[object],
        *,
        allowed_source_models: Iterable[str],
        records_by_symbol: Mapping[str, Sequence[EventRecord]] | None = None,
    ) -> M23PatternFilterReport:
        """Join closed trades to causal records and persist execution rules."""

        allowed = {str(item or "").upper() for item in allowed_source_models}
        candidates: list[tuple[object, str, datetime]] = []
        ignored_legacy = 0
        for row in audit_rows:
            if not _is_closed_m23_row(row):
                continue
            source = _source_model(row)
            if source not in allowed:
                ignored_legacy += 1
                continue
            timestamp = _row_timestamp(row)
            if timestamp is None:
                continue
            candidates.append((row, source, timestamp))
        candidates.sort(key=lambda item: item[2])

        samples: list[M23PatternSample] = []
        grouped_symbols = sorted({_text(_value(row, "symbol")).upper() for row, _, _ in candidates})
        supplied = records_by_symbol or {}
        for symbol in grouped_symbols:
            records = tuple(supplied.get(symbol) or self.load_event_records(symbol))
            if not records:
                continue
            timestamps = [_utc(record.timestamp).timestamp() for record in records]
            symbol_candidates = [item for item in candidates if _text(_value(item[0], "symbol")).upper() == symbol]
            for row, source, timestamp in symbol_candidates:
                record_index = bisect_right(timestamps, _utc(timestamp).timestamp()) - 1
                if record_index < 0:
                    continue
                record = records[record_index]
                direction = _direction(_value(row, "side"))
                context = context_from_record(record, direction=direction, history=records, index=record_index)
                parameters = _stop_parameters(row)
                entry_setup = _text(_value(row, "entry_setup"))
                entry_type = model23_entry_type(
                    parameters,
                    entry_setup=entry_setup,
                    alpha_id=_value(row, "alpha_id"),
                ) or "N/D"
                samples.append(
                    M23PatternSample(
                        source_model=source,
                        symbol=symbol,
                        entry_type=entry_type,
                        entry_setup=entry_setup,
                        direction=direction,
                        timestamp=_utc(timestamp).isoformat(),
                        net_result=_net_result(row),
                        split="",
                        pattern_id=_pattern_id(context.signature),
                        context=context,
                    )
                )

        samples = _assign_chronological_splits(samples)
        rules = _build_rules(samples)
        report = M23PatternFilterReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            source_rows=len(audit_rows),
            eligible_rows=len(candidates),
            contextualized_rows=len(samples),
            ignored_legacy_rows=ignored_legacy,
            rules=tuple(rules),
            samples=tuple(samples),
        )
        self.save(report)
        return report

    def evaluate(
        self,
        *,
        source_model: str,
        symbol: str,
        entry_type: str,
        direction: str,
        record: EventRecord | None,
        history: Sequence[EventRecord] = (),
    ) -> M23PatternFilterDecision:
        """Evaluate one live signal using the persisted out-of-sample rules."""

        if record is None:
            return M23PatternFilterDecision(
                reason="Filtro M23 sem candle M5 causal; entrada preservada."
            )
        report = self.load()
        if report is None:
            return M23PatternFilterDecision(
                reason="Filtro M23 ainda nao foi calculado; entrada preservada."
            )
        context = context_from_record(
            record,
            direction=_direction(direction),
            history=history,
            index=(len(history) - 1 if history else None),
        )
        pattern_id = _pattern_id(context.signature)
        normalized_source = str(source_model or "").upper()
        matching = [
            rule
            for rule in report.rules
            if rule.source_model == normalized_source
            and rule.direction == _direction(direction)
            and rule.decision in {"APPROVE", "BLOCK"}
            and _context_rule_value(context, rule.pattern_scope) == rule.pattern_value
        ]
        if not matching:
            return M23PatternFilterDecision(
                pattern_id=pattern_id,
                reason="Contexto atual nao possui amostra OOS suficiente; nenhuma trava aplicada."
            )
        # In block-only mode, a validated source-specific block cannot be
        # neutralized by an informational APPROVE rule from another dimension.
        blocking = [rule for rule in matching if rule.decision == "BLOCK"]
        rule = max(blocking or matching, key=_rule_strength)
        return M23PatternFilterDecision(
            decision=rule.decision,
            rule_id=rule.rule_id,
            pattern_id=rule.pattern_id,
            reason=(
                f"Filtro individual M23 {rule.decision} para {normalized_source}: "
                f"n={rule.samples}, validacao={rule.validation_expectancy:.2f}, "
                f"OOS={rule.oos_expectancy:.2f}."
            ),
            samples=rule.samples,
            validation_expectancy=rule.validation_expectancy,
            oos_expectancy=rule.oos_expectancy,
        )

    @staticmethod
    def classify_sample(
        sample: M23PatternSample,
        report: M23PatternFilterReport,
    ) -> str:
        """Classify a historical sample with the same precedence used live."""

        matching = [
            rule
            for rule in report.rules
            if rule.source_model == sample.source_model
            and rule.direction == sample.direction
            and rule.decision in {"APPROVE", "BLOCK"}
            and _context_rule_value(sample.context, rule.pattern_scope)
            == rule.pattern_value
        ]
        if any(rule.decision == "BLOCK" for rule in matching):
            return "BLOCK"
        if any(rule.decision == "APPROVE" for rule in matching):
            return "APPROVE"
        return "NO_EVIDENCE"

    def save(self, report: M23PatternFilterReport) -> None:
        payload = {
            **{key: value for key, value in asdict(report).items() if key not in {"rules", "samples"}},
            "rules": [asdict(item) for item in report.rules],
            "samples": [asdict(item) for item in report.samples],
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.report_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
        temporary.replace(self.report_path)
        self._cached_report = report
        self._cached_mtime_ns = self.report_path.stat().st_mtime_ns

    def load(self) -> M23PatternFilterReport | None:
        try:
            mtime_ns = self.report_path.stat().st_mtime_ns
        except OSError:
            return None
        if self._cached_report is not None and mtime_ns == self._cached_mtime_ns:
            return self._cached_report
        try:
            payload = json.loads(self.report_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return None
        if payload.get("schema_version") != MODEL_23_PATTERN_FILTER_SCHEMA:
            return None
        report = M23PatternFilterReport(
            schema_version=str(payload["schema_version"]),
            mode=str(payload.get("mode") or MODEL_23_PATTERN_FILTER_MODE),
            generated_at=str(payload.get("generated_at") or "N/D"),
            source_rows=int(payload.get("source_rows") or 0),
            eligible_rows=int(payload.get("eligible_rows") or 0),
            contextualized_rows=int(payload.get("contextualized_rows") or 0),
            ignored_legacy_rows=int(payload.get("ignored_legacy_rows") or 0),
            rules=tuple(M23PatternRule(**item) for item in payload.get("rules", [])),
            samples=tuple(
                M23PatternSample(
                    **{key: value for key, value in item.items() if key != "context"},
                    context=M23PatternContext(**item["context"]),
                )
                for item in payload.get("samples", [])
            ),
        )
        self._cached_report = report
        self._cached_mtime_ns = mtime_ns
        return report

    @staticmethod
    def load_event_records(symbol: str) -> tuple[EventRecord, ...]:
        summary_path = _pattern_summary_path(symbol)
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            cache_key = str(summary["cache_key"])
            cache_path = summary_path.parent / f"pattern_miner_event_store_{cache_key}.pkl.gz"
            with gzip.open(cache_path, "rb") as source:
                payload = pickle.load(source)
            return tuple(payload.get("records") or ())
        except (OSError, ValueError, TypeError, KeyError, EOFError, pickle.PickleError):
            return ()


def context_from_record(
    record: EventRecord,
    *,
    direction: str,
    history: Sequence[EventRecord] = (),
    index: int | None = None,
) -> M23PatternContext:
    sign = 1 if direction == "BUY" else -1
    trend = _alignment(record.trend_state, sign)
    structure = _alignment(record.structure_state, sign)
    rsi = float(record.rsi14) if record.rsi14 is not None else None
    adx = float(record.adx14) if record.adx14 is not None else None
    latest_event = "NO_MAJOR_EVENT"
    records = history or (record,)
    resolved_index = len(records) - 1 if index is None else index
    for candidate in reversed(records[max(0, resolved_index - 11) : resolved_index + 1]):
        for event in reversed(candidate.events):
            if event.event_type.startswith(_MAJOR_EVENT_PREFIXES):
                alignment = "WITH" if int(event.direction or 0) == sign else "AGAINST" if event.direction else "NEUTRAL"
                latest_event = f"{event.event_type}:{alignment}"
                break
        if latest_event != "NO_MAJOR_EVENT":
            break
    atr_relative = None
    if record.atr14 is not None and records:
        recent_atr = [
            float(item.atr14)
            for item in records[max(0, resolved_index - 19) : resolved_index + 1]
            if item.atr14 is not None
        ]
        if recent_atr:
            average = sum(recent_atr) / len(recent_atr)
            atr_relative = float(record.atr14) / average if average > 0.0 else None
    return M23PatternContext(
        trend_alignment=trend,
        structure_alignment=structure,
        rsi_zone=_bucket(rsi, (30.0, 50.0, 70.0), ("RSI_LT30", "RSI_30_50", "RSI_50_70", "RSI_GE70")),
        adx_zone=_bucket(adx, (20.0, 25.0), ("ADX_LT20", "ADX_20_25", "ADX_GE25")),
        atr_regime=(
            "ATR_UNKNOWN"
            if atr_relative is None
            else "ATR_COMPRESSION"
            if atr_relative <= 0.8
            else "ATR_EXPANSION"
            if atr_relative >= 1.2
            else "ATR_NORMAL"
        ),
        session=str(record.session or "N/D").upper(),
        latest_event=latest_event,
    )


def _build_rules(samples: Sequence[M23PatternSample]) -> list[M23PatternRule]:
    groups: dict[tuple[str, str, str, str], list[M23PatternSample]] = defaultdict(list)
    for sample in samples:
        for scope, value in _sample_rule_dimensions(sample):
            groups[(sample.source_model, sample.direction, scope, value)].append(sample)
    rules: list[M23PatternRule] = []
    for (source, direction, scope, value), items in groups.items():
        discovery = [item.net_result for item in items if item.split == "DISCOVERY"]
        validation = [item.net_result for item in items if item.split == "VALIDATION"]
        oos = [item.net_result for item in items if item.split == "OOS"]
        decision = "NO_EVIDENCE"
        if (
            len(items) >= MODEL_23_PATTERN_FILTER_MIN_SAMPLES
            and len(discovery) >= 3
            and len(validation) >= 3
            and len(oos) >= 3
        ):
            discovery_expectancy = _mean(discovery)
            validation_expectancy = _mean(validation)
            oos_expectancy = _mean(oos)
            win_rate = sum(item.net_result > 0.0 for item in items) / len(items)
            if (
                discovery_expectancy < 0.0
                and validation_expectancy < 0.0
                and oos_expectancy < 0.0
                and win_rate < 0.5
            ):
                decision = "BLOCK"
            elif (
                discovery_expectancy > 0.0
                and validation_expectancy > 0.0
                and oos_expectancy > 0.0
                and win_rate > 0.5
            ):
                decision = "APPROVE"
        pattern_id = _pattern_id(f"{scope}|{value}")
        rule_key = f"{source}|{direction}|{scope}|{value}"
        rules.append(
            M23PatternRule(
                rule_id="M23F-" + hashlib.sha1(rule_key.encode("utf-8")).hexdigest()[:12].upper(),
                source_model=source,
                symbol="TODOS",
                entry_type="TODOS",
                direction=direction,
                pattern_scope=scope,
                pattern_value=value,
                pattern_id=pattern_id,
                signature=f"{scope}={value}",
                decision=decision,
                samples=len(items),
                wins=sum(item.net_result > 0.0 for item in items),
                win_rate=sum(item.net_result > 0.0 for item in items) / len(items),
                net_result=sum(item.net_result for item in items),
                expectancy=_mean([item.net_result for item in items]),
                discovery_expectancy=_mean(discovery),
                validation_expectancy=_mean(validation),
                oos_expectancy=_mean(oos),
            )
        )
    return sorted(rules, key=lambda item: (item.decision != "BLOCK", -item.samples, item.rule_id))


def _sample_rule_dimensions(sample: M23PatternSample) -> tuple[tuple[str, str], ...]:
    context = sample.context
    return (
        ("BASE", "ALL"),
        ("TREND", context.trend_alignment),
        ("STRUCTURE", context.structure_alignment),
        ("RSI", context.rsi_zone),
        ("ADX", context.adx_zone),
        ("ATR", context.atr_regime),
        ("SESSION", context.session),
        ("EVENT", _event_family(context.latest_event)),
        (
            "TREND_STRUCTURE",
            f"{context.trend_alignment}|{context.structure_alignment}",
        ),
        ("RSI_TREND", f"{context.rsi_zone}|{context.trend_alignment}"),
        ("RSI_STRUCTURE", f"{context.rsi_zone}|{context.structure_alignment}"),
        ("RSI_ADX", f"{context.rsi_zone}|{context.adx_zone}"),
        ("RSI_ATR", f"{context.rsi_zone}|{context.atr_regime}"),
        ("RSI_SESSION", f"{context.rsi_zone}|{context.session}"),
        ("RSI_EVENT", f"{context.rsi_zone}|{_event_family(context.latest_event)}"),
    )


def _context_rule_value(context: M23PatternContext, scope: str) -> str:
    values = {
        "BASE": "ALL",
        "TREND": context.trend_alignment,
        "STRUCTURE": context.structure_alignment,
        "RSI": context.rsi_zone,
        "ADX": context.adx_zone,
        "ATR": context.atr_regime,
        "SESSION": context.session,
        "EVENT": _event_family(context.latest_event),
        "TREND_STRUCTURE": (
            f"{context.trend_alignment}|{context.structure_alignment}"
        ),
        "RSI_TREND": f"{context.rsi_zone}|{context.trend_alignment}",
        "RSI_STRUCTURE": f"{context.rsi_zone}|{context.structure_alignment}",
        "RSI_ADX": f"{context.rsi_zone}|{context.adx_zone}",
        "RSI_ATR": f"{context.rsi_zone}|{context.atr_regime}",
        "RSI_SESSION": f"{context.rsi_zone}|{context.session}",
        "RSI_EVENT": f"{context.rsi_zone}|{_event_family(context.latest_event)}",
    }
    return values.get(str(scope or "").upper(), "N/D")


def _event_family(latest_event: str) -> str:
    normalized = str(latest_event or "NO_MAJOR_EVENT").upper()
    if normalized == "NO_MAJOR_EVENT":
        return "NO_MAJOR_EVENT"
    return normalized.split("_", 1)[0]


def _rule_strength(rule: M23PatternRule) -> tuple[float, int, int]:
    evidence = min(abs(rule.validation_expectancy), abs(rule.oos_expectancy))
    specificity = int(rule.pattern_scope == "TREND_STRUCTURE")
    return (evidence, specificity, rule.samples)


def _assign_chronological_splits(samples: Sequence[M23PatternSample]) -> list[M23PatternSample]:
    grouped: dict[tuple[str, str], list[M23PatternSample]] = defaultdict(list)
    for sample in samples:
        grouped[(sample.source_model, sample.direction)].append(sample)
    assigned: list[M23PatternSample] = []
    for group in grouped.values():
        ordered = sorted(group, key=lambda item: item.timestamp)
        total = len(ordered)
        discovery_end = int(total * 0.60)
        validation_end = int(total * 0.80)
        for index, sample in enumerate(ordered):
            split = (
                "DISCOVERY"
                if index < discovery_end
                else "VALIDATION"
                if index < validation_end
                else "OOS"
            )
            assigned.append(
                M23PatternSample(
                    **{
                        **asdict(sample),
                        "context": sample.context,
                        "split": split,
                    }
                )
            )
    return sorted(assigned, key=lambda item: item.timestamp)


def _is_closed_m23_row(row: object) -> bool:
    model = _text(_value(row, "operational_model")).upper()
    status = _text(_value(row, "operation_status")).upper()
    result = _net_result(row)
    return model.startswith("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M") and "FECHADA" in status and abs(result) > 1e-9


def _source_model(row: object) -> str:
    parameters = _stop_parameters(row)
    return _text(parameters.get("source_operational_model")).upper()


def _stop_parameters(row: object) -> dict[str, Any]:
    snapshot = _value(row, "plan_snapshot", default={}) or {}
    if not isinstance(snapshot, Mapping):
        return {}
    parameters = snapshot.get("stop_management_parameters") or {}
    return dict(parameters) if isinstance(parameters, Mapping) else {}


def _net_result(row: object) -> float:
    return sum(
        _number(_value(row, name, default=0.0))
        for name in ("mt5_realized_profit", "mt5_commission", "mt5_swap", "mt5_fee")
    )


def _row_timestamp(row: object) -> datetime | None:
    for name in ("timestamp", "mt5_time"):
        parsed = _parse_timestamp(_value(row, name))
        if parsed is not None:
            return parsed
    return None


def _parse_timestamp(value: object) -> datetime | None:
    normalized = _text(value).strip()
    if not normalized or normalized.upper() in {"N/D", "NONE"}:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        parsed = None
        for pattern in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
            try:
                parsed = datetime.strptime(normalized, pattern)
                break
            except ValueError:
                continue
        if parsed is None:
            return None
    return _utc(parsed)


def _pattern_summary_path(symbol: str) -> Path:
    normalized = str(symbol or "").upper()
    if normalized == "XAUUSD":
        return Path(".traderia") / "research" / "historicoXAU" / "pattern_miner_summary.json"
    return (
        Path(".traderia")
        / "research"
        / "historicosMercado"
        / f"historico{normalized}"
        / "pattern_miner_summary.json"
    )


def _alignment(state: object, sign: int) -> str:
    normalized = str(state or "").lower()
    bullish = any(token in normalized for token in ("bull", "alta", "up"))
    bearish = any(token in normalized for token in ("bear", "baixa", "down"))
    if not bullish and not bearish:
        return "NEUTRAL"
    aligned = bullish if sign > 0 else bearish
    return "ALIGNED" if aligned else "COUNTER"


def _bucket(value: float | None, limits: Sequence[float], labels: Sequence[str]) -> str:
    if value is None:
        return "UNKNOWN"
    for index, limit in enumerate(limits):
        if value < limit:
            return labels[index]
    return labels[-1]


def _pattern_id(signature: str) -> str:
    return "CTX-" + hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12].upper()


def _direction(value: object) -> str:
    normalized = _text(value).upper()
    return "BUY" if normalized in {"BUY", "COMPRAR"} else "SELL"


def _value(row: object, name: str, *, default: Any = None) -> Any:
    if isinstance(row, Mapping):
        return row.get(name, default)
    return getattr(row, name, default)


def _text(value: object) -> str:
    return str(value or "")


def _number(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _utc(value: datetime) -> datetime:
    return value.astimezone(timezone.utc) if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
