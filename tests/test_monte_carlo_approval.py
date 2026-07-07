"""Testes do gate oficial de aprovacao Monte Carlo."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
import unittest

from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.validation.monte_carlo.monte_carlo_analyzer import (
    MonteCarloAnalysisResult,
)
from research.validation.monte_carlo.monte_carlo_approval import (
    APPROVED,
    FAILED,
    WARNING,
    MonteCarloApproval,
    MonteCarloApprovalResult,
)
from research.validation.monte_carlo.monte_carlo_engine import MonteCarloResult
from research.validation.monte_carlo.monte_carlo_profile import MonteCarloProfile
from research.validation.monte_carlo.monte_carlo_report import MonteCarloReport
from tests.architecture_test_utils import calls_from, imports_from, read_source


class MonteCarloApprovalTest(unittest.TestCase):
    """Valida decisao institucional sem execucao operacional."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MonteCarloApprovalResult))
        self.assertTrue(MonteCarloApprovalResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(MonteCarloApprovalResult)],
            ["status", "message", "report"],
        )

    def test_approval_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(MonteCarloApproval))
        self.assertTrue(MonteCarloApproval.__dataclass_params__.frozen)

    def test_retorna_approved_para_resultado_robusto(self) -> None:
        report = self._report(
            robustness_score=0.9,
            average_return=10.0,
            expected_drawdown=0.1,
        )

        result = MonteCarloApproval().evaluate(report)

        self.assertEqual(result.status, APPROVED)
        self.assertIs(result.report, report)

    def test_retorna_warning_em_limite_institucional(self) -> None:
        report = self._report(
            robustness_score=0.7,
            average_return=10.0,
            expected_drawdown=0.1,
        )

        result = MonteCarloApproval().evaluate(report)

        self.assertEqual(result.status, WARNING)
        self.assertIs(result.report, report)

    def test_retorna_failed_quando_robustez_e_baixa(self) -> None:
        report = self._report(
            robustness_score=0.6,
            average_return=10.0,
            expected_drawdown=0.1,
        )

        result = MonteCarloApproval().evaluate(report)

        self.assertEqual(result.status, FAILED)

    def test_retorna_failed_quando_retorno_ou_drawdown_falham(self) -> None:
        negative_return = MonteCarloApproval().evaluate(
            self._report(
                robustness_score=0.9,
                average_return=-1.0,
                expected_drawdown=0.1,
            )
        )
        high_drawdown = MonteCarloApproval().evaluate(
            self._report(
                robustness_score=0.9,
                average_return=10.0,
                expected_drawdown=0.4,
            )
        )

        self.assertEqual(negative_return.status, FAILED)
        self.assertEqual(high_drawdown.status, FAILED)

    def test_result_e_imutavel(self) -> None:
        result = MonteCarloApproval().evaluate(
            self._report(
                robustness_score=0.9,
                average_return=10.0,
                expected_drawdown=0.1,
            )
        )

        with self.assertRaises(FrozenInstanceError):
            result.status = FAILED

    def test_approval_nao_executa_pesquisa_replay_dashboard_ou_metricas(self) -> None:
        source = read_source(
            Path("research/validation/monte_carlo/monte_carlo_approval.py")
        )
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
        path = Path("research/validation/monte_carlo/monte_carlo_approval.py")
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
        robustness_score: float,
        average_return: float,
        expected_drawdown: float,
    ) -> MonteCarloReport:
        analysis = MonteCarloAnalysisResult(
            average_return=average_return,
            worst_case_return=-5.0,
            best_case_return=20.0,
            expected_drawdown=expected_drawdown,
            robustness_score=robustness_score,
        )
        return MonteCarloReport(
            monte_carlo_result=self._monte_carlo_result(),
            analysis_result=analysis,
            simulations=3,
            confidence_level=0.95,
            average_return=average_return,
            worst_case_return=analysis.worst_case_return,
            best_case_return=analysis.best_case_return,
            expected_drawdown=expected_drawdown,
            robustness_score=robustness_score,
            execution_time=1.0,
            metadata={},
        )

    def _monte_carlo_result(self) -> MonteCarloResult:
        return MonteCarloResult(
            campaign_id="campaign-alpha001-mc",
            profile=self._profile(),
            executed_experiments=(self._experiment(),),
            total_simulations=3,
            simulated_returns=(10.0, 20.0, -5.0),
            simulated_drawdowns=(0.1, 0.2, 0.3),
            average_return=25.0 / 3.0,
            worst_return=-5.0,
            best_return=20.0,
            confidence_level=0.95,
        )

    def _profile(self) -> MonteCarloProfile:
        return MonteCarloProfile(
            profile_id="monte-carlo-baseline-001",
            simulations=3,
            random_seed=42,
            confidence_level=0.95,
            resampling_method="REORDER_TRADES",
            metadata={},
        )

    def _experiment(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="experiment-alpha001-mc",
            alpha_id="Alpha001",
            alpha_version="1.0",
            configuration_version="cfg-001",
            replay_period="2026-01",
            dataset="WDO-1m",
            status="COMPLETED",
            priority=1,
            created_at="2026-06-28T07:20:00-03:00",
            metadata={},
        )


if __name__ == "__main__":
    unittest.main()
