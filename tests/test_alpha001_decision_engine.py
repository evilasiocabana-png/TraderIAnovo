"""Testes do orquestrador de decisao da Alpha 001."""

import unittest

from alpha.alpha001_decision_engine import (
    Alpha001Decision,
    Alpha001DecisionEngine,
)
from domain.candle import Candle
from domain.contracts.market_snapshot import MarketSnapshot


class Alpha001DecisionEngineTest(unittest.TestCase):
    """Valida orquestracao dos componentes Alpha 001."""

    def test_aprova_buy_quando_todos_componentes_aprovam(self) -> None:
        """BUY deve ser aprovado quando todos os filtros passam."""
        decision = Alpha001DecisionEngine().evaluate(
            self._buy_candles(),
            self._snapshot(),
            current_price=126.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

        self.assertTrue(decision.approved)
        self.assertEqual(decision.decision, "BUY")
        self.assertEqual(decision.confidence, 1.0)

    def test_aprova_sell_quando_todos_componentes_aprovam(self) -> None:
        """SELL deve ser aprovado quando todos os filtros passam."""
        decision = Alpha001DecisionEngine().evaluate(
            self._sell_candles(),
            self._snapshot(),
            current_price=94.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

        self.assertTrue(decision.approved)
        self.assertEqual(decision.decision, "SELL")
        self.assertEqual(decision.confidence, 1.0)

    def test_retorna_wait_quando_uma_validacao_falha(self) -> None:
        """Qualquer falha deve transformar decisao final em WAIT."""
        decision = Alpha001DecisionEngine().evaluate(
            self._buy_candles(),
            self._snapshot(regime="RANGE"),
            current_price=126.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

        self.assertFalse(decision.approved)
        self.assertEqual(decision.decision, "WAIT")
        self.assertIn("regime desfavoravel", decision.reasons)

    def test_retorna_wait_sem_breakout(self) -> None:
        """Preco dentro da faixa deve manter WAIT."""
        decision = Alpha001DecisionEngine().evaluate(
            self._buy_candles(),
            self._snapshot(),
            current_price=110.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

        self.assertFalse(decision.approved)
        self.assertEqual(decision.decision, "WAIT")
        self.assertIn("preco dentro da opening range", decision.reasons)

    def test_agrega_reasons_dos_componentes(self) -> None:
        """Reasons devem vir dos componentes orquestrados."""
        decision = Alpha001DecisionEngine().evaluate(
            self._buy_candles(),
            self._snapshot(),
            current_price=126.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

        self.assertIn("rompimento da maxima", decision.reasons)
        self.assertIn("momentum comprador", decision.reasons)
        self.assertIn("regime favoravel", decision.reasons)
        self.assertIn("volatilidade suficiente", decision.reasons)
        self.assertIn("liquidez suficiente", decision.reasons)

    def test_calcula_confidence_por_validadores_aprovados(self) -> None:
        """Confidence deve ser aprovados dividido pelo total."""
        decision = Alpha001DecisionEngine().evaluate(
            self._buy_candles(),
            self._snapshot(regime="RANGE", liquidity=500.0),
            current_price=110.0,
            minimum_range_size=30.0,
            minimum_volume=1000.0,
        )

        self.assertEqual(decision.decision, "WAIT")
        self.assertEqual(decision.confidence, 1 / 6)

    def test_retorna_alpha001_decision(self) -> None:
        """Engine deve retornar Alpha001Decision."""
        decision = Alpha001DecisionEngine().evaluate(
            self._buy_candles(),
            self._snapshot(),
            current_price=126.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

        self.assertIsInstance(decision, Alpha001Decision)

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
