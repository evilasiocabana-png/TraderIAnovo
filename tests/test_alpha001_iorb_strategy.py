"""Testes da Strategy oficial Alpha 001 IORB."""

import unittest
from dataclasses import dataclass
from typing import Any

from alpha.alpha001_decision_engine import Alpha001Decision
from domain.contracts.strategy_signal import StrategySignal
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy


class Alpha001IORBStrategyTest(unittest.TestCase):
    """Valida adaptacao de Alpha001Decision para StrategySignal."""

    def test_retorna_buy_quando_decision_engine_aprova_buy(self) -> None:
        """BUY aprovado deve virar StrategySignal BUY."""
        strategy = Alpha001IORBStrategy(
            decision_engine=FakeDecisionEngine(
                Alpha001Decision("BUY", True, 1.0, ["aprovado"]),
            ),
        )

        signal = self._generate(strategy)

        self.assertEqual(signal.decision, "BUY")
        self.assertEqual(signal.score, 100)

    def test_retorna_sell_quando_decision_engine_aprova_sell(self) -> None:
        """SELL aprovado deve virar StrategySignal SELL."""
        strategy = Alpha001IORBStrategy(
            decision_engine=FakeDecisionEngine(
                Alpha001Decision("SELL", True, 0.75, ["aprovado"]),
            ),
        )

        signal = self._generate(strategy)

        self.assertEqual(signal.decision, "SELL")
        self.assertEqual(signal.score, 75)

    def test_retorna_wait_quando_decision_engine_reprova(self) -> None:
        """Decisao reprovada deve virar WAIT."""
        strategy = Alpha001IORBStrategy(
            decision_engine=FakeDecisionEngine(
                Alpha001Decision("BUY", False, 0.5, ["reprovado"]),
            ),
        )

        signal = self._generate(strategy)

        self.assertEqual(signal.decision, "WAIT")
        self.assertEqual(signal.confidence, 0.5)

    def test_preserva_confidence_e_reasons(self) -> None:
        """StrategySignal deve preservar confidence e reasons."""
        reasons = ["rompimento da maxima", "momentum comprador"]
        strategy = Alpha001IORBStrategy(
            decision_engine=FakeDecisionEngine(
                Alpha001Decision("BUY", True, 0.83, reasons),
            ),
        )

        signal = self._generate(strategy)

        self.assertEqual(signal.confidence, 0.83)
        self.assertEqual(signal.reasons, reasons)

    def test_chama_alpha001_decision_engine(self) -> None:
        """Strategy deve delegar avaliacao ao engine recebido."""
        engine = FakeDecisionEngine(Alpha001Decision("WAIT", False, 0.0, []))
        strategy = Alpha001IORBStrategy(decision_engine=engine)

        self._generate(strategy)

        self.assertTrue(engine.called)

    def test_retorna_strategy_signal(self) -> None:
        """generate_signal deve retornar StrategySignal."""
        strategy = Alpha001IORBStrategy(
            decision_engine=FakeDecisionEngine(
                Alpha001Decision("WAIT", False, 0.0, []),
            ),
        )

        signal = self._generate(strategy)

        self.assertIsInstance(signal, StrategySignal)

    def _generate(self, strategy: Alpha001IORBStrategy) -> StrategySignal:
        return strategy.generate_signal(
            candles=[],
            market_snapshot=object(),
            current_price=0.0,
            minimum_range_size=0.0,
            minimum_volume=0.0,
        )


@dataclass
class FakeDecisionEngine:
    """Fake para garantir que a strategy apenas delega."""

    decision: Alpha001Decision
    called: bool = False

    def evaluate(self, **kwargs: Any) -> Alpha001Decision:
        self.called = True
        return self.decision


if __name__ == "__main__":
    unittest.main()
