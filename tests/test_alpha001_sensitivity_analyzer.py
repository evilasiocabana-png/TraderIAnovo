"""Testes da analise de sensibilidade da Alpha001."""

import unittest

from research.alpha001_parameter_sweep import (
    Alpha001ParameterSet,
    Alpha001ParameterSweepResult,
)
from research.alpha001_sensitivity_analyzer import (
    Alpha001SensitivityAnalyzer,
    Alpha001SensitivityResult,
)


class Alpha001SensitivityAnalyzerTest(unittest.TestCase):
    """Valida sensibilidade por parametro sem executar pesquisas."""

    def test_analisa_opening_range_minutes(self) -> None:
        """Analyzer deve identificar melhor e pior opening range."""
        result = Alpha001SensitivityAnalyzer().analyze(
            self._results_by_opening_range(),
            "opening_range_minutes",
        )

        self.assertEqual(result.parameter_name, "opening_range_minutes")
        self.assertEqual(result.best_value, 15)
        self.assertEqual(result.worst_value, 5)

    def test_analisa_minimum_range_size(self) -> None:
        """Analyzer deve aceitar minimum_range_size."""
        result = Alpha001SensitivityAnalyzer().analyze(
            self._results_by_range_size(),
            "minimum_range_size",
        )

        self.assertEqual(result.best_value, 30.0)
        self.assertEqual(result.worst_value, 20.0)

    def test_analisa_minimum_volume(self) -> None:
        """Analyzer deve aceitar minimum_volume."""
        result = Alpha001SensitivityAnalyzer().analyze(
            self._results_by_volume(),
            "minimum_volume",
        )

        self.assertEqual(result.best_value, 1500)
        self.assertEqual(result.worst_value, 1000)

    def test_classifica_sensibilidade_baixa(self) -> None:
        """Impacto pequeno deve ser LOW."""
        result = Alpha001SensitivityAnalyzer().analyze(
            [
                self._result(5, 20.0, 1000, 100.0),
                self._result(10, 20.0, 1000, 120.0),
            ],
            "opening_range_minutes",
        )

        self.assertEqual(result.metric_impact, 20.0)
        self.assertEqual(result.sensitivity_level, "LOW")

    def test_classifica_sensibilidade_media(self) -> None:
        """Impacto intermediario deve ser MEDIUM."""
        result = Alpha001SensitivityAnalyzer().analyze(
            [
                self._result(5, 20.0, 1000, 100.0),
                self._result(10, 20.0, 1000, 180.0),
            ],
            "opening_range_minutes",
        )

        self.assertEqual(result.metric_impact, 80.0)
        self.assertEqual(result.sensitivity_level, "MEDIUM")

    def test_classifica_sensibilidade_alta(self) -> None:
        """Impacto grande deve ser HIGH."""
        result = Alpha001SensitivityAnalyzer().analyze(
            [
                self._result(5, 20.0, 1000, 100.0),
                self._result(10, 20.0, 1000, 230.0),
            ],
            "opening_range_minutes",
        )

        self.assertEqual(result.metric_impact, 130.0)
        self.assertEqual(result.sensitivity_level, "HIGH")

    def test_agrega_media_por_valor_do_parametro(self) -> None:
        """Valores repetidos devem ser comparados por media."""
        result = Alpha001SensitivityAnalyzer().analyze(
            [
                self._result(5, 20.0, 1000, 100.0),
                self._result(5, 25.0, 1000, 140.0),
                self._result(10, 20.0, 1000, 200.0),
                self._result(10, 25.0, 1000, 220.0),
            ],
            "opening_range_minutes",
        )

        self.assertEqual(result.best_value, 10)
        self.assertEqual(result.metric_impact, 90.0)

    def test_lista_vazia_retorna_resultado_seguro(self) -> None:
        """Sem resultados a analise deve retornar LOW com reason."""
        result = Alpha001SensitivityAnalyzer().analyze(
            [],
            "opening_range_minutes",
        )

        self.assertIsNone(result.best_value)
        self.assertEqual(result.metric_impact, 0.0)
        self.assertEqual(result.sensitivity_level, "LOW")

    def test_parametro_invalido_retorna_resultado_seguro(self) -> None:
        """Parametros fora da lista oficial nao devem quebrar."""
        result = Alpha001SensitivityAnalyzer().analyze(
            self._results_by_opening_range(),
            "stop_points",
        )

        self.assertIsNone(result.best_value)
        self.assertIn("Parametro invalido", result.reasons[0])

    def test_retorna_alpha001_sensitivity_result(self) -> None:
        """Analyzer deve retornar DTO de sensibilidade."""
        result = Alpha001SensitivityAnalyzer().analyze(
            self._results_by_opening_range(),
            "opening_range_minutes",
        )

        self.assertIsInstance(result, Alpha001SensitivityResult)
        self.assertIsInstance(result.reasons, list)

    def _results_by_opening_range(self) -> list[Alpha001ParameterSweepResult]:
        return [
            self._result(5, 20.0, 1000, 100.0),
            self._result(10, 20.0, 1000, 140.0),
            self._result(15, 20.0, 1000, 190.0),
        ]

    def _results_by_range_size(self) -> list[Alpha001ParameterSweepResult]:
        return [
            self._result(15, 20.0, 1000, 100.0),
            self._result(15, 25.0, 1000, 130.0),
            self._result(15, 30.0, 1000, 180.0),
        ]

    def _results_by_volume(self) -> list[Alpha001ParameterSweepResult]:
        return [
            self._result(15, 20.0, 1000, 100.0),
            self._result(15, 20.0, 1200, 125.0),
            self._result(15, 20.0, 1500, 160.0),
        ]

    def _result(
        self,
        opening_range: int,
        range_size: float,
        volume: int,
        net_profit: float,
    ) -> Alpha001ParameterSweepResult:
        return Alpha001ParameterSweepResult(
            parameters=Alpha001ParameterSet(opening_range, range_size, volume),
            total_trades=40,
            win_rate=0.6,
            profit_factor=1.5,
            max_drawdown_points=10.0,
            net_profit_points=net_profit,
            validation_status="APPROVED",
        )


if __name__ == "__main__":
    unittest.main()
