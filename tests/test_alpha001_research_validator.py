"""Testes do validador de pesquisa da Alpha 001."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from research.alpha001_drawdown_engine import Alpha001DrawdownResult
from research.alpha001_expectancy_engine import Alpha001ExpectancyResult
from research.alpha001_metrics_engine import Alpha001MetricsResult
from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import Alpha001ProfitFactorResult
from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha001_research_validator import (
    Alpha001ResearchValidationResult,
    Alpha001ResearchValidator,
)
from research.alpha001_winrate_engine import Alpha001WinRateResult
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha001ResearchValidatorTest(unittest.TestCase):
    """Valida regras estatisticas sobre Alpha001ResearchResult."""

    def test_validation_result_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha001ResearchValidationResult))
        self.assertTrue(Alpha001ResearchValidationResult.__dataclass_params__.frozen)

    def test_aprova_resultado_estatistico_valido(self) -> None:
        result = self._validator().validate(self._research_result())

        self.assertTrue(result.approved)
        self.assertEqual(result.status, "APPROVED")
        self.assertEqual(
            result.reasons,
            ("Pesquisa Alpha001 atende aos criterios estatisticos.",),
        )
        self.assertFalse(result.real_trading_authorized)

    def test_rejeita_quantidade_minima_de_trades(self) -> None:
        result = self._validator().validate(
            self._research_result(total_trades=10),
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "INSUFFICIENT_TRADES")
        self.assertIn(
            "Quantidade de trades abaixo do minimo configurado.",
            result.reasons,
        )

    def test_rejeita_profit_factor_minimo(self) -> None:
        result = self._validator().validate(
            self._research_result(profit_factor=1.1),
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "LOW_PROFIT_FACTOR")
        self.assertIn(
            "Profit factor abaixo do minimo configurado.",
            result.reasons,
        )

    def test_rejeita_drawdown_maximo(self) -> None:
        result = self._validator().validate(
            self._research_result(max_drawdown=101.0),
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "HIGH_DRAWDOWN")
        self.assertIn(
            "Drawdown acima do maximo configurado.",
            result.reasons,
        )

    def test_rejeita_win_rate_minimo(self) -> None:
        result = self._validator().validate(
            self._research_result(win_rate=0.39),
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "LOW_WIN_RATE")
        self.assertIn(
            "Win rate abaixo do minimo configurado.",
            result.reasons,
        )

    def test_preserva_thresholds_no_resultado(self) -> None:
        result = self._validator().validate(self._research_result())

        self.assertEqual(result.minimum_trades, 30)
        self.assertEqual(result.minimum_profit_factor, 1.2)
        self.assertEqual(result.maximum_drawdown, 100.0)
        self.assertEqual(result.minimum_win_rate, 0.4)

    def test_resultado_e_imutavel(self) -> None:
        result = self._validator().validate(self._research_result())

        with self.assertRaises(FrozenInstanceError):
            result.status = "CHANGED"

    def test_nao_autoriza_operacao_real_mesmo_quando_aprovado(self) -> None:
        result = self._validator().validate(self._research_result())

        self.assertTrue(result.approved)
        self.assertFalse(result.real_trading_authorized)

    def test_validator_nao_importa_camadas_operacionais(self) -> None:
        path = Path("research/alpha001_research_validator.py")
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
        }
        forbidden_calls = {
            "calculate",
            "run",
            "open",
            "write",
            "order_send",
            "execute_order",
            "send_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def test_validator_nao_altera_engines_ou_research_report(self) -> None:
        source = read_source(Path("research/alpha001_research_validator.py"))
        forbidden_fragments = (
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "ResearchReport(",
            ".calculate(",
            "ReplayEngine",
            "Domain",
        )
        leaked = [
            fragment for fragment in forbidden_fragments
            if fragment in source
        ]

        self.assertEqual(leaked, [])

    def _validator(self) -> Alpha001ResearchValidator:
        return Alpha001ResearchValidator(
            minimum_trades=30,
            minimum_profit_factor=1.2,
            maximum_drawdown=100.0,
            minimum_win_rate=0.4,
        )

    def _research_result(
        self,
        total_trades: int = 40,
        profit_factor: float = 1.5,
        max_drawdown: float = 50.0,
        win_rate: float = 0.6,
    ) -> Alpha001ResearchResult:
        return Alpha001ResearchResult(
            metrics=Alpha001MetricsResult(
                total_trades=total_trades,
                total_buy=total_trades,
                total_sell=0,
                total_wait=0,
            ),
            profit=Alpha001ProfitResult(
                gross_profit_points=150.0,
                gross_loss_points=100.0,
                net_profit_points=50.0,
            ),
            drawdown=Alpha001DrawdownResult(
                equity_curve=(0.0, 50.0),
                max_drawdown_points=max_drawdown,
                max_drawdown_percent=10.0,
            ),
            win_rate=Alpha001WinRateResult(
                winning_trades=24,
                losing_trades=16,
                breakeven_trades=0,
                win_rate=win_rate,
            ),
            profit_factor=Alpha001ProfitFactorResult(
                profit_factor=profit_factor,
            ),
            expectancy=Alpha001ExpectancyResult(
                average_win=10.0,
                average_loss=5.0,
                payoff_ratio=2.0,
                expectancy=4.0,
            ),
        )


if __name__ == "__main__":
    unittest.main()
