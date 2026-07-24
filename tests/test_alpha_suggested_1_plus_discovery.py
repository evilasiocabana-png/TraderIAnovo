from __future__ import annotations

import unittest

from research.alpha_suggested.alpha_suggested_1_plus_discovery import (
    chronological_windows,
)


class AlphaSuggestedOnePlusDiscoveryTest(unittest.TestCase):
    def test_chronological_windows_preserve_unseen_holdout(self) -> None:
        self.assertEqual(
            chronological_windows(20_000),
            {
                "train": (0, 12_000),
                "validation": (12_000, 16_000),
                "holdout": (16_000, 20_000),
            },
        )

    def test_original_snapshot_uses_same_sixty_twenty_twenty_contract(self) -> None:
        self.assertEqual(
            chronological_windows(5_000),
            {
                "train": (0, 3_000),
                "validation": (3_000, 4_000),
                "holdout": (4_000, 5_000),
            },
        )


if __name__ == "__main__":
    unittest.main()
