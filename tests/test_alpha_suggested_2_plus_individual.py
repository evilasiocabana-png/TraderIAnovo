from __future__ import annotations

import unittest

from research.alpha_suggested.alpha_suggested_2_plus_individual import (
    _qualification,
    chronological_research_windows,
    generate_candidates,
    summarize_outcomes,
)


class AlphaSuggestedTwoPlusIndividualTest(unittest.TestCase):
    def test_windows_keep_final_holdout_outside_four_development_blocks(self) -> None:
        windows = chronological_research_windows(20_000)

        self.assertEqual(windows.development, (0, 16_000))
        self.assertEqual(
            windows.stability_blocks,
            ((0, 4_000), (4_000, 8_000), (8_000, 12_000), (12_000, 16_000)),
        )
        self.assertEqual(windows.holdout, (16_000, 20_000))

    def test_net_metrics_include_round_trip_cost(self) -> None:
        metrics = summarize_outcomes(
            [
                {"gross_return": 0.0020, "net_return": 0.0018, "duration_candles": 4.0},
                {"gross_return": -0.0010, "net_return": -0.0012, "duration_candles": 2.0},
            ]
        )

        self.assertAlmostEqual(metrics["net_return"], 0.0006)
        self.assertAlmostEqual(metrics["profit_factor"], 1.5)
        self.assertGreater(metrics["gross_profit_factor"], metrics["profit_factor"])

    def test_qualification_requires_ict_b_even_when_profit_factor_passes(self) -> None:
        base = {
            "sample_size": 200,
            "profit_factor": 1.50,
            "expectancy": 0.0004,
            "max_drawdown": 0.05,
            "ict_score": 69.99,
            "minimum_filters_passed": True,
        }
        holdout = {**base, "sample_size": 40}
        blocks = [{**base, "sample_size": 30} for _ in range(4)]

        qualified, reasons = _qualification(base, holdout, base, holdout, blocks)

        self.assertFalse(qualified)
        self.assertIn("ICT total abaixo de B (70).", reasons)

    def test_candidate_generation_is_deterministic_and_unique(self) -> None:
        first = generate_candidates(50, 123)
        second = generate_candidates(50, 123)

        self.assertEqual(first, second)
        self.assertEqual(len(first), len({str(sorted(row.items())) for row in first}))


if __name__ == "__main__":
    unittest.main()
