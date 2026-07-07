"""Testes do gate oficial de aprovacao Walk-Forward."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.walk_forward_analyzer import WalkForwardAnalysisResult
from research.validation.walk_forward_approval import (
    APPROVED,
    FAILED,
    WARNING,
    WalkForwardApproval,
    WalkForwardApprovalResult,
)
from research.validation.walk_forward_engine import WalkForwardResult
from research.validation.walk_forward_profile import WalkForwardProfile
from research.validation.walk_forward_report import WalkForwardReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class WalkForwardApprovalTest(unittest.TestCase):
    """Valida decisao institucional sem execucao operacional."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(WalkForwardApprovalResult))
        self.assertTrue(WalkForwardApprovalResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(WalkForwardApprovalResult)],
            ["status", "message", "report"],
        )

    def test_approval_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(WalkForwardApproval))
        self.assertTrue(WalkForwardApproval.__dataclass_params__.frozen)

    def test_retorna_approved_para_scores_saudaveis(self) -> None:
        report = self._report(
            stability_score=0.9,
            consistency_score=0.85,
            degradation_score=0.1,
        )

        result = WalkForwardApproval().evaluate(report)

        self.assertEqual(result.status, APPROVED)
        self.assertIs(result.report, report)

    def test_retorna_warning_em_limite_institucional(self) -> None:
        report = self._report(
            stability_score=0.7,
            consistency_score=0.8,
            degradation_score=0.2,
        )

        result = WalkForwardApproval().evaluate(report)

        self.assertEqual(result.status, WARNING)
        self.assertIs(result.report, report)

    def test_retorna_failed_quando_degradacao_excede_limite(self) -> None:
        report = self._report(
            stability_score=0.9,
            consistency_score=0.9,
            degradation_score=0.4,
        )

        result = WalkForwardApproval().evaluate(report)

        self.assertEqual(result.status, FAILED)
        self.assertIs(result.report, report)

    def test_retorna_failed_quando_estabilidade_ou_consistencia_sao_baixas(self) -> None:
        low_stability = WalkForwardApproval().evaluate(
            self._report(
                stability_score=0.6,
                consistency_score=0.9,
                degradation_score=0.1,
            )
        )
        low_consistency = WalkForwardApproval().evaluate(
            self._report(
                stability_score=0.9,
                consistency_score=0.6,
                degradation_score=0.1,
            )
        )

        self.assertEqual(low_stability.status, FAILED)
        self.assertEqual(low_consistency.status, FAILED)

    def test_result_e_imutavel(self) -> None:
        result = WalkForwardApproval().evaluate(
            self._report(
                stability_score=0.9,
                consistency_score=0.9,
                degradation_score=0.0,
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.status = FAILED

    def test_approval_nao_executa_pesquisa_replay_dashboard_ou_metricas(self) -> None:
        source = read_source(Path("research/validation/walk_forward_approval.py"))
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
        path = Path("research/validation/walk_forward_approval.py")
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
        stability_score: float,
        consistency_score: float,
        degradation_score: float,
    ) -> WalkForwardReport:
        analysis = WalkForwardAnalysisResult(
            stability_score=stability_score,
            degradation_score=degradation_score,
            consistency_score=consistency_score,
            validation_score=0.8,
        )
        return WalkForwardReport(
            walk_forward_result=self._walk_forward_result(),
            analysis_result=analysis,
            training_summary="Treino.",
            validation_summary="Validacao.",
            testing_summary="Teste.",
            degradation_score=degradation_score,
            stability_score=stability_score,
            consistency_score=consistency_score,
            execution_time=1.0,
            metadata={},
        )

    def _walk_forward_result(self) -> WalkForwardResult:
        experiments = (self._experiment("exp-1"),)
        return WalkForwardResult(
            campaign_id="campaign-alpha001-wf",
            profile=self._profile(),
            executed_experiments=experiments,
            training_experiments=experiments,
            validation_experiments=(),
            testing_experiments=(),
            rolling_window=1,
            minimum_samples=100,
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
            created_at="2026-06-28T06:20:00-03:00",
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


if __name__ == "__main__":
    unittest.main()
