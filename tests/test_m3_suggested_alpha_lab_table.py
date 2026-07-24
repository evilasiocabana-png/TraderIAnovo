from __future__ import annotations

import unittest

from dashboard_app import _m3_suggested_alpha_research_rows


class M3SuggestedAlphaLabTableTest(unittest.TestCase):
    def test_builds_one_auditable_m3_row_per_pair(self) -> None:
        payload = {
            "model_destination": "MODELO_3",
            "operational": False,
            "results": {
                "EURUSD": {
                    "alpha_id": "ALPHA_SUGERIDA_002_PLUS_EURUSD",
                    "selected_timeframe": "M30",
                    "selection_status": "APROVADA_B_PARA_REPLAY",
                    "operational": False,
                    "winner": {
                        "parameters": {
                            "family": "SQUEEZE_RELEASE",
                            "fast": 13,
                            "slow": 55,
                            "adx_min": 15,
                            "stop_factor": 2.5,
                            "risk_reward": 1.0,
                            "atr_regime": "NORMAL",
                        },
                        "full_sample": {
                            "sample_size": 138,
                            "win_rate": 0.50,
                            "profit_factor": 1.43,
                            "net_return": 0.05,
                            "max_drawdown": 0.014,
                            "ict_score": 70.8,
                            "ict_grade": "B",
                        },
                        "holdout": {"profit_factor": 1.54},
                        "stress_holdout": {"profit_factor": 1.36},
                    },
                }
            },
        }

        rows = _m3_suggested_alpha_research_rows(payload)

        self.assertEqual(1, len(rows))
        row = rows[0]
        self.assertEqual("M3", row["Modelo"])
        self.assertEqual("EURUSD", row["Par"])
        self.assertEqual("M30", row["TF vencedor"])
        self.assertEqual("1.43", row["PF liquido"])
        self.assertEqual("70.80 / B", row["ICT"])
        self.assertEqual("APROVADA_B_PARA_REPLAY", row["Situacao M3"])
        self.assertIn("ATR NORMAL", row["Parametros"])


if __name__ == "__main__":
    unittest.main()
