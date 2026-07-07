"""Testes de padronizacao das estrategias."""

import ast
import unittest
from pathlib import Path

from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from domain.market_state import MarketState
from strategies.breakout import BreakoutStrategy
from strategies.alpha101.alpha101_strategy import Alpha101Strategy
from strategies.pullback import PullbackStrategy
from strategies.score_contexto import ScoreContextoStrategy
from strategies.smart_money import SmartMoneyStrategy


class StrategiesContractTest(unittest.TestCase):
    """Garante que estrategias retornam o contrato oficial."""

    def test_todas_estrategias_retornam_strategy_signal(self) -> None:
        """Valida o tipo de retorno das estrategias existentes."""
        estado = self._estado()
        estrategias = [
            ScoreContextoStrategy(),
            Alpha101Strategy(),
            BreakoutStrategy(),
            PullbackStrategy(),
            SmartMoneyStrategy(),
        ]

        for estrategia in estrategias:
            with self.subTest(estrategia=estrategia.nome):
                signal = estrategia.analisar(estado)
                self.assertIsInstance(signal, StrategySignal)
                self.assertIn(signal.decision, {"BUY", "SELL", "WAIT"})

    def test_estrategias_nao_retornam_dict(self) -> None:
        """Impede retornos literais em dicionario nas estrategias."""
        for caminho in Path("strategies").glob("*.py"):
            tree = ast.parse(caminho.read_text(encoding="utf-8"))
            retornos = [node for node in ast.walk(tree) if isinstance(node, ast.Return)]
            dicts = [node for node in retornos if isinstance(node.value, ast.Dict)]
            self.assertEqual(dicts, [], f"{caminho} retorna dict")

    def _estado(self) -> MarketState:
        candle = Candle("2026-06-25 09:23", 5500, 5530, 5480, 5522, 1500)
        return MarketState(candle, vwap=5516, atr=51, pullback_pontos=13, horario=9)


if __name__ == "__main__":
    unittest.main()
