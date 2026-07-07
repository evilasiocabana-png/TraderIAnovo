"""Testes da pesquisa quantitativa com dataset historico real."""

from __future__ import annotations

import unittest
from pathlib import Path

from application.research_lab_service import RealDataResearchData, ResearchLabService


class RealDataResearchTest(unittest.TestCase):
    """Valida Research Lab usando o dataset historico interno."""

    def test_run_real_data_research_retorna_fluxo_consolidado(self) -> None:
        data = ResearchLabService().run_real_data_research()

        self.assertIsInstance(data, RealDataResearchData)
        self.assertEqual(data.dataset_id, "wdo_1m_2025")
        self.assertEqual(data.campaign_id, "campaign-wdo_1m_2025")
        self.assertEqual(data.total_candles, 2)
        self.assertEqual(data.experiment.experiment_name, "Real Data Research wdo_1m_2025")
        self.assertEqual(data.research_runner_status, "COMPLETED")
        self.assertGreaterEqual(data.total_benchmarks, 4)
        self.assertGreaterEqual(data.total_validations, 4)
        self.assertIn(
            data.validation_suite_status,
            {
                "VALIDATED_WITH_REAL_DATA",
                "INSUFFICIENT_REAL_DATA_SAMPLE",
            },
        )
        self.assertEqual(data.portfolio_status, "PORTFOLIO_EVALUATED_WITH_REAL_DATA")

    def test_run_real_data_benchmarks_usa_dataset_catalogado(self) -> None:
        service = ResearchLabService()

        benchmarks = service.run_real_data_benchmarks()

        self.assertGreaterEqual(len(benchmarks), 4)
        self.assertTrue(all(benchmark.strategy_name for benchmark in benchmarks))

    def test_research_lab_service_nao_acessa_arquivo_real_diretamente(self) -> None:
        source = Path("application/research_lab_service.py").read_text(
            encoding="utf-8",
        )

        self.assertIn("load_dataset", source)
        self.assertNotIn("historical_data/datasets/WDO/1m/2025/data.csv", source)


if __name__ == "__main__":
    unittest.main()
