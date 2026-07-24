from __future__ import annotations

import unittest

from dashboard_app import _m5_best_across_models_rows


class M5BestAcrossModelsLabTableTests(unittest.TestCase):
    def test_table_exposes_operational_m5_winner_origin(self) -> None:
        payload = {
            "model_destination": "MODELO_5_PESQUISA_CONSOLIDADO",
            "operational": False,
            "results": {
                "EURUSD": {
                    "selection_status": "APROVADA_B_PARA_REPLAY",
                    "selection_reason": (
                        "nivel 4; PF total 1.430; holdout 30 / PF 1.540"
                    ),
                    "winner": {
                        "source_model": "M3",
                        "alpha_id": "ALPHA_SUGERIDA_002_PLUS_EURUSD",
                        "timeframe": "M30",
                        "source_status": "APROVADA_B_PARA_REPLAY",
                        "parameters": {
                            "family": "SQUEEZE_RELEASE",
                            "fast": 13,
                            "slow": 55,
                            "stop_factor": 2.5,
                            "risk_reward": 1.0,
                        },
                        "full_sample": {
                            "sample_size": 138,
                            "win_rate": 0.50,
                            "profit_factor": 1.43,
                            "ict_score": 70.8,
                            "ict_grade": "B",
                        },
                        "holdout": {
                            "sample_size": 30,
                            "profit_factor": 1.54,
                        },
                        "stress_holdout": {
                            "sample_size": 30,
                            "profit_factor": 1.36,
                        },
                    },
                }
            },
        }

        rows = _m5_best_across_models_rows(payload)

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("M5", row["Modelo"])
        self.assertEqual("M3", row["Origem vencedora"])
        self.assertEqual("M30", row["TF"])
        self.assertEqual("SQUEEZE_RELEASE", row["Setup vencedor"])
        self.assertEqual("30", str(row["Holdout N"]))
        self.assertEqual("1.54", row["PF holdout"])
        self.assertEqual("70.80 / B", row["ICT"])
        self.assertEqual(
            "APROVADA_B_PARA_REPLAY",
            row["Situacao M5"],
        )


if __name__ == "__main__":
    unittest.main()
