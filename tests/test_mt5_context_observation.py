"""Freshness metadata cannot be refreshed by cache fallback or failed reads."""
from pathlib import Path
import unittest
from unittest.mock import patch

from application.mt5_market_data_service import MT5MarketDataService
from core.configuration_manager import ConfigurationManager
from tests.test_mt5_market_data_service import (
    ForexProvider, BatchForexProvider, EmptyExternalBatchProvider,
    ErrorForexProvider,
)


class MarketContextObservationReviewTest(unittest.TestCase):
    def setUp(self):
        ConfigurationManager.reset_configuration()
        self.hydrate = patch.object(MT5MarketDataService, '_hydrate_supplemental_forex_cache')
        self.persist = patch.object(MT5MarketDataService, '_persist_supplemental_forex_cache')
        self.clock = patch('application.mt5_market_data_service.perf_counter', return_value=1000.0)
        self.hydrate.start()
        self.persist.start()
        self.clock.start()
        self.addCleanup(self.hydrate.stop)
        self.addCleanup(self.persist.stop)
        self.addCleanup(self.clock.stop)
        self.addCleanup(ConfigurationManager.reset_configuration)

    def test_primary_success_records_live_observation(self):
        service = MT5MarketDataService(provider=ForexProvider())
        service.load_forex_signal_dashboard(timeframe='M5')
        self.assertEqual(service.m23_context_observed_at[('XAUUSD', 'M5')], 1000.0)

    def test_primary_failure_does_not_refresh_old_observation(self):
        service = MT5MarketDataService(provider=ErrorForexProvider())
        service.m23_context_observed_at[('XAUUSD', 'M5')] = 10.0
        service.load_forex_signal_dashboard(timeframe='M5')
        self.assertEqual(service.m23_context_observed_at, {('XAUUSD', 'M5'): 10.0})

    def test_primary_empty_response_does_not_mark_live(self):
        provider = ForexProvider()
        provider.get_candles = lambda *_: []
        service = MT5MarketDataService(provider=provider)
        service.load_forex_signal_dashboard(timeframe='M5')
        self.assertEqual(service.m23_context_observed_at, {})

    def test_multitimeframe_success_records_live_observation(self):
        service = MT5MarketDataService(provider=BatchForexProvider())
        service.load_forex_signal_dashboard_for_timeframes({'XAUUSD': 'M5'})
        self.assertEqual(service.m23_context_observed_at[('XAUUSD', 'M5')], 1000.0)

    def test_multitimeframe_cached_fallback_does_not_mark_live(self):
        service = MT5MarketDataService(provider=EmptyExternalBatchProvider())
        service.latest_forex_candles[('XAUUSD', 'M5')] = ForexProvider().get_candles('XAUUSD', 'M5', 201)
        service.m23_context_observed_at[('XAUUSD', 'M5')] = 10.0
        service.load_forex_signal_dashboard_for_timeframes({'XAUUSD': 'M5'})
        self.assertEqual(service.m23_context_observed_at, {('XAUUSD', 'M5'): 10.0})

    def test_seed_alone_does_not_mark_live(self):
        service = MT5MarketDataService(provider=ForexProvider())
        candles = ForexProvider().get_candles('XAUUSD', 'M5', 201)
        service.seed_supplemental_forex_candles({('XAUUSD', 'M5'): candles})
        self.assertIn(('XAUUSD', 'M5'), service.supplemental_forex_seed_only_keys)
        self.assertEqual(service.m23_context_observed_at, {})

    def test_successful_supplemental_read_marks_live_and_clears_seed(self):
        service = MT5MarketDataService(provider=ForexProvider())
        service.supplemental_forex_seed_only_keys.add(('XAUUSD', 'M5'))
        errors = service._read_supplemental_forex_batch({'M5': {'XAUUSD'}}, count=201)
        self.assertEqual(errors, {})
        self.assertNotIn(('XAUUSD', 'M5'), service.supplemental_forex_seed_only_keys)
        self.assertEqual(service.m23_context_observed_at[('XAUUSD', 'M5')], 1000.0)

    def test_failed_supplemental_read_does_not_mark_live_or_clear_seed(self):
        service = MT5MarketDataService(provider=ErrorForexProvider())
        service.supplemental_forex_seed_only_keys.add(('XAUUSD', 'M5'))
        errors = service._read_supplemental_forex_batch({'M5': {'XAUUSD'}}, count=201)
        self.assertTrue(errors)
        self.assertIn(('XAUUSD', 'M5'), service.supplemental_forex_seed_only_keys)
        self.assertEqual(service.m23_context_observed_at, {})

    def test_incomplete_seed_reconciliation_does_not_mark_live(self):
        service = MT5MarketDataService(provider=ForexProvider())
        service.supplemental_forex_seed_only_keys.add(('XAUUSD', 'M5'))
        errors = service._read_supplemental_forex_batch({'M5': {'XAUUSD'}}, count=2)
        self.assertTrue(errors)
        self.assertEqual(service.m23_context_observed_at, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
