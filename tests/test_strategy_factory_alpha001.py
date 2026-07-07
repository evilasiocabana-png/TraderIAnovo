"""Testes do registro da Alpha 001 na StrategyFactory."""

import unittest

from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from domain.market_state import MarketState
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy
from strategies.alpha101.alpha101_strategy import Alpha101Strategy
from strategies.base import Strategy
from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
from strategies.score_contexto import ScoreContextoStrategy
from strategies.smart_money import SmartMoneyStrategy
from strategies.strategy_factory import StrategyFactory


class StrategyFactoryAlpha001Test(unittest.TestCase):
    """Valida registro oficial da Alpha 001 no catalogo."""

    def test_instancia_alpha001_pela_strategy_factory(self) -> None:
        """Factory deve criar Alpha001IORBStrategy pelo nome oficial."""
        strategy = StrategyFactory().create("alpha001_iorb")

        self.assertIsInstance(strategy, Alpha001IORBStrategy)

    def test_estrategia_implementa_interface_base(self) -> None:
        """Alpha 001 deve implementar a interface Strategy."""
        strategy = StrategyFactory().create("alpha001_iorb")

        self.assertIsInstance(strategy, Strategy)

    def test_estrategia_retorna_strategy_signal(self) -> None:
        """Alpha 001 deve retornar StrategySignal pela interface basica."""
        strategy = StrategyFactory().create("alpha001_iorb")

        signal = strategy.analisar(self._estado())

        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "WAIT")

    def test_registro_nao_quebra_estrategias_existentes(self) -> None:
        """Factory deve continuar criando estrategias ja existentes."""
        factory = StrategyFactory()

        self.assertIsInstance(factory.create("breakout"), BreakoutStrategy)
        self.assertIsInstance(factory.create("alpha101"), Alpha101Strategy)
        self.assertIsInstance(factory.create("pullback"), PullbackStrategy)
        self.assertIsInstance(
            factory.create("score_contexto"),
            ScoreContextoStrategy,
        )
        self.assertIsInstance(factory.create("smart_money"), SmartMoneyStrategy)

    def test_lista_alpha001_no_catalogo(self) -> None:
        """Catalogo deve expor Alpha 001 entre as estrategias."""
        strategies = StrategyFactory().list_available()

        self.assertIn("alpha001_iorb", strategies)
        self.assertIn("alpha101", strategies)

    def _estado(self) -> MarketState:
        candle = Candle(
            data="2026-06-26 09:16",
            abertura=100.0,
            maxima=120.0,
            minima=95.0,
            fechamento=110.0,
            volume=1500,
        )
        return MarketState(
            candle=candle,
            vwap=105.0,
            atr=25.0,
            pullback_pontos=5.0,
            horario=9,
        )


if __name__ == "__main__":
    unittest.main()
