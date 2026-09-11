"""Synchronization validation preserves the M28 pattern's own validity window."""
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import json
import unittest

from application.model28_context_sync import validate_model28_context


def fixture():
    start = datetime(2025, 1, 8, 8, tzinfo=timezone.utc)
    rows = [dict(time=start + timedelta(minutes=5 * index), open=100.0 + index,
                 high=103.0 + index, low=99.0 + index, close=102.0 + index)
            for index in range(3)]
    closed = rows[-2]
    record = SimpleNamespace(timestamp=closed['time'], index=201,
                             warmup_complete=True, **{name: closed[name] for name in ('open', 'high', 'low', 'close')})
    return dict(rows=rows, record=record, observed_at=1000.0, now=1004.0)


class Model28ContextSyncTest(unittest.TestCase):
    def setUp(self):
        self.arguments = fixture()

    def evaluate(self, **changes):
        return validate_model28_context(**dict(self.arguments, **changes))

    def assert_not_ready(self, expected_status, **changes):
        result = self.evaluate(**changes)
        self.assertFalse(result.ready)
        self.assertEqual(result.status, expected_status)
        return result

    def test_valid_latest_closed_record_is_ready_and_auditable(self):
        result = self.evaluate()
        self.assertTrue(result.ready)
        self.assertEqual(result.status, 'ALIGNED')
        audit = result.audit()
        self.assertTrue(all(name.startswith('m28_context_') for name in audit))
        self.assertEqual(audit['m28_context_expected_candle'], audit['m28_context_candle'])
        self.assertEqual(audit['m28_context_observation_age_seconds'], 4.0)
        json.dumps(audit, allow_nan=False)
        with self.assertRaises(FrozenInstanceError):
            result.ready = False

    def test_seed_does_not_prove_current_live_context(self):
        self.assert_not_ready('SEED_ONLY', seed_only=True)

    def test_absent_observation_is_not_ready(self):
        self.assert_not_ready('MISSING_OBSERVATION', observed_at=None)

    def test_old_observation_is_not_ready(self):
        self.assert_not_ready('STALE_OBSERVATION', now=1060.001)

    def test_zero_and_sixty_second_age_are_valid_boundaries(self):
        self.assertTrue(self.evaluate(now=1000.0).ready)
        self.assertTrue(self.evaluate(now=1060.0).ready)

    def test_future_observation_is_not_ready(self):
        self.assert_not_ready('FUTURE_OBSERVATION', now=999.999)

    def test_nonfinite_or_invalid_clock_values_are_rejected(self):
        for key in ('now', 'observed_at'):
            for value in (float('nan'), float('inf'), float('-inf'), True, 'not-a-clock'):
                with self.subTest(key=key, value=value):
                    result = self.assert_not_ready('INVALID_OBSERVATION', **{key: value})
                    json.dumps(result.audit(), allow_nan=False)

    def test_requires_closed_and_forming_rows(self):
        for rows in (None, [], self.arguments['rows'][-1:]):
            with self.subTest(rows=rows):
                self.assert_not_ready('MISSING_CANDLES', rows=rows)

    def test_duplicate_or_reversed_candles_are_not_silently_sorted(self):
        rows = self.arguments['rows']
        self.assert_not_ready('UNORDERED_CANDLES', rows=rows[::-1])
        self.assert_not_ready('UNORDERED_CANDLES', rows=[rows[0], rows[0], rows[1], rows[2]])

    def test_gap_before_forming_candle_is_rejected(self):
        rows = self.arguments['rows']
        rows[-1]['time'] += timedelta(minutes=5)
        self.assert_not_ready('M5_GAP')

    def test_invalid_datetime_and_nonfinite_epoch_are_rejected(self):
        for value in ('invalid', float('nan'), float('inf'), True):
            with self.subTest(value=value):
                rows = [dict(row) for row in self.arguments['rows']]
                rows[-2]['time'] = value
                self.assert_not_ready('INVALID_CANDLES', rows=rows)

    def test_missing_or_not_warmed_record_is_rejected(self):
        self.assert_not_ready('MISSING_RECORD', record=None)
        for warmup in (False, None, 'False'):
            with self.subTest(warmup=warmup):
                record = SimpleNamespace(**vars(self.arguments['record']))
                record.warmup_complete = warmup
                self.assert_not_ready('WARMUP_INCOMPLETE', record=record)

    def test_stale_record_and_forming_record_are_distinguished(self):
        self.arguments['record'].timestamp = self.arguments['rows'][0]['time']
        self.assert_not_ready('RECORD_MISMATCH')
        self.arguments['record'].timestamp = self.arguments['rows'][-1]['time']
        self.assert_not_ready('RECORD_NOT_CLOSED')
        self.arguments['record'].timestamp += timedelta(minutes=5)
        self.assert_not_ready('RECORD_NOT_CLOSED')

    def test_each_ohlc_difference_is_detected(self):
        for name in ('open', 'high', 'low', 'close'):
            with self.subTest(name=name):
                record = SimpleNamespace(**vars(self.arguments['record']))
                setattr(record, name, getattr(record, name) + 0.01)
                self.assert_not_ready('OHLC_MISMATCH', record=record)

    def test_nonfinite_closed_prices_are_rejected(self):
        self.arguments['rows'][-2]['close'] = float('nan')
        self.assert_not_ready('INVALID_CANDLES')

    def test_nonfinite_record_prices_are_rejected(self):
        self.arguments['record'].high = float('inf')
        self.assert_not_ready('INVALID_RECORD')

    def test_forming_prices_do_not_enter_context_comparison(self):
        self.arguments['rows'][-1]['close'] = float('nan')
        self.assertTrue(self.evaluate().ready)

    def test_candle_objects_with_portuguese_field_names_are_supported(self):
        rows = [SimpleNamespace(data=row['time'].isoformat(), abertura=row['open'], maxima=row['high'],
                                minima=row['low'], fechamento=row['close']) for row in self.arguments['rows']]
        self.assertTrue(self.evaluate(rows=rows).ready)

    def test_epoch_iso_and_timestamp_aliases_share_the_same_clock_domain(self):
        rows = [dict(row) for row in self.arguments['rows']]
        rows[0]['time'] = rows[0]['time'].timestamp()
        rows[1]['timestamp'] = rows[1].pop('time').isoformat().replace('+00:00', 'Z')
        rows[2]['data'] = rows[2].pop('time').replace(tzinfo=None)
        self.assertTrue(self.evaluate(rows=rows).ready)

    def test_timezone_representation_does_not_add_a_fixed_broker_offset(self):
        record = self.arguments['record']
        record.timestamp = record.timestamp.astimezone(timezone(timedelta(hours=3))).isoformat()
        self.assertTrue(self.evaluate().ready)

    def test_older_selection_remains_ready_until_original_index_expiry(self):
        selection = SimpleNamespace(selected_at=self.arguments['rows'][0]['time'].isoformat(),
                                    valid_until_index=201)
        result = self.evaluate(selection=selection)
        self.assertTrue(result.ready)
        self.assertLess(result.selected_at, result.record_time)
        self.assertEqual(result.valid_until_index, result.record_index)

    def test_expired_selection_is_rejected(self):
        selection = SimpleNamespace(selected_at=self.arguments['rows'][0]['time'], valid_until_index=200)
        self.assert_not_ready('EXPIRED_SELECTION', selection=selection)

    def test_future_selection_time_is_rejected(self):
        selection = SimpleNamespace(selected_at=self.arguments['rows'][-1]['time'], valid_until_index=205)
        self.assert_not_ready('FUTURE_SELECTION', selection=selection)

    def test_optional_selection_index_is_checked_without_equal_time_requirement(self):
        selection = SimpleNamespace(selected_at=self.arguments['rows'][0]['time'], selected_index=199, valid_until_index=205)
        self.assertTrue(self.evaluate(selection=selection).ready)
        selection.selected_index = 202
        self.assert_not_ready('FUTURE_SELECTION', selection=selection)

    def test_bad_selection_bounds_or_missing_record_index_are_rejected(self):
        for expiry in (float('nan'), -1, 201.5, True):
            with self.subTest(expiry=expiry):
                selection = SimpleNamespace(selected_at=self.arguments['rows'][0]['time'], valid_until_index=expiry)
                self.assert_not_ready('INVALID_SELECTION', selection=selection)
        selection = SimpleNamespace(selected_at=self.arguments['rows'][0]['time'], selected_index=202, valid_until_index=201)
        self.assert_not_ready('INVALID_SELECTION', selection=selection)
        del self.arguments['record'].index
        selection = SimpleNamespace(selected_at=self.arguments['rows'][0]['time'], valid_until_index=201)
        self.assert_not_ready('INVALID_SELECTION', selection=selection)


if __name__ == '__main__':
    unittest.main()
