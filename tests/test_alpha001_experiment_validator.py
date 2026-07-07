"""Testes do validador de experimentos da Alpha 001."""

import unittest

from domain.contracts.backtest_result import BacktestResult
from research.alpha001_experiment_validator import (
    Alpha001ExperimentValidator,
    Alpha001ValidationResult,
)


class Alpha001ExperimentValidatorTest(unittest.TestCase):
    """Valida avaliacao deterministica de BacktestResult."""

    def test_aprova_experimento_valido(self) -> None:
        """Metricas acima dos thresholds devem aprovar."""
        result = self._validator().validate(self._backtest_result())

        self.assertTrue(result.approved)
        self.assertEqual(result.status, "APPROVED")

    def test_rejeita_pouca_amostra(self) -> None:
        """Poucas operacoes devem retornar INSUFFICIENT_SAMPLE."""
        result = self._validator().validate(
            self._backtest_result(total_trades=10),
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "INSUFFICIENT_SAMPLE")

    def test_rejeita_profit_factor_baixo(self) -> None:
        """Profit factor baixo deve retornar LOW_PROFIT_FACTOR."""
        result = self._validator().validate(
            self._backtest_result(profit_factor=0.8),
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "LOW_PROFIT_FACTOR")

    def test_rejeita_drawdown_elevado(self) -> None:
        """Drawdown acima do limite deve retornar HIGH_DRAWDOWN."""
        result = self._validator().validate(
            self._backtest_result(drawdown=250.0),
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "HIGH_DRAWDOWN")

    def test_valida_status_rejected_para_outras_metricas_ruins(self) -> None:
        """Win rate ou lucro baixo devem rejeitar sem status especifico."""
        result = self._validator().validate(
            self._backtest_result(win_rate=0.1),
        )

        self.assertFalse(result.approved)
        self.assertEqual(result.status, "VALIDATION_REJECTED")

    def test_valida_reasons(self) -> None:
        """Reasons devem explicar as rejeicoes encontradas."""
        result = self._validator().validate(
            self._backtest_result(
                total_trades=10,
                profit_factor=0.8,
                drawdown=250.0,
                win_rate=0.1,
                total_profit=-10.0,
            ),
        )

        self.assertIn("Poucas operacoes para validar a Alpha 001.", result.reasons)
        self.assertIn(
            "Profit factor abaixo do minimo configurado.",
            result.reasons,
        )
        self.assertIn("Drawdown acima do limite configurado.", result.reasons)
        self.assertIn("Win rate abaixo do minimo configurado.", result.reasons)
        self.assertIn(
            "Resultado liquido abaixo do minimo configurado.",
            result.reasons,
        )

    def test_valida_metrics(self) -> None:
        """Metrics deve conter os campos exigidos pelo playbook."""
        result = self._validator().validate(self._backtest_result())

        self.assertEqual(result.metrics["total_trades"], 40)
        self.assertEqual(result.metrics["win_rate"], 0.6)
        self.assertEqual(result.metrics["profit_factor"], 1.5)
        self.assertEqual(result.metrics["max_drawdown_points"], 50.0)
        self.assertEqual(result.metrics["net_profit_points"], 100.0)

    def test_valida_retorno_alpha001_validation_result(self) -> None:
        """Validator deve retornar Alpha001ValidationResult."""
        result = self._validator().validate(self._backtest_result())

        self.assertIsInstance(result, Alpha001ValidationResult)

    def _validator(self) -> Alpha001ExperimentValidator:
        return Alpha001ExperimentValidator(
            minimum_total_trades=30,
            minimum_win_rate=0.4,
            minimum_profit_factor=1.2,
            maximum_drawdown_points=100.0,
            minimum_net_profit_points=0.0,
        )

    def _backtest_result(
        self,
        total_profit: float = 100.0,
        total_trades: int = 40,
        win_rate: float = 0.6,
        drawdown: float = 50.0,
        profit_factor: float = 1.5,
        sharpe: float = 1.0,
    ) -> BacktestResult:
        return BacktestResult(
            total_profit=total_profit,
            total_trades=total_trades,
            win_rate=win_rate,
            drawdown=drawdown,
            profit_factor=profit_factor,
            sharpe=sharpe,
        )


if __name__ == "__main__":
    unittest.main()
