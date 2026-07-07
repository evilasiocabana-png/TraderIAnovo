"""Testes do motor de Profit Factor da Alpha 001."""

import unittest

from research.alpha001_profit_engine import Alpha001ProfitResult
from research.alpha001_profit_factor_engine import (
    Alpha001ProfitFactorEngine,
    Alpha001ProfitFactorResult,
)


class Alpha001ProfitFactorEngineTest(unittest.TestCase):
    """Valida calculo isolado de Profit Factor."""

    def test_calculate_retorna_resultado_tipado(self) -> None:
        profit_result = Alpha001ProfitResult(
            gross_profit_points=120.0,
            gross_loss_points=40.0,
            net_profit_points=80.0,
        )

        result = Alpha001ProfitFactorEngine().calculate(profit_result)

        self.assertIsInstance(result, Alpha001ProfitFactorResult)

    def test_calculate_profit_factor(self) -> None:
        profit_result = Alpha001ProfitResult(
            gross_profit_points=120.0,
            gross_loss_points=40.0,
            net_profit_points=80.0,
        )

        result = Alpha001ProfitFactorEngine().calculate(profit_result)

        self.assertEqual(result.profit_factor, 3.0)

    def test_calculate_profit_factor_com_perda_negativa(self) -> None:
        profit_result = Alpha001ProfitResult(
            gross_profit_points=120.0,
            gross_loss_points=-40.0,
            net_profit_points=80.0,
        )

        result = Alpha001ProfitFactorEngine().calculate(profit_result)

        self.assertEqual(result.profit_factor, 3.0)

    def test_calculate_retorna_zero_quando_gross_loss_e_zero(self) -> None:
        profit_result = Alpha001ProfitResult(
            gross_profit_points=120.0,
            gross_loss_points=0.0,
            net_profit_points=120.0,
        )

        result = Alpha001ProfitFactorEngine().calculate(profit_result)

        self.assertEqual(result.profit_factor, 0.0)

    def test_nao_calcula_metricas_fora_do_escopo(self) -> None:
        profit_result = Alpha001ProfitResult(
            gross_profit_points=120.0,
            gross_loss_points=40.0,
            net_profit_points=80.0,
        )

        result = Alpha001ProfitFactorEngine().calculate(profit_result)

        forbidden_fields = (
            "gross_profit_points",
            "gross_loss_points",
            "net_profit_points",
            "win_rate",
            "drawdown",
            "max_drawdown_points",
            "expectancy",
            "sharpe",
            "sortino",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_camadas_proibidas(self) -> None:
        with open(
            "research/alpha001_profit_factor_engine.py",
            encoding="utf-8",
        ) as file:
            source = file.read()

        forbidden_fragments = (
            "Replay",
            "Dashboard",
            "DecisionPipeline",
            "EventBus",
            "Alpha001Config",
            "Alpha001Experiment",
            "Alpha001MetricsEngine",
            "Alpha001DrawdownEngine",
            "Alpha001WinRateEngine",
            "Broker",
            "MT5",
            "database",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)


if __name__ == "__main__":
    unittest.main()
