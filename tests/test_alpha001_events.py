"""Testes dos eventos oficiais da Alpha 001 no EventBus."""

import unittest

from core.event_bus import EventBus
from core.events import (
    ALPHA001_SIGNAL_CREATED,
    ALPHA001_VALIDATION_COMPLETED,
    OFFICIAL_EVENTS,
    STRATEGY_SIGNAL_CREATED,
)
from domain.candle import Candle
from domain.contracts.backtest_result import BacktestResult
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_experiment_validator import Alpha001ExperimentValidator
from research.alpha001_experiment_validator import Alpha001ValidationResult
from strategies.strategy_factory import StrategyFactory


class Alpha001EventsTest(unittest.TestCase):
    """Valida registro e publicacao de eventos da Alpha 001."""

    def test_eventos_alpha001_estao_registrados_como_oficiais(self) -> None:
        """Eventos Alpha 001 devem estar no catalogo oficial."""
        self.assertIn(ALPHA001_SIGNAL_CREATED, OFFICIAL_EVENTS)
        self.assertIn(ALPHA001_VALIDATION_COMPLETED, OFFICIAL_EVENTS)

    def test_publica_strategy_signal_created_para_alpha001(self) -> None:
        """Evento atual deve continuar aceitando StrategySignal da Alpha."""
        bus = EventBus()
        received: list[StrategySignal] = []
        bus.subscribe(STRATEGY_SIGNAL_CREATED, received.append)

        signal = self._alpha001_signal()
        bus.publish(STRATEGY_SIGNAL_CREATED, signal)

        self.assertEqual(received, [signal])

    def test_publica_alpha001_signal_created_apos_strategy_signal(self) -> None:
        """Evento especifico deve ser publicado apos gerar StrategySignal."""
        bus = EventBus()
        received: list[StrategySignal] = []
        bus.subscribe(ALPHA001_SIGNAL_CREATED, received.append)

        signal = self._alpha001_signal()
        bus.publish(ALPHA001_SIGNAL_CREATED, signal)

        self.assertEqual(received, [signal])

    def test_publica_alpha001_validation_completed(self) -> None:
        """Evento de validacao deve transportar Alpha001ValidationResult."""
        bus = EventBus()
        received: list[Alpha001ValidationResult] = []
        bus.subscribe(ALPHA001_VALIDATION_COMPLETED, received.append)

        validation = self._validation_result()
        bus.publish(ALPHA001_VALIDATION_COMPLETED, validation)

        self.assertEqual(received, [validation])

    def test_eventos_atuais_permanecem_compativeis(self) -> None:
        """Registro Alpha nao deve remover evento generico existente."""
        self.assertIn(STRATEGY_SIGNAL_CREATED, OFFICIAL_EVENTS)

    def _alpha001_signal(self) -> StrategySignal:
        strategy = StrategyFactory().create("alpha001_iorb")
        return strategy.generate_signal(
            candles=self._candles(),
            market_snapshot=self._snapshot(),
            current_price=126.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

    def _validation_result(self) -> Alpha001ValidationResult:
        validator = Alpha001ExperimentValidator(
            minimum_total_trades=30,
            minimum_win_rate=0.4,
            minimum_profit_factor=1.2,
            maximum_drawdown_points=100.0,
            minimum_net_profit_points=0.0,
        )
        return validator.validate(
            BacktestResult(
                total_profit=100.0,
                total_trades=40,
                win_rate=0.6,
                drawdown=50.0,
                profit_factor=1.5,
                sharpe=1.0,
            )
        )

    def _snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:16",
            regime="TREND",
            volatility=30.0,
            liquidity=1500.0,
            trend_strength=0.8,
            market_dna_score=70.0,
        )

    def _candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0),
            self._candle("09:05", 105.0, 118.0, 98.0),
            self._candle("09:16", 126.0, 128.0, 121.0),
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
