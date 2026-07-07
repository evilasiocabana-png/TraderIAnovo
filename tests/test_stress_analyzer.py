"""Testes do analyzer oficial de cenarios de estresse."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.stress.stress_analyzer import (
    StressAnalysisResult,
    StressAnalyzer,
)
from research.validation.stress.stress_engine import StressResult
from research.validation.stress.stress_scenario import (
    StressScenario,
    StressScenarioType,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class StressAnalyzerTest(unittest.TestCase):
    """Valida analise sob estresse sem recalculo de metricas das Alphas."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(StressAnalysisResult))
        self.assertTrue(StressAnalysisResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(StressAnalysisResult)],
            [
                "degradation_score",
                "recovery_score",
                "resilience_score",
                "stability_score",
            ],
        )

    def test_analyzer_calcula_scores_para_cenario_concluido(self) -> None:
        result = StressAnalyzer().analyze(
            self._stress_result(
                statuses=("COMPLETED", "COMPLETED"),
                severity=0.2,
                enabled=True,
                status="COMPLETED",
            )
        )

        self.assertEqual(result.stability_score, 1.0)
        self.assertEqual(result.recovery_score, 1.0)
        self.assertEqual(result.degradation_score, 0.1)
        self.assertGreater(result.resilience_score, 0.9)

    def test_analyzer_penaliza_falhas_e_severidade_alta(self) -> None:
        strong = StressAnalyzer().analyze(
            self._stress_result(
                statuses=("COMPLETED", "COMPLETED"),
                severity=0.2,
                enabled=True,
                status="COMPLETED",
            )
        )
        fragile = StressAnalyzer().analyze(
            self._stress_result(
                statuses=("COMPLETED", "FAILED"),
                severity=1.0,
                enabled=True,
                status="COMPLETED",
            )
        )

        self.assertGreater(strong.resilience_score, fragile.resilience_score)
        self.assertGreater(fragile.degradation_score, strong.degradation_score)

    def test_analyzer_retorna_zero_para_cenario_desabilitado(self) -> None:
        result = StressAnalyzer().analyze(
            self._stress_result(
                statuses=(),
                severity=1.0,
                enabled=False,
                status="SKIPPED",
            )
        )

        self.assertEqual(result.degradation_score, 0.0)
        self.assertEqual(result.recovery_score, 0.0)
        self.assertEqual(result.resilience_score, 0.0)
        self.assertEqual(result.stability_score, 0.0)

    def test_analyzer_retorna_zero_para_execucao_nao_concluida(self) -> None:
        result = StressAnalyzer().analyze(
            self._stress_result(
                statuses=("COMPLETED",),
                severity=0.5,
                enabled=True,
                status="FAILED",
            )
        )

        self.assertEqual(result.recovery_score, 0.0)
        self.assertLess(result.resilience_score, result.stability_score)

    def test_result_e_imutavel(self) -> None:
        result = StressAnalyzer().analyze(
            self._stress_result(
                statuses=("COMPLETED",),
                severity=0.2,
                enabled=True,
                status="COMPLETED",
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.stability_score = 0.0

    def test_analyzer_nao_recalcula_metricas_ou_altera_validation_runner(self) -> None:
        source = read_source(Path("research/validation/stress/stress_analyzer.py"))
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
            "max_drawdown",
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
        path = Path("research/validation/stress/stress_analyzer.py")
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

    def _stress_result(
        self,
        statuses: tuple[str, ...],
        severity: float,
        enabled: bool,
        status: str,
    ) -> StressResult:
        experiments = tuple(
            self._experiment(f"experiment-{index}", experiment_status)
            for index, experiment_status in enumerate(statuses)
        )
        return StressResult(
            campaign_id="campaign-alpha001-stress",
            scenario=self._scenario(severity=severity, enabled=enabled),
            executed_experiments=experiments,
            total_experiments=len(experiments),
            scenario_enabled=enabled,
            status=status,
        )

    def _scenario(
        self,
        severity: float,
        enabled: bool,
    ) -> StressScenario:
        return StressScenario(
            scenario_id="stress-black-swan-001",
            scenario_type=StressScenarioType.BLACK_SWAN,
            description="Evento extremo de mercado.",
            severity=severity,
            enabled=enabled,
            metadata={"scope": "validation"},
        )

    def _experiment(
        self,
        experiment_id: str,
        status: str,
    ) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id=experiment_id,
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status=status,
            priority=1,
            created_at="2026-06-28T07:40:00-03:00",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
