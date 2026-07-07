"""Testes do Research Lab com datasets historicos importados."""

import tempfile
import unittest
from pathlib import Path

from application.research_lab_service import (
    ResearchExperimentData,
    ResearchLabService,
)
from data.historical_data_loader import HistoricalDataLoader
from domain.contracts.backtest_result import BacktestResult
from research.alpha001_experiment_validator import Alpha001ExperimentValidator
from research.alpha001_research_runner import Alpha001ResearchRunner
from research.research_lab import ResearchExperiment, ResearchLab


class ResearchHistoricalDatasetTest(unittest.TestCase):
    """Valida experimentos com candles historicos reais importaveis."""

    def test_executa_experimento_usando_dataset_historico(self) -> None:
        """ResearchLab deve aceitar candles vindos do loader."""
        candles = HistoricalDataLoader().load_csv(self._historical_csv()).candles()
        experiment = self._experiment(candles)

        completed = ResearchLab().run_experiment(experiment)

        self.assertIsNotNone(completed.result)
        self.assertEqual(completed.result.total_candles, len(candles))
        self.assertTrue(completed.result.is_finished)

    def test_research_lab_service_executa_csv_historico(self) -> None:
        """Servico deve importar CSV e executar experimento Alpha001."""
        data = ResearchLabService().run_historical_csv_experiment(
            self._historical_csv(),
        )

        self.assertIsInstance(data, ResearchExperimentData)
        self.assertEqual(data.experiment_name, "Historical WDO Research")
        self.assertEqual(data.strategy_name, "alpha001_iorb")

    def test_executa_alpha001_sobre_candles_historicos(self) -> None:
        """Alpha001 deve rodar normalmente no ResearchLab historico."""
        data = ResearchLabService().run_historical_csv_experiment(
            self._historical_csv(),
            strategy_name="alpha001_iorb",
        )

        self.assertEqual(data.strategy_name, "alpha001_iorb")
        self.assertGreaterEqual(data.total_trades, 0)

    def test_gera_backtest_result_via_alpha001_runner(self) -> None:
        """Runner deve converter replay historico em BacktestResult."""
        candles = HistoricalDataLoader().load_csv(self._historical_csv()).candles()
        runner = Alpha001ResearchRunner(
            validator=Alpha001ExperimentValidator(
                minimum_total_trades=1,
                minimum_win_rate=0.0,
                minimum_profit_factor=0.0,
                maximum_drawdown_points=500.0,
                minimum_net_profit_points=-500.0,
            ),
        )

        result = runner.run([self._experiment(candles)])
        validation = result.validation_results[0]["validation"]

        self.assertIn("total_trades", validation.metrics)
        self.assertIsInstance(
            runner._to_backtest_result(runner.research_lab.last_experiment()),
            BacktestResult,
        )

    def test_mantem_compatibilidade_com_experimentos_atuais(self) -> None:
        """Experimento demo atual deve continuar funcionando."""
        data = ResearchLabService().run_demo_experiment()

        self.assertIsInstance(data, ResearchExperimentData)
        self.assertEqual(data.experiment_name, "Demo Research Lab")

    def test_csv_historico_invalido_retorna_erro_seguro(self) -> None:
        """CSV invalido deve ser rejeitado antes do ResearchLab."""
        service = ResearchLabService()

        with self.assertRaises(ValueError):
            service.run_historical_csv_experiment(self._invalid_csv())

    def _experiment(self, candles: list[object]) -> ResearchExperiment:
        return ResearchExperiment(
            experiment_name="historical_alpha001",
            strategy_name="alpha001_iorb",
            stop_points=50.0,
            target_points=100.0,
            candles=candles,
        )

    def _historical_csv(self) -> Path:
        return self._csv(
            "datetime,open,high,low,close,volume\n"
            "2026-06-26 09:00,1000,1025,995,1010,1500\n"
            "2026-06-26 09:05,1010,1030,1000,1020,1600\n"
            "2026-06-26 09:16,1020,1040,1015,1035,1700\n"
            "2026-06-26 09:17,1035,1140,1030,1135,1800\n"
        )

    def _invalid_csv(self) -> Path:
        return self._csv("foo,bar\n1,2\n")

    def _csv(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
            newline="",
        )
        with handle:
            handle.write(content)
        return Path(handle.name)


if __name__ == "__main__":
    unittest.main()
