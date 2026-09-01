"""Diagnose M28 forward performance without changing the live contract."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
from pathlib import Path
from typing import Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    ROOT
    / ".traderia"
    / "research"
    / "model28_forward_validation"
    / "comparison_report.json"
)
AUDIT_PATH = ROOT / ".traderia" / "runtime" / "mt5_trade_audit_report.json"
OUTPUT_PATH = (
    ROOT
    / ".traderia"
    / "research"
    / "model28_forward_validation"
    / "performance_diagnosis.json"
)


@dataclass(frozen=True, slots=True)
class ForwardTrade:
    ticket: str
    signal_time: str
    symbol: str
    direction: str
    pattern_id: str
    theory_r: float
    actual_r: float
    result_usd: float
    gross_usd: float
    costs_usd: float
    risk_usd: float
    cost_r: float
    adverse_slippage_r: float
    confidence: float
    validation_performance: float
    oos_performance: float
    technical_score: float
    target_r: float
    rsi: float | None
    trend: str
    session: str
    split: str = ""


@dataclass(frozen=True, slots=True)
class FilterResult:
    name: str
    parameters: dict[str, float]
    discovery: dict[str, float]
    validation: dict[str, float]
    oos: dict[str, float]
    selected_without_oos: bool


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _number(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _ticket_rows(audit: dict[str, object]) -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for source in list(audit.get("rows", []) or []):
        row = dict(source or {})
        ticket = str(row.get("mt5_ticket") or "")
        if ticket:
            output[ticket] = row
    return output


def _plan_parameters(row: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    plan = dict(row.get("plan_snapshot") or {})
    parameters = dict(plan.get("stop_management_parameters") or {})
    return plan, parameters


def _build_trades(
    report: dict[str, object],
    audit: dict[str, object],
) -> list[ForwardTrade]:
    theoretical = {
        str(row.get("ticket")): dict(row)
        for row in list(report.get("matched_theoretical_curve", []) or [])
    }
    realized = {
        str(row.get("ticket")): dict(row)
        for row in list(report.get("matched_realized_curve", []) or [])
    }
    comparisons = {
        str(row.get("ticket")): dict(row)
        for row in list(report.get("comparisons", []) or [])
        if str(row.get("comparison_status"))
        in {"CONFERE", "CONFERE_TOLERANCIA_ATR"}
    }
    audits = _ticket_rows(audit)
    output: list[ForwardTrade] = []
    for ticket in sorted(set(theoretical) & set(realized) & set(comparisons)):
        theory = theoretical[ticket]
        actual = realized[ticket]
        comparison = comparisons[ticket]
        audit_row = audits.get(ticket, {})
        plan, parameters = _plan_parameters(audit_row)
        entry = _number(comparison.get("theoretical_entry"))
        stop = _number(comparison.get("theoretical_stop"))
        target = _number(comparison.get("theoretical_target"))
        executed = _number(
            comparison.get("mt5_executed_price"),
            _number(comparison.get("mt5_entry_plan"), entry),
        )
        price_risk = abs(entry - stop)
        sign = 1.0 if str(comparison.get("direction")).upper() == "BUY" else -1.0
        risk_usd = abs(_number(actual.get("risk_usd")))
        costs_usd = _number(actual.get("costs_usd"))
        output.append(
            ForwardTrade(
                ticket=ticket,
                signal_time=str(theory.get("signal_time") or comparison.get("candle_time") or ""),
                symbol=str(theory.get("symbol") or comparison.get("symbol") or "N/D"),
                direction=str(theory.get("direction") or comparison.get("direction") or "N/D"),
                pattern_id=str(theory.get("pattern_id") or comparison.get("pattern_id") or "N/D"),
                theory_r=_number(theory.get("result_r")),
                actual_r=_number(actual.get("result_r")),
                result_usd=_number(actual.get("result_usd")),
                gross_usd=_number(actual.get("gross_usd")),
                costs_usd=costs_usd,
                risk_usd=risk_usd,
                cost_r=(-costs_usd / risk_usd if risk_usd > 0.0 else float("inf")),
                adverse_slippage_r=(sign * (executed - entry) / price_risk if price_risk > 0.0 else 0.0),
                confidence=_number(parameters.get("pattern_confidence")),
                validation_performance=_number(parameters.get("validation_performance")),
                oos_performance=_number(parameters.get("oos_performance")),
                technical_score=_number(plan.get("technical_score")),
                target_r=(abs(target - entry) / price_risk if price_risk > 0.0 else 0.0),
                rsi=(None if plan.get("rsi") is None else _number(plan.get("rsi"))),
                trend=str(plan.get("trend") or "N/D"),
                session=str(plan.get("forex_session") or "N/D"),
            )
        )
    return _assign_splits(output)


def _assign_splits(trades: list[ForwardTrade]) -> list[ForwardTrade]:
    ordered = sorted(trades, key=lambda item: (item.signal_time, item.ticket))
    discovery_end = int(len(ordered) * 0.60)
    validation_end = int(len(ordered) * 0.80)
    return [
        ForwardTrade(
            **{
                **asdict(item),
                "split": (
                    "DISCOVERY"
                    if index < discovery_end
                    else "VALIDATION"
                    if index < validation_end
                    else "OOS"
                ),
            }
        )
        for index, item in enumerate(ordered)
    ]


def _metrics(rows: Iterable[ForwardTrade]) -> dict[str, float]:
    items = list(rows)
    if not items:
        return {"trades": 0, "win_rate": 0.0, "net_r": 0.0, "expectancy_r": 0.0, "net_usd": 0.0}
    return {
        "trades": len(items),
        "win_rate": sum(item.actual_r > 0.0 for item in items) / len(items),
        "net_r": sum(item.actual_r for item in items),
        "expectancy_r": sum(item.actual_r for item in items) / len(items),
        "net_usd": sum(item.result_usd for item in items),
    }


def _filter_result(
    name: str,
    parameters: dict[str, float],
    trades: list[ForwardTrade],
    predicate: Callable[[ForwardTrade], bool],
) -> FilterResult:
    by_split = {
        split: _metrics(item for item in trades if item.split == split and predicate(item))
        for split in ("DISCOVERY", "VALIDATION", "OOS")
    }
    discovery = by_split["DISCOVERY"]
    validation = by_split["VALIDATION"]
    selected = (
        discovery["trades"] >= 15
        and validation["trades"] >= 5
        and discovery["expectancy_r"] > 0.0
        and validation["expectancy_r"] > 0.0
    )
    return FilterResult(
        name=name,
        parameters=parameters,
        discovery=discovery,
        validation=validation,
        oos=by_split["OOS"],
        selected_without_oos=selected,
    )


def _candidate_filters(trades: list[ForwardTrade]) -> list[FilterResult]:
    candidates: list[FilterResult] = [
        _filter_result("BASELINE", {}, trades, lambda _: True)
    ]
    evidence_levels = (0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.80)
    cost_levels = (0.15, 0.20, 0.25, 0.30, 0.40, 0.50)
    drift_levels = (0.05, 0.10, 0.15, 0.20, 0.25)
    confidence_levels = (0.10, 0.20, 0.30, 0.40)
    for level in evidence_levels:
        candidates.append(
            _filter_result(
                "MIN_VALIDATION_OOS",
                {"minimum": level},
                trades,
                lambda item, value=level: min(
                    item.validation_performance,
                    item.oos_performance,
                )
                >= value,
            )
        )
    for level in confidence_levels:
        candidates.append(
            _filter_result(
                "MIN_CONFIDENCE",
                {"minimum": level},
                trades,
                lambda item, value=level: item.confidence >= value,
            )
        )
    for level in cost_levels:
        candidates.append(
            _filter_result(
                "MAX_COST_R",
                {"maximum": level},
                trades,
                lambda item, value=level: item.cost_r <= value,
            )
        )
    for level in drift_levels:
        candidates.append(
            _filter_result(
                "MAX_ADVERSE_DRIFT_R",
                {"maximum": level},
                trades,
                lambda item, value=level: item.adverse_slippage_r <= value,
            )
        )
    for evidence in evidence_levels:
        for cost in cost_levels:
            for drift in drift_levels:
                candidates.append(
                    _filter_result(
                        "QUALITY_COST_DRIFT",
                        {
                            "minimum_validation_oos": evidence,
                            "maximum_cost_r": cost,
                            "maximum_adverse_drift_r": drift,
                        },
                        trades,
                        lambda item, a=evidence, b=cost, c=drift: (
                            min(item.validation_performance, item.oos_performance) >= a
                            and item.cost_r <= b
                            and item.adverse_slippage_r <= c
                        ),
                    )
                )
    return candidates


def _group_summary(
    trades: list[ForwardTrade],
    key: Callable[[ForwardTrade], str],
) -> list[dict[str, object]]:
    grouped: dict[str, list[ForwardTrade]] = defaultdict(list)
    for item in trades:
        grouped[key(item)].append(item)
    return [
        {"group": group, **_metrics(items)}
        for group, items in sorted(
            grouped.items(),
            key=lambda pair: _metrics(pair[1])["net_r"],
        )
    ]


def main() -> int:
    report = _read_json(REPORT_PATH)
    audit = _read_json(AUDIT_PATH)
    trades = _build_trades(report, audit)
    filters = _candidate_filters(trades)
    selected = sorted(
        (item for item in filters if item.selected_without_oos),
        key=lambda item: (
            min(item.discovery["expectancy_r"], item.validation["expectancy_r"]),
            item.discovery["trades"] + item.validation["trades"],
        ),
        reverse=True,
    )
    payload = {
        "schema_version": "m28-forward-performance-diagnosis-v1",
        "generated_from": str(report.get("generated_at") or "N/D"),
        "trades": len(trades),
        "baseline": {
            split: _metrics(item for item in trades if item.split == split)
            for split in ("DISCOVERY", "VALIDATION", "OOS")
        },
        "overall": _metrics(trades),
        "by_symbol": _group_summary(trades, lambda item: item.symbol),
        "by_pattern": _group_summary(
            trades,
            lambda item: f"{item.symbol}|{item.pattern_id}",
        ),
        "selected_filters_without_oos": [asdict(item) for item in selected],
        "all_filters": [asdict(item) for item in filters],
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True),
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "generated_from": payload["generated_from"],
                "trades": payload["trades"],
                "baseline": payload["baseline"],
                "overall": payload["overall"],
                "selected_filters_without_oos": payload[
                    "selected_filters_without_oos"
                ][:10],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
