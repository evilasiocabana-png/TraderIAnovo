"""Testes do analisador de estabilidade temporal."""

import unittest

from research.period_performance_analyzer import (
    PeriodPerformanceMetrics,
    PeriodPerformanceReport,
)
from research.temporal_stability_analyzer import (
    TemporalStabilityAnalyzer,
    TemporalStabilityResult,
)


class TemporalStabilityAnalyzerTest(unittest.TestCase):
    """Valida estabilidade temporal sem executar experimentos."""

    def test_retorna_stable_quando_consistente(self) -> None:
        """Serie positiva e consistente deve ser estavel."""
        result = TemporalStabilityAnalyzer().analyze(self._stable_periods())

        self.assertEqual(result.status, "STABLE")
        self.assertEqual(result.stability_score, 100.0)

    def test_detecta_profit_factor_instavel(self) -> None:
        """Grande variacao de profit factor deve reduzir estabilidade."""
        periods = self._stable_periods()
        periods[2] = self._period("2026-03", profit_factor=3.5)

        result = TemporalStabilityAnalyzer().analyze(periods)

        self.assertEqual(result.status, "UNSTABLE")
        self.assertIn("Profit factor instavel.", result.reasons)

    def test_detecta_variacao_de_drawdown(self) -> None:
        """Drawdown muito disperso deve ser sinalizado."""
        periods = self._stable_periods()
        periods[2] = self._period("2026-03", drawdown=100.0)

        result = TemporalStabilityAnalyzer().analyze(periods)

        self.assertEqual(result.status, "UNSTABLE")
        self.assertIn("Drawdown variavel.", result.reasons)

    def test_detecta_periodos_negativos_excessivos(self) -> None:
        """Muitos periodos negativos indicam instabilidade."""
        result = TemporalStabilityAnalyzer().analyze(
            [
                self._period("2026-01", net_profit=100.0),
                self._period("2026-02", net_profit=-20.0),
                self._period("2026-03", net_profit=-30.0),
                self._period("2026-04", net_profit=-40.0),
            ]
        )

        self.assertEqual(result.status, "UNSTABLE")
        self.assertIn("Periodos negativos excessivos.", result.reasons)

    def test_detecta_degradacao_recente(self) -> None:
        """Queda recente relevante deve ser sinalizada."""
        result = TemporalStabilityAnalyzer().analyze(
            [
                self._period("2026-01", net_profit=200.0),
                self._period("2026-02", net_profit=180.0),
                self._period("2026-03", net_profit=80.0),
                self._period("2026-04", net_profit=70.0),
            ]
        )

        self.assertEqual(result.status, "UNSTABLE")
        self.assertIn("Degradacao recente de performance.", result.reasons)

    def test_retorna_inconclusive_com_pouca_amostra(self) -> None:
        """Menos de dois periodos nao permite estabilidade temporal."""
        result = TemporalStabilityAnalyzer().analyze(
            [self._period("2026-01", net_profit=100.0)]
        )

        self.assertEqual(result.status, "INCONCLUSIVE")
        self.assertEqual(result.stability_score, 0.0)

    def test_lista_vazia_retorna_inconclusive(self) -> None:
        """Lista vazia deve retornar resultado seguro."""
        result = TemporalStabilityAnalyzer().analyze([])

        self.assertEqual(result.status, "INCONCLUSIVE")
        self.assertIn("Amostra temporal insuficiente.", result.reasons)

    def test_retorna_temporal_stability_result(self) -> None:
        """Analyzer deve retornar DTO de estabilidade."""
        result = TemporalStabilityAnalyzer().analyze(self._stable_periods())

        self.assertIsInstance(result, TemporalStabilityResult)
        self.assertIsInstance(result.reasons, list)

    def _stable_periods(self) -> list[PeriodPerformanceReport]:
        return [
            self._period("2026-01", net_profit=100.0, profit_factor=1.5),
            self._period("2026-02", net_profit=110.0, profit_factor=1.6),
            self._period("2026-03", net_profit=105.0, profit_factor=1.4),
            self._period("2026-04", net_profit=115.0, profit_factor=1.5),
        ]

    def _period(
        self,
        period: str,
        net_profit: float = 100.0,
        profit_factor: float = 1.5,
        drawdown: float = 10.0,
    ) -> PeriodPerformanceReport:
        return PeriodPerformanceReport(
            period=period,
            metrics=PeriodPerformanceMetrics(
                total_trades=30,
                win_rate=0.6,
                profit_factor=profit_factor,
                max_drawdown_points=drawdown,
                net_profit_points=net_profit,
            ),
        )


if __name__ == "__main__":
    unittest.main()
