"""Testes da validacao cientifica oficial da Alpha102."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha001_benchmark_comparator import Alpha001BenchmarkResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_advisor import Alpha001ResearchRecommendation
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_validator import Alpha001ResearchValidationResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.alpha102.alpha102_benchmark import (
    Alpha102BenchmarkResult,
    Alpha102PeerBenchmark,
)
from research.alpha102.alpha102_portfolio_evaluation import (
    Alpha102PortfolioEvaluationResult,
)
from research.alpha102.alpha102_scientific_validation import (
    Alpha102ScientificValidation,
    Alpha102ScientificValidationResult,
)
from research.alpha102.alpha102_validation_suite import Alpha102ValidationSuiteResult
from research.benchmark.alpha_benchmark_engine import AlphaBenchmarkResult
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.benchmark.alpha_benchmark_report import AlphaBenchmarkReport
from research.benchmark.alpha_dominance_engine import AlphaDominanceResult
from research.benchmark.alpha_similarity_engine import AlphaSimilarityResult
from research.campaigns.research_campaign import ResearchCampaign
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage
from research.validation.monte_carlo.monte_carlo_approval import (
    MonteCarloApprovalResult,
)
from research.validation.stress.stress_approval import StressApprovalResult
from research.validation.suite.validation_certification import (
    ValidationCertificationResult,
)
from research.validation.suite.validation_suite import (
    ValidationSuite,
    ValidationSuiteStep,
)
from research.validation.suite.validation_suite_report import ValidationSuiteReport
from research.validation.suite.validation_suite_result import ValidationSuiteResult
from research.validation.suite.validation_suite_runner import (
    ValidationSuiteResult as ValidationSuiteExecutionResult,
)
from research.validation.walk_forward_approval import WalkForwardApprovalResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha102ScientificValidationTest(unittest.TestCase):
    """Valida orquestracao cientifica sem duplicar infraestrutura."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha102ScientificValidationResult))
        self.assertTrue(Alpha102ScientificValidationResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(Alpha102ScientificValidationResult)],
            [
                "research_result",
                "validation_suite_result",
                "benchmark_result",
                "portfolio_evaluation",
                "certification_status",
                "metadata",
            ],
        )

    def test_executa_pipeline_suite_benchmark_e_portfolio_evaluation(self) -> None:
        calls: list[str] = []
        result = self._subject(calls).validate(
            experiment=object(),
            suite=self._suite(),
            campaign=self._campaign(),
            peer_results={"Alpha101": self._research_result()},
            allocation=self._allocation(),
            optimization=self._optimization(),
            comparison_period="2026-Q1",
            created_at="2026-06-28T14:05:00-03:00",
        )

        self.assertEqual(
            calls,
            [
                "research_runner.run",
                "validation_suite.submit",
                "benchmark.position",
                "portfolio_evaluation.evaluate",
            ],
        )
        self.assertEqual(result.certification_status, "PORTFOLIO_READY")
        self.assertEqual(result.metadata["alpha_id"], "Alpha102")
        self.assertEqual(result.metadata["portfolio_decision"], "CONTINUE_RESEARCH")

    def test_result_preserva_resultados_dos_componentes_oficiais(self) -> None:
        calls: list[str] = []
        subject = self._subject(calls)

        result = subject.validate(
            experiment=object(),
            suite=self._suite(),
            campaign=self._campaign(),
            peer_results={"Alpha101": self._research_result()},
            allocation=self._allocation(),
            optimization=self._optimization(),
            comparison_period="2026-Q1",
            created_at="2026-06-28T14:05:00-03:00",
        )

        self.assertIs(result.research_result, subject.research_runner.result)
        self.assertIs(result.validation_suite_result, subject.validation_suite.result)
        self.assertIs(result.benchmark_result, subject.benchmark.result)
        self.assertIs(result.portfolio_evaluation, subject.portfolio_evaluation.result)

    def test_result_e_imutavel(self) -> None:
        result = self._subject([]).validate(
            experiment=object(),
            suite=self._suite(),
            campaign=self._campaign(),
            peer_results={"Alpha101": self._research_result()},
            allocation=self._allocation(),
            optimization=self._optimization(),
            comparison_period="2026-Q1",
            created_at="2026-06-28T14:05:00-03:00",
        )

        with self.assertRaises(FrozenInstanceError):
            result.certification_status = "RESEARCH_ONLY"

    def test_nao_duplica_research_validation_benchmark_ou_portfolio(self) -> None:
        source = read_source(Path("research/alpha102/alpha102_scientific_validation.py"))
        forbidden_fragments = (
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "WalkForwardEngine",
            "MonteCarloEngine",
            "StressEngine",
            "AlphaBenchmarkEngine",
            "PortfolioOptimizationEngine",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".next_candle(",
            ".generate_signal(",
            "net_profit_points =",
            "profit_factor =",
            "win_rate =",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha102/alpha102_scientific_validation.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
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
            "execute",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.research_runner", imports)
        self.assertIn("research.alpha102.alpha102_validation_suite", imports)
        self.assertIn("research.alpha102.alpha102_benchmark", imports)
        self.assertIn("research.alpha102.alpha102_portfolio_evaluation", imports)

    def _subject(self, calls: list[str]) -> Alpha102ScientificValidation:
        return Alpha102ScientificValidation(
            research_runner=_ResearchRunnerSpy(calls, self._research_result()),
            validation_suite=_ValidationSuiteSpy(calls, self._validation_result()),
            benchmark=_BenchmarkSpy(calls, self._benchmark_result()),
            portfolio_evaluation=_PortfolioEvaluationSpy(
                calls,
                self._portfolio_result(),
            ),
        )

    def _suite(self) -> ValidationSuite:
        return ValidationSuite(
            suite_id="validation-suite-alpha102-001",
            name="Alpha102 Scientific Validation",
            enabled_steps=(
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
                ValidationSuiteStep.STRESS_TESTING,
            ),
            required_steps=(
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
                ValidationSuiteStep.STRESS_TESTING,
            ),
            created_at="2026-06-28T14:05:00-03:00",
            metadata={},
        )

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha102-scientific-validation",
            name="Alpha102 Scientific Validation",
            description="Campanha cientifica da Alpha102.",
            alpha_id="Alpha102",
            objective="Certificar Alpha102.",
            status="PENDING",
            created_at="2026-06-28T14:05:00-03:00",
            created_by="CTO",
            metadata={},
        )

    def _allocation(self) -> AllocationWeightResult:
        return AllocationWeightResult(
            equal_weight={"Alpha102": 0.2},
            risk_adjusted_weight={"Alpha102": 0.2},
        )

    def _optimization(self) -> PortfolioOptimizationResult:
        return PortfolioOptimizationResult(
            profile_id="portfolio-alpha102",
            optimization_goal="BALANCED",
            allocation_method="RISK_ADJUSTED",
            selected_weights={"Alpha102": 0.2},
            equal_weight={"Alpha102": 0.2},
            risk_adjusted_weight={"Alpha102": 0.2},
            benchmark_recommendation="PORTFOLIO_CANDIDATE",
            execution_time=1.0,
            metadata={},
        )

    def _research_result(self) -> ResearchExecutionResult:
        research = Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(10, 5, 3, 2),
            profit=Alpha001ProfitResult(80.0, 20.0, 60.0),
            drawdown=Alpha001DrawdownResult((0.0, 60.0), 5.0, 0.0),
            win_rate=Alpha001WinRateResult(6, 3, 1, 0.6),
            profit_factor=Alpha001ProfitFactorResult(4.0),
            expectancy=Alpha001ExpectancyResult(10.0, 5.0, 2.0, 3.0),
        )
        return ResearchExecutionResult(
            experiment=Alpha001ExperimentResult(10, 10, 5, 3, 2, 0.0),
            metrics=research.metrics,
            profit=research.profit,
            drawdown=research.drawdown,
            win_rate=research.win_rate,
            profit_factor=research.profit_factor,
            expectancy=research.expectancy,
            benchmark=Alpha001BenchmarkResult(0, None, None, None, None, None, None, None),
            research_report=research,
            validation=Alpha001ResearchValidationResult(
                approved=True,
                status="APPROVED",
                reasons=(),
                minimum_trades=1,
                minimum_profit_factor=1.0,
                maximum_drawdown=10.0,
                minimum_win_rate=0.1,
                real_trading_authorized=False,
            ),
            recommendation=Alpha001ResearchRecommendation(
                recommendation="APPROVED_FOR_MORE_RESEARCH",
                status="APPROVED",
                reasons=(),
                real_trading_authorized=False,
            ),
            stage_results=(),
            started_at=datetime(2026, 6, 28, 14, 5, 0),
            finished_at=datetime(2026, 6, 28, 14, 6, 0),
            duration=60.0,
            status=ResearchStage.COMPLETED,
            errors=(),
        )

    def _validation_result(self) -> Alpha102ValidationSuiteResult:
        validation_result = ValidationSuiteResult(
            walk_forward_approval=WalkForwardApprovalResult(
                status="APPROVED",
                message="Walk Forward approved.",
                report=None,
            ),
            monte_carlo_approval=MonteCarloApprovalResult(
                status="APPROVED",
                message="Monte Carlo approved.",
                report=None,
            ),
            stress_approval=StressApprovalResult(
                status="APPROVED",
                message="Stress approved.",
                report=None,
            ),
            scientific_score=1.0,
            robustness_score=1.0,
            reproducibility_score=1.0,
        )
        certification = ValidationCertificationResult(
            status="PORTFOLIO_READY",
            message="Alpha certified for portfolio research.",
            validation_result=validation_result,
        )
        return Alpha102ValidationSuiteResult(
            suite_execution=ValidationSuiteExecutionResult(
                suite_id="validation-suite-alpha102-001",
                campaign_id="campaign-alpha102-scientific-validation",
                executed_steps=(),
                skipped_steps=(),
                walk_forward_result=None,
                monte_carlo_result=None,
                stress_result=None,
                status="COMPLETED",
            ),
            validation_report=ValidationSuiteReport(
                validation_result=validation_result,
                certification_result=certification,
                scientific_score=1.0,
                robustness_score=1.0,
                reproducibility_score=1.0,
                certification="PORTFOLIO_READY",
                executed_validations=(
                    "WALK_FORWARD",
                    "MONTE_CARLO",
                    "STRESS_TESTING",
                ),
                execution_time=1.0,
                metadata={},
            ),
            certification=certification,
            status="PORTFOLIO_READY",
        )

    def _benchmark_result(self) -> Alpha102BenchmarkResult:
        benchmark = AlphaBenchmarkResult(
            profile=AlphaBenchmarkProfile(
                benchmark_id="benchmark-alpha102-alpha101",
                alpha_a="Alpha102",
                alpha_b="Alpha101",
                experiment_ids=("exp-alpha102", "exp-alpha101"),
                campaign_ids=("campaign-alpha102", "campaign-alpha101"),
                comparison_period="2026-Q1",
                metrics=("net_profit", "max_drawdown"),
                created_at="2026-06-28T14:05:00-03:00",
                metadata={},
            ),
            total_results=0,
            comparisons=(),
            best_net_profit=None,
            best_max_drawdown=None,
            best_profit_factor=None,
            best_win_rate=None,
            best_expectancy=None,
            best_robustness=None,
            best_reproducibility=None,
        )
        report = AlphaBenchmarkReport(
            benchmark_result=benchmark,
            dominance=AlphaDominanceResult(
                benchmark_id="benchmark-alpha102-alpha101",
                alpha_a="Alpha102",
                alpha_b="Alpha101",
                decision="ALPHA_A_DOMINATES",
                alpha_a_score=4,
                alpha_b_score=1,
                compared_metrics=("net_profit", "max_drawdown"),
            ),
            similarity=AlphaSimilarityResult(0.3, 0.0, 0.7),
            alpha_a="Alpha102",
            alpha_b="Alpha101",
            benchmark_summary="Alpha102 benchmarked against Alpha101.",
            dominance_result="ALPHA_A_DOMINATES",
            similarity_score=0.3,
            diversification_score=0.7,
            recommendation="PORTFOLIO_CANDIDATE",
            execution_time=0.0,
            metadata={},
        )
        return Alpha102BenchmarkResult(
            alpha_id="Alpha102",
            peers=("Alpha101",),
            peer_benchmarks=(Alpha102PeerBenchmark("Alpha101", report),),
            dominance_summary={"Alpha101": "ALPHA_A_DOMINATES"},
            similarity_summary={"Alpha101": 0.3},
            portfolio_position="LEADING",
        )

    def _portfolio_result(self) -> Alpha102PortfolioEvaluationResult:
        return Alpha102PortfolioEvaluationResult(
            improves_portfolio=True,
            worsens_portfolio=False,
            is_redundant=False,
            should_continue=True,
            official_decision="CONTINUE_RESEARCH",
            metadata={},
        )


