"""Testes da Alpha 001 integrada ao DecisionPipeline oficial."""

import unittest

from core.decision_pipeline import DecisionPipeline
from domain.candle import Candle
from domain.contracts.decision_context import DecisionContext
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy
from strategies.strategy_factory import StrategyFactory


class Alpha001DecisionPipelineTest(unittest.TestCase):
    """Valida processamento da Alpha 001 pelo pipeline oficial."""

    def test_alpha001_registrada_gera_strategy_signal_para_pipeline(self) -> None:
        """Alpha 001 registrada deve gerar StrategySignal normal."""
        strategy = StrategyFactory().create("alpha001_iorb")

        signal = self._generate_signal(strategy)

        self.assertIsInstance(strategy, Alpha001IORBStrategy)
        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "BUY")

    def test_pipeline_processa_strategy_signal_da_alpha001(self) -> None:
        """DecisionPipeline deve processar sinal da Alpha 001 sem adaptador."""
        signal = self._generate_signal(StrategyFactory().create("alpha001_iorb"))

        context = DecisionPipeline().processar(
            signal,
            self._snapshot(),
            RiskDecision(True, "Replay demonstrativo", 1, 1.0),
        )

        self.assertIsInstance(context, DecisionContext)
        self.assertEqual(context.strategy_signal, signal)
        self.assertEqual(context.final_decision, "BUY")
        self.assertEqual(context.final_confidence, signal.confidence)
        self.assertTrue(context.approved)

    def test_pipeline_preserva_wait_da_alpha001(self) -> None:
        """WAIT da Alpha 001 deve permanecer WAIT no pipeline."""
        strategy = StrategyFactory().create("alpha001_iorb")
        signal = strategy.generate_signal(
            candles=self._wait_candles(),
            market_snapshot=self._snapshot(),
            current_price=110.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
        )

        context = DecisionPipeline().processar(
            signal,
            self._snapshot(),
            RiskDecision(True, "Replay demonstrativo", 1, 1.0),
        )

        self.assertEqual(context.final_decision, "WAIT")
        self.assertEqual(context.final_confidence, signal.confidence)

    def test_pipeline_bloqueia_alpha001_quando_risco_nao_aprova(self) -> None:
        """Pipeline deve respeitar RiskDecision sem alterar o sinal."""
        signal = self._generate_signal(StrategyFactory().create("alpha001_iorb"))

        context = DecisionPipeline().processar(
            signal,
            self._snapshot(),
            RiskDecision(False, "Risco bloqueado", 0, 0.0),
        )

        self.assertEqual(context.final_decision, "BUY")
        self.assertFalse(context.approved)

    def _generate_signal(self, strategy: Alpha001IORBStrategy) -> StrategySignal:
        return strategy.generate_signal(
            candles=self._buy_candles(),
            market_snapshot=self._snapshot(),
            current_price=126.0,
            minimum_range_size=20.0,
            minimum_volume=1000.0,
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

    def _buy_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 126.0, 128.0, 121.0, 1500),
        ]

    def _wait_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 110.0, 116.0, 104.0, 1500),
        ]

    def _candle(
        self,
        candle_time: str,
        close: float,
        high: float,
        low: float,
        volume: int,
    ) -> Candle:
        return Candle(
            data=f"2026-06-26 {candle_time}",
            abertura=close,
            maxima=high,
            minima=low,
            fechamento=close,
            volume=volume,
        )


if __name__ == "__main__":
    unittest.main()
