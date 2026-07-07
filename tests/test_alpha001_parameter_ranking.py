"""Testes do ranking de parametros da Alpha 001."""

import unittest

from research.alpha001_parameter_ranking import Alpha001ParameterRanking
from research.alpha001_parameter_sweep import (
    Alpha001ParameterSet,
    Alpha001ParameterSweepResult,
)


class Alpha001ParameterRankingTest(unittest.TestCase):
    """Valida ordenacao de resultados existentes da Alpha 001."""

    def test_prioriza_approved(self) -> None:
        """Resultados aprovados devem vir antes dos rejeitados."""
        rejected = self._result("LOW_PROFIT_FACTOR", 10.0, 0.0, 500.0, 10)
        approved = self._result("APPROVED", 1.0, 10.0, 100.0, 1)

        ranked = Alpha001ParameterRanking().rank([rejected, approved])

        self.assertIs(ranked[0], approved)

    def test_ordena_por_profit_factor(self) -> None:
        """Maior profit factor deve vencer entre aprovados."""
        weak = self._result("APPROVED", 1.5, 10.0, 100.0, 10)
        strong = self._result("APPROVED", 2.0, 10.0, 100.0, 10)

        ranked = Alpha001ParameterRanking().rank([weak, strong])

        self.assertIs(ranked[0], strong)

    def test_desempata_por_drawdown(self) -> None:
        """Menor drawdown deve vencer quando profit factor empata."""
        high_drawdown = self._result("APPROVED", 2.0, 20.0, 100.0, 10)
        low_drawdown = self._result("APPROVED", 2.0, 5.0, 100.0, 10)

        ranked = Alpha001ParameterRanking().rank([high_drawdown, low_drawdown])

        self.assertIs(ranked[0], low_drawdown)

    def test_desempata_por_lucro_liquido(self) -> None:
        """Maior lucro liquido deve vencer apos drawdown."""
        low_profit = self._result("APPROVED", 2.0, 5.0, 80.0, 10)
        high_profit = self._result("APPROVED", 2.0, 5.0, 120.0, 10)

        ranked = Alpha001ParameterRanking().rank([low_profit, high_profit])

        self.assertIs(ranked[0], high_profit)

    def test_desempata_por_total_trades(self) -> None:
        """Maior amostra deve vencer apos lucro liquido."""
        few_trades = self._result("APPROVED", 2.0, 5.0, 120.0, 10)
        many_trades = self._result("APPROVED", 2.0, 5.0, 120.0, 20)

        ranked = Alpha001ParameterRanking().rank([few_trades, many_trades])

        self.assertIs(ranked[0], many_trades)

    def test_rejeitados_ficam_no_fim(self) -> None:
        """Rejeitados devem permanecer depois dos aprovados."""
        approved = self._result("APPROVED", 1.0, 50.0, -100.0, 1)
        rejected = self._result("HIGH_DRAWDOWN", 10.0, 0.0, 1000.0, 100)

        ranked = Alpha001ParameterRanking().rank([rejected, approved])

        self.assertIs(ranked[-1], rejected)

    def _result(
        self,
        status: str,
        profit_factor: float,
        drawdown: float,
        net_profit: float,
        total_trades: int,
    ) -> Alpha001ParameterSweepResult:
        return Alpha001ParameterSweepResult(
            parameters=Alpha001ParameterSet(15, 20.0, 1000),
            total_trades=total_trades,
            win_rate=0.5,
            profit_factor=profit_factor,
            max_drawdown_points=drawdown,
            net_profit_points=net_profit,
            validation_status=status,
        )


if __name__ == "__main__":
    unittest.main()
