from __future__ import annotations

import unittest

from research.alpha_suggested.select_m5_best_across_models import (
    MODEL_DESTINATION,
    build_consolidated_payload,
    candidate_rank,
    normalize_m1,
    normalize_m2,
    normalize_m3,
    normalize_m4,
    select_best_by_pair,
)


def _metrics(
    *,
    sample: int = 130,
    pf: float = 1.40,
    expectancy: float = 0.001,
    ict: float = 68.0,
) -> dict[str, object]:
    return {
        "sample_size": sample,
        "win_rate": 0.50,
        "profit_factor": pf,
        "expectancy": expectancy,
        "max_drawdown": 0.03,
        "ict_score": ict,
        "ict_grade": "C",
    }


class SelectM5BestAcrossModelsTests(unittest.TestCase):
    def test_m1_certified_candidate_keeps_highest_evidence_tier(self) -> None:
        candidates = normalize_m1(
            {
                "best_scenarios_by_market": [
                    {
                        "pair": "USDCAD",
                        "alpha_id": "ALPHA003",
                        "timeframe": "H1",
                        "ict_status": "CERTIFICADA_B",
                        "ict_score": 71.0,
                        "ict_grade": "B",
                        "lab_confidence_sample_size": 104,
                        "lab_confidence": 0.57,
                        "lab_confidence_profit_factor": 2.05,
                        "lab_confidence_expectancy": 0.001,
                        "lab_confidence_max_drawdown": 0.01,
                        "parameters": {"alpha": "ALPHA003"},
                    }
                ]
            }
        )

        self.assertEqual(1, len(candidates))
        self.assertEqual(4, candidates[0]["selection_tier"])
        self.assertEqual("M1", candidates[0]["source_model"])

    def test_m3_robust_candidate_beats_m1_hypothesis(self) -> None:
        m1 = {
            "pair": "AUDUSD",
            "source_model": "M1",
            "selection_tier": 2,
            "full_sample": _metrics(pf=1.70),
            "validation": {},
            "holdout": {},
            "stress_holdout": {},
        }
        m3 = {
            "pair": "AUDUSD",
            "source_model": "M3",
            "selection_tier": 3,
            "full_sample": _metrics(pf=1.40),
            "validation": {},
            "holdout": _metrics(sample=25, pf=1.35),
            "stress_holdout": _metrics(sample=25, pf=1.20),
        }

        winner = select_best_by_pair([m1, m3])["AUDUSD"]

        self.assertEqual("M3", winner["source_model"])

    def test_stressed_m4_hypothesis_beats_equal_tier_without_holdout(self) -> None:
        m1 = {
            "pair": "USDCHF",
            "source_model": "M1",
            "selection_tier": 2,
            "full_sample": _metrics(sample=127, pf=1.51),
            "validation": {},
            "holdout": {},
            "stress_holdout": {},
        }
        m4 = {
            "pair": "USDCHF",
            "source_model": "M4-P",
            "selection_tier": 2,
            "full_sample": _metrics(sample=74, pf=1.99),
            "validation": _metrics(sample=14, pf=2.28),
            "holdout": _metrics(sample=10, pf=1.66),
            "stress_holdout": _metrics(sample=10, pf=1.55),
        }

        self.assertGreater(candidate_rank(m4), candidate_rank(m1))
        self.assertEqual(
            "M4-P",
            select_best_by_pair([m1, m4])["USDCHF"]["source_model"],
        )

    def test_normalizers_preserve_all_four_source_models(self) -> None:
        m2 = normalize_m2(
            {
                "alpha_id": "ALPHA_SUGERIDA_001_PLUS",
                "results": {
                    "EURUSD": [
                        {
                            "parameters": {"family": "TREND_IMPULSE"},
                            "full": _metrics(sample=150, pf=1.4),
                            "validation": _metrics(sample=30, pf=1.2),
                            "holdout": _metrics(sample=30, pf=1.3),
                        }
                    ]
                },
            }
        )
        m3 = normalize_m3(
            {
                "results": {
                    "EURUSD": {
                        "alpha_id": "A3",
                        "selected_timeframe": "M30",
                        "selection_status": "PROMISSORA_PARA_REPLAY",
                        "winner": {
                            "parameters": {},
                            "full_sample": _metrics(),
                            "holdout": _metrics(sample=25),
                            "stress_holdout": _metrics(sample=25, pf=1.2),
                        },
                    }
                }
            }
        )
        m4 = normalize_m4(
            {
                "results": {
                    "EURUSD": {
                        "alpha_id": "A4",
                        "qualified": False,
                        "winner": {
                            "base_parameters": {},
                            "full_sample": _metrics(sample=80, pf=1.5),
                            "validation": _metrics(sample=12, pf=1.3),
                            "holdout": _metrics(sample=12, pf=1.4),
                            "stress_holdout": _metrics(sample=12, pf=1.2),
                        },
                    }
                }
            }
        )

        self.assertEqual("M2", m2[0]["source_model"])
        self.assertEqual("M3", m3[0]["source_model"])
        self.assertEqual("M4-P", m4[0]["source_model"])

    def test_consolidated_payload_is_read_only_and_keeps_audit_candidates(
        self,
    ) -> None:
        m1 = {
            "best_scenarios_by_market": [
                {
                    "pair": "EURUSD",
                    "alpha_id": "ALPHA013",
                    "timeframe": "H1",
                    "ict_status": "REJEITADA",
                    "ict_score": 48.0,
                    "ict_grade": "E",
                    "lab_confidence_sample_size": 108,
                    "lab_confidence_profit_factor": 1.4,
                    "lab_confidence_expectancy": 0.001,
                    "lab_confidence_max_drawdown": 0.03,
                }
            ]
        }
        m2 = {"results": {}}
        m3 = {
            "results": {
                "EURUSD": {
                    "alpha_id": "A3",
                    "selected_timeframe": "M30",
                    "selection_status": "APROVADA_B_PARA_REPLAY",
                    "winner": {
                        "parameters": {"family": "SQUEEZE_RELEASE"},
                        "full_sample": _metrics(ict=72.0),
                        "holdout": _metrics(sample=30, pf=1.5),
                        "stress_holdout": _metrics(sample=30, pf=1.3),
                    },
                }
            }
        }
        m4 = {"results": {}}

        payload = build_consolidated_payload(m1, m2, m3, m4)
        result = payload["results"]["EURUSD"]

        self.assertEqual(MODEL_DESTINATION, payload["model_destination"])
        self.assertFalse(payload["operational"])
        self.assertEqual("M3", result["winner"]["source_model"])
        self.assertEqual(2, len(result["compared_candidates"]))
        self.assertFalse(result["operational"])


if __name__ == "__main__":
    unittest.main()
