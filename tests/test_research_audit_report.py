"""Testes do relatorio de auditoria do Research Lab."""

from dataclasses import FrozenInstanceError, is_dataclass
from datetime import datetime
from pathlib import Path
import unittest

from research.alpha001_benchmark_comparator import Alpha001BenchmarkResult
from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_advisor import Alpha001ResearchRecommendation
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_validator import Alpha001ResearchValidationResult
from research.alpha001_winrate_engine import Alpha001WinRateResult
from research.experiment_version_manager import ExperimentVersion
from research.research_audit_report import ResearchAuditReport
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage, ResearchStageResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ResearchAuditReportTest(unittest.TestCase):
    """Valida consolidacao auditavel de execucao e versao."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ResearchAuditReport))
        self.assertTrue(ResearchAuditReport.__dataclass_params__.frozen)

    def test_from_execution_consolida_campos_obrigatorios(self) -> None:
        execution = self._execution_result()
        version = self._experiment_version()

        report = ResearchAuditReport.from_execution(
            execution_result=execution,
            experiment_version=version,
            alpha_name="Alpha001",
            architecture_version="clean-architecture-v1",
        )

        self.assertEqual(report.experiment_id, "exp-001")
        self.assertEqual(report.version, 3)
        self.assertEqual(report.alpha_name, "Alpha001")
        self.assertEqual(report.architecture_version, "clean-architecture-v1")
        self.assertEqual(report.execution_date, execution.started_at)
        self.assertEqual(report.configuration_hash, "hash-001")
        self.assertEqual(report.pipeline_steps, ("Etapa concluida.",))
        self.assertEqual(report.execution_time, 2.0)
        self.assertEqual(report.final_status, "COMPLETED")
        self.assertEqual(
            report.recommendation,
            "APPROVED_FOR_MORE_RESEARCH",
        )

    def test_from_execution_usa_defaults_controlados(self) -> None:
        report = ResearchAuditReport.from_execution(
            execution_result=self._execution_result(started_at=None),
            experiment_version=self._experiment_version(),
        )

        self.assertEqual(report.alpha_name, "Alpha001")
        self.assertEqual(report.architecture_version, "research-lab-v1")
        self.assertEqual(report.execution_date, self._execution_result().finished_at)

    def test_from_execution_pode_ler_alpha_name_da_execucao(self) -> None:
        execution = self._execution_result()
        object.__setattr__(execution, "alpha_name", "AlphaXYZ")

        report = ResearchAuditReport.from_execution(
            execution_result=execution,
            experiment_version=self._experiment_version(),
        )

        self.assertEqual(report.alpha_name, "AlphaXYZ")

    def test_report_e_imutavel(self) -> None:
        report = ResearchAuditReport.from_execution(
            execution_result=self._execution_result(),
            experiment_version=self._experiment_version(),
        )

        with self.assertRaises(FrozenInstanceError):
            report.final_status = "FAILED"

    def test_report_nao_gera_exportacoes_ou_interface(self) -> None:
        source = read_source(Path("research/research_audit_report.py"))
        forbidden_fragments = (
            "pdf",
            "html",
            "dashboard",
            "streamlit",
            "open(",
            ".write(",
            "export",
            "render",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment.lower() in source.lower()
        ]

        self.assertEqual(leaked, [])

    def test_report_nao_executa_pipeline_ou_calculos(self) -> None:
        source = read_source(Path("research/research_audit_report.py"))
        forbidden_fragments = (
            ".run(",
            ".calculate(",
            ".compare(",
            ".validate(",
            ".recommend(",
            "sum(",
            "max(",
            "min(",
            " / ",
            " * ",
            " + ",
            " - ",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/research_audit_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "research.research_pipeline",
            "research.research_runner",
            "database",
            "sqlite3",
            "redis",
            "requests",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "write",
            "connect",
            "execute",
            "run",
            "calculate",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _experiment_version(self) -> ExperimentVersion:
        return ExperimentVersion(
            experiment_id="exp-001",
            version=3,
            created_at=datetime(2026, 6, 27, 20, 55, 0),
            configuration_hash="hash-001",
        )

    def _execution_result(
        self,
        *,
        started_at: datetime | None = datetime(2026, 6, 27, 21, 0, 0),
    ) -> ResearchExecutionResult:
        metrics = Alpha001MetricsResult(1, 1, 0, 0)
        profit = Alpha001ProfitResult(10.0, 5.0, 5.0)
        drawdown = Alpha001DrawdownResult((0.0, 5.0), 1.0, 1.0)
        win_rate = Alpha001WinRateResult(1, 0, 0, 1.0)
        profit_factor = Alpha001ProfitFactorResult(2.0)
        expectancy = Alpha001ExpectancyResult(10.0, 5.0, 2.0, 5.0)
        research_report = Alpha001ResearchResult(
            metrics=metrics,
            profit=profit,
            drawdown=drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
        )
        return ResearchExecutionResult(
            experiment=Alpha001ExperimentResult(
                total_candles=1,
                total_signals=1,
                total_buy=1,
                total_sell=0,
                total_wait=0,
                execution_time_ms=1.0,
                signals=(),
            ),
            metrics=metrics,
            profit=profit,
            drawdown=drawdown,
            win_rate=win_rate,
            profit_factor=profit_factor,
            expectancy=expectancy,
            benchmark=Alpha001BenchmarkResult(
                total_results=1,
                best_overall=research_report,
                best_total_trades=research_report,
                best_net_profit=research_report,
                best_max_drawdown=research_report,
                best_profit_factor=research_report,
                best_win_rate=research_report,
                best_expectancy=research_report,
                ranking=(research_report,),
            ),
            research_report=research_report,
            validation=Alpha001ResearchValidationResult(
                approved=True,
                status="APPROVED",
                reasons=("ok",),
                minimum_trades=1,
                minimum_profit_factor=1.0,
                maximum_drawdown=10.0,
                minimum_win_rate=0.1,
                real_trading_authorized=False,
            ),
            recommendation=Alpha001ResearchRecommendation(
                recommendation="APPROVED_FOR_MORE_RESEARCH",
                status="APPROVED",
                reasons=("ok",),
                real_trading_authorized=False,
            ),
            stage_results=(
                ResearchStageResult(
                    stage=ResearchStage.COMPLETED,
                    started_at=None,
                    finished_at=None,
                    duration=0.0,
                    success=True,
                    message="Etapa concluida.",
                ),
            ),
            started_at=started_at,
            finished_at=datetime(2026, 6, 27, 21, 0, 2),
            duration=2.0,
            status=ResearchStage.COMPLETED,
            errors=(),
        )


if __name__ == "__main__":
    unittest.main()
