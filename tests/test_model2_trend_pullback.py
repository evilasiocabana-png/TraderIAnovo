"""Tests for the independent M2 Trend Pullback operational contract."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from application.lab_operational_model_service import (
    LabOperationalModelService,
    MODEL_10_ID,
    MODEL_2_ID,
    MODEL_8_ID,
    MODEL_9_ID,
)
from research.alpha_suggested.model2_trend_pullback import (
    MODEL_2_ALPHA_ID,
    MODEL_2_FAMILY,
    Model2TrendPullbackReading,
    evaluate_model2_trend_pullback,
)


class Model2TrendPullbackTest(unittest.TestCase):
    def test_production_contract_covers_all_pairs_with_m15_and_h1(self) -> None:
        service = LabOperationalModelService()
        results = service.results(MODEL_2_ID)

        self.assertEqual(
            set(results),
            {
                "AUDUSD",
                "EURJPY",
                "EURUSD",
                "GBPUSD",
                "NZDUSD",
                "USDCAD",
                "USDCHF",
                "USDJPY",
            },
        )
        for pair, winner in results.items():
            with self.subTest(pair=pair):
                self.assertEqual(winner["alpha_id"], MODEL_2_ALPHA_ID)
                self.assertEqual(winner["timeframe"], "M15")
                self.assertEqual(winner["parameters"]["family"], MODEL_2_FAMILY)
                self.assertEqual(winner["parameters"]["risk_reward"], 2.0)
                self.assertTrue(winner["demo_forward_enabled"])

        required = service.required_timeframes((MODEL_2_ID,))
        self.assertEqual(required["EURUSD"], {"M15", "H1"})

    def test_timeframe_variants_cover_all_pairs_with_independent_contracts(self) -> None:
        service = LabOperationalModelService()
        expected = {
            MODEL_8_ID: ("M8", "M5", "H1"),
            MODEL_9_ID: ("M9", "M1", "M15"),
            MODEL_10_ID: ("M10", "M15", "D1"),
        }

        for model_id, (label, entry_timeframe, context_timeframe) in expected.items():
            with self.subTest(model=label):
                results = service.results(model_id)
                self.assertEqual(len(results), 8)
                self.assertEqual({row["source_model"] for row in results.values()}, {label})
                self.assertEqual(
                    {row["timeframe"] for row in results.values()},
                    {entry_timeframe},
                )
                self.assertTrue(all(row["demo_forward_enabled"] for row in results.values()))
                self.assertTrue(
                    all(row["parameters"]["risk_reward"] == 2.0 for row in results.values())
                )
                required = service.required_timeframes((model_id,))
                self.assertEqual(
                    required["EURUSD"],
                    {entry_timeframe, context_timeframe},
                )

    def test_buy_requires_pullback_confirmation_and_h1_alignment(self) -> None:
        m15 = self._trend_candles(step=0.0002)
        h1 = self._trend_candles(step=0.0004)
        m15[-2].update(
            abertura=1.2220,
            maxima=1.2240,
            minima=1.2190,
            fechamento=1.2210,
        )
        m15[-1].update(
            abertura=1.2215,
            maxima=1.2245,
            minima=1.2210,
            fechamento=1.2240,
        )

        reading = evaluate_model2_trend_pullback(m15, h1)

        self.assertEqual(reading.direction, 1)
        self.assertGreater(reading.atr, 0.0)
        self.assertIn("PULLBACK_TOUCH=1", reading.diagnostics)
        self.assertIn("CONFIRM_BULLISH=1", reading.diagnostics)
        self.assertIn("H1_TREND=BUY", reading.diagnostics)

    def test_sell_is_the_exact_directional_inverse(self) -> None:
        m15 = self._trend_candles(step=0.0002, descending=True)
        h1 = self._trend_candles(step=0.0004, descending=True)
        m15[-2].update(
            abertura=1.1780,
            maxima=1.1810,
            minima=1.1760,
            fechamento=1.1790,
        )
        m15[-1].update(
            abertura=1.1785,
            maxima=1.1790,
            minima=1.1755,
            fechamento=1.1760,
        )

        reading = evaluate_model2_trend_pullback(m15, h1)

        self.assertEqual(reading.direction, -1)
        self.assertIn("PULLBACK_TOUCH=1", reading.diagnostics)
        self.assertIn("CONFIRM_BEARISH=1", reading.diagnostics)
        self.assertIn("H1_TREND=SELL", reading.diagnostics)

    def test_runtime_materializes_fixed_125_atr_stop_and_2r_target(self) -> None:
        now = datetime(2026, 7, 29, 12, 0, tzinfo=timezone.utc)
        service = LabOperationalModelService(now_provider=lambda: now)
        candles = {
            ("EURUSD", "M15"): self._runtime_candles(now, minutes=15),
            ("EURUSD", "H1"): self._runtime_candles(now, minutes=60),
        }
        reading = Model2TrendPullbackReading(
            direction=1,
            atr=0.001,
            diagnostics=("M2_SIGNAL=BUY",),
        )

        with patch(
            "application.lab_operational_model_service."
            "evaluate_trend_pullback",
            return_value=reading,
        ) as evaluate:
            decision = service.evaluate(
                model_id=MODEL_2_ID,
                pair="EURUSD",
                candles_by_market=candles,
                current_price=1.2000,
                server_timestamp=(now + timedelta(seconds=10)).isoformat(),
            )
            updated_price = service.evaluate(
                model_id=MODEL_2_ID,
                pair="EURUSD",
                candles_by_market=candles,
                current_price=1.2010,
                server_timestamp=(now + timedelta(seconds=10)).isoformat(),
            )

        self.assertTrue(decision.ready)
        self.assertEqual(decision.direction, "BUY")
        self.assertAlmostEqual(decision.stop or 0.0, 1.19875)
        self.assertAlmostEqual(decision.target or 0.0, 1.2025)
        self.assertAlmostEqual(updated_price.entry_price or 0.0, 1.2010)
        self.assertEqual(evaluate.call_count, 1)

    def _trend_candles(
        self,
        *,
        step: float,
        descending: bool = False,
        count: int = 120,
    ) -> list[dict[str, object]]:
        start = datetime(2026, 7, 20, tzinfo=timezone.utc)
        multiplier = -1 if descending else 1
        candles: list[dict[str, object]] = []
        for index in range(count):
            close = 1.2 + multiplier * index * step
            candles.append(
                {
                    "data": (start + timedelta(minutes=15 * index)).isoformat(),
                    "abertura": close - multiplier * step * 0.2,
                    "maxima": close + step * 0.8,
                    "minima": close - step * 0.8,
                    "fechamento": close,
                    "volume": 100,
                }
            )
        return candles

    def _runtime_candles(
        self,
        current_bar: datetime,
        *,
        minutes: int,
        count: int = 300,
    ) -> list[dict[str, object]]:
        start = current_bar - timedelta(minutes=minutes * (count - 1))
        return [
            {
                "data": (start + timedelta(minutes=minutes * index)).isoformat(),
                "abertura": 1.1 + index * 0.00005,
                "maxima": 1.101 + index * 0.00005,
                "minima": 1.099 + index * 0.00005,
                "fechamento": 1.1002 + index * 0.00005,
                "volume": 100,
            }
            for index in range(count)
        ]


if __name__ == "__main__":
    unittest.main()
