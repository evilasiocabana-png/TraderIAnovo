from __future__ import annotations

import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

from research.alpha_suggested.alpha_suggested_1_plus_discovery import MarketArrays
from research.alpha_suggested.model4_contextual_frontier import (
    ContextArrays,
    apply_context_overlay,
    currency_strength_edges,
    frontier_windows,
    generate_overlay_candidates,
    precompute_next_open_paths,
)


class Model4ContextualFrontierTests(unittest.TestCase):
    def test_windows_reserve_validation_embargo_and_holdout(self) -> None:
        windows = frontier_windows(20_000)
        self.assertEqual((0, 12_000), windows.discovery)
        self.assertEqual((12_000, 15_000), windows.validation)
        self.assertEqual((15_000, 16_000), windows.embargo)
        self.assertEqual((16_000, 20_000), windows.holdout)

    def test_overlay_candidates_are_deterministic_and_unique(self) -> None:
        first = generate_overlay_candidates(5, 100, 42)
        second = generate_overlay_candidates(5, 100, 42)
        self.assertEqual(first, second)
        keys = {tuple(sorted(item.items())) for item in first}
        self.assertEqual(len(first), len(keys))

    def test_context_overlay_can_require_buy_and_higher_tf_alignment(self) -> None:
        signal = np.asarray([1, -1, 1, -1], dtype=np.int8)
        context = ContextArrays(
            h1_trend=np.asarray([1, -1, -1, -1], dtype=float),
            h1_adx=np.asarray([25, 25, 25, 25], dtype=float),
            h4_trend=np.asarray([1, 1, 1, 1], dtype=float),
            h4_adx=np.asarray([25, 25, 25, 25], dtype=float),
            strength_fast=np.ones(4),
            strength_slow=np.ones(4),
            volatility_low=np.zeros(4),
            volatility_high=np.ones(4) * 2,
        )
        overlay = {
            "direction_mode": "BUY_ONLY",
            "h1_mode": "ALIGNED",
            "h4_mode": "NONE",
            "htf_adx_min": 20,
            "strength_mode": "NONE",
            "strength_min": 0.0,
            "volatility_band": "ALL",
        }
        filtered = apply_context_overlay(signal, context, np.ones(4), overlay)
        self.assertEqual([1, 0, 0, 0], filtered.tolist())

    def test_entry_uses_next_open_and_ambiguous_bar_counts_stop_first(self) -> None:
        market = SimpleNamespace(
            frame=pd.DataFrame({"open": [100.0, 100.0, 100.0, 100.0]}),
            high=np.asarray([100.0, 100.0, 101.5, 100.0]),
            low=np.asarray([100.0, 100.0, 98.5, 100.0]),
            close=np.asarray([100.0, 95.0, 100.0, 100.0]),
            atr=np.asarray([1.0, 1.0, 1.0, 1.0]),
        )
        paths = precompute_next_open_paths(
            market,
            np.asarray([0, 1, 0, 0], dtype=np.int8),
            stop_factor=1.0,
            risk_reward=1.0,
        )
        self.assertEqual(1, len(paths))
        self.assertEqual(2, int(paths[0]["entry_index"]))
        self.assertAlmostEqual(-0.01, paths[0]["gross_return"])

    def test_currency_strength_edge_is_positive_for_rising_base(self) -> None:
        times = pd.date_range("2026-01-01", periods=6, freq="30min", tz="UTC")
        eurusd = MarketArrays(
            pair="EURUSD",
            frame=pd.DataFrame(
                {
                    "data": times.astype(str),
                    "close": [1.0, 1.01, 1.02, 1.03, 1.04, 1.05],
                }
            ),
            high=np.zeros(6),
            low=np.zeros(6),
            close=np.zeros(6),
            atr=np.zeros(6),
        )
        usdjpy = MarketArrays(
            pair="USDJPY",
            frame=pd.DataFrame(
                {"data": times.astype(str), "close": [100.0] * 6}
            ),
            high=np.zeros(6),
            low=np.zeros(6),
            close=np.zeros(6),
            atr=np.zeros(6),
        )
        edges = currency_strength_edges(
            {"EURUSD": eurusd, "USDJPY": usdjpy},
            lookback=1,
        )
        self.assertGreater(edges["EURUSD"][-1], 0.0)


if __name__ == "__main__":
    unittest.main()