class _ResearchRunnerSpy:
    def __init__(self, calls: list[str], result: ResearchExecutionResult) -> None:
        self.calls = calls
        self.result = result

    def run(self, experiment: object) -> ResearchExecutionResult:
        self.calls.append("research_runner.run")
        return self.result


class _ValidationSuiteSpy:
    def __init__(self, calls: list[str], result: Alpha102ValidationSuiteResult) -> None:
        self.calls = calls
        self.result = result

    def submit(
        self,
        suite: ValidationSuite,
        campaign: ResearchCampaign,
    ) -> Alpha102ValidationSuiteResult:
        self.calls.append("validation_suite.submit")
        return self.result


class _BenchmarkSpy:
    def __init__(self, calls: list[str], result: Alpha102BenchmarkResult) -> None:
        self.calls = calls
        self.result = result

    def position(
        self,
        alpha102_result: ResearchExecutionResult,
        peer_results: dict[str, ResearchExecutionResult],
        comparison_period: str,
        created_at: str,
    ) -> Alpha102BenchmarkResult:
        self.calls.append("benchmark.position")
        return self.result


class _PortfolioEvaluationSpy:
    def __init__(
        self,
        calls: list[str],
        result: Alpha102PortfolioEvaluationResult,
    ) -> None:
        self.calls = calls
        self.result = result

    def evaluate(
        self,
        allocation: AllocationWeightResult,
        optimization: PortfolioOptimizationResult,
        benchmark: Alpha102BenchmarkResult,
    ) -> Alpha102PortfolioEvaluationResult:
        self.calls.append("portfolio_evaluation.evaluate")
        return self.result


if __name__ == "__main__":
    unittest.main()
