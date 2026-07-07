"""Testes do motor de qualidade de amostra Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_sample_quality_engine import (
    Alpha001SampleQualityEngine,
    Alpha001SampleQualityResult,
)
from research.alpha001_winrate_engine import Alpha001WinRateResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001SampleQualityEngineTest(unittest.TestCase):
    """Valida avaliacao estrutural da amostra da Alpha001."""

    def test_resultado_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001SampleQualityResult))
        self.assertTrue(Alpha001SampleQualityResult.__dataclass_params__.frozen)

    def test_calcula_qualidade_de_amostra_agregada(self) -> None:
        result = Alpha001SampleQualityEngine().calculate(
            self._research_result(total_trades=12),
        )

        self.assertEqual(result.total_trading_days, 1)
        self.assertEqual(result.average_trades_per_day, 12.0)
        self.assertEqual(result.maximum_trades_per_day, 12)
        self.assertEqual(result.minimum_trades_per_day, 12)
        self.assertTrue(result.sufficient_sample)

    def test_amostra_sem_trades_retorna_zero_e_insuficiente(self) -> None:
        result = Alpha001SampleQualityEngine().calculate(
            self._research_result(total_trades=0),
        )

        self.assertEqual(result.total_trading_days, 0)
        self.assertEqual(result.average_trades_per_day, 0.0)
        self.assertEqual(result.maximum_trades_per_day, 0)
        self.assertEqual(result.minimum_trades_per_day, 0)
        self.assertFalse(result.sufficient_sample)

    def test_limites_configuraveis_definem_sufficient_sample(self) -> None:
        result = Alpha001SampleQualityEngine(
            minimum_trading_days=2,
            minimum_average_trades_per_day=1.0,
        ).calculate(self._research_result(total_trades=12))

        self.assertFalse(result.sufficient_sample)

    def test_resultado_e_imutavel(self) -> None:
        result = Alpha001SampleQualityEngine().calculate(
            self._research_result(total_trades=12),
        )

        with self.assertRaises(FrozenInstanceError):
            result.total_trading_days = 2

    def test_engine_nao_calcula_metricas_financeiras(self) -> None:
        source = read_source(Path("research/alpha001_sample_quality_engine.py"))
        forbidden_fragments = (
            "gross_profit",
            "gross_loss",
            "net_profit",
            "drawdown",
            "profit_factor",
            "win_rate",
            "expectancy",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001WinRateEngine",
            "Alpha001ExpectancyEngine",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def test_engine_permanece_desacoplado_de_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_sample_quality_engine.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "domain",
            "replay",
            "application.replay_service",
            "dashboard_app",
            "streamlit",
            "core.decision_pipeline",
            "core.event_bus",
            "broker",
            "mt5",
            "MetaTrader5",
            "alpha",
        }
        forbidden_calls = {
            "open",
            "write",
            "run",
            "generate_signal",
            "order_send",
            "execute_order",
            "next_candle",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_engine_nao_altera_research_report_ou_engines_existentes(self) -> None:
        source = read_source(Path("research/alpha001_sample_quality_engine.py"))

        self.assertIn("Alpha001ResearchResult", source)
        self.assertNotIn("Alpha001ResearchResult(", source)
        self.assertNotIn("ResearchReport(", source)
        self.assertNotIn(".calculate(", source)

    def _research_result(self, total_trades: int) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=total_trades,
                total_buy=total_trades,
                total_sell=0,
                total_wait=0,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=0.0,
                gross_loss_points=0.0,
                net_profit_points=0.0,
            ),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0,),
                max_drawdown_points=0.0,
                max_drawdown_percent=0.0,
            ),
            win_rate=Alpha001WinRateResult(
                winning_trades=0,
                losing_trades=0,
                breakeven_trades=0,
                win_rate=0.0,
            ),
            profit_factor=Alpha001ProfitFactorResult(profit_factor=0.0),
            expectancy=Alpha001ExpectancyResult(
                average_win=0.0,
                average_loss=0.0,
                payoff_ratio=0.0,
                expectancy=0.0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
