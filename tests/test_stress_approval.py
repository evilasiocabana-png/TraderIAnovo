"""Testes do gate oficial de aprovacao sob estresse."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.stress.stress_analyzer import StressAnalysisResult
from research.validation.stress.stress_approval import (
    APPROVED,
    FAILED,
    WARNING,
    StressApproval,
    StressApprovalResult,
)
from research.validation.stress.stress_engine import StressResult
from research.validation.stress.stress_report import StressReport
from research.validation.stress.stress_scenario import (
    StressScenario,
    StressScenarioType,
)
from tests.architecture_test_utils import calls_from, imports_from, read_source


class StressApprovalTest(unittest.TestCase):
    """Valida decisao institucional sem execucao operacional."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(StressApprovalResult))
        self.assertTrue(StressApprovalResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(StressApprovalResult)],
            ["status", "message", "report"],
        )

    def test_approval_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(StressApproval))
        self.assertTrue(StressApproval.__dataclass_params__.frozen)

    def test_retorna_approved_para_resultado_resiliente(self) -> None:
        report = self._report(
            degradation_score=0.1,
            resilience_score=0.9,
            stability_score=0.85,
        )

        result = StressApproval().evaluate(report)

        self.assertEqual(result.status, APPROVED)
        self.assertIs(result.report, report)

    def test_retorna_warning_em_limite_institucional(self) -> None:
        report = self._report(
            degradation_score=0.3,
            resilience_score=0.8,
            stability_score=0.8,
        )

        result = StressApproval().evaluate(report)

        self.assertEqual(result.status, WARNING)
        self.assertIs(result.report, report)

    def test_retorna_failed_quando_resiliencia_e_baixa(self) -> None:
        report = self._report(
            degradation_score=0.1,
            resilience_score=0.6,
            stability_score=0.9,
        )

        result = StressApproval().evaluate(report)

        self.assertEqual(result.status, FAILED)

    def test_retorna_failed_quando_estabilidade_ou_degradacao_falham(self) -> None:
        low_stability = StressApproval().evaluate(
            self._report(
                degradation_score=0.1,
                resilience_score=0.9,
                stability_score=0.6,
            )
        )
        high_degradation = StressApproval().evaluate(
            self._report(
                degradation_score=0.4,
                resilience_score=0.9,
                stability_score=0.9,
            )
        )

        self.assertEqual(low_stability.status, FAILED)
        self.assertEqual(high_degradation.status, FAILED)

    def test_result_e_imutavel(self) -> None:
        result = StressApproval().evaluate(
            self._report(
                degradation_score=0.1,
                resilience_score=0.9,
                stability_score=0.9,
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.status = FAILED

    def test_approval_nao_executa_pesquisa_replay_dashboard_ou_metricas(self) -> None:
        source = read_source(Path("research/validation/stress/stress_approval.py"))
        forbidden_fragments = (
            "ValidationGate",
            "ResearchPipeline",
            "ResearchRunner",
            "ReplayEngine",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "order_send",
            "execute_order",
            ".run(",
            ".calculate(",
            ".analyze(",
            ".next_candle(",
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

    def test_approval_permanece_desacoplado_de_domain_e_operacao(self) -> None:
        path = Path("research/validation/stress/stress_approval.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
            "research.validation.validation_gate",
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
            "analyze",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(
        self,
        degradation_score: float,
        resilience_score: float,
        stability_score: float,
    ) -> StressReport:
        analysis = StressAnalysisResult(
            degradation_score=degradation_score,
            recovery_score=0.9,
            resilience_score=resilience_score,
            stability_score=stability_score,
        )
        return StressReport(
            stress_result=self._stress_result(),
            analysis_result=analysis,
            scenario=self._scenario(),
            degradation_score=degradation_score,
            recovery_score=analysis.recovery_score,
            resilience_score=resilience_score,
            stability_score=stability_score,
            execution_time=1.0,
            metadata={},
        )

    def _stress_result(self) -> StressResult:
        return StressResult(
            campaign_id="campaign-alpha001-stress",
            scenario=self._scenario(),
            executed_experiments=(self._experiment(),),
            total_experiments=1,
            scenario_enabled=True,
            status="COMPLETED",
        )

    def _scenario(self) -> StressScenario:
        return StressScenario(
            scenario_id="stress-black-swan-001",
            scenario_type=StressScenarioType.BLACK_SWAN,
            description="Evento extremo de mercado.",
            severity=1.0,
            enabled=True,
            metadata={"scope": "validation"},
        )

    def _experiment(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="experiment-alpha001-stress",
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T08:00:00-03:00",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
