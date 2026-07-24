from __future__ import annotations

import unittest

from dashboard_app import _m2_suggested_alpha_research_rows


class M2SuggestedAlphaLabTableTest(unittest.TestCase):
    def test_builds_one_m2_row_per_pair_without_authorizing_execution(self) -> None:
        payload = {
            "alpha_id": "ALPHA_SUGERIDA_001_PLUS",
            "timeframe": "H1",
            "results": {
                "USDCAD": [
                    {
                        "parameters": {
                            "family": "TREND_IMPULSE",
                            "fast": 30,
                            "slow": 100,
                            "adx_rising": True,
                            "volume_min": 1.1,
                            "stop_factor": 1.0,
                            "risk_reward": 2.5,
                            "session": "OVERLAP",
                        },
                        "full": {
                            "sample_size": 144,
                            "win_rate": 0.3472,
                            "profit_factor": 1.397,
                            "expectancy": 0.00022,
                            "max_drawdown": 0.0092,
                            "ict_score": 45.92,
                            "ict_grade": "E",
                        },
                        "holdout": {"profit_factor": 1.385},
                        "qualified": False,
                    }
                ],
                "AUDUSD": [
                    {
                        "parameters": {"family": "COMPRESSION_RELEASE"},
                        "full": {"ict_score": 40.0, "ict_grade": "E"},
                        "holdout": {},
                        "qualified": False,
                    }
                ],
            },
        }

        rows = _m2_suggested_alpha_research_rows(payload)

        self.assertEqual([row["Par"] for row in rows], ["AUDUSD", "USDCAD"])
        self.assertTrue(all(row["Modelo"] == "M2" for row in rows))
        self.assertTrue(
            all(row["Situacao M2"] == "NAO_QUALIFICADA / NAO_ATIVA" for row in rows)
        )
        usdcad = rows[1]
        self.assertEqual(usdcad["Alpha sugerida"], "ALPHA_SUGERIDA_001_PLUS")
        self.assertEqual(usdcad["ICT"], "45.92 / E")
        self.assertIn("Sessao OVERLAP", usdcad["Parametros"])


if __name__ == "__main__":
    unittest.main()
