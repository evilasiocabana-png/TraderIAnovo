"""Causal M23 context contract regressions; temporary reports only."""

from dataclasses import asdict, replace
from datetime import timedelta
import hashlib
import json

from application.model23_pattern_filter import (
    M23PatternFilterService, context_from_record, _pattern_id,
)
from test_model23_pattern_filter import _record, _row, SOURCE_M1


def _service(tmp_path):
    service = M23PatternFilterService(tmp_path / 'report.json')
    records = tuple(_record(i) for i in range(30))
    service.analyze([_row(i) for i in range(1, 26)],
                    allowed_source_models=(SOURCE_M1,),
                    records_by_symbol={'EURUSD': records})
    return service, records


def _evaluate(service, record, history=(), **kwargs):
    return service.evaluate(source_model=SOURCE_M1, symbol='EURUSD',
                            entry_type='INITIAL', direction='SELL',
                            record=record, history=history, **kwargs)


def test_missing_context_preserves_allow_policy_and_report_metadata(tmp_path):
    service, _ = _service(tmp_path)
    decision = _evaluate(service, None)
    assert decision.decision == 'NO_EVIDENCE'
    assert decision.context_status == 'MISSING'
    assert decision.context_pattern_id == 'N/D'
    assert decision.report_generated_at == service.load().generated_at


def test_wrong_signal_candle_cannot_match_existing_block(tmp_path):
    service, records = _service(tmp_path)
    decision = _evaluate(service, records[-1], records,
                         expected_record_time=records[-1].timestamp + timedelta(minutes=5))
    assert decision.decision == 'NO_EVIDENCE'
    assert decision.context_status == 'MISMATCH'
    assert decision.context_snapshot
    assert decision.rule_id == 'N/D'


def test_candle_must_be_fully_closed_at_decision(tmp_path):
    service, records = _service(tmp_path)
    record = records[-1]
    decision = _evaluate(service, record, records,
                         expected_record_time=record.timestamp,
                         decision_time=record.timestamp + timedelta(minutes=4, seconds=59))
    assert decision.decision == 'NO_EVIDENCE'
    assert decision.context_status == 'NOT_CLOSED'


def test_old_context_cannot_match_even_without_expected_timestamp(tmp_path):
    service, records = _service(tmp_path)
    decision = _evaluate(service, records[-1], records,
                         decision_time=records[-1].timestamp + timedelta(minutes=10, seconds=1))
    assert decision.decision == 'NO_EVIDENCE'
    assert decision.context_status == 'STALE'


def test_incomplete_warmup_cannot_match_existing_block(tmp_path):
    service, records = _service(tmp_path)
    record = replace(records[-1], warmup_complete=False)
    decision = _evaluate(service, record, records,
                         expected_record_time=record.timestamp)
    assert decision.decision == 'NO_EVIDENCE'
    assert decision.context_status == 'WARMUP_INCOMPLETE'


def test_valid_closed_signal_uses_same_frozen_rules(tmp_path):
    service, records = _service(tmp_path)
    record = records[-1]
    before = hashlib.sha256(service.report_path.read_bytes()).hexdigest()
    decision = _evaluate(service, record, records,
                         expected_record_time=record.timestamp,
                         decision_time=record.timestamp + timedelta(minutes=5))
    assert decision.decision == 'BLOCK'
    assert decision.context_status == 'VALID'
    assert decision.context_timestamp == record.timestamp.isoformat()
    assert decision.samples == 25
    assert hashlib.sha256(service.report_path.read_bytes()).hexdigest() == before


