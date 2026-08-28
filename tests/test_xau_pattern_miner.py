"""Tests for the causal XAUUSD Replay Pattern Miner."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from threading import Thread
import unittest

from replay.pattern_miner.config import PatternMinerConfig
from replay.pattern_miner.causality import PatternCausalityAuditor
from replay.pattern_miner.detectors import CausalEventDetector
from replay.pattern_miner.engine import PatternReplayEngine
from replay.pattern_miner.indicators import IndicatorEngine
from replay.pattern_miner.mining import OutcomeEngine
from replay.pattern_miner.models import CandleBar, PatternOccurrence, ReplaySpeed


class PatternIndicatorEngineTest(unittest.TestCase):
    """Validate causal EMA, RSI, ATR, ADX, and volume features."""

    def setUp(self) -> None:
        self.config = PatternMinerConfig()

    def test_ema_uses_only_current_and_past_closes(self) -> None:
        candles = self._trend_candles(250)
        full = IndicatorEngine(self.config).compute(candles)
        prefix = IndicatorEngine(self.config).compute(candles[:221])
        self.assertAlmostEqual(full.ema9[220] or 0.0, prefix.ema9[220] or 0.0, places=12)
        self.assertAlmostEqual(full.ema200[220] or 0.0, prefix.ema200[220] or 0.0, places=12)

    def test_rsi_for_strict_uptrend_reaches_100(self) -> None:
        frame = IndicatorEngine(self.config).compute(self._trend_candles(60))
        self.assertAlmostEqual(frame.rsi14[-1] or 0.0, 100.0, places=8)

    def test_atr_adx_and_di_are_available_and_directional(self) -> None:
        frame = IndicatorEngine(self.config).compute(self._trend_candles(80))
        self.assertGreater(frame.atr14[-1] or 0.0, 0.0)
        self.assertGreater(frame.adx14[-1] or 0.0, 25.0)
        self.assertGreater(frame.plus_di14[-1] or 0.0, frame.minus_di14[-1] or 0.0)

    def test_volume_features_are_rolling_and_causal(self) -> None:
        candles = self._trend_candles(40)
        frame = IndicatorEngine(self.config).compute(candles)
        self.assertIsNone(frame.volume_average[18])
        self.assertIsNotNone(frame.volume_average[19])
        self.assertGreater(frame.volume_percentile[-1] or 0.0, 0.0)

    @staticmethod
    def _trend_candles(quantity: int) -> list[CandleBar]:
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return [
            CandleBar(
                index=index,
                timestamp=start + timedelta(minutes=5 * index),
                open=100.0 + index,
                high=101.5 + index,
                low=99.5 + index,
                close=101.0 + index,
                volume=100.0 + index,
                spread=20.0,
                real_volume=0.0,
            )
            for index in range(quantity)
        ]


class CausalDetectorTest(unittest.TestCase):
    """Validate causal confirmation and objective event rules."""

    def setUp(self) -> None:
        self.config = PatternMinerConfig(warmup_candles=5)

    def test_swing_origin_is_published_only_after_right_bars(self) -> None:
        candles = self._bars(
            [(10, 8), (11, 9), (15, 10), (12, 9), (11, 8)],
        )
        records = self._records(candles)
        self.assertNotIn("SWING_HIGH", records[2].event_types)
        event = next(event for event in records[4].events if event.event_type == "SWING_HIGH")
        self.assertEqual(event.origin_index, 2)
        self.assertEqual(event.index, 4)

    def test_bos_and_sweep_save_quantitative_characteristics(self) -> None:
        base = self._bars([(10, 8), (11, 9), (15, 10), (12, 9), (11, 8)])
        break_bar = self._bar(5, open_price=14.0, high=17.0, low=13.0, close=16.0)
        records = self._records(base + [break_bar])
        bos = next(event for event in records[-1].events if event.event_type == "BOS_UP")
        self.assertEqual(bos.level, 15.0)
        self.assertIn("distance_points", bos.feature_map())

        sweep_bar = self._bar(5, open_price=14.0, high=16.0, low=13.0, close=14.0)
        sweep_records = self._records(base + [sweep_bar])
        sweep = next(event for event in sweep_records[-1].events if event.event_type == "SWEEP_HIGH")
        self.assertIn("wick_ratio", sweep.feature_map())
        self.assertIn("penetration_atr", sweep.feature_map())

    def test_choch_depends_on_prior_structure_state(self) -> None:
        candles = self._bars([(10, 8), (11, 9), (15, 10), (12, 9), (11, 8)])
        frame = IndicatorEngine(self.config).compute(candles + [self._bar(5, 14, 17, 13, 16)])
        detector = CausalEventDetector(self.config)
        for index in range(5):
            detector.process(index, candles + [self._bar(5, 14, 17, 13, 16)], frame)
        detector.structure_state = "bearish"
        record = detector.process(5, candles + [self._bar(5, 14, 17, 13, 16)], frame)
        self.assertIn("CHOCH_UP", record.event_types)

    def test_three_candle_fvg_is_detected_without_future_bar(self) -> None:
        candles = [
            self._bar(0, 9.0, 10.0, 8.0, 9.5),
            self._bar(1, 10.0, 12.0, 9.5, 11.5),
            self._bar(2, 12.5, 14.0, 12.0, 13.5),
        ]
        records = self._records(candles)
        fvg = next(event for event in records[2].events if event.event_type == "FVG_UP")
        self.assertEqual(fvg.feature_map()["bottom"], 10.0)
        self.assertEqual(fvg.feature_map()["top"], 12.0)

    def test_event_at_n_is_unchanged_when_future_is_removed(self) -> None:
        candles = self._bars(
            [(10, 8), (11, 9), (15, 10), (12, 9), (11, 8), (17, 13), (18, 14), (16, 12)],
        )
        full = self._records(candles)
        prefix = self._records(candles[:6])
        self.assertEqual(full[5], prefix[5])

    def test_displacement_creates_objective_order_block(self) -> None:
        config = PatternMinerConfig(
            warmup_candles=2,
            atr_period=2,
            adx_period=2,
            volume_window=2,
            displacement_body_atr=0.50,
            displacement_range_atr=0.50,
            displacement_body_ratio=0.60,
            displacement_volume_relative=1.00,
        )
        candles = [
            self._bar(0, 100.0, 101.0, 99.5, 100.8),
            self._bar(1, 100.8, 101.0, 100.0, 100.2),
            self._bar(2, 100.2, 100.8, 100.0, 100.6),
            CandleBar(
                index=3,
                timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=15),
                open=100.6,
                high=105.2,
                low=100.4,
                close=105.0,
                volume=1000.0,
                spread=20.0,
                real_volume=0.0,
            ),
        ]
        frame = IndicatorEngine(config).compute(candles)
        detector = CausalEventDetector(config)
        records = [detector.process(index, candles, frame) for index in range(len(candles))]
        self.assertIn("DISPLACEMENT_UP", records[-1].event_types)
        order_block = next(event for event in records[-1].events if event.event_type == "ORDER_BLOCK_UP")
        self.assertEqual(order_block.origin_index, 1)
        self.assertEqual(
            order_block.feature_map()["definition"],
            "last_opposite_candle_before_objective_displacement",
        )

    def test_automatic_causality_audit_compares_full_and_prefix_runs(self) -> None:
        candles = self._bars(
            [(10, 8), (11, 9), (15, 10), (12, 9), (11, 8), (17, 13), (18, 14), (16, 12)],
        )
        records = self._records(candles)
        audit = PatternCausalityAuditor(self.config).audit(candles, records, indices=(5, 7))
        self.assertTrue(audit.passed)
        self.assertEqual(tuple(item.index for item in audit.checks), (5, 7))

    def _records(self, candles: list[CandleBar]):
        frame = IndicatorEngine(self.config).compute(candles)
        detector = CausalEventDetector(self.config)
        return [detector.process(index, candles, frame) for index in range(len(candles))]

    def _bars(self, high_low: list[tuple[float, float]]) -> list[CandleBar]:
        return [
            self._bar(
                index,
                open_price=(high + low) / 2.0,
                high=high,
                low=low,
                close=(high + low) / 2.0,
            )
            for index, (high, low) in enumerate(high_low)
        ]

    @staticmethod
    def _bar(
        index: int,
        open_price: float,
        high: float,
        low: float,
        close: float,
    ) -> CandleBar:
        return CandleBar(
            index=index,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=5 * index),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=100.0 + index,
            spread=20.0,
            real_volume=0.0,
        )


class OutcomeEngineTest(unittest.TestCase):
    """Validate forward returns, MFE, MAE, and first passage."""

    def test_outcomes_use_only_candles_after_pattern_completion(self) -> None:
        config = PatternMinerConfig(outcome_horizons=(1, 3), first_passage_targets_atr=(1.0, 2.0))
        candles = [
            self._bar(0, 100.0, 100.2, 99.8, 100.0),
            self._bar(1, 100.0, 101.2, 99.8, 101.0),
            self._bar(2, 101.0, 102.2, 100.8, 102.0),
            self._bar(3, 102.0, 102.5, 101.5, 102.0),
        ]
        records = self._records_with_atr(candles, atr=1.0)
        occurrence = PatternOccurrence(
            pattern_id="PAT-TEST",
            sequence=("SWEEP_LOW", "BOS_UP"),
            gap_buckets=("1-2 candles",),
            direction=1,
            start_index=0,
            end_index=0,
            event_indices=(0, 0),
            split="DISCOVERY",
        )
        outcome = OutcomeEngine(config).evaluate(occurrence, candles, records)
        self.assertIsNotNone(outcome)
        assert outcome is not None
        horizon_three = next(item for item in outcome.horizons if item.horizon == 3)
        self.assertAlmostEqual(horizon_three.return_atr, 2.0)
        self.assertAlmostEqual(horizon_three.mfe_atr, 2.5)
        self.assertAlmostEqual(horizon_three.mae_atr, 0.2)
        fp1 = next(item for item in outcome.first_passage if item.target_atr == 1.0)
        self.assertEqual(fp1.status, "SUCCESS")
        self.assertEqual(fp1.candles_to_hit, 1)

    @staticmethod
    def _records_with_atr(candles: list[CandleBar], atr: float):
        from replay.pattern_miner.models import EventRecord

        return [
            EventRecord(
                index=bar.index,
                timestamp=bar.timestamp,
                open=bar.open,
                high=bar.high,
                low=bar.low,
                close=bar.close,
                volume=bar.volume,
                spread=bar.spread,
                real_volume=bar.real_volume,
                ema9=None,
                ema20=None,
                ema50=None,
                ema200=None,
                rsi14=None,
                atr14=atr,
                adx14=None,
                plus_di14=None,
                minus_di14=None,
                volume_average=None,
                volume_relative=None,
                volume_zscore=None,
                volume_percentile=None,
                trend_state="neutral",
                structure_state="neutral",
                warmup_complete=True,
                session="Asia",
            )
            for bar in candles
        ]

    @staticmethod
    def _bar(index: int, open_price: float, high: float, low: float, close: float) -> CandleBar:
        return CandleBar(
            index=index,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=5 * index),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=100.0,
            spread=20.0,
            real_volume=0.0,
        )


class PatternReplayEngineDatasetTest(unittest.TestCase):
    """Validate the official closed-candle gate and architecture boundary."""

    def test_loader_ignores_forming_candle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "historicoXAU.csv"
            path.write_text(
                "datetime,open,high,low,close,volume,spread,real_volume,is_closed\n"
                "2026-01-01 00:00:00,100,101,99,100.5,10,20,0,1\n"
                "2026-01-01 00:05:00,100.5,102,100,101,11,20,0,0\n",
                encoding="utf-8",
            )
            state = PatternReplayEngine().load_dataset(path)
            self.assertEqual(state.total_candles, 1)

    def test_pattern_miner_does_not_import_execution_layers(self) -> None:
        root = Path("replay/pattern_miner")
        source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
        self.assertNotIn("execution_provider", source)
        self.assertNotIn("order_send", source)
        self.assertNotIn("MetaTrader5", source)

    def test_reset_cannot_mutate_live_tokens_during_batch_iteration(self) -> None:
        engine = PatternReplayEngine(PatternMinerConfig(warmup_candles=20))
        candles = PatternIndicatorEngineTest._trend_candles(300)
        engine.candles = candles
        engine.indicators = engine.indicator_engine.compute(candles)
        engine.start(ReplaySpeed.MAXIMUM)
        errors: list[BaseException] = []

        def process() -> None:
            try:
                engine.process_batch(300)
            except BaseException as exc:  # pragma: no cover - asserted below
                errors.append(exc)

        worker = Thread(target=process)
        worker.start()
        engine.reset()
        worker.join(timeout=10)

        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
