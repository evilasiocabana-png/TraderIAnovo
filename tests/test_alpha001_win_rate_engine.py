"""Testes do motor de taxa de acerto da Alpha 001."""

import unittest

from research.alpha001_experiment import Alpha001ExperimentResult
from research.alpha001_win_rate_engine import (
    Alpha001WinRateEngine,
    Alpha001WinRateResult,
)


class Alpha001WinRateEngineContractTest(unittest.TestCase):
    """Valida calculo isolado de taxa de acerto."""

    def test_calculate_retorna_resultado_tipado(self) -> None:
        result = Alpha001WinRateEngine().calculate(self._experiment_result())

        self.assertIsInstance(result, Alpha001WinRateResult)

    def test_calculate_retorna_campos_de_taxa_de_acerto(self) -> None:
        result = Alpha001WinRateEngine().calculate(self._experiment_result())

        self.assertEqual(result.winning_trades, 0)
        self.assertEqual(result.losing_trades, 0)
        self.assertEqual(result.breakeven_trades, 0)
        self.assertEqual(result.win_rate, 0.0)

    def test_nao_calcula_metricas_fora_do_escopo(self) -> None:
        result = Alpha001WinRateEngine().calculate(self._experiment_result())

        forbidden_fields = (
            "expectancy",
            "profit_factor",
            "drawdown",
            "max_drawdown_points",
            "sharpe",
            "sortino",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_engines_anteriores_ou_camadas_proibidas(self) -> None:
        with open(
            "research/alpha001_win_rate_engine.py",
            encoding="utf-8",
        ) as file:
            source = file.read()

        forbidden_fragments = (
            "Alpha001MetricsEngine",
            "Alpha001ProfitEngine",
            "Alpha001DrawdownEngine",
            "Alpha001ProfitFactorEngine",
            "Alpha001ExpectancyEngine",
            "Replay",
            "Dashboard",
            "DecisionPipeline",
            "EventBus",
            "Broker",
            "MT5",
            "database",
        )
        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def _experiment_result(self) -> Alpha001ExperimentResult:
        return Alpha001ExperimentResult(
            total_candles=3,
            total_signals=3,
            total_buy=1,
            total_sell=1,
            total_wait=1,
            execution_time_ms=1.0,
            signals=(),
        )


if __name__ == "__main__":
    unittest.main()
