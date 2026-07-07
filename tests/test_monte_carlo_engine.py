"""Testes do engine oficial de validacao Monte Carlo."""

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
from research.validation.monte_carlo.monte_carlo_engine import (
    BOOTSTRAP_TRADES,
    MonteCarloEngine,
    MonteCarloResult,
)
from research.validation.monte_carlo.monte_carlo_profile import MonteCarloProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MonteCarloEngineTest(unittest.TestCase):
    """Valida simulacoes deterministicas sem recalculo de metricas."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MonteCarloResult))
        self.assertTrue(MonteCarloResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(MonteCarloResult)],
            [
                "campaign_id",
                "profile",
                "executed_experiments",
                "total_simulations",
                "simulated_returns",
                "simulated_drawdowns",
                "average_return",
                "worst_return",
                "best_return",
                "confidence_level",
            ],
        )

    def test_engine_delega_campanha_e_reordena_trades(self) -> None:
        calls: list[str] = []
        engine = MonteCarloEngine(
            campaign_runner=_CampaignRunnerSpy(calls, (self._experiment("exp-1"),)),
            research_runner=self._runner(),
            research_pipeline=ResearchPipeline(),
        )

        result = engine.run(
            self._campaign(trades=(1.0, -2.0, 3.0)),
            self._profile(resampling_method="REORDER_TRADES", simulations=3),
        )

        self.assertEqual(calls, ["campaign_runner.run"])
        self.assertEqual(result.campaign_id, "campaign-alpha001-mc")
        self.assertEqual(result.total_simulations, 3)
        self.assertEqual(result.simulated_returns, (2.0, 2.0, 2.0))
        self.assertEqual(len(result.simulated_drawdowns), 3)
        self.assertEqual(result.average_return, 2.0)
        self.assertEqual(result.worst_return, 2.0)
        self.assertEqual(result.best_return, 2.0)
        self.assertEqual(result.confidence_level, 0.95)

    def test_engine_bootstrap_e_deterministico_por_seed(self) -> None:
        campaign = self._campaign(trades=(1.0, -2.0, 3.0))
        profile = self._profile(
            resampling_method=BOOTSTRAP_TRADES,
            simulations=5,
        )

        first = self._engine().run(campaign, profile)
        second = self._engine().run(campaign, profile)

        self.assertEqual(first.simulated_returns, second.simulated_returns)
        self.assertEqual(first.simulated_drawdowns, second.simulated_drawdowns)

    def test_engine_retorna_vazio_sem_trades(self) -> None:
        result = self._engine().run(
            self._campaign(trades=()),
            self._profile(resampling_method=BOOTSTRAP_TRADES, simulations=10),
        )

        self.assertEqual(result.total_simulations, 0)
        self.assertEqual(result.simulated_returns, ())
        self.assertEqual(result.simulated_drawdowns, ())
        self.assertEqual(result.average_return, 0.0)
        self.assertEqual(result.worst_return, 0.0)
        self.assertEqual(result.best_return, 0.0)

    def test_engine_retorna_vazio_quando_simulacoes_sao_zero(self) -> None:
        result = self._engine().run(
            self._campaign(trades=(1.0, -1.0)),
            self._profile(resampling_method=BOOTSTRAP_TRADES, simulations=0),
        )

        self.assertEqual(result.total_simulations, 0)

    def test_engine_reutiliza_runner_e_pipeline_injetados(self) -> None:
        runner = self._runner()
        pipeline = ResearchPipeline()
        engine = MonteCarloEngine(
            campaign_runner=_CampaignRunnerSpy([], ()),
            research_runner=runner,
            research_pipeline=pipeline,
        )

        self.assertIs(engine.research_runner, runner)
        self.assertIs(engine.research_pipeline, pipeline)

    def test_result_e_imutavel(self) -> None:
        result = self._engine().run(
            self._campaign(trades=(1.0, -1.0)),
            self._profile(resampling_method=BOOTSTRAP_TRADES, simulations=1),
        )

        with self.assertRaises(FrozenInstanceError):
            result.total_simulations = 0

    def test_engine_nao_usa_ia_otimizacao_replay_ou_validation_runner(self) -> None:
        source = read_source(
            Path("research/validation/monte_carlo/monte_carlo_engine.py")
        )
        forbidden_fragments = (
            "openai",
            "llm",
            "Machine Learning",
            "optimize",
            "optimizer",
            "best_parameters",
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
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/monte_carlo/monte_carlo_engine.py")
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

    def _engine(self) -> MonteCarloEngine:
        return MonteCarloEngine(
            campaign_runner=_CampaignRunnerSpy([], (self._experiment("exp-1"),)),
            research_runner=self._runner(),
            research_pipeline=ResearchPipeline(),
        )

    def _campaign(self, trades: tuple[float, ...]) -> ResearchCampaign:
        return ResearchCampaign(
            campaign_id="campaign-alpha001-mc",
            name="Monte Carlo Campaign",
            description="Campanha de validacao Monte Carlo.",
            alpha_id="Alpha001",
            objective="Validar robustez por reamostragem.",
            status="PENDING",
            created_at="2026-06-28T06:30:00-03:00",
            created_by="CTO",
            metadata={"trades": trades},
        )

    def _profile(
        self,
        resampling_method: str,
        simulations: int,
    ) -> MonteCarloProfile:
        return MonteCarloProfile(
            profile_id="monte-carlo-baseline-001",
            simulations=simulations,
            random_seed=42,
            confidence_level=0.95,
            resampling_method=resampling_method,
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
            created_at="2026-06-28T06:30:00-03:00",
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
