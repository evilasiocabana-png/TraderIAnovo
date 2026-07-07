"""Testes do relatorio oficial de pesquisa por familia de estrategia."""

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
from research.research_configuration_profile import ResearchConfigurationProfile
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage, ResearchStageResult
from research.research_timeframe_profile import INTRADAY_TIMEFRAME_PROFILE
from research.strategy_research_report import StrategyResearchReport
from strategies.strategy_profile import StrategyProfile
from tests.architecture_test_utils import calls_from, imports_from, read_source


class StrategyResearchReportTest(unittest.TestCase):
    """Valida consolidacao declarativa de pesquisas por familia."""

    def test_report_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(StrategyResearchReport))
        self.assertTrue(StrategyResearchReport.__dataclass_params__.frozen)

    def test_report_define_campos_obrigatorios(self) -> None:
        self.assertEqual(
            [field.name for field in fields(StrategyResearchReport)],
            [
                "strategy_profile",
                "research_configuration",
                "research_execution",
                "strategy_family",
                "timeframe",
                "total_experiments",
                "approved_experiments",
                "rejected_experiments",
                "reproducibility",
                "robustness",
                "validation_status",
            ],
        )

    def test_report_possui_type_hints_explicitos(self) -> None:
        annotations = StrategyResearchReport.__annotations__

        self.assertEqual(annotations["strategy_profile"], "StrategyProfile")
        self.assertEqual(
            annotations["research_configuration"],
            "ResearchConfigurationProfile",
        )
        self.assertEqual(annotations["research_execution"], "ResearchExecutionResult")
        self.assertEqual(annotations["strategy_family"], "str")
        self.assertEqual(annotations["timeframe"], "str")
        self.assertEqual(annotations["total_experiments"], "int")
        self.assertEqual(annotations["approved_experiments"], "int")
        self.assertEqual(annotations["rejected_experiments"], "int")
        self.assertEqual(annotations["reproducibility"], "str")
        self.assertEqual(annotations["robustness"], "str")
        self.assertEqual(annotations["validation_status"], "str")

    def test_report_agrega_componentes_tipados(self) -> None:
        report = self._report()

        self.assertIsInstance(report.strategy_profile, StrategyProfile)
        self.assertIsInstance(
            report.research_configuration,
            ResearchConfigurationProfile,
        )
        self.assertIsInstance(report.research_execution, ResearchExecutionResult)
        self.assertEqual(report.strategy_family, "INTRADAY")
        self.assertEqual(report.timeframe, "INTRADAY")
        self.assertEqual(report.total_experiments, 3)
        self.assertEqual(report.approved_experiments, 2)
        self.assertEqual(report.rejected_experiments, 1)
        self.assertEqual(report.reproducibility, "REPRODUCIBLE")
        self.assertEqual(report.robustness, "ROBUST")
        self.assertEqual(report.validation_status, "PASSED")

    def test_report_preserva_referencias_recebidas(self) -> None:
        strategy_profile = self._strategy_profile()
        research_configuration = self._research_configuration()
        research_execution = self._research_execution()

        report = StrategyResearchReport(
            strategy_profile=strategy_profile,
            research_configuration=research_configuration,
            research_execution=research_execution,
            strategy_family=strategy_profile.family,
            timeframe=research_configuration.timeframe_profile.timeframe,
            total_experiments=3,
            approved_experiments=2,
            rejected_experiments=1,
            reproducibility="REPRODUCIBLE",
            robustness="ROBUST",
            validation_status="PASSED",
        )

        self.assertIs(report.strategy_profile, strategy_profile)
        self.assertIs(report.research_configuration, research_configuration)
        self.assertIs(report.research_execution, research_execution)

    def test_report_e_imutavel(self) -> None:
        report = self._report()

        with self.assertRaises(FrozenInstanceError):
            report.validation_status = "FAILED"

    def test_report_nao_calcula_nem_gera_saida(self) -> None:
        source = read_source(Path("research/strategy_research_report.py"))
        forbidden_fragments = (
            "def ",
            "len(",
            "sum(",
            "max(",
            "min(",
            "round(",
            "Dashboard",
            "streamlit",
            "HTML",
            "PDF",
            "open(",
            "write(",
            ".run(",
            ".execute(",
            ".calculate(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_report_permanece_desacoplado_de_componentes_proibidos(self) -> None:
        path = Path("research/strategy_research_report.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "research.research_pipeline",
            "research.research_runner",
            "strategies.alpha001",
            "strategies.alpha002",
            "strategies.alpha003",
            "dashboard_app",
            "streamlit",
            "broker",
            "mt5",
            "MetaTrader5",
        }
        forbidden_calls = {
            "open",
            "run",
            "execute",
            "calculate",
            "validate",
            "generate_signal",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _report(self) -> StrategyResearchReport:
        strategy_profile = self._strategy_profile()
        research_configuration = self._research_configuration()
        return StrategyResearchReport(
            strategy_profile=strategy_profile,
            research_configuration=research_configuration,
            research_execution=self._research_execution(),
            strategy_family=strategy_profile.family,
            timeframe=research_configuration.timeframe_profile.timeframe,
            total_experiments=3,
            approved_experiments=2,
            rejected_experiments=1,
            reproducibility="REPRODUCIBLE",
            robustness="ROBUST",
            validation_status="PASSED",
        )

    def _strategy_profile(self) -> StrategyProfile:
        return StrategyProfile(
            strategy_id="Alpha003",
            name="Alpha003",
            family="INTRADAY",
            asset_class="FUTURES",
            supported_markets=("WDO",),
            supported_timeframes=("1m", "5m"),
            holding_period="INTRADAY",
            research_status="VALIDATION",
            version="1.0",
            metadata={"source": "unit-test"},
        )

    def _research_configuration(self) -> ResearchConfigurationProfile:
        return ResearchConfigurationProfile(
            strategy_family="INTRADAY",
            timeframe_profile=INTRADAY_TIMEFRAME_PROFILE,
            minimum_sample_size=30,
            required_metrics=("profit_factor", "win_rate", "drawdown"),
            validation_rules=("minimum_trades", "maximum_drawdown"),
            campaign_profile={"campaign_size": 30},
        )

    def _research_execution(self) -> ResearchExecutionResult:
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
            started_at=None,
            finished_at=None,
            duration=0.0,
            status=ResearchStage.COMPLETED,
            errors=(),
        )


if __name__ == "__main__":
    unittest.main()
