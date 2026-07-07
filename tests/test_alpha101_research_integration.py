"""Testes de integracao da Alpha101 com o ecossistema de Research."""

from pathlib import Path
import unittest

from domain.candle import Candle
from research.alpha001_benchmark_comparator import Alpha001BenchmarkResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_advisor import Alpha001ResearchRecommendation
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_validator import Alpha001ResearchValidationResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.alpha101.alpha101_experiment import Alpha101Experiment
from research.alpha101.alpha101_research_integration import (
    Alpha101ResearchIntegration,
)
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.reproducibility.research_snapshot import ResearchSnapshot
from research.research_execution_plan import (
    ResearchExecutionPlan,
    ResearchExecutionStep,
)
from research.research_pipeline import ResearchPipeline, ResearchPipelineResult
from research.research_runner import ResearchRunner
from research.research_stage import ResearchStage
from research.validation.validation_rule_registry import ValidationRuleRegistry
from strategies.alpha101.alpha101_config import Alpha101Config
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha101ResearchIntegrationTest(unittest.TestCase):
    """Valida reutilizacao integral da arquitetura existente pela Alpha101."""

    def test_research_pipeline_processa_alpha101_com_engines_existentes(self) -> None:
        calls: list[str] = []
        integration = Alpha101ResearchIntegration(
            pipeline=ResearchPipeline(
                metrics_engine=_SpyCalculate("metrics", calls, self._metrics()),
                profit_engine=_SpyCalculate("profit", calls, self._profit()),
                drawdown_engine=_SpyCalculate("drawdown", calls, self._drawdown()),
                win_rate_engine=_SpyCalculate("win_rate", calls, self._win_rate()),
                profit_factor_engine=_SpyCalculate(
                    "profit_factor",
                    calls,
                    self._profit_factor(),
                ),
                expectancy_engine=_SpyCalculate(
                    "expectancy",
                    calls,
                    self._expectancy(),
                ),
                benchmark_comparator=_SpyComparator(calls),
                validator=_SpyValidator(calls, self._validation()),
                advisor=_SpyAdvisor(calls, self._recommendation()),
            ),
        )

        result = integration.run_research(self._experiment())

        self.assertIsInstance(result, ResearchPipelineResult)
        self.assertEqual(
            calls,
            [
                "metrics",
                "profit",
                "drawdown",
                "win_rate",
                "profit_factor",
                "expectancy",
                "benchmark",
                "validator",
                "advisor",
            ],
        )
        self.assertEqual(result.experiment.total_candles, 2)
        self.assertIsInstance(result.research, Alpha001ResearchResult)

    def test_research_runner_executa_alpha101_sem_alterar_runner(self) -> None:
        calls: list[str] = []
        plan = ResearchExecutionPlan(
            steps=(
                ResearchExecutionStep(
                    name="Alpha001Experiment",
                    order=1,
                    description="Executa experimento pelo contrato existente.",
                    enabled=True,
                    required=True,
                ),
                ResearchExecutionStep(
                    name="Alpha001MetricsEngine",
                    order=2,
                    description="Reutiliza MetricsEngine existente.",
                    enabled=True,
                    required=True,
                ),
            ),
        )
        runner = ResearchRunner(
            plan=plan,
            metrics_engine=_SpyCalculate("metrics", calls, self._metrics()),
        )

        result = Alpha101ResearchIntegration().run_with_runner(
            runner,
            _ExperimentSpy(calls),
        )

        self.assertEqual(calls, ["experiment", "metrics"])
        self.assertEqual(result.status, ResearchStage.COMPLETED)
        self.assertTrue(all(stage.success for stage in result.stage_results))

    def test_validation_reproducibility_e_campaigns_reutilizam_componentes(self) -> None:
        integration = Alpha101ResearchIntegration()
        snapshot = self._snapshot()

        fingerprint = integration.generate_fingerprint(snapshot)
        reproducibility = integration.validate_reproducibility(snapshot, fingerprint)
        campaign_experiments = integration.build_campaign(
            self._campaign(),
            self._experiment_definition(),
        )
        validation = integration.run_validation(
            self._execution_result(),
            ValidationRuleRegistry(),
        )

        self.assertEqual(fingerprint.experiment_id, "exp-alpha101-001")
        self.assertTrue(reproducibility.is_reproducible)
        self.assertEqual(campaign_experiments[0].alpha_id, "Alpha101")
        self.assertGreaterEqual(len(validation.passed_rules), 1)

    def test_alpha101_nao_cria_engines_de_research_proprios(self) -> None:
        alpha101_files = [
            path
            for path in Path("research/alpha101").glob("*.py")
            if path.name != "__init__.py"
        ]
        forbidden_class_names = (
            "Alpha101MetricsEngine",
            "Alpha101ProfitEngine",
            "Alpha101DrawdownEngine",
            "Alpha101WinRateEngine",
            "Alpha101ProfitFactorEngine",
            "Alpha101ExpectancyEngine",
        )
        forbidden_files = [
            path
            for path in alpha101_files
            if path.name.endswith("_engine.py")
        ]
        forbidden_classes = [
            f"{path}:{class_name}"
            for path in alpha101_files
            for class_name in forbidden_class_names
            if class_name in read_source(path)
        ]

        self.assertEqual(forbidden_files, [])
        self.assertEqual(forbidden_classes, [])

    def test_integracao_nao_acopla_labs_operacionais_ou_infraestrutura(self) -> None:
        path = Path("research/alpha101/alpha101_research_integration.py")
        forbidden_imports = {
            "core.decision_pipeline",
            "replay.replay_engine",
            "market.features.feature_pipeline",
            "market.context.context_pipeline",
            "risk.risk_pipeline",
            "market.data.data_pipeline",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "order_send",
            "execute_order",
            "send_order",
            "next_candle",
            "load_candles",
            "processar",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports_from(path)))
        self.assertTrue(forbidden_calls.isdisjoint(calls_from(path)))

    def test_research_pipeline_permanece_sem_acoplamento_alpha101(self) -> None:
        source = read_source(Path("research/research_pipeline.py"))

        self.assertNotIn("Alpha101", source)

    def _experiment(self) -> Alpha101Experiment:
        return Alpha101Experiment(
            config=self._config(),
            candles=(
                Candle("2026-06-27T10:00:00-03:00", 5500.0, 5520.0, 5480.0, 5525.0, 2000),
                Candle("2026-06-27T10:01:00-03:00", 5525.0, 5530.0, 5490.0, 5510.0, 2100),
            ),
        )

    def _config(self) -> Alpha101Config:
        return Alpha101Config(
            timeframe="DAILY",
            holding_period="SWING",
            stop_points=120.0,
            target_points=240.0,
            minimum_volume=1000.0,
            minimum_volatility=20.0,
            minimum_confidence=0.7,
            risk_profile="swing-research",
        )

    def _snapshot(self) -> ResearchSnapshot:
        return ResearchSnapshot(
            snapshot_id="snapshot-alpha101-001",
            experiment_id="exp-alpha101-001",
            alpha_id="Alpha101",
            alpha_version="1.0",
            configuration_version="cfg-101",
            feature_version="feat-1",
            context_version="ctx-1",
            risk_version="risk-1",
            research_pipeline_version="research-1",
            replay_period="2026-01",
            dataset="wdo-2026",
            random_seed=42,
            created_at="2026-06-27T10:00:00",
            metadata={"parameters": {"risk_profile": "swing-research"}},
        )

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha101",
            name="Alpha101 Research Campaign",
            description="Campanha declarativa da Alpha101.",
            alpha_id="Alpha101",
            objective="Validar Alpha101 em pesquisa.",
            status="PENDING",
            created_at="2026-06-27T10:00:00",
            created_by="CTO",
            metadata={"datasets": ("wdo-2026",)},
        )

    def _experiment_definition(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="template-alpha101",
            alpha_id="Alpha101",
            alpha_version="1.0",
            configuration_version="cfg-101",
            replay_period="2026-01",
            dataset="wdo-2026",
            status="PENDING",
            priority=1,
            created_at="2026-06-27T10:00:00",
            metadata={},
        )

    def _execution_result(self):
        plan = ResearchExecutionPlan(
            steps=(
                ResearchExecutionStep("Alpha001Experiment", 1, "Contrato existente.", True, True),
                ResearchExecutionStep("Alpha001MetricsEngine", 2, "Metricas.", True, True),
                ResearchExecutionStep("Alpha001ProfitEngine", 3, "Lucro.", True, True),
                ResearchExecutionStep("Alpha001DrawdownEngine", 4, "Drawdown.", True, True),
                ResearchExecutionStep("Alpha001WinRateEngine", 5, "Win rate.", True, True),
                ResearchExecutionStep("Alpha001ProfitFactorEngine", 6, "PF.", True, True),
                ResearchExecutionStep("Alpha001ExpectancyEngine", 7, "Expectancy.", True, True),
                ResearchExecutionStep("Alpha001BenchmarkComparator", 8, "Benchmark.", True, True),
                ResearchExecutionStep("Alpha001ResearchReport", 9, "Report.", True, True),
                ResearchExecutionStep("Alpha001ResearchValidator", 10, "Validacao.", True, True),
                ResearchExecutionStep("Alpha001ResearchAdvisor", 11, "Advisor.", True, True),
            ),
        )
        return Alpha101ResearchIntegration().run_with_runner(
            ResearchRunner(plan=plan),
            self._experiment(),
        )

    def _metrics(self) -> Alpha001MetricsResult:
        return Alpha001MetricsResult(2, 1, 1, 0)

    def _profit(self) -> Alpha001ProfitResult:
        return Alpha001ProfitResult(10.0, 5.0, 5.0)

    def _drawdown(self) -> Alpha001DrawdownResult:
        return Alpha001DrawdownResult((0.0, 5.0), 1.0, 1.0)

    def _win_rate(self) -> Alpha001WinRateResult:
        return Alpha001WinRateResult(1, 1, 0, 0.5)

    def _profit_factor(self) -> Alpha001ProfitFactorResult:
        return Alpha001ProfitFactorResult(2.0)

    def _expectancy(self) -> Alpha001ExpectancyResult:
        return Alpha001ExpectancyResult(10.0, 5.0, 2.0, 5.0)

    def _validation(self) -> Alpha001ResearchValidationResult:
        return Alpha001ResearchValidationResult(
            approved=True,
            status="APPROVED",
            reasons=("ok",),
            minimum_trades=1,
            minimum_profit_factor=1.0,
            maximum_drawdown=10.0,
            minimum_win_rate=0.1,
            real_trading_authorized=False,
        )

    def _recommendation(self) -> Alpha001ResearchRecommendation:
        return Alpha001ResearchRecommendation(
            recommendation="APPROVED_FOR_MORE_RESEARCH",
            status="APPROVED",
            reasons=("ok",),
            real_trading_authorized=False,
        )


