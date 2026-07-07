"""Testes do simulador teorico de alocacao."""

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
from research.portfolio.allocation_simulation import (
    AllocationSimulation,
    AllocationSimulationResult,
)
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.research_execution_result import ResearchExecutionResult
from research.research_stage import ResearchStage, ResearchStageResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class AllocationSimulationTest(unittest.TestCase):
    """Valida simulacao sem executar novas estrategias ou replay."""

    def test_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AllocationSimulationResult))
        self.assertTrue(AllocationSimulationResult.__dataclass_params__.frozen)

    def test_result_define_campos_obrigatorios(self) -> None:
        field_names = [field.name for field in fields(AllocationSimulationResult)]

        self.assertEqual(
            field_names,
            [
                "portfolio_equity_curve",
                "portfolio_return",
                "portfolio_drawdown",
                "portfolio_volatility",
            ],
        )

    def test_result_possui_type_hints_explicitos(self) -> None:
        annotations = AllocationSimulationResult.__annotations__

        self.assertEqual(annotations["portfolio_equity_curve"], "tuple[float, ...]")
        self.assertEqual(annotations["portfolio_return"], "float")
        self.assertEqual(annotations["portfolio_drawdown"], "float")
        self.assertEqual(annotations["portfolio_volatility"], "float")

    def test_simulation_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(AllocationSimulation))
        self.assertTrue(AllocationSimulation.__dataclass_params__.frozen)

    def test_simulation_combina_curvas_de_equity(self) -> None:
        result = AllocationSimulation().simulate(
            self._weights(),
            (
                self._execution_result("Alpha001", (0.0, 10.0, 5.0, 15.0)),
                self._execution_result("Alpha002", (0.0, -5.0, 5.0, 10.0)),
            ),
        )

        self.assertEqual(result.portfolio_equity_curve, (0.0, 3.0, 3.0, 8.0))
        self.assertEqual(result.portfolio_return, 8.0)
        self.assertEqual(result.portfolio_drawdown, 0.0)
        self.assertAlmostEqual(result.portfolio_volatility, 2.0548046676563256)

    def test_simulation_calcula_drawdown_do_portfolio(self) -> None:
        result = AllocationSimulation().simulate(
            self._weights(),
            (
                self._execution_result("Alpha001", (0.0, 10.0, -10.0)),
                self._execution_result("Alpha002", (0.0, 0.0, 0.0)),
            ),
        )

        self.assertEqual(result.portfolio_equity_curve, (0.0, 4.0, -4.0))
        self.assertEqual(result.portfolio_drawdown, 8.0)

    def test_simulation_retorna_zero_sem_curvas(self) -> None:
        result = AllocationSimulation().simulate(
            AllocationWeightResult(equal_weight={}, risk_adjusted_weight={}),
            (),
        )

        self.assertEqual(result.portfolio_equity_curve, ())
        self.assertEqual(result.portfolio_return, 0.0)
        self.assertEqual(result.portfolio_drawdown, 0.0)
        self.assertEqual(result.portfolio_volatility, 0.0)

    def test_simulation_mantem_ultimo_valor_quando_curvas_tem_tamanhos_diferentes(self) -> None:
        result = AllocationSimulation().simulate(
            self._weights(),
            (
                self._execution_result("Alpha001", (0.0, 10.0, 20.0)),
                self._execution_result("Alpha002", (0.0, 10.0)),
            ),
        )

        self.assertEqual(result.portfolio_equity_curve, (0.0, 6.0, 10.0))

    def test_simulation_nao_modifica_pesos_ou_resultados(self) -> None:
        weights = self._weights()
        execution = self._execution_result("Alpha001", (0.0, 10.0))

        AllocationSimulation().simulate(weights, (execution,))

        self.assertEqual(weights.risk_adjusted_weight, {"Alpha001": 0.4, "Alpha002": 0.2})
        self.assertEqual(execution.drawdown.equity_curve, (0.0, 10.0))

    def test_result_e_imutavel(self) -> None:
        result = AllocationSimulation().simulate(self._weights(), ())

        with self.assertRaises(FrozenInstanceError):
            result.portfolio_return = 1.0

    def test_simulation_nao_executa_estrategias_replay_ou_runner(self) -> None:
        source = read_source(Path("research/portfolio/allocation_simulation.py"))
        forbidden_fragments = (
            "ReplayEngine",
            "ResearchRunner",
            "ResearchPipeline",
            "Strategy",
            "generate_signal",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            ".run(",
            ".execute(",
            ".next_candle(",
            ".generate_signal(",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_simulation_permanece_desacoplada_de_operacao(self) -> None:
        path = Path("research/portfolio/allocation_simulation.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "strategies",
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

    def _weights(self) -> AllocationWeightResult:
        return AllocationWeightResult(
            equal_weight={"Alpha001": 0.3, "Alpha002": 0.3},
            risk_adjusted_weight={"Alpha001": 0.4, "Alpha002": 0.2},
        )

    def _execution_result(
        self,
        alpha_id: str,
        equity_curve: tuple[float, ...],
    ) -> ResearchExecutionResult:
        metrics = Alpha001MetricsResult(1, 1, 0, 0)
        profit = Alpha001ProfitResult(10.0, 5.0, 5.0)
        drawdown = Alpha001DrawdownResult(equity_curve, 0.0, 0.0)
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
        result = ResearchExecutionResult(
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
                    duration=1.0,
                    success=True,
                    message="Etapa simulada.",
                ),
            ),
            started_at=None,
            finished_at=None,
            duration=1.0,
            status=ResearchStage.COMPLETED,
            errors=(),
        )
        object.__setattr__(result, "alpha_id", alpha_id)
        return result


if __name__ == "__main__":
    unittest.main()
