"""Testes da varredura de parametros da Alpha 001."""

import unittest

from research.alpha001_parameter_sweep import (
    Alpha001ParameterSet,
    Alpha001ParameterSweep,
    Alpha001ParameterSweepResult,
)


class Alpha001ParameterSweepTest(unittest.TestCase):
    """Valida execucao em lote de parametros Alpha 001."""

    def test_executa_multiplas_combinacoes(self) -> None:
        """Sweep deve executar todas as combinacoes recebidas."""
        results = Alpha001ParameterSweep().run(self._parameter_grid())

        self.assertEqual(len(results), 3)

    def test_consolida_resultados(self) -> None:
        """Cada combinacao deve retornar metricas consolidadas."""
        results = Alpha001ParameterSweep().run(self._parameter_grid())

        for result in results:
            self.assertGreaterEqual(result.total_trades, 0)
            self.assertGreaterEqual(result.win_rate, 0.0)
            self.assertGreaterEqual(result.profit_factor, 0.0)
            self.assertIsInstance(result.validation_status, str)

    def test_preserva_ordem_dos_experimentos(self) -> None:
        """Ordem dos resultados deve seguir o grid recebido."""
        grid = self._parameter_grid()

        results = Alpha001ParameterSweep().run(grid)

        self.assertEqual(results[0].parameters.opening_range_minutes, 5)
        self.assertEqual(results[1].parameters.opening_range_minutes, 10)
        self.assertEqual(results[2].parameters.opening_range_minutes, 15)

    def test_valida_estrutura_do_retorno(self) -> None:
        """Retorno deve usar o DTO oficial da varredura."""
        result = Alpha001ParameterSweep().run(self._parameter_grid())[0]

        self.assertIsInstance(result, Alpha001ParameterSweepResult)
        self.assertIsInstance(result.parameters, Alpha001ParameterSet)
        self.assertIsInstance(result.total_trades, int)
        self.assertIsInstance(result.win_rate, float)
        self.assertIsInstance(result.profit_factor, float)
        self.assertIsInstance(result.max_drawdown_points, float)
        self.assertIsInstance(result.net_profit_points, float)
        self.assertIsInstance(result.validation_status, str)

    def test_aceita_grid_em_dict(self) -> None:
        """Sweep deve aceitar parametros serializaveis em dict."""
        results = Alpha001ParameterSweep().run(
            [
                {
                    "opening_range_minutes": 20,
                    "minimum_range_size": 20.0,
                    "minimum_volume": 1000,
                }
            ]
        )

        self.assertEqual(results[0].parameters.opening_range_minutes, 20)

    def _parameter_grid(self) -> list[Alpha001ParameterSet]:
        return [
            Alpha001ParameterSet(5, 20.0, 1000),
            Alpha001ParameterSet(10, 25.0, 1200),
            Alpha001ParameterSet(15, 30.0, 1500),
        ]


if __name__ == "__main__":
    unittest.main()
