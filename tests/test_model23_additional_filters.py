"""Additional candidates require exact valid context and explicit blocking mode."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from application.model23_additional_filters import (
    CONTEXT_FIELDS, DIRECTION, SOURCE_MODEL, SYMBOL,
    evaluate_additional_filters, load_catalog,
)

CATALOG_PATH = Path(__file__).resolve().parents[1] / 'config/m23_additional_filters.json'


class AdditionalFiltersTest(unittest.TestCase):
    def setUp(self):
        self.catalog = load_catalog(CATALOG_PATH)
        self.assertEqual(self.catalog.status, 'READY')
        self.rule = self.catalog.rules[0]
        self.arguments = dict(
            catalog=self.catalog, source_model=SOURCE_MODEL, symbol=SYMBOL,
            direction=DIRECTION, context_snapshot=dict(self.rule.context_snapshot),
            context_status='VALID',
        )

    def evaluate(self, **changes):
        return evaluate_additional_filters(**dict(self.arguments, **changes))

    def mutated_catalog(self, change):
        payload = json.loads(CATALOG_PATH.read_text(encoding='utf-8-sig'))
        change(payload)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'catalog.json'
            path.write_text(json.dumps(payload), encoding='utf-8')
            return load_catalog(path)

    def test_catalog_contains_only_three_exploratory_m7_gold_buy_rules(self):
        self.assertEqual(len(self.catalog.rules), 3)
        self.assertEqual(len({rule.rule_id for rule in self.catalog.rules}), 3)
        for rule in self.catalog.rules:
            self.assertEqual((rule.source_model, rule.symbol, rule.direction), (SOURCE_MODEL, SYMBOL, DIRECTION))
            self.assertEqual(set(rule.context_snapshot), set(CONTEXT_FIELDS))
            self.assertFalse(rule.validated)
            self.assertEqual(set(rule.evidence), {'operations', 'validated'})

    def test_explicit_block_mode_blocks_each_exact_context(self):
        for rule in self.catalog.rules:
            with self.subTest(rule=rule.label):
                result = self.evaluate(catalog=replace(self.catalog, mode='BLOCK'), context_snapshot=dict(rule.context_snapshot))
                self.assertTrue(result.blocks_execution)
                self.assertEqual(result.matched_ids, (rule.rule_id,))
                self.assertEqual(result.matched_labels, (rule.label,))

    def test_observe_reports_match_without_blocking(self):
        result = self.evaluate(catalog=replace(self.catalog, mode='OBSERVE'))
        self.assertEqual(result.matched_ids, (self.rule.rule_id,))
        self.assertFalse(result.blocks_execution)

    def test_off_never_blocks(self):
        result = self.evaluate(catalog=replace(self.catalog, mode='OFF'))
        self.assertEqual(result.status, 'DISABLED')
        self.assertFalse(result.matched_ids)
        self.assertFalse(result.blocks_execution)

    def test_other_sources_symbols_and_directions_never_match(self):
        for changes in ({'source_model': 'MODELO_8_SMA_RSI'}, {'symbol': 'BTCUSD'}, {'direction': 'SELL'}):
            with self.subTest(changes=changes):
                result = self.evaluate(**changes)
                self.assertEqual(result.status, 'OUT_OF_SCOPE')
                self.assertFalse(result.blocks_execution)
                self.assertFalse(result.matched_ids)

    def test_each_of_seven_fields_is_required(self):
        for field in CONTEXT_FIELDS:
            context = dict(self.rule.context_snapshot)
            context.pop(field)
            with self.subTest(field=field):
                result = self.evaluate(context_snapshot=context)
                self.assertEqual(result.status, 'INVALID_CONTEXT')
                self.assertFalse(result.blocks_execution)

    def test_one_changed_dimension_prevents_exact_match(self):
        for field in CONTEXT_FIELDS:
            context = dict(self.rule.context_snapshot, **{field: 'A_DIFFERENT_CONTEXT'})
            with self.subTest(field=field):
                result = self.evaluate(context_snapshot=context)
                self.assertFalse(result.blocks_execution)
                self.assertFalse(result.matched_ids)

    def test_invalid_or_unverified_context_status_cannot_block(self):
        for status in ('MISSING', 'STALE', 'MISMATCH', 'UNVERIFIED', 'ALIGNED', ''):
            with self.subTest(status=status):
                result = self.evaluate(context_status=status)
                self.assertEqual(result.status, 'INVALID_CONTEXT')
                self.assertFalse(result.blocks_execution)

    def test_context_status_must_be_supplied_explicitly(self):
        arguments = dict(self.arguments)
        arguments.pop('context_status')
        result = evaluate_additional_filters(**arguments)
        self.assertEqual(result.status, 'INVALID_CONTEXT')
        self.assertFalse(result.blocks_execution)

    def test_extra_metadata_does_not_broaden_the_seven_field_match(self):
        context = dict(self.rule.context_snapshot, timestamp='synthetic')
        result = self.evaluate(context_snapshot=context)
        self.assertEqual(result.matched_ids, (self.rule.rule_id,))

    def test_missing_catalog_has_no_active_block(self):
        with tempfile.TemporaryDirectory() as temporary:
            catalog = load_catalog(Path(temporary) / 'absent.json')
        self.assertEqual(catalog.mode, 'OBSERVE')
        self.assertEqual(catalog.status, 'MISSING')
        self.assertFalse(self.evaluate(catalog=catalog).blocks_execution)

    def test_missing_mode_defaults_to_observe(self):
        catalog = self.mutated_catalog(lambda payload: payload.pop('mode'))
        self.assertEqual(catalog.mode, 'OBSERVE')
        self.assertEqual(catalog.status, 'READY')
        self.assertFalse(self.evaluate(catalog=catalog).blocks_execution)

    def test_invalid_mode_catalog_never_blocks(self):
        catalog = self.mutated_catalog(lambda payload: payload.update(mode='UNKNOWN'))
        self.assertEqual(catalog.status, 'INVALID')
        self.assertFalse(self.evaluate(catalog=catalog).blocks_execution)

    def test_duplicate_identifier_invalidates_catalog(self):
        catalog = self.mutated_catalog(lambda payload: payload['rules'].append(payload['rules'][0]))
        self.assertEqual(catalog.status, 'INVALID')
        self.assertFalse(self.evaluate(catalog=catalog).blocks_execution)

    def test_missing_rule_context_field_invalidates_catalog(self):
        catalog = self.mutated_catalog(lambda payload: payload['rules'][0]['context_snapshot'].pop('session'))
        self.assertEqual(catalog.status, 'INVALID')
        self.assertFalse(self.evaluate(catalog=catalog).blocks_execution)

    def test_catalog_cannot_expand_scope_to_other_models(self):
        catalog = self.mutated_catalog(lambda payload: payload['rules'][0].update(source_model='MODELO_8_SMA_RSI'))
        self.assertEqual(catalog.status, 'INVALID')
        self.assertFalse(self.evaluate(catalog=catalog).blocks_execution)


if __name__ == '__main__':
    unittest.main()
