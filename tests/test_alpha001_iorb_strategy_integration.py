"""Testes de integracao da Strategy Alpha 001 com seu DecisionEngine."""

import unittest

from domain.candle import Candle
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy


class Alpha001IORBStrategyIntegrationTest(unittest.TestCase):
    """Valida StrategySignal gerado pelo fluxo Alpha 001 integrado."""

    def test_buy_aprovado(self) -> None:
        """Fluxo favoravel de compra deve retornar BUY."""
        signal = self._generate(
            candles=self._buy_candles(),
            current_price=126.0,
        )

        self.assert_strategy_signal(signal)
        self.assertEqual(signal.decision, "BUY")
        self.assertEqual(signal.confidence, 1.0)
        self.assertIn("rompimento da maxima", signal.reasons)

    def test_sell_aprovado(self) -> None:
        """Fluxo favoravel de venda deve retornar SELL."""
        signal = self._generate(
            candles=self._sell_candles(),
            current_price=94.0,
        )

        self.assert_strategy_signal(signal)
        self.assertEqual(signal.decision, "SELL")
        self.assertEqual(signal.confidence, 1.0)
        self.assertIn("rompimento da minima", signal.reasons)

    def test_wait_quando_nao_houver_breakout(self) -> None:
        """Preco dentro da faixa deve retornar WAIT."""
        signal = self._generate(
            candles=self._buy_candles(),
            current_price=110.0,
        )

        self.assert_strategy_signal(signal)
        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("preco dentro da opening range", signal.reasons)

    def test_wait_quando_regime_for_range(self) -> None:
        """Regime RANGE deve impedir sinal operacional."""
        signal = self._generate(
            candles=self._buy_candles(),
            current_price=126.0,
            market_snapshot=self._snapshot(regime="RANGE"),
        )

        self.assert_strategy_signal(signal)
        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("regime desfavoravel", signal.reasons)

    def test_wait_quando_volatilidade_for_insuficiente(self) -> None:
        """Range menor que o minimo deve retornar WAIT."""
        signal = self._generate(
            candles=self._buy_candles(),
            current_price=126.0,
            minimum_range_size=40.0,
        )

        self.assert_strategy_signal(signal)
        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("volatilidade insuficiente", signal.reasons)

    def test_wait_quando_liquidez_for_insuficiente(self) -> None:
        """Liquidez abaixo do minimo deve retornar WAIT."""
        signal = self._generate(
            candles=self._buy_candles(),
            current_price=126.0,
            market_snapshot=self._snapshot(liquidity=500.0),
            minimum_volume=1000.0,
        )

        self.assert_strategy_signal(signal)
        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("liquidez insuficiente", signal.reasons)

    def test_confidence_vem_do_alpha001_decision(self) -> None:
        """Confidence deve refletir aprovacoes do DecisionEngine."""
        signal = self._generate(
            candles=self._buy_candles(),
            current_price=126.0,
            market_snapshot=self._snapshot(regime="RANGE"),
        )

        self.assertEqual(signal.confidence, 5 / 6)

    def test_reasons_sao_preservados(self) -> None:
        """Reasons do DecisionEngine devem chegar ao StrategySignal."""
        signal = self._generate(
            candles=self._buy_candles(),
            current_price=126.0,
        )

        self.assertEqual(
            signal.reasons,
            [
                "rompimento da maxima",
                "momentum comprador",
                "regime favoravel",
                "volatilidade suficiente",
                "liquidez suficiente",
            ],
        )

    def assert_strategy_signal(self, signal: StrategySignal) -> None:
        """Valida contrato StrategySignal em todos os cenarios."""
        self.assertIsInstance(signal, StrategySignal)

    def _generate(
        self,
        candles: list[Candle],
        current_price: float,
        market_snapshot: MarketSnapshot | None = None,
        minimum_range_size: float = 20.0,
        minimum_volume: float = 1000.0,
    ) -> StrategySignal:
        return Alpha001IORBStrategy().generate_signal(
            candles=candles,
            market_snapshot=market_snapshot or self._snapshot(),
            current_price=current_price,
            minimum_range_size=minimum_range_size,
            minimum_volume=minimum_volume,
        )

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
            volume=1000,
        )

    def _snapshot(
        self,
        regime: str = "TREND",
        liquidity: float = 1500.0,
    ) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:16",
            regime=regime,
            volatility=30.0,
            liquidity=liquidity,
            trend_strength=0.8,
            market_dna_score=70.0,
        )


if __name__ == "__main__":
    unittest.main()
