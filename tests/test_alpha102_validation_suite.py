"""Testes da submissao da Alpha102 a Validation Suite oficial."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.alpha102.alpha102_validation_suite import (
    Alpha102ValidationSuite,
    Alpha102ValidationSuiteResult,
)
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import ExperimentDefinition
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
    ValidationSuiteResult as ValidationSuiteExecutionResult,
)
from research.validation.walk_forward_engine import WalkForwardResult
from research.validation.walk_forward_profile import WalkForwardProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


_DEFAULT = object()


class Alpha102ValidationSuiteTest(unittest.TestCase):
    """Valida certificacao da Alpha102 sem novos validadores."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha102ValidationSuiteResult))
        self.assertTrue(Alpha102ValidationSuiteResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(Alpha102ValidationSuiteResult)],
            [
                "suite_execution",
                "validation_report",
                "certification",
                "status",
            ],
        )

    def test_suite_submete_alpha102_as_tres_validacoes_oficiais(self) -> None:
        calls: list[str] = []
        result = self._subject(calls).submit(self._suite(), self._campaign())

        self.assertEqual(calls, ["suite_runner.run"])
        self.assertEqual(
            result.suite_execution.executed_steps,
            (
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
                ValidationSuiteStep.STRESS_TESTING,
            ),
        )
        self.assertEqual(
            result.validation_report.executed_validations,
            ("WALK_FORWARD", "MONTE_CARLO", "STRESS_TESTING"),
        )
        self.assertEqual(result.certification.status, "PORTFOLIO_READY")
        self.assertEqual(result.status, "PORTFOLIO_READY")

    def test_suite_gera_validation_report_e_certification(self) -> None:
        result = self._subject([]).submit(self._suite(), self._campaign())

        self.assertIs(
            result.validation_report.validation_result,
            result.certification.validation_result,
        )
        self.assertEqual(result.validation_report.certification, "PORTFOLIO_READY")
        self.assertEqual(result.validation_report.scientific_score, 1.0)
        self.assertEqual(result.validation_report.robustness_score, 1.0)
        self.assertEqual(result.validation_report.reproducibility_score, 1.0)
        self.assertEqual(result.validation_report.metadata["alpha_id"], "Alpha102")
        self.assertEqual(
            result.validation_report.metadata["campaign_id"],
            "campaign-alpha102-validation-suite",
        )

    def test_result_e_imutavel(self) -> None:
        result = self._subject([]).submit(self._suite(), self._campaign())

        with self.assertRaises(FrozenInstanceError):
            result.status = "RESEARCH_ONLY"

    def test_suite_falha_claramente_quando_validacao_obrigatoria_nao_existe(self) -> None:
        execution = self._suite_execution(
            walk_forward_result=None,
            monte_carlo_result=self._monte_carlo_result(),
            stress_result=self._stress_result(),
        )
        subject = Alpha102ValidationSuite(
            suite_runner=_SuiteRunnerSpy([], execution),
        )

        with self.assertRaisesRegex(RuntimeError, "Walk Forward result is required"):
            subject.submit(self._suite(), self._campaign())

    def test_suite_nao_cria_validadores_novos_ou_acessa_operacao(self) -> None:
        source = read_source(Path("research/alpha102/alpha102_validation_suite.py"))
        forbidden_fragments = (
            "ExperimentValidationRunner",
            "ValidationGate",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".next_candle(",
            ".generate_signal(",
            "class Alpha102Validator",
            "def validate",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_suite_permanece_desacoplada_de_domain_replay_e_dashboard(self) -> None:
        path = Path("research/alpha102/alpha102_validation_suite.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
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
        self.assertIn("research.validation.suite.validation_suite_runner", imports)
        self.assertIn("research.validation.suite.validation_certification", imports)
        self.assertIn("research.validation.walk_forward_approval", imports)
        self.assertIn("research.validation.monte_carlo.monte_carlo_approval", imports)
        self.assertIn("research.validation.stress.stress_approval", imports)

    def _subject(self, calls: list[str]) -> Alpha102ValidationSuite:
        return Alpha102ValidationSuite(
            suite_runner=_SuiteRunnerSpy(calls, self._suite_execution()),
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
            created_at="2026-06-28T13:30:00-03:00",
            metadata={},
        )

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha102-validation-suite",
            name="Alpha102 Validation Suite",
            description="Campanha de certificacao cientifica da Alpha102.",
            alpha_id="Alpha102",
            objective="Submeter Alpha102 a Validation Suite oficial.",
            status="PENDING",
            created_at="2026-06-28T13:30:00-03:00",
            created_by="CTO",
            metadata={"trades": (2.0, 1.0, 3.0)},
        )

    def _suite_execution(
        self,
        walk_forward_result: WalkForwardResult | None | object = _DEFAULT,
        monte_carlo_result: MonteCarloResult | None | object = _DEFAULT,
        stress_result: StressResult | None | object = _DEFAULT,
    ) -> ValidationSuiteExecutionResult:
        walk_forward = (
            self._walk_forward_result()
            if walk_forward_result is _DEFAULT
            else walk_forward_result
        )
        monte_carlo = (
            self._monte_carlo_result()
            if monte_carlo_result is _DEFAULT
            else monte_carlo_result
        )
        stress = (
            self._stress_result()
            if stress_result is _DEFAULT
            else stress_result
        )
        return ValidationSuiteExecutionResult(
            suite_id="validation-suite-alpha102-001",
            campaign_id="campaign-alpha102-validation-suite",
            executed_steps=(
                ValidationSuiteStep.WALK_FORWARD,
                ValidationSuiteStep.MONTE_CARLO,
                ValidationSuiteStep.STRESS_TESTING,
            ),
            skipped_steps=(),
            walk_forward_result=walk_forward,
            monte_carlo_result=monte_carlo,
            stress_result=stress,
            status="COMPLETED",
        )

    def _walk_forward_result(self) -> WalkForwardResult:
        training = self._experiment("wf-training")
        validation = self._experiment("wf-validation")
        testing = self._experiment("wf-testing")
        return WalkForwardResult(
            campaign_id="campaign-alpha102-validation-suite",
            profile=WalkForwardProfile(
                profile_id="walk-forward-alpha102",
                training_window=1,
                validation_window=1,
                testing_window=1,
                rolling_window=1,
                minimum_samples=3,
                metadata={},
            ),
            executed_experiments=(training, validation, testing),
            training_experiments=(training,),
            validation_experiments=(validation,),
            testing_experiments=(testing,),
            rolling_window=1,
            minimum_samples=3,
        )

    def _monte_carlo_result(self) -> MonteCarloResult:
        return MonteCarloResult(
            campaign_id="campaign-alpha102-validation-suite",
            profile=MonteCarloProfile(
                profile_id="monte-carlo-alpha102",
                simulations=3,
                random_seed=102,
                confidence_level=0.95,
                resampling_method="REORDER_TRADES",
                metadata={},
            ),
            executed_experiments=(self._experiment("mc-001"),),
            total_simulations=3,
            simulated_returns=(2.0, 2.0, 2.0),
            simulated_drawdowns=(0.0, 0.0, 0.0),
            average_return=2.0,
            worst_return=2.0,
            best_return=2.0,
            confidence_level=0.95,
        )

    def _stress_result(self) -> StressResult:
        return StressResult(
            campaign_id="campaign-alpha102-validation-suite",
            scenario=StressScenario(
                scenario_id="stress-alpha102-low-severity",
                scenario_type=StressScenarioType.TRENDING_MARKET,
                description="Cenario institucional de validacao Alpha102.",
                severity=0.2,
                enabled=True,
                metadata={},
            ),
            executed_experiments=(self._experiment("stress-001"),),
            total_experiments=1,
            scenario_enabled=True,
            status="COMPLETED",
        )

    def _experiment(self, experiment_id: str) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id=experiment_id,
            alpha_id="Alpha102",
            alpha_version="1.0.0",
            configuration_version="cfg-alpha102-001",
            replay_period="2026-01-01/2026-03-31",
            dataset="WDO-swing-2026",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T13:30:00-03:00",
            metadata={"alpha_id": "Alpha102"},
        )


class _SuiteRunnerSpy:
    def __init__(
        self,
        calls: list[str],
        result: ValidationSuiteExecutionResult,
    ) -> None:
        self.calls = calls
        self.result = result

    def run(
        self,
        suite: ValidationSuite,
        campaign: ResearchCampaign,
    ) -> ValidationSuiteExecutionResult:
        self.calls.append("suite_runner.run")
        return self.result


if __name__ == "__main__":
    unittest.main()
