from __future__ import annotations

import unittest

from research.alpha_suggested.promote_model4_all_pairs_demo import (
    EVIDENCE_PAIR,
    EVIDENCE_STATUS,
    EXPANSION_STATUS,
    PAIRS,
    build_payload,
)


class PromoteModel4AllPairsDemoTest(unittest.TestCase):
    def test_preserves_audusd_evidence_without_copying_metrics(self) -> None:
        source = {
            "results": {
                EVIDENCE_PAIR: {
                    "pair": EVIDENCE_PAIR,
                    "qualified": False,
                    "status": "RESEARCH_NOT_QUALIFIED",
                    "winner": {
                        "base_parameters": {
                            "family": "LIQUIDITY_RECLAIM",
                            "stop_factor": 2.5,
                            "risk_reward": 3.0,
                        },
                        "context_overlay": {"direction_mode": "BUY_ONLY"},
                        "full_sample": {
                            "sample_size": 100,
                            "profit_factor": 1.468,
                        },
                        "holdout": {
                            "sample_size": 14,
                            "profit_factor": 2.121,
                        },
                    },
                }
            }
        }

        payload = build_payload(source)

        self.assertEqual(set(PAIRS), set(payload["results"]))
        evidence = payload["results"][EVIDENCE_PAIR]
        self.assertEqual(EVIDENCE_STATUS, evidence["status"])
        self.assertEqual(100, evidence["winner"]["full_sample"]["sample_size"])
        for pair in set(PAIRS) - {EVIDENCE_PAIR}:
            with self.subTest(pair=pair):
                row = payload["results"][pair]
                self.assertEqual(EXPANSION_STATUS, row["status"])
                self.assertEqual({}, row["winner"]["full_sample"])
                self.assertEqual(
                    evidence["winner"]["base_parameters"],
                    row["winner"]["base_parameters"],
                )


if __name__ == "__main__":
    unittest.main()
