"""Testes da analise de robustez Alpha001."""

import unittest

from research.alpha001_parameter_sweep import (
    Alpha001ParameterSet,
    Alpha001ParameterSweepResult,
)
from research.alpha001_robustness_analyzer import (
    Alpha001RobustnessAnalyzer,
    Alpha001RobustnessResult,
)


class Alpha001RobustnessAnalyzerTest(unittest.TestCase):
    """Valida robustez usando resultados existentes."""

    def test_retorna_robust_quando_consistente(self) -> None:
        """Resultados consistentes devem ser robustos."""
        result = Alpha001RobustnessAnalyzer().analyze(self._robust_results())

        self.assertEqual(result.status, "ROBUST")
        self.assertEqual(result.robustness_score, 100.0)

    def test_retorna_fragile_com_profit_factor_inconsistente(self) -> None:
        """Profit factor inconsistente reduz robustez."""
        results = self._robust_results()
        results[1] = self._result(10, 0.8, 10.0, 100.0, 40)

        result = Alpha001RobustnessAnalyzer().analyze(results)

        self.assertEqual(result.status, "FRAGILE")
        self.assertIn("Profit factor inconsistente.", result.reasons)

    def test_retorna_fragile_com_drawdown_elevado(self) -> None:
        """Drawdown relativo alto deve ser sinalizado."""
        results = self._robust_results()
        results[1] = self._result(10, 1.5, 80.0, 100.0, 40)

        result = Alpha001RobustnessAnalyzer().analyze(results)

        self.assertEqual(result.status, "FRAGILE")
        self.assertIn("Drawdown relativo elevado.", result.reasons)

    def test_retorna_inconclusive_com_poucos_trades(self) -> None:
        """Amostra pequena deve tornar analise inconclusiva."""
        results = self._robust_results()
        results[1] = self._result(10, 1.5, 10.0, 100.0, 5)

        result = Alpha001RobustnessAnalyzer().analyze(results)

        self.assertEqual(result.status, "INCONCLUSIVE")
        self.assertIn("Quantidade minima de trades insuficiente.", result.reasons)

    def test_detecta_instabilidade_entre_configuracoes(self) -> None:
        """Lucros muito dispersos indicam instabilidade."""
        results = self._robust_results()
        results[2] = self._result(15, 1.5, 10.0, 300.0, 40)

        result = Alpha001RobustnessAnalyzer().analyze(results)

        self.assertEqual(result.status, "FRAGILE")
        self.assertIn("Configuracoes proximas instaveis.", result.reasons)

    def test_lista_vazia_retorna_inconclusive(self) -> None:
        """Sem resultados nao ha analise suficiente."""
        result = Alpha001RobustnessAnalyzer().analyze([])

        self.assertEqual(result.status, "INCONCLUSIVE")
        self.assertEqual(result.robustness_score, 0.0)

    def test_retorna_alpha001_robustness_result(self) -> None:
        """Analyzer deve retornar DTO de robustez."""
        result = Alpha001RobustnessAnalyzer().analyze(self._robust_results())

        self.assertIsInstance(result, Alpha001RobustnessResult)
        self.assertIsInstance(result.reasons, list)

    def _robust_results(self) -> list[Alpha001ParameterSweepResult]:
        return [
            self._result(5, 1.4, 10.0, 100.0, 40),
            self._result(10, 1.5, 12.0, 110.0, 42),
            self._result(15, 1.6, 14.0, 120.0, 45),
        ]

    def _result(
        self,
        opening_range: int,
        profit_factor: float,
        drawdown: float,
        net_profit: float,
        total_trades: int,
    ) -> Alpha001ParameterSweepResult:
        return Alpha001ParameterSweepResult(
            parameters=Alpha001ParameterSet(opening_range, 20.0, 1000),
            total_trades=total_trades,
            win_rate=0.6,
            profit_factor=profit_factor,
            max_drawdown_points=drawdown,
            net_profit_points=net_profit,
            validation_status="APPROVED",
        )


if __name__ == "__main__":
    unittest.main()
