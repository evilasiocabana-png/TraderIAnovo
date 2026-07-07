"""Testes do analyzer oficial de validacao Monte Carlo."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.monte_carlo.monte_carlo_analyzer import (
    MonteCarloAnalysisResult,
    MonteCarloAnalyzer,
)
from research.validation.monte_carlo.monte_carlo_engine import MonteCarloResult
from research.validation.monte_carlo.monte_carlo_profile import MonteCarloProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MonteCarloAnalyzerTest(unittest.TestCase):
    """Valida analise de Monte Carlo sem recalculo de metricas das Alphas."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MonteCarloAnalysisResult))
        self.assertTrue(MonteCarloAnalysisResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(MonteCarloAnalysisResult)],
            [
                "average_return",
                "worst_case_return",
                "best_case_return",
                "expected_drawdown",
                "robustness_score",
            ],
        )

    def test_analyzer_calcula_resumo_das_simulacoes(self) -> None:
        result = MonteCarloAnalyzer().analyze(
            self._monte_carlo_result(
                simulated_returns=(10.0, 20.0, -5.0),
                simulated_drawdowns=(2.0, 4.0, 6.0),
            )
        )

        self.assertEqual(result.average_return, 25.0 / 3.0)
        self.assertEqual(result.worst_case_return, -5.0)
        self.assertEqual(result.best_case_return, 20.0)
        self.assertEqual(result.expected_drawdown, 4.0)
        self.assertGreater(result.robustness_score, 0.0)
        self.assertLessEqual(result.robustness_score, 1.0)

    def test_analyzer_retorna_zero_sem_simulacoes(self) -> None:
        result = MonteCarloAnalyzer().analyze(
            self._monte_carlo_result(
                simulated_returns=(),
                simulated_drawdowns=(),
            )
        )

        self.assertEqual(result.average_return, 0.0)
        self.assertEqual(result.worst_case_return, 0.0)
        self.assertEqual(result.best_case_return, 0.0)
        self.assertEqual(result.expected_drawdown, 0.0)
        self.assertEqual(result.robustness_score, 0.0)

    def test_analyzer_penaliza_retorno_negativo_e_drawdown_alto(self) -> None:
        strong = MonteCarloAnalyzer().analyze(
            self._monte_carlo_result(
                simulated_returns=(12.0, 10.0, 8.0),
                simulated_drawdowns=(1.0, 1.0, 2.0),
            )
        )
        fragile = MonteCarloAnalyzer().analyze(
            self._monte_carlo_result(
                simulated_returns=(-12.0, -10.0, -8.0),
                simulated_drawdowns=(8.0, 9.0, 10.0),
            )
        )

        self.assertGreater(strong.robustness_score, fragile.robustness_score)

    def test_result_e_imutavel(self) -> None:
        result = MonteCarloAnalyzer().analyze(
            self._monte_carlo_result(
                simulated_returns=(1.0,),
                simulated_drawdowns=(0.0,),
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.robustness_score = 0.0

    def test_analyzer_nao_recalcula_metricas_ou_altera_validation_runner(self) -> None:
        source = read_source(
            Path("research/validation/monte_carlo/monte_carlo_analyzer.py")
        )
        forbidden_fragments = (
            "ValidationRunner",
            "ExperimentValidationRunner",
            "ResearchPipeline",
            "ResearchRunner",
            "CampaignRunner",
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "net_profit",
            "profit_factor",
            "win_rate",
            "ReplayEngine",
            "openai",
            "llm",
            ".run(",
            ".calculate(",
            ".next_candle(",
            ".generate_signal(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_analyzer_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/monte_carlo/monte_carlo_analyzer.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
            "research.campaigns.campaign_runner",
            "research.validation.experiment_validation_runner",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "database",
            "openai",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "calculate",
            "validate",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _monte_carlo_result(
        self,
        simulated_returns: tuple[float, ...],
        simulated_drawdowns: tuple[float, ...],
    ) -> MonteCarloResult:
        return MonteCarloResult(
            campaign_id="campaign-alpha001-mc",
            profile=self._profile(),
            executed_experiments=(self._experiment(),),
            total_simulations=len(simulated_returns),
            simulated_returns=simulated_returns,
            simulated_drawdowns=simulated_drawdowns,
            average_return=0.0,
            worst_return=0.0,
            best_return=0.0,
            confidence_level=0.95,
        )

    def _profile(self) -> MonteCarloProfile:
        return MonteCarloProfile(
            profile_id="monte-carlo-baseline-001",
            simulations=3,
            random_seed=42,
            confidence_level=0.95,
            resampling_method="REORDER_TRADES",
            metadata={},
        )

    def _experiment(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="experiment-alpha001-mc",
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T07:00:00-03:00",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
