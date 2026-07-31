from __future__ import annotations

import unittest

from research.alpha_suggested.promote_model3_all_pairs_demo import (
    CERTIFIED_PAIR,
    EXPANSION_STATUS,
    PAIRS,
    build_payload,
)


class PromoteModel3AllPairsDemoTest(unittest.TestCase):
    def test_preserves_certified_metrics_only_for_usdcad(self) -> None:
        source = {
            "method": "NESTED",
            "candidate_count_per_pair": 6000,
            "timeframes_compared": ["M30", "H1"],
            "results": {
                CERTIFIED_PAIR: {
                    "pair": CERTIFIED_PAIR,
                    "alpha_id": "CERTIFIED",
                    "selected_timeframe": "H1",
                    "selection_status": "QUALIFIED_FOR_DEMO_REPLAY",
                    "winner": {
                        "parameters": {
                            "family": "STRUCTURE_CONTINUATION",
                            "fast": 21,
                            "slow": 55,
                        },
                        "full_sample": {
                            "sample_size": 116,
                            "profit_factor": 1.4,
                        },
                    },
                }
            },
        }

        payload = build_payload(source)

        self.assertEqual(set(PAIRS), set(payload["results"]))
        certified = payload["results"][CERTIFIED_PAIR]
        self.assertEqual(116, certified["winner"]["full_sample"]["sample_size"])
        for pair in set(PAIRS) - {CERTIFIED_PAIR}:
            with self.subTest(pair=pair):
                row = payload["results"][pair]
                self.assertEqual(EXPANSION_STATUS, row["selection_status"])
                self.assertEqual({}, row["winner"]["full_sample"])
                self.assertEqual(
                    certified["winner"]["parameters"],
                    row["winner"]["parameters"],
                )
                self.assertIsNot(
                    certified["winner"]["parameters"],
                    row["winner"]["parameters"],
                )


if __name__ == "__main__":
    unittest.main()
