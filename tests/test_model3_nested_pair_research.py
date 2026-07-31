import unittest

from research.alpha_suggested.model3_nested_pair_research import (
    _validation_allowed,
    _windows,
)


class Model3NestedPairResearchTests(unittest.TestCase):
    def test_windows_keep_final_twenty_percent_untouched(self) -> None:
        windows = _windows(20_000)

        self.assertEqual((0, 12_000), windows["train"])
        self.assertEqual((12_000, 16_000), windows["validation"])
        self.assertEqual((16_000, 20_000), windows["holdout"])
        self.assertEqual(3, len(windows["blocks"]))

    def test_validation_rejects_negative_stressed_candidate(self) -> None:
        validation = {
            "sample_size": 20,
            "profit_factor": 1.40,
            "expectancy": 0.001,
        }
        stress_validation = {
            "profit_factor": 0.90,
        }
        blocks = [
            {"sample_size": 20, "profit_factor": 1.20, "expectancy": 0.001},
            {"sample_size": 20, "profit_factor": 1.10, "expectancy": 0.001},
            {"sample_size": 20, "profit_factor": 0.90, "expectancy": -0.001},
        ]

        self.assertFalse(
            _validation_allowed(validation, stress_validation, blocks)
        )

    def test_validation_accepts_stable_candidate(self) -> None:
        validation = {
            "sample_size": 20,
            "profit_factor": 1.30,
            "expectancy": 0.001,
        }
        stress_validation = {
            "profit_factor": 1.10,
        }
        blocks = [
            {"sample_size": 20, "profit_factor": 1.20, "expectancy": 0.001},
            {"sample_size": 20, "profit_factor": 1.10, "expectancy": 0.001},
            {"sample_size": 20, "profit_factor": 0.90, "expectancy": -0.001},
        ]

        self.assertTrue(
            _validation_allowed(validation, stress_validation, blocks)
        )


if __name__ == "__main__":
    unittest.main()
