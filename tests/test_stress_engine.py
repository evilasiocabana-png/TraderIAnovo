"""Testes do engine oficial de cenarios de estresse."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.research_execution_plan import ResearchExecutionPlan
from research.research_pipeline import ResearchPipeline
from research.research_runner import ResearchRunner
from research.validation.stress.stress_engine import StressEngine, StressResult
from research.validation.stress.stress_scenario import (
    StressScenario,
    StressScenarioType,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class StressEngineTest(unittest.TestCase):
    """Valida execucao de campanha sob estresse sem acoplamento operacional."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(StressResult))
        self.assertTrue(StressResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(StressResult)],
            [
                "campaign_id",
                "scenario",
                "executed_experiments",
                "total_experiments",
                "scenario_enabled",
                "status",
            ],
        )

    def test_engine_delega_execucao_da_campanha(self) -> None:
        calls: list[str] = []
        experiments = (
            self._experiment("exp-1"),
            self._experiment("exp-2"),
        )
        engine = StressEngine(
            campaign_runner=_CampaignRunnerSpy(calls, experiments),
            research_runner=self._runner(),
            research_pipeline=ResearchPipeline(),
        )

        result = engine.run(self._campaign(), self._scenario(enabled=True))

        self.assertEqual(calls, ["campaign_runner.run"])
        self.assertEqual(result.campaign_id, "campaign-alpha001-stress")
        self.assertIs(result.scenario.scenario_type, StressScenarioType.BLACK_SWAN)
        self.assertEqual(result.executed_experiments, experiments)
        self.assertEqual(result.total_experiments, 2)
        self.assertTrue(result.scenario_enabled)
        self.assertEqual(result.status, "COMPLETED")

    def test_engine_nao_executa_cenario_desabilitado(self) -> None:
        calls: list[str] = []
        engine = StressEngine(
            campaign_runner=_CampaignRunnerSpy(calls, (self._experiment("exp-1"),)),
            research_runner=self._runner(),
            research_pipeline=ResearchPipeline(),
        )

        result = engine.run(self._campaign(), self._scenario(enabled=False))

        self.assertEqual(calls, [])
        self.assertEqual(result.executed_experiments, ())
        self.assertEqual(result.total_experiments, 0)
        self.assertFalse(result.scenario_enabled)
        self.assertEqual(result.status, "SKIPPED")

    def test_engine_reutiliza_runner_e_pipeline_injetados(self) -> None:
        runner = self._runner()
        pipeline = ResearchPipeline()
        engine = StressEngine(
            campaign_runner=_CampaignRunnerSpy([], ()),
            research_runner=runner,
            research_pipeline=pipeline,
        )

        self.assertIs(engine.research_runner, runner)
        self.assertIs(engine.research_pipeline, pipeline)

    def test_result_e_imutavel(self) -> None:
        result = self._engine().run(self._campaign(), self._scenario(enabled=True))

        with self.assertRaises(FrozenInstanceError):
            result.status = "FAILED"

    def test_engine_nao_usa_ia_replay_ou_validation_runner(self) -> None:
        source = read_source(Path("research/validation/stress/stress_engine.py"))
        forbidden_fragments = (
            "openai",
            "llm",
            "Machine Learning",
            "ValidationRunner",
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

    def test_engine_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/stress/stress_engine.py")
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
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertIn("research.campaigns.campaign_runner", imports)
        self.assertIn("research.research_runner", imports)
        self.assertIn("research.research_pipeline", imports)

    def _engine(self) -> StressEngine:
        return StressEngine(
            campaign_runner=_CampaignRunnerSpy([], (self._experiment("exp-1"),)),
            research_runner=self._runner(),
            research_pipeline=ResearchPipeline(),
        )

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha001-stress",
            name="Stress Campaign",
            description="Campanha de validacao por estresse.",
            alpha_id="Alpha001",
            objective="Validar comportamento sob estresse.",
            status="PENDING",
            created_at="2026-06-28T07:30:00-03:00",
            created_by="CTO",
            metadata={},
        )

    def _scenario(self, enabled: bool) -> StressScenario:
        return StressScenario(
            scenario_id="stress-black-swan-001",
            scenario_type=StressScenarioType.BLACK_SWAN,
            description="Evento extremo de mercado.",
            severity=1.0,
            enabled=enabled,
            metadata={"scope": "validation"},
        )

    def _experiment(self, experiment_id: str) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id=experiment_id,
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T07:30:00-03:00",
            metadata={},
        )

    def _runner(self) -> ResearchRunner:
        return ResearchRunner(plan=ResearchExecutionPlan(steps=()))


class _CampaignRunnerSpy:
    def __init__(
        self,
        calls: list[str],
        result: tuple[ExperimentDefinition, ...],
    ) -> None:
        self.calls = calls
        self.result = result

    def run(
        self,
        campaign: ResearchCampaign,
    ) -> tuple[ExperimentDefinition, ...]:
        self.calls.append("campaign_runner.run")
        return self.result


if __name__ == "__main__":
    unittest.main()
