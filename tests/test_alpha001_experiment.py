"""Testes do experimento controlado da Alpha 001."""

import unittest

from alpha.alpha001_config import Alpha001Config
from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_experiment import (
    Alpha001Experiment,
    Alpha001ExperimentResult,
)


class Alpha001ExperimentTest(unittest.TestCase):
    """Valida a infraestrutura inicial de experimentacao da Alpha 001."""

    def test_experiment_retorna_resultado_tipado(self) -> None:
        result = Alpha001Experiment(
            config=Alpha001Config(),
            candles=self._buy_candles(),
        ).run()

        self.assertIsInstance(result, Alpha001ExperimentResult)

    def test_resultado_contem_campos_iniciais(self) -> None:
        result = Alpha001Experiment(
            config=Alpha001Config(),
            candles=self._buy_candles(),
        ).run()

        self.assertEqual(result.total_candles, 3)
        self.assertEqual(result.total_signals, 3)
        self.assertEqual(result.total_buy, 1)
        self.assertEqual(result.total_sell, 0)
        self.assertEqual(result.total_wait, 2)
        self.assertGreaterEqual(result.execution_time_ms, 0.0)

    def test_coleta_todos_os_strategy_signals_gerados(self) -> None:
        candles = self._buy_candles()
        result = Alpha001Experiment(
            config=Alpha001Config(),
            candles=candles,
        ).run()

        self.assertEqual(len(result.signals), len(candles))
        self.assertTrue(
            all(isinstance(signal, StrategySignal) for signal in result.signals)
        )

    def test_contabiliza_sell(self) -> None:
        result = Alpha001Experiment(
            config=Alpha001Config(),
            candles=self._sell_candles(),
        ).run()

        self.assertEqual(result.total_candles, 3)
        self.assertEqual(result.total_signals, 3)
        self.assertEqual(result.total_buy, 0)
        self.assertEqual(result.total_sell, 1)
        self.assertEqual(result.total_wait, 2)

    def test_aceita_colecao_vazia(self) -> None:
        result = Alpha001Experiment(
            config=Alpha001Config(),
            candles=[],
        ).run()

        self.assertEqual(result.signals, ())
        self.assertEqual(result.total_candles, 0)
        self.assertEqual(result.total_signals, 0)
        self.assertEqual(result.total_buy, 0)
        self.assertEqual(result.total_sell, 0)
        self.assertEqual(result.total_wait, 0)

    def test_nao_calcula_metricas_financeiras(self) -> None:
        result = Alpha001Experiment(
            config=Alpha001Config(),
            candles=self._buy_candles(),
        ).run()

        forbidden_fields = (
            "gross_profit",
            "gross_loss",
            "net_profit",
            "average_trade",
            "win_rate",
            "profit_factor",
            "equity_curve",
            "peak_equity",
            "max_drawdown_points",
        )
        for field_name in forbidden_fields:
            with self.subTest(field=field_name):
                self.assertFalse(hasattr(result, field_name))

    def test_nao_importa_camadas_operacionais_proibidas(self) -> None:
        source = self._source()

        forbidden_imports = (
            "decision_pipeline",
            "event_bus",
            "dashboard",
            "broker",
            "mt5",
            "MetaTrader",
            "EquityDrawdownCalculator",
        )
        for forbidden in forbidden_imports:
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def _source(self) -> str:
        with open("research/alpha001_experiment.py", encoding="utf-8") as file:
            return file.read()

    def _buy_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0),
            self._candle("09:05", 105.0, 118.0, 98.0),
            self._candle("09:16", 126.0, 128.0, 121.0),
        ]

    def _sell_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 110.0, 120.0, 95.0),
            self._candle("09:05", 105.0, 118.0, 98.0),
            self._candle("09:16", 94.0, 99.0, 92.0),
        ]

    def _candle(
        self,
        candle_time: str,
        close: float,
        high: float,
        low: float,
    ) -> Candle:
        return Candle(
            data=f"2026-06-26 {candle_time}",
            abertura=close,
            maxima=high,
            minima=low,
            fechamento=close,
            volume=1500,
        )


if __name__ == "__main__":
    unittest.main()
