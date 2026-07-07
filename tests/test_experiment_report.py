"""Testes do relatorio consolidado de experimentos."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
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
from research.experiment_management.experiment_definition import ExperimentDefinition
from research.experiment_management.experiment_monitor import ExperimentExecutionStatus
from research.experiment_management.experiment_report import ExperimentReport
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ExperimentReportTest(unittest.TestCase):
    """Valida consolidacao sem calculo ou geracao de saida."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ExperimentReport))
        self.assertTrue(ExperimentReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(ExperimentReport)]

        self.assertEqual(
            field_names,
            [
                "definition",
                "execution_status",
                "execution_result",
                "experiment_id",
                "alpha_id",
                "status",
                "execution_time",
                "success",
                "total_errors",
                "recommendation",
                "metadata",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = ExperimentReport.__annotations__

        self.assertEqual(annotations["definition"], "ExperimentDefinition")
        self.assertEqual(annotations["execution_status"], "ExperimentExecutionStatus")
        self.assertEqual(annotations["execution_result"], "ResearchExecutionResult")
        self.assertEqual(annotations["experiment_id"], "str")
        self.assertEqual(annotations["alpha_id"], "str")
        self.assertEqual(annotations["status"], "str")
        self.assertEqual(annotations["execution_time"], "float")
        self.assertEqual(annotations["success"], "bool")
        self.assertEqual(annotations["total_errors"], "int")
        self.assertEqual(annotations["recommendation"], "str")
        self.assertEqual(annotations["metadata"], "Mapping[str, object]")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.definition, ExperimentDefinition)
        self.assertIsInstance(report.execution_status, ExperimentExecutionStatus)
        self.assertIsInstance(report.execution_result, ResearchExecutionResult)
        self.assertEqual(report.experiment_id, "exp-alpha002-001")
        self.assertEqual(report.alpha_id, "Alpha002")
        self.assertEqual(report.status, "completed")
        self.assertEqual(report.execution_time, 12.5)
        self.assertTrue(report.success)
        self.assertEqual(report.total_errors, 0)
        self.assertEqual(report.recommendation, "APPROVED_FOR_MORE_RESEARCH")
        self.assertEqual(report.metadata["source"], "test")

    def test_report_preserva_referencias_recebidas(self) -> None:
        definition = self._definition()
        status = self._status()
        execution_result = self._execution_result()
        metadata = {"source": "test"}

        report = ExperimentReport(
            definition=definition,
            execution_status=status,
            execution_result=execution_result,
            experiment_id="exp-alpha002-001",
            alpha_id="Alpha002",
            status="completed",
            execution_time=12.5,
            success=True,
            total_errors=0,
            recommendation="APPROVED_FOR_MORE_RESEARCH",
            metadata=metadata,
        )

        self.assertIs(report.definition, definition)
        self.assertIs(report.execution_status, status)
        self.assertIs(report.execution_result, execution_result)
        self.assertIs(report.metadata, metadata)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.success = False

    def test_report_nao_calcula_ou_gera_saida(self) -> None:
        source = read_source(
            Path("research/experiment_management/experiment_report.py")
        )
        forbidden_fragments = (
            "def ",
            "sum(",
            "len(",
            "round(",
            "Dashboard",
            "streamlit",
            "HTML",
            "PDF",
            "open(",
            "write(",
            "persist",
            "ResearchRunner",
            "ResearchPipeline",
            "ReplayEngine",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/experiment_management/experiment_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "alpha",
            "strategies",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
            "paper",
            "database",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "next_candle",
            "generate_signal",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> ExperimentReport:
        return ExperimentReport(
            definition=self._definition(),
            execution_status=self._status(),
            execution_result=self._execution_result(),
            experiment_id="exp-alpha002-001",
            alpha_id="Alpha002",
            status="completed",
            execution_time=12.5,
            success=True,
            total_errors=0,
            recommendation="APPROVED_FOR_MORE_RESEARCH",
            metadata={"source": "test"},
        )

    def _definition(self) -> ExperimentDefinition:
        return ExperimentDefinition(
            experiment_id="exp-alpha002-001",
            alpha_id="Alpha002",
            alpha_version="0.1.0",
            configuration_version="cfg-001",
            replay_period="2026-01-01/2026-01-31",
            dataset="WDO-1m-2026-01",
            status="PENDING",
            priority=1,
            created_at="2026-06-27T23:40:00-03:00",
            metadata={"source": "definition"},
        )

    def _status(self) -> ExperimentExecutionStatus:
        return ExperimentExecutionStatus(
            experiment_id="exp-alpha002-001",
            status="completed",
            started_at=datetime(2026, 6, 27, 10, 0, 0),
            finished_at=datetime(2026, 6, 27, 10, 0, 12),
            execution_time=12.5,
            error_message="",
        )

    def _execution_result(self) -> ResearchExecutionResult:
        research = self._research_result()
        return ResearchExecutionResult(
            experiment=Alpha001ExperimentResult(0, 0, 0, 0, 0, 0.0, ()),
            metrics=research.metrics,
            profit=research.profit,
            drawdown=research.drawdown,
            win_rate=research.win_rate,
            profit_factor=research.profit_factor,
            expectancy=research.expectancy,
            benchmark=Alpha001BenchmarkResult(0, None, None, None, None, None, None, None, ()),
            research_report=research,
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
            stage_results=(),
            started_at=datetime(2026, 6, 27, 10, 0, 0),
            finished_at=datetime(2026, 6, 27, 10, 0, 12),
            duration=12.5,
            status=ResearchStage.COMPLETED,
            errors=(),
        )

    def _research_result(self) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(0, 0, 0, 0),
            profit=Alpha001ProfitResult(0.0, 0.0, 0.0),
            drawdown=Alpha001DrawdownResult((0.0,), 0.0, 0.0),
            win_rate=Alpha001WinRateResult(0, 0, 0, 0.0),
            profit_factor=Alpha001ProfitFactorResult(0.0),
            expectancy=Alpha001ExpectancyResult(0.0, 0.0, 0.0, 0.0),
        )


if __name__ == "__main__":
    unittest.main()
