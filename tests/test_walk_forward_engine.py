"""Testes do engine Walk-Forward para campanhas completas."""

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
from research.validation.walk_forward_engine import (
    WalkForwardEngine,
    WalkForwardResult,
)
from research.validation.walk_forward_profile import WalkForwardProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class WalkForwardEngineTest(unittest.TestCase):
    """Valida Walk-Forward de campanhas sem recalculo de metricas."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(WalkForwardResult))
        self.assertTrue(WalkForwardResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(WalkForwardResult)],
            [
                "campaign_id",
                "profile",
                "executed_experiments",
                "training_experiments",
                "validation_experiments",
                "testing_experiments",
                "rolling_window",
                "minimum_samples",
            ],
        )

    def test_engine_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(WalkForwardEngine))
        self.assertTrue(WalkForwardEngine.__dataclass_params__.frozen)

    def test_engine_delega_campanha_e_separa_janelas(self) -> None:
        calls: list[str] = []
        experiments = tuple(
            self._experiment(f"exp-{index}")
            for index in range(1, 7)
        )
        engine = WalkForwardEngine(
            campaign_runner=_CampaignRunnerSpy(calls, experiments),
            research_runner=self._runner(),
            research_pipeline=ResearchPipeline(),
        )

        result = engine.run(self._campaign(), self._profile())

        self.assertEqual(calls, ["campaign_runner.run"])
        self.assertEqual(result.campaign_id, "campaign-alpha001-wf")
        self.assertEqual(result.executed_experiments, experiments)
        self.assertEqual(
            [item.experiment_id for item in result.training_experiments],
            ["exp-1", "exp-2"],
        )
        self.assertEqual(
            [item.experiment_id for item in result.validation_experiments],
            ["exp-3", "exp-4"],
        )
        self.assertEqual(
            [item.experiment_id for item in result.testing_experiments],
            ["exp-5"],
        )
        self.assertEqual(result.rolling_window, 1)
        self.assertEqual(result.minimum_samples, 100)

    def test_engine_reutiliza_research_runner_e_pipeline_injetados(self) -> None:
        runner = self._runner()
        pipeline = ResearchPipeline()
        engine = WalkForwardEngine(
            campaign_runner=_CampaignRunnerSpy([], ()),
            research_runner=runner,
            research_pipeline=pipeline,
        )

        self.assertIs(engine.research_runner, runner)
        self.assertIs(engine.research_pipeline, pipeline)

    def test_janelas_incompletas_preservam_experimentos_disponiveis(self) -> None:
        result = WalkForwardEngine(
            campaign_runner=_CampaignRunnerSpy([], (self._experiment("exp-1"),)),
            research_runner=self._runner(),
            research_pipeline=ResearchPipeline(),
        ).run(self._campaign(), self._profile())

        self.assertEqual(len(result.training_experiments), 1)
        self.assertEqual(result.validation_experiments, ())
        self.assertEqual(result.testing_experiments, ())

    def test_result_e_imutavel(self) -> None:
        result = WalkForwardEngine(
            campaign_runner=_CampaignRunnerSpy([], ()),
            research_runner=self._runner(),
            research_pipeline=ResearchPipeline(),
        ).run(self._campaign(), self._profile())

        with self.assertRaises(FrozenInstanceError):
            result.campaign_id = "changed"

    def test_engine_nao_otimiza_parametros_usa_ia_ou_recalcula_metricas(self) -> None:
        source = read_source(Path("research/validation/walk_forward_engine.py"))
        forbidden_fragments = (
            "optimize",
            "optimizer",
            "best_parameters",
            "select_parameters",
            "openai",
            "llm",
            "Machine Learning",
            "sklearn",
            "ReplayEngine",
            "Alpha001Experiment(",
            ".calculate(",
            ".validate(",
            ".next_candle(",
            ".generate_signal(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/walk_forward_engine.py")
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

    def _campaign(self) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha001-wf",
            name="Walk Forward Campaign",
            description="Campanha de validacao walk-forward.",
            alpha_id="Alpha001",
            objective="Validar janelas de pesquisa.",
            status="PENDING",
            created_at="2026-06-28T05:50:00-03:00",
            created_by="CTO",
            metadata={},
        )

    def _profile(self) -> WalkForwardProfile:
        return WalkForwardProfile(
            profile_id="walk-forward-balanced-001",
            training_window=2,
            validation_window=2,
            testing_window=1,
            rolling_window=1,
            minimum_samples=100,
            metadata={},
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
            created_at="2026-06-28T05:50:00-03:00",
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
