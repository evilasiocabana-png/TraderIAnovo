from __future__ import annotations

import unittest

from dashboard_app import _m4_contextual_frontier_rows


class M4ContextualFrontierLabTableTests(unittest.TestCase):
    def test_rows_identify_research_model_without_operational_promotion(self) -> None:
        payload = {
            "model_destination": "MODELO_4_PESQUISA",
            "operational": False,
            "results": {
                "EURUSD": {
                    "alpha_id": "ALPHA_SUGERIDA_003_CONTEXTUAL_MTF_EURUSD",
                    "qualified": True,
                    "status": "QUALIFIED_FOR_MODEL4_REPLAY",
                    "winner": {
                        "base_parameters": {"family": "SQUEEZE_RELEASE"},
                        "context_overlay": {
                            "direction_mode": "BOTH",
                            "h1_mode": "ALIGNED",
                            "h4_mode": "NOT_OPPOSED",
                            "strength_mode": "CONFIRM_FAST",
                            "strength_min": 0.5,
                            "volatility_band": "MID",
                        },
                        "full_sample": {
                            "sample_size": 150,
                            "win_rate": 0.5,
                            "profit_factor": 1.5,
                            "net_return": 0.07,
                            "max_drawdown": 0.02,
                            "ict_score": 72.0,
                            "ict_grade": "B",
                        },
                        "validation": {"profit_factor": 1.2},
                        "holdout": {"profit_factor": 1.4},
                        "stress_holdout": {"profit_factor": 1.3},
                    },
                }
            },
        }

        rows = _m4_contextual_frontier_rows(payload)

        self.assertEqual(1, len(rows))
        self.assertEqual("M4-P", rows[0]["Modelo"])
        self.assertEqual("M30 -> proxima abertura", rows[0]["Entrada"])
        self.assertEqual("1.40", rows[0]["PF holdout"])
        self.assertEqual("72.00 / B", rows[0]["ICT"])
        self.assertIn("H1 ALIGNED", rows[0]["Filtro vencedor"])
        self.assertEqual(
            "APROVADA_PARA_REPLAY",
            rows[0]["Situacao M4-P"],
        )


if __name__ == "__main__":
    unittest.main()
