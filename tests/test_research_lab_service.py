"""Testes do servico de aplicacao do Research Lab."""

import unittest

from application.research_lab_service import (
    BenchmarkComparisonData,
    BenchmarkData,
    ExperimentValidationData,
    ParameterGridData,
    ResearchExperimentData,
    ResearchLabService,
    ResearchReportData,
)
from core.configuration_manager import ConfigurationManager
from domain.contracts.strategy_signal import StrategySignal


class ResearchLabServiceTest(unittest.TestCase):
    """Valida a fachada de aplicacao do laboratorio quantitativo."""

    def setUp(self) -> None:
        """Restaura configuracao antes de cada teste."""
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        """Evita vazamento de configuracao entre testes."""
        ConfigurationManager.reset_configuration()

    def test_run_demo_experiment_retorna_dto(self) -> None:
        """Garante execucao demo por DTO de aplicacao."""
        data = ResearchLabService().run_demo_experiment()

        self.assertIsInstance(data, ResearchExperimentData)
        self.assertEqual(data.experiment_name, "Demo Research Lab")
        self.assertEqual(data.strategy_name, "alpha001_iorb")

    def test_list_experiments_retorna_dtos(self) -> None:
        """Garante listagem dos experimentos executados."""
        service = ResearchLabService()
        first = service.run_demo_experiment()

        experiments = service.list_experiments()

        self.assertEqual(experiments, [first])
        self.assertIsInstance(experiments[0], ResearchExperimentData)

    def test_live_experiment_e_exposto_por_dtos_em_memoria(self) -> None:
        """Garante exposicao de experimento live via Research Lab."""
        service = ResearchLabService()
        service.live_experiment_runner.record_signal(
            StrategySignal("BUY", score=1, confidence=0.70),
            timestamp="2026-06-29T01:00:00+00:00",
            symbol="EURUSD",
            timeframe="H1",
            strategy_name="alpha_live",
            regime="TREND",
        )

        signals = service.list_live_experiment_signals()
        summary = service.live_experiment_summary()

        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].strategy_name, "alpha_live")
        self.assertEqual(signals[0].timeframe, "H1")
        self.assertEqual(signals[0].decision, "BUY")
        self.assertEqual(summary.total_signals, 1)
        self.assertEqual(summary.buy_count, 1)
        self.assertEqual(summary.confidence_std, 0.0)
        self.assertEqual(summary.by_regime, {"TREND": 1})
        self.assertEqual(summary.by_strategy, {"alpha_live": 1})

    def test_last_experiment_retorna_ultimo_dto(self) -> None:
        """Garante consulta do ultimo experimento executado."""
        service = ResearchLabService()
        data = service.run_demo_experiment()

        self.assertEqual(service.last_experiment(), data)

    def test_last_experiment_retorna_none_sem_execucao(self) -> None:
        """Garante estado vazio inicial."""
        self.assertIsNone(ResearchLabService().last_experiment())

    def test_run_demo_alpha001_experiment_retorna_dto(self) -> None:
        """Garante execucao Alpha001Experiment por DTO de aplicacao."""
        data = ResearchLabService().run_demo_alpha001_experiment()

        self.assertIsInstance(data, ResearchExperimentData)
        self.assertEqual(data.experiment_name, "Demo Alpha001 Experiment")
        self.assertEqual(data.strategy_name, "alpha001_iorb")

    def test_research_report_retorna_inconclusive_sem_alpha001_experiment(self) -> None:
        """Sem Alpha001Experiment, relatorio deve ser seguro."""
        report = ResearchLabService().research_report()

        self.assertIsInstance(report, ResearchReportData)
        self.assertEqual(report.conclusion, "INCONCLUSIVE")

    def test_research_report_consolida_ultimo_alpha001_experiment(self) -> None:
        """Relatorio deve consolidar o ultimo Alpha001Experiment executado."""
        service = ResearchLabService()
        service.run_demo_alpha001_experiment()

        report = service.research_report()

        self.assertIsInstance(report, ResearchReportData)
        self.assertIn("initial_stop_points", report.parameters)
        self.assertIn("total_signals", report.metrics)
        self.assertTrue(report.statistical_summary)

    def test_clear_limpa_experimentos(self) -> None:
        """Garante limpeza dos experimentos em memoria."""
        service = ResearchLabService()
        service.run_demo_experiment()

        service.clear()

        self.assertEqual(service.list_experiments(), [])
        self.assertIsNone(service.last_experiment())

    def test_run_demo_experiment_expoe_metricas_basicas(self) -> None:
        """Garante campos quantitativos no DTO."""
        data = ResearchLabService().run_demo_experiment()

        self.assertGreaterEqual(data.total_trades, 0)
        self.assertGreaterEqual(data.wins, 0)
        self.assertGreaterEqual(data.losses, 0)
        self.assertIsInstance(data.net_profit_points, float)
        self.assertIsInstance(data.win_rate, float)
        self.assertIsInstance(data.profit_factor, float)
        self.assertIsInstance(data.max_drawdown_points, float)

    def test_run_demo_benchmarks_retorna_benchmark_data(self) -> None:
        """Garante execucao de benchmarks demo."""
        data = ResearchLabService().run_demo_benchmarks()

        self.assertTrue(data)
        self.assertIsInstance(data[0], BenchmarkData)

    def test_list_benchmarks_retorna_dtos(self) -> None:
        """Garante listagem dos benchmarks executados."""
        service = ResearchLabService()
        benchmarks = service.run_demo_benchmarks()

        self.assertEqual(service.list_benchmarks(), benchmarks)

    def test_compare_benchmarks_retorna_comparison_data(self) -> None:
        """Garante comparacao de benchmarks por DTO."""
        service = ResearchLabService()
        service.run_demo_benchmarks()

        comparison = service.compare_benchmarks()

        self.assertIsInstance(comparison, BenchmarkComparisonData)
        self.assertTrue(comparison.ranking)
        self.assertIsNotNone(comparison.best_strategy)

    def test_last_comparison_retorna_ultima_comparacao(self) -> None:
        """Garante consulta da ultima comparacao."""
        service = ResearchLabService()
        service.run_demo_benchmarks()
        comparison = service.compare_benchmarks()

        self.assertEqual(service.last_comparison(), comparison)

    def test_clear_limpa_benchmarks_e_comparacao(self) -> None:
        """Garante limpeza completa do laboratorio."""
        service = ResearchLabService()
        service.run_demo_benchmarks()
        service.compare_benchmarks()

        service.clear()

        self.assertEqual(service.list_benchmarks(), [])
        self.assertIsNone(service.last_comparison())

    def test_run_demo_parameter_grid_retorna_dtos(self) -> None:
        """Garante execucao da grade demo por DTO."""
        data = ResearchLabService().run_demo_parameter_grid()

        self.assertEqual(len(data), 4)
        self.assertIsInstance(data[0], ParameterGridData)

    def test_list_parameter_grid_results_retorna_dtos(self) -> None:
        """Garante listagem dos resultados da grade."""
        service = ResearchLabService()
        data = service.run_demo_parameter_grid()

        self.assertEqual(service.list_parameter_grid_results(), data)

    def test_best_parameter_grid_result_retorna_melhor(self) -> None:
        """Garante identificacao da melhor combinacao."""
        service = ResearchLabService()
        data = service.run_demo_parameter_grid()

        best = service.best_parameter_grid_result()

        self.assertEqual(
            best,
            max(data, key=lambda result: result.net_profit_points),
        )

    def test_validate_all_benchmarks_retorna_dtos(self) -> None:
        """Garante validacao estatistica dos benchmarks."""
        service = ResearchLabService()
        service.run_demo_benchmarks()

        validations = service.validate_all_benchmarks()

        self.assertTrue(validations)
        self.assertIsInstance(validations[0], ExperimentValidationData)

    def test_list_validations_retorna_dtos(self) -> None:
        """Garante listagem das validacoes."""
        service = ResearchLabService()
        service.run_demo_benchmarks()
        validations = service.validate_all_benchmarks()

        self.assertEqual(service.list_validations(), validations)

    def test_last_validation_retorna_ultima_validacao(self) -> None:
        """Garante consulta da ultima validacao."""
        service = ResearchLabService()
        service.run_demo_benchmarks()
        validations = service.validate_all_benchmarks()

        self.assertEqual(service.last_validation(), validations[-1])


if __name__ == "__main__":
    unittest.main()