def test_rule_identifier_and_context_identifier_are_separate(tmp_path):
    service, records = _service(tmp_path)
    record = records[-1]
    context = context_from_record(record, direction='SELL', history=records)
    for status in ('APPROVE', 'BLOCK'):
        report = service.load()
        service.save(replace(report, rules=tuple(replace(rule, decision=status)
                                                for rule in report.rules)))
        decision = _evaluate(service, record, records,
                             expected_record_time=record.timestamp)
        chosen = next(rule for rule in service.load().rules if rule.rule_id == decision.rule_id)
        assert decision.decision == status
        assert decision.pattern_id == chosen.pattern_id
        assert decision.context_pattern_id == _pattern_id(context.signature)
        assert decision.context_snapshot == asdict(context)
        assert decision.report_generated_at == report.generated_at


def test_no_evidence_keeps_full_context_metadata(tmp_path):
    service, records = _service(tmp_path)
    report = service.load()
    service.save(replace(report, rules=()))
    decision = _evaluate(service, records[-1], records,
                         expected_record_time=records[-1].timestamp)
    assert decision.decision == 'NO_EVIDENCE'
    assert decision.context_status == 'VALID'
    assert decision.context_pattern_id == decision.pattern_id
    assert len(decision.context_snapshot) == 7


def test_future_history_cannot_change_signal_context(tmp_path):
    service, records = _service(tmp_path)
    record = records[-2]
    future = replace(records[-1], events=_record(30, event='BOS_UP').events, atr14=100)
    with_future = _evaluate(service, record, records[:-1] + (future,),
                            expected_record_time=record.timestamp)
    without_future = _evaluate(service, record, records[:-1],
                               expected_record_time=record.timestamp)
    assert with_future == without_future
    assert with_future.context_snapshot['latest_event'] == 'BOS_DOWN:WITH'


def test_training_uses_previous_closed_bar_inside_current_m5(tmp_path):
    service = M23PatternFilterService(tmp_path / 'report.json')
    previous = _record(0, rsi14=25)
    current = _record(1, rsi14=75)
    entry = current.timestamp + timedelta(minutes=2)
    row = _row(0)
    row.update(timestamp=entry.isoformat(), mt5_time=entry.isoformat())
    report = service.analyze([row], allowed_source_models=(SOURCE_M1,),
                             records_by_symbol={'EURUSD': (previous, current)})
    assert report.contextualized_rows == 1
    assert report.samples[0].context.rsi_zone == 'RSI_LT30'
    assert report.ignored_context_rows == 0


def test_training_skips_stale_and_unwarmed_contexts(tmp_path):
    service = M23PatternFilterService(tmp_path / 'report.json')
    record = replace(_record(0), warmup_complete=False)
    rows = [_row(0), _row(100)]
    report = service.analyze(rows, allowed_source_models=(SOURCE_M1,),
                             records_by_symbol={'EURUSD': (record,)})
    assert report.contextualized_rows == 0
    assert report.ignored_context_rows == 2
    assert service.load().ignored_context_rows == 2


def test_legacy_report_loads_without_rewriting_or_new_field(tmp_path):
    service, _ = _service(tmp_path)
    payload = json.loads(service.report_path.read_text())
    payload.pop('ignored_context_rows')
    service.report_path.write_text(json.dumps(payload), encoding='utf-8')
    before = service.report_path.read_bytes()
    loaded = M23PatternFilterService(service.report_path).load()
    assert loaded.ignored_context_rows == 0
    assert loaded.block_rules > 0
    assert service.report_path.read_bytes() == before


def test_optional_legacy_time_contract_is_explicitly_unverified(tmp_path):
    service, records = _service(tmp_path)
    decision = _evaluate(service, records[-1], records)
    assert decision.decision == 'BLOCK'
    assert decision.context_status == 'UNVERIFIED_TIME'


def test_missing_report_still_records_valid_context_without_writing(tmp_path):
    service = M23PatternFilterService(tmp_path / 'missing.json')
    record = _record(29)
    decision = _evaluate(service, record, expected_record_time=record.timestamp)
    assert decision.decision == 'NO_EVIDENCE'
    assert decision.context_status == 'VALID'
    assert decision.context_snapshot
    assert decision.report_generated_at == 'N/D'
    assert not service.report_path.exists()
