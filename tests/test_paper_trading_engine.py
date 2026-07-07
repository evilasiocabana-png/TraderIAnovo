"""Testes do PaperTradingEngine oficial."""

import ast
from pathlib import Path
import unittest

from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal
from paper.paper_trading_engine import (
    PaperOrder,
    PaperPosition,
    PaperTrade,
    PaperTradingEngine,
)


class PaperTradingEngineTest(unittest.TestCase):
    """Valida paper trading sem broker, MT5 ou ordem real."""

    def test_abre_buy_paper(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)

        result = engine.process(self._signal("BUY"), self._snapshot(100.0))

        self.assertIsInstance(result.order, PaperOrder)
        self.assertIsInstance(result.position, PaperPosition)
        self.assertEqual("BUY", result.position.side)
        self.assertEqual(90.0, result.position.stop)
        self.assertEqual(120.0, result.position.target)

    def test_abre_sell_paper(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)

        result = engine.process(self._signal("SELL"), self._snapshot(100.0))

        self.assertIsInstance(result.order, PaperOrder)
        self.assertEqual("SELL", result.position.side)
        self.assertEqual(110.0, result.position.stop)
        self.assertEqual(80.0, result.position.target)

    def test_fecha_buy_por_stop(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)
        engine.process(self._signal("BUY"), self._snapshot(100.0))

        result = engine.process(self._signal("WAIT"), self._snapshot(90.0))

        self.assertIsInstance(result.trade, PaperTrade)
        self.assertIsNone(result.position)
        self.assertEqual("STOP", result.trade.close_reason)
        self.assertEqual(-10.0, result.trade.result_points)

    def test_fecha_buy_por_target(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)
        engine.process(self._signal("BUY"), self._snapshot(100.0))

        result = engine.process(self._signal("WAIT"), self._snapshot(120.0))

        self.assertEqual("TARGET", result.trade.close_reason)
        self.assertEqual(20.0, result.trade.result_points)
        self.assertEqual([0.0, 20.0], result.equity_curve)

    def test_fecha_sell_por_stop(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)
        engine.process(self._signal("SELL"), self._snapshot(100.0))

        result = engine.process(self._signal("WAIT"), self._snapshot(110.0))

        self.assertEqual("STOP", result.trade.close_reason)
        self.assertEqual(-10.0, result.trade.result_points)

    def test_fecha_sell_por_target(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)
        engine.process(self._signal("SELL"), self._snapshot(100.0))

        result = engine.process(self._signal("WAIT"), self._snapshot(80.0))

        self.assertEqual("TARGET", result.trade.close_reason)
        self.assertEqual(20.0, result.trade.result_points)

    def test_fecha_por_reversao(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)
        engine.process(self._signal("BUY"), self._snapshot(100.0))

        result = engine.process(self._signal("SELL"), self._snapshot(105.0))

        self.assertEqual("REVERSAL", result.trade.close_reason)
        self.assertEqual(5.0, result.trade.result_points)
        self.assertIsNone(result.order)

    def test_registra_historico_e_atualiza_equity_curve(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)
        engine.process(self._signal("BUY"), self._snapshot(100.0))

        result = engine.process(self._signal("WAIT"), self._snapshot(120.0))

        self.assertEqual(1, len(result.trades_history))
        self.assertEqual([0.0, 20.0], result.equity_curve)
        self.assertEqual(result.trade, result.trades_history[0])

    def test_multiplas_operacoes_consecutivas(self):
        engine = PaperTradingEngine(stop_points=10.0, target_points=20.0)
        engine.process(self._signal("BUY"), self._snapshot(100.0))
        engine.process(self._signal("WAIT"), self._snapshot(120.0))
        engine.process(self._signal("SELL"), self._snapshot(100.0))

        result = engine.process(self._signal("WAIT"), self._snapshot(110.0))

        self.assertEqual(2, len(result.trades_history))
        self.assertEqual([0.0, 20.0, 10.0], result.equity_curve)
        self.assertEqual(-10.0, result.trade.result_points)

    def test_wait_nao_abre_posicao(self):
        engine = PaperTradingEngine()

        result = engine.process(self._signal("WAIT"), self._snapshot(100.0))

        self.assertIsNone(result.order)
        self.assertIsNone(result.position)
        self.assertFalse(result.decision_context.approved)

    def test_nao_importa_broker_ou_mt5(self):
        path = Path("paper/paper_trading_engine.py")
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = self._imported_modules(tree)

        self.assertNotIn("broker", imports)
        self.assertNotIn("MetaTrader5", imports)

    def _signal(self, decision):
        return StrategySignal(
            decision=decision,
            score=100 if decision != "WAIT" else 0,
            confidence=1.0 if decision != "WAIT" else 0.0,
            reasons=[decision],
        )

    def _snapshot(self, price):
        return MarketSnapshot(
            symbol="WDO",
            datetime="2026-06-26 09:00:00",
            regime="TREND",
            volatility=1.0,
            liquidity=1.0,
            trend_strength=1.0,
            market_dna_score=price,
        )

    def _imported_modules(self, tree):
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports


if __name__ == "__main__":
    unittest.main()
