"""Testes do analisador agregado de campanhas."""

from dataclasses import FrozenInstanceError, fields, is_dataclass
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
from research.campaigns.campaign_analyzer import (
    CampaignAnalysisResult,
    CampaignAnalyzer,
)
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage, ResearchStageResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class CampaignAnalyzerTest(unittest.TestCase):
    """Valida agregacao sem recalculo de metricas individuais."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(CampaignAnalysisResult))
        self.assertTrue(CampaignAnalysisResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(CampaignAnalysisResult)]

        self.assertEqual(
            field_names,
            [
                "total_experiments",
                "successful_experiments",
                "failed_experiments",
                "approved_experiments",
                "rejected_experiments",
                "average_execution_time",
                "campaign_success_rate",
            ],
        )

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = CampaignAnalysisResult.__annotations__

        self.assertEqual(annotations["total_experiments"], "int")
        self.assertEqual(annotations["successful_experiments"], "int")
        self.assertEqual(annotations["failed_experiments"], "int")
        self.assertEqual(annotations["approved_experiments"], "int")
        self.assertEqual(annotations["rejected_experiments"], "int")
        self.assertEqual(annotations["average_execution_time"], "float")
        self.assertEqual(annotations["campaign_success_rate"], "float")

    def test_analyzer_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(CampaignAnalyzer))
        self.assertTrue(CampaignAnalyzer.__dataclass_params__.frozen)

    def test_analyzer_calcula_agregados_da_campanha(self) -> None:
        results = (
            self._execution_result(
                status=ResearchStage.COMPLETED,
                duration=2.0,
                approved=True,
                recommendation="APPROVED_FOR_MORE_RESEARCH",
            ),
            self._execution_result(
                status=ResearchStage.FAILED,
                duration=4.0,
                approved=False,
                recommendation="REJECTED",
                errors=("falha",),
            ),
            self._execution_result(
                status=ResearchStage.COMPLETED,
                duration=6.0,
                approved=False,
                recommendation="INSUFFICIENT_SAMPLE",
            ),
        )

        analysis = CampaignAnalyzer().analyze(results)

        self.assertEqual(analysis.total_experiments, 3)
        self.assertEqual(analysis.successful_experiments, 2)
        self.assertEqual(analysis.failed_experiments, 1)
        self.assertEqual(analysis.approved_experiments, 1)
        self.assertEqual(analysis.rejected_experiments, 1)
        self.assertEqual(analysis.average_execution_time, 4.0)
        self.assertEqual(analysis.campaign_success_rate, 2 / 3)

    def test_analyzer_retorna_zero_para_colecao_vazia(self) -> None:
        analysis = CampaignAnalyzer().analyze(())

        self.assertEqual(analysis.total_experiments, 0)
        self.assertEqual(analysis.successful_experiments, 0)
        self.assertEqual(analysis.failed_experiments, 0)
        self.assertEqual(analysis.approved_experiments, 0)
        self.assertEqual(analysis.rejected_experiments, 0)
        self.assertEqual(analysis.average_execution_time, 0.0)
        self.assertEqual(analysis.campaign_success_rate, 0.0)

    def test_analyzer_considera_erro_como_falha_mesmo_status_completed(self) -> None:
        analysis = CampaignAnalyzer().analyze(
            (
                self._execution_result(
                    status=ResearchStage.COMPLETED,
                    errors=("erro",),
                ),
            )
        )

        self.assertEqual(analysis.successful_experiments, 0)
        self.assertEqual(analysis.failed_experiments, 1)

    def test_analyzer_nao_altera_resultados_recebidos(self) -> None:
        result = self._execution_result(duration=3.0)

        CampaignAnalyzer().analyze((result,))

        self.assertEqual(result.duration, 3.0)
        self.assertEqual(result.status, ResearchStage.COMPLETED)

    def test_result_e_imutavel(self) -> None:
        analysis = CampaignAnalyzer().analyze(())

        with self.assertRaises(FrozenInstanceError):
            analysis.total_experiments = 10

    def test_analyzer_nao_recalcula_metricas_individuais_ou_acessa_camadas(self) -> None:
        source = read_source(Path("research/campaigns/campaign_analyzer.py"))
        forbidden_fragments = (
            "Dashboard",
            "streamlit",
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
            ".calculate(",
            ".validate(",
            ".next_candle(",
            ".generate_signal(",
            "gross_profit",
            "drawdown",
            "win_rate",
            "profit_factor",
            "expectancy",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_analyzer_permanece_desacoplado_de_operacao(self) -> None:
        path = Path("research/campaigns/campaign_analyzer.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_runner",
            "research.research_pipeline",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
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

    def _execution_result(
        self,
        *,
        status: ResearchStage = ResearchStage.COMPLETED,
        duration: float = 1.0,
        approved: bool = True,
        recommendation: str = "APPROVED_FOR_MORE_RESEARCH",
        errors: tuple[str, ...] = (),
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
        benchmark = Alpha001BenchmarkResult(
            total_results=1,
            best_overall=research_report,
            best_total_trades=research_report,
            best_net_profit=research_report,
            best_max_drawdown=research_report,
            best_profit_factor=research_report,
            best_win_rate=research_report,
            best_expectancy=research_report,
            ranking=(research_report,),
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
            benchmark=benchmark,
            research_report=research_report,
            validation=Alpha001ResearchValidationResult(
                approved=approved,
                status="APPROVED" if approved else "REJECTED",
                reasons=("ok",) if approved else ("rejected",),
                minimum_trades=1,
                minimum_profit_factor=1.0,
                maximum_drawdown=10.0,
                minimum_win_rate=0.1,
                real_trading_authorized=False,
            ),
            recommendation=Alpha001ResearchRecommendation(
                recommendation=recommendation,
                status="APPROVED" if approved else "REJECTED",
                reasons=("ok",),
                real_trading_authorized=False,
            ),
            stage_results=(
                ResearchStageResult(
                    stage=status,
                    started_at=None,
                    finished_at=None,
                    duration=duration,
                    success=status == ResearchStage.COMPLETED and not errors,
                    message="Etapa analisada.",
                ),
            ),
            started_at=None,
            finished_at=None,
            duration=duration,
            status=status,
            errors=errors,
        )


if __name__ == "__main__":
    unittest.main()
