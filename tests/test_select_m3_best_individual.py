from __future__ import annotations

import unittest
from pathlib import Path

from research.alpha_suggested.select_m3_best_individual import (
    build_consolidated_payload,
    candidate_status,
    select_best_by_pair,
)


def _result(
    *,
    qualified: bool = False,
    full_pf: float = 1.40,
    holdout_pf: float = 1.30,
    stress_pf: float = 1.20,
    sample_size: int = 130,
    ict: float = 68.0,
    drawdown: float = 0.04,
) -> dict[str, object]:
    metric = {
        "sample_size": sample_size,
        "profit_factor": full_pf,
        "expectancy": 0.001,
        "max_drawdown": drawdown,
        "ict_score": ict,
    }
    return {
        "qualified": qualified,
        "alpha_id": "ALPHA_SUGERIDA_002_PLUS_EURUSD",
        "winner": {
            "parameters": {"family": "SQUEEZE_RELEASE"},
            "full_sample": metric,
            "holdout": {
                **metric,
                "sample_size": 30,
                "profit_factor": holdout_pf,
            },
            "stress_holdout": {
                **metric,
                "sample_size": 30,
                "profit_factor": stress_pf,
            },
            "stability_blocks": [
                {"net_return": 0.01},
                {"net_return": 0.02},
                {"net_return": 0.01},
                {"net_return": -0.01},
            ],
        },
    }


class SelectM3BestIndividualTests(unittest.TestCase):
    def test_certified_result_has_highest_status(self) -> None:
        status, tier, reasons = candidate_status(_result(qualified=True))
        self.assertEqual("APROVADA_B_PARA_REPLAY", status)
        self.assertEqual(3, tier)
        self.assertEqual([], reasons)

    def test_robust_non_certified_result_is_replay_candidate(self) -> None:
        status, tier, reasons = candidate_status(_result())
        self.assertEqual("PROMISSORA_PARA_REPLAY", status)
        self.assertEqual(2, tier)
        self.assertEqual([], reasons)

    def test_weak_holdout_is_rejected(self) -> None:
        status, tier, reasons = candidate_status(_result(holdout_pf=0.80))
        self.assertEqual("REJEITADA_NAO_ATIVA", status)
        self.assertEqual(1, tier)
        self.assertTrue(any("holdout" in reason.lower() for reason in reasons))

    def test_selection_prioritizes_certification_before_raw_pf(self) -> None:
        h1 = {
            "timeframe": "H1",
            "results": {"EURUSD": _result(full_pf=2.0, holdout_pf=2.0)},
        }
        m30 = {
            "timeframe": "M30",
            "results": {
                "EURUSD": _result(
                    qualified=True,
                    full_pf=1.35,
                    holdout_pf=1.20,
                )
            },
        }
        selected = select_best_by_pair(
            [(Path("h1.json"), h1), (Path("m30.json"), m30)]
        )
        self.assertEqual("M30", selected["EURUSD"]["source_timeframe"])

    def test_consolidated_payload_is_m3_and_never_operational(self) -> None:
        payload = build_consolidated_payload(
            [
                (
                    Path("m30.json"),
                    {"timeframe": "M30", "results": {"EURUSD": _result()}},
                )
            ]
        )
        self.assertEqual("MODELO_3", payload["model_destination"])
        self.assertFalse(payload["operational"])
        self.assertEqual("MODELO_3", payload["results"]["EURUSD"]["model"])
        self.assertFalse(payload["results"]["EURUSD"]["operational"])


if __name__ == "__main__":
    unittest.main()
