"""Testes do calculador reutilizavel de equity e drawdown."""

import unittest

from research.equity_drawdown import (
    EquityDrawdownCalculator,
    EquityDrawdownResult,
)


class EquityDrawdownCalculatorTest(unittest.TestCase):
    """Valida curva de equity, pico e drawdown maximo."""

    def test_retorna_curva_inicial_sem_trades(self) -> None:
        result = EquityDrawdownCalculator().calculate([])

        self.assertIsInstance(result, EquityDrawdownResult)
        self.assertEqual(result.equity_curve, (0.0,))
        self.assertEqual(result.peak_equity, 0.0)
        self.assertEqual(result.max_drawdown_points, 0.0)

    def test_curva_positiva_nao_tem_drawdown(self) -> None:
        result = EquityDrawdownCalculator().calculate([10.0, 5.0])

        self.assertEqual(result.equity_curve, (0.0, 10.0, 15.0))
        self.assertEqual(result.peak_equity, 15.0)
        self.assertEqual(result.max_drawdown_points, 0.0)

    def test_calcula_queda_apos_pico(self) -> None:
        result = EquityDrawdownCalculator().calculate([10.0, -3.0, -8.0, 4.0])

        self.assertEqual(result.equity_curve, (0.0, 10.0, 7.0, -1.0, 3.0))
        self.assertEqual(result.peak_equity, 10.0)
        self.assertEqual(result.max_drawdown_points, 11.0)


if __name__ == "__main__":
    unittest.main()
