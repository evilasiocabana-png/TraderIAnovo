"""Testes do executor oficial da Validation Suite."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.monte_carlo.monte_carlo_engine import MonteCarloResult
from research.validation.monte_carlo.monte_carlo_profile import MonteCarloProfile
from research.validation.stress.stress_engine import StressResult
from research.validation.stress.stress_scenario import (
    StressScenario,
    StressScenarioType,
)
from research.validation.suite.validation_suite import (
    ValidationSuite,
    ValidationSuiteStep,
)
from research.validation.suite.validation_suite_runner import (
    ValidationSuiteResult,
    ValidationSuiteRunner,
)
from research.validation.walk_forward_engine import WalkForwardResult
from research.validation.walk_forward_profile import WalkForwardProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ValidationSuiteRunnerTest(unittest.TestCase):
    """Valida orquestracao sequencial sem duplicar validacoes."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ValidationSuiteResult))
        self.assertTrue(ValidationSuiteResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(ValidationSuiteResult)],
            [
                "suite_id",
                "campaign_id",
                "executed_steps",
                "skipped_steps",
                "walk_forward_result",
                "monte_carlo_result",
                "stress_result",
                "status",
            ],
        )

    def test_runner_executa_na_ordem_institucional(self) -> None:
        calls: list[str] = []
        runner = self._runner(calls)

        result = runner.run(self._suite(), self._campaign())

        self.assertEqual(
            calls,
            [
                "walk_forward_engine.run",
                "monte_carlo_engine.run",
                "stress_engine.run",
            ],
        )
        self.assertEqual(
            result.executed_steps,
            (
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
                ValidationSuiteStep.STRESS_TESTING,
            ),
        )
        self.assertEqual(result.skipped_steps, ())
        self.assertEqual(result.status, "COMPLETED")
        self.assertIsNotNone(result.walk_forward_result)
        self.assertIsNotNone(result.monte_carlo_result)
        self.assertIsNotNone(result.stress_result)

    def test_runner_pula_etapas_desabilitadas(self) -> None:
        calls: list[str] = []
        suite = ValidationSuite(
            suite_id="validation-suite-alpha001-001",
            name="Alpha001 Scientific Validation",
            enabled_steps=(ValidationSuiteStep.MONTE_CARLO,),
            required_steps=(ValidationSuiteStep.WALK_FORWARD,),
            created_at="2026-06-28T08:20:00-03:00",
            metadata={},
        )

        result = self._runner(calls).run(suite, self._campaign())

        self.assertEqual(calls, ["monte_carlo_engine.run"])
        self.assertEqual(
            result.skipped_steps,
            (
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.STRESS_TESTING,
            ),
        )
        self.assertEqual(result.status, "INCOMPLETE")
        self.assertIsNone(result.walk_forward_result)
        self.assertIsNotNone(result.monte_carlo_result)
        self.assertIsNone(result.stress_result)

    def test_runner_repassa_perfis_e_cenario_aos_engines(self) -> None:
        calls: list[str] = []
        runner = self._runner(calls)
        campaign = self._campaign()

        result = runner.run(self._suite(), campaign)

        self.assertIs(result.walk_forward_result.profile, runner.walk_forward_profile)
        self.assertIs(result.monte_carlo_result.profile, runner.monte_carlo_profile)
        self.assertIs(result.stress_result.scenario, runner.stress_scenario)

    def test_result_e_imutavel(self) -> None:
        result = self._runner([]).run(self._suite(), self._campaign())

        with self.assertRaises(FrozenInstanceError):
            result.status = "FAILED"

    def test_runner_nao_recalcula_metricas_replay_ou_duplica_validacao(self) -> None:
        source = read_source(
            Path("research/validation/suite/validation_suite_runner.py")
        )
        forbidden_fragments = (
            "ExperimentValidationRunner",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".calculate(",
            ".validate(",
            ".analyze(",
            ".next_candle(",
            ".generate_signal(",
            "net_profit",
            "profit_factor",
            "win_rate",
            "max_drawdown",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_runner_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/suite/validation_suite_runner.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
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
            "execute",
            "calculate",
            "validate",
            "analyze",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.validation.walk_forward_engine", imports)
        self.assertIn("research.validation.monte_carlo.monte_carlo_engine", imports)
        self.assertIn("research.validation.stress.stress_engine", imports)

    def _runner(self, calls: list[str]) -> ValidationSuiteRunner:
        return ValidationSuiteRunner(
            walk_forward_engine=_WalkForwardEngineSpy(calls, self._walk_forward()),
            monte_carlo_engine=_MonteCarloEngineSpy(calls, self._monte_carlo()),
            stress_engine=_StressEngineSpy(calls, self._stress()),
            walk_forward_profile=self._walk_forward_profile(),
            monte_carlo_profile=self._monte_carlo_profile(),
            stress_scenario=self._scenario(),
        )

    def _suite(self) -> ValidationSuite:
        return ValidationSuite(
            suite_id="validation-suite-alpha001-001",
            name="Alpha001 Scientific Validation",
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
            created_at="2026-06-28T08:20:00-03:00",
            metadata={},
        )

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha001-validation-suite",
            name="Validation Suite Campaign",
            description="Campanha de validacao cientifica.",
            alpha_id="Alpha001",
            objective="Executar suite de validacao.",
            status="PENDING",
            created_at="2026-06-28T08:20:00-03:00",
            created_by="CTO",
            metadata={},
        )

    def _walk_forward_profile(self) -> WalkForwardProfile:
        return WalkForwardProfile(
            profile_id="walk-forward-balanced-001",
            training_window=1,
            validation_window=1,
            testing_window=1,
            rolling_window=1,
            minimum_samples=100,
            metadata={},
        )

    def _monte_carlo_profile(self) -> MonteCarloProfile:
        return MonteCarloProfile(
            profile_id="monte-carlo-baseline-001",
            simulations=3,
            random_seed=42,
            confidence_level=0.95,
            resampling_method="REORDER_TRADES",
            metadata={},
        )

    def _scenario(self) -> StressScenario:
        return StressScenario(
            scenario_id="stress-black-swan-001",
            scenario_type=StressScenarioType.BLACK_SWAN,
            description="Evento extremo de mercado.",
            severity=1.0,
            enabled=True,
            metadata={},
        )

    def _experiment(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="experiment-alpha001-suite",
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T08:20:00-03:00",
            metadata={},
        )

    def _walk_forward(self) -> WalkForwardResult:
        experiment = self._experiment()
        return WalkForwardResult(
            campaign_id="campaign-alpha001-validation-suite",
            profile=self._walk_forward_profile(),
            executed_experiments=(experiment,),
            training_experiments=(experiment,),
            validation_experiments=(),
            testing_experiments=(),
            rolling_window=1,
            minimum_samples=100,
        )

    def _monte_carlo(self) -> MonteCarloResult:
        return MonteCarloResult(
            campaign_id="campaign-alpha001-validation-suite",
            profile=self._monte_carlo_profile(),
            executed_experiments=(self._experiment(),),
            total_simulations=3,
            simulated_returns=(1.0, 1.0, 1.0),
            simulated_drawdowns=(0.0, 0.0, 0.0),
            average_return=1.0,
            worst_return=1.0,
            best_return=1.0,
            confidence_level=0.95,
        )

    def _stress(self) -> StressResult:
        return StressResult(
            campaign_id="campaign-alpha001-validation-suite",
            scenario=self._scenario(),
            executed_experiments=(self._experiment(),),
            total_experiments=1,
            scenario_enabled=True,
            status="COMPLETED",
        )