class _ExperimentSpy:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def run(self) -> object:
        self.calls.append("experiment")
        return object()


class _SpyCalculate:
    def __init__(self, name: str, calls: list[str], result: object) -> None:
        self.name = name
        self.calls = calls
        self.result = result

    def calculate(self, value: object) -> object:
        self.calls.append(self.name)
        return self.result


class _SpyComparator:
    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def compare(
        self,
        results: list[Alpha001ResearchResult],
    ) -> Alpha001BenchmarkResult:
        self.calls.append("benchmark")
        best = results[0] if results else None
        return Alpha001BenchmarkResult(
            total_results=len(results),
            best_overall=best,
            best_total_trades=best,
            best_net_profit=best,
            best_max_drawdown=best,
            best_profit_factor=best,
            best_win_rate=best,
            best_expectancy=best,
            ranking=tuple(results),
        )


class _SpyValidator:
    def __init__(
        self,
        calls: list[str],
        result: Alpha001ResearchValidationResult,
    ) -> None:
        self.calls = calls
        self.result = result

    def validate(
        self,
        research_result: Alpha001ResearchResult,
    ) -> Alpha001ResearchValidationResult:
        self.calls.append("validator")
        return self.result


class _SpyAdvisor:
    def __init__(
        self,
        calls: list[str],
        result: Alpha001ResearchRecommendation,
    ) -> None:
        self.calls = calls
        self.result = result

    def recommend(
        self,
        validation_result: Alpha001ResearchValidationResult,
    ) -> Alpha001ResearchRecommendation:
        self.calls.append("advisor")
        return self.result


if __name__ == "__main__":
    unittest.main()
