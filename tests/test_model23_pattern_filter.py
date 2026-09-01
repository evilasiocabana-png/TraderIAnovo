"""Regressions for the causal M23 signal replay and execution filter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from application.model23_pattern_filter import (
    MODEL_23_PATTERN_FILTER_ALL_SOURCES,
    M23PatternFilterService,
    context_from_record,
)
from replay.pattern_miner.models import EventRecord, MarketEvent


SOURCE_M1 = "MODELO_1_ALPHA_ATUAL"
SOURCE_M2 = "MODELO_2_LAB_ALPHA_SUGERIDA_1_PLUS"


def _record(
    index: int,
    *,
    event: str = "BOS_DOWN",
    rsi14: float = 42.0,
) -> EventRecord:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=5 * index)
    return EventRecord(
        index=index,
        timestamp=timestamp,
        open=100.0,
        high=101.0,
        low=98.0,
        close=99.0,
        volume=100.0,
        spread=2.0,
        real_volume=0.0,
        ema9=100.0,
        ema20=101.0,
        ema50=102.0,
        ema200=103.0,
        rsi14=rsi14,
        atr14=2.0,
        adx14=28.0,
        plus_di14=12.0,
        minus_di14=25.0,
        volume_average=90.0,
        volume_relative=1.1,
        volume_zscore=0.5,
        volume_percentile=70.0,
        trend_state="bearish",
        structure_state="bearish",
        warmup_complete=True,
        session="London",
        events=(
            MarketEvent(
                event_type=event,
                index=index,
                origin_index=index,
                direction=-1 if event.endswith("DOWN") else 1,
            ),
        ),
    )


def _row(
    index: int,
    *,
    profit: float = -1.0,
    source_model: str = SOURCE_M1,
) -> dict[str, object]:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=5 * index)
    return {
        "timestamp": timestamp.isoformat(),
        "mt5_time": timestamp.isoformat(),
        "symbol": "EURUSD",
        "side": "SELL",
        "operation_status": "FECHADA/HISTORICO",
        "operational_model": "MODELO_23_BASKET_ACCUMULATOR_SOURCE_M1",
        "entry_setup": "M23 <- M1 | TEST_SETUP",
        "alpha_id": "ALPHA001",
        "mt5_realized_profit": profit,
        "mt5_commission": 0.0,
        "mt5_swap": 0.0,
        "mt5_fee": 0.0,
        "plan_snapshot": {
            "stop_management_parameters": {
                "source_operational_model": source_model,
                "m23_entry_type": "INITIAL",
            }
        },
    }


def test_replay_builds_block_rule_only_with_validation_and_oos(tmp_path) -> None:
    service = M23PatternFilterService(tmp_path / "report.json")
    records = tuple(_record(index) for index in range(30))
    report = service.analyze(
        [_row(index) for index in range(1, 26)],
        allowed_source_models=(SOURCE_M1,),
        records_by_symbol={"EURUSD": records},
    )

    assert report.contextualized_rows == 25
    assert report.block_rules >= 1
    assert report.rules[0].decision == "BLOCK"
    assert report.rules[0].validation_expectancy == -1.0
    assert report.rules[0].oos_expectancy == -1.0


def test_legacy_source_is_not_mixed_with_current_contract(tmp_path) -> None:
    service = M23PatternFilterService(tmp_path / "report.json")
    legacy = _row(1)
    legacy["plan_snapshot"] = {
        "stop_management_parameters": {
            "source_operational_model": "MODELO_19_APOSENTADO",
            "m23_entry_type": "INITIAL",
        }
    }
    report = service.analyze(
        [legacy],
        allowed_source_models=(SOURCE_M1,),
        records_by_symbol={"EURUSD": (_record(1),)},
    )

    assert report.contextualized_rows == 0
    assert report.ignored_legacy_rows == 1


def test_context_is_causal_and_does_not_read_future_event() -> None:
    records = (_record(0, event="BOS_DOWN"), _record(1, event="BOS_UP"))
    context = context_from_record(
        records[0],
        direction="SELL",
        history=records,
        index=0,
    )

    assert context.latest_event == "BOS_DOWN:WITH"
    assert "BOS_UP" not in context.signature


def test_persisted_rule_can_be_evaluated_without_reanalysis(tmp_path) -> None:
    path = tmp_path / "report.json"
    service = M23PatternFilterService(path)
    records = tuple(_record(index) for index in range(30))
    service.analyze(
        [_row(index) for index in range(1, 26)],
        allowed_source_models=(SOURCE_M1,),
        records_by_symbol={"EURUSD": records},
    )

    decision = M23PatternFilterService(path).evaluate(
        source_model=SOURCE_M1,
        symbol="EURUSD",
        entry_type="INITIAL",
        direction="SELL",
        record=records[-1],
        history=records,
    )

    assert decision.decision == "BLOCK"
    assert decision.samples == 25


def test_sparse_exact_context_falls_back_to_stable_pattern_family(tmp_path) -> None:
    service = M23PatternFilterService(tmp_path / "report.json")
    records = tuple(_record(index, event=("BOS_DOWN" if index % 2 else "FVG_DOWN")) for index in range(30))
    report = service.analyze(
        [_row(index) for index in range(1, 26)],
        allowed_source_models=(SOURCE_M1,),
        records_by_symbol={"EURUSD": records},
    )

    assert any(rule.pattern_scope == "TREND" and rule.decision == "BLOCK" for rule in report.rules)
    assert any(rule.pattern_scope == "EVENT" for rule in report.rules)


def test_filter_never_blocks_when_evidence_is_missing(tmp_path) -> None:
    decision = M23PatternFilterService(tmp_path / "missing.json").evaluate(
        source_model=SOURCE_M1,
        symbol="EURUSD",
        entry_type="INITIAL",
        direction="SELL",
        record=_record(1),
    )

    assert decision.decision == "NO_EVIDENCE"


def test_rules_and_splits_are_independent_for_each_source(tmp_path) -> None:
    path = tmp_path / "report.json"
    service = M23PatternFilterService(path)
    records = tuple(_record(index, rsi14=25.0) for index in range(30))
    rows = [
        _row(index, profit=-1.0, source_model=SOURCE_M1)
        for index in range(1, 26)
    ] + [
        _row(index, profit=1.0, source_model=SOURCE_M2)
        for index in range(1, 26)
    ]
    report = service.analyze(
        rows,
        allowed_source_models=(SOURCE_M1, SOURCE_M2),
        records_by_symbol={"EURUSD": records},
    )

    assert not any(
        rule.source_model == MODEL_23_PATTERN_FILTER_ALL_SOURCES
        for rule in report.rules
    )
    assert any(
        rule.source_model == SOURCE_M1
        and rule.pattern_scope == "RSI"
        and rule.pattern_value == "RSI_LT30"
        and rule.decision == "BLOCK"
        for rule in report.rules
    )
    assert any(
        rule.source_model == SOURCE_M2
        and rule.pattern_scope == "RSI"
        and rule.pattern_value == "RSI_LT30"
        and rule.decision == "APPROVE"
        for rule in report.rules
    )
    assert {
        sample.split
        for sample in report.samples
        if sample.source_model == SOURCE_M1
    } == {"DISCOVERY", "VALIDATION", "OOS"}
    blocked = M23PatternFilterService(path).evaluate(
        source_model=SOURCE_M1,
        symbol="EURUSD",
        entry_type="INITIAL",
        direction="SELL",
        record=records[-1],
        history=records,
    )

    approved = M23PatternFilterService(path).evaluate(
        source_model=SOURCE_M2,
        symbol="EURUSD",
        entry_type="INITIAL",
        direction="SELL",
        record=records[-1],
        history=records,
    )

    assert blocked.decision == "BLOCK"
    assert blocked.samples == 25
    assert approved.decision == "APPROVE"


def test_validated_source_block_has_precedence_over_approve(tmp_path) -> None:
    path = tmp_path / "report.json"
    service = M23PatternFilterService(path)
    records = tuple(_record(index, rsi14=42.0) for index in range(30))
    rows = [
        _row(index, profit=(-2.0 if index % 2 else 1.0))
        for index in range(1, 26)
    ]
    report = service.analyze(
        rows,
        allowed_source_models=(SOURCE_M1,),
        records_by_symbol={"EURUSD": records},
    )
    # Force two dimensions to disagree without changing their source identity.
    rules = list(report.rules)
    block = next(rule for rule in rules if rule.pattern_scope == "RSI")
    approve_index = next(
        index for index, rule in enumerate(rules) if rule.pattern_scope == "TREND"
    )
    from dataclasses import replace

    rules[approve_index] = replace(rules[approve_index], decision="APPROVE")
    service.save(replace(report, rules=tuple(rules)))

    decision = M23PatternFilterService(path).evaluate(
        source_model=SOURCE_M1,
        symbol="EURUSD",
        entry_type="INITIAL",
        direction="SELL",
        record=records[-1],
        history=records,
    )

    assert block.decision == "BLOCK"
    assert decision.decision == "BLOCK"