class _WalkForwardEngineSpy:
    def __init__(self, calls: list[str], result: WalkForwardResult) -> None:
        self.calls = calls
        self.result = result

    def run(
        self,
        campaign: ResearchCampaign,
        profile: WalkForwardProfile,
    ) -> WalkForwardResult:
        self.calls.append("walk_forward_engine.run")
        return WalkForwardResult(
            campaign_id=self.result.campaign_id,
            profile=profile,
            executed_experiments=self.result.executed_experiments,
            training_experiments=self.result.training_experiments,
            validation_experiments=self.result.validation_experiments,
            testing_experiments=self.result.testing_experiments,
            rolling_window=self.result.rolling_window,
            minimum_samples=self.result.minimum_samples,
        )


class _MonteCarloEngineSpy:
    def __init__(self, calls: list[str], result: MonteCarloResult) -> None:
        self.calls = calls
        self.result = result

    def run(
        self,
        campaign: ResearchCampaign,
        profile: MonteCarloProfile,
    ) -> MonteCarloResult:
        self.calls.append("monte_carlo_engine.run")
        return MonteCarloResult(
            campaign_id=self.result.campaign_id,
            profile=profile,
            executed_experiments=self.result.executed_experiments,
            total_simulations=self.result.total_simulations,
            simulated_returns=self.result.simulated_returns,
            simulated_drawdowns=self.result.simulated_drawdowns,
            average_return=self.result.average_return,
            worst_return=self.result.worst_return,
            best_return=self.result.best_return,
            confidence_level=self.result.confidence_level,
        )


class _StressEngineSpy:
    def __init__(self, calls: list[str], result: StressResult) -> None:
        self.calls = calls
        self.result = result

    def run(
        self,
        campaign: ResearchCampaign,
        scenario: StressScenario,
    ) -> StressResult:
        self.calls.append("stress_engine.run")
        return StressResult(
            campaign_id=self.result.campaign_id,
            scenario=scenario,
            executed_experiments=self.result.executed_experiments,
            total_experiments=self.result.total_experiments,
            scenario_enabled=self.result.scenario_enabled,
            status=self.result.status,
        )


if __name__ == "__main__":
    unittest.main()
