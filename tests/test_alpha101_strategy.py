"""Testes da strategy oficial da Alpha101."""

from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
import unittest

from domain.candle import Candle
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal
from domain.market_state import MarketState
from strategies.alpha101.alpha101_config import Alpha101Config
from strategies.alpha101.alpha101_strategy import Alpha101Strategy
from strategies.base import Strategy
from tests.architecture_test_utils import calls_from, imports_from, read_source


class Alpha101StrategyTest(unittest.TestCase):
    """Valida Alpha101 sem acoplamento operacional."""

    def test_strategy_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(Alpha101Strategy))
        self.assertTrue(Alpha101Strategy.__dataclass_params__.frozen)

    def test_strategy_e_imutavel(self) -> None:
        strategy = Alpha101Strategy()

        with self.assertRaises(FrozenInstanceError):
            strategy.nome = "outra"

    def test_strategy_implementa_interface_base(self) -> None:
        self.assertIsInstance(Alpha101Strategy(), Strategy)

    def test_analisar_sem_historico_retorna_wait(self) -> None:
        signal = Alpha101Strategy().analisar(self._estado())

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("Alpha101 requer historico diario", signal.reasons[0])

    def test_generate_signal_retorna_buy_para_volume_momentum_breakout(self) -> None:
        signal = Alpha101Strategy().generate_signal(
            candles=self._buy_candles(),
            market_snapshot=self._snapshot(),
            current_price=150.0,
        )

        self.assertIsInstance(signal, StrategySignal)
        self.assertEqual(signal.decision, "BUY")
        self.assertGreater(signal.score, 0)
        self.assertGreater(signal.confidence, 0.0)
        self.assertIn("momentum de 5 dias positivo", signal.reasons)

    def test_generate_signal_retorna_wait_com_historico_insuficiente(self) -> None:
        signal = Alpha101Strategy().generate_signal(
            candles=self._buy_candles()[:50],
            market_snapshot=self._snapshot(),
            current_price=120.0,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("historico insuficiente para Alpha101", signal.reasons)

    def test_generate_signal_retorna_wait_sem_volume(self) -> None:
        candles = self._buy_candles()
        candles[-1] = Candle(
            data=candles[-1].data,
            abertura=candles[-1].abertura,
            maxima=candles[-1].maxima,
            minima=candles[-1].minima,
            fechamento=candles[-1].fechamento,
            volume=800,
        )

        signal = Alpha101Strategy().generate_signal(
            candles=candles,
            market_snapshot=self._snapshot(),
            current_price=150.0,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("volume relativo de 20 dias abaixo do minimo", signal.reasons)

    def test_generate_signal_retorna_wait_sem_momentum(self) -> None:
        candles = self._buy_candles()
        base = candles[-6].fechamento
        candles[-1] = Candle(
            data=candles[-1].data,
            abertura=base,
            maxima=base + 0.2,
            minima=base - 0.2,
            fechamento=base - 0.1,
            volume=5000,
        )

        signal = Alpha101Strategy().generate_signal(
            candles=candles,
            market_snapshot=self._snapshot(),
            current_price=base - 0.1,
        )

        self.assertEqual(signal.decision, "WAIT")
        self.assertIn("momentum de 5 dias nao positivo", signal.reasons)

    def test_strategy_nao_acessa_camadas_proibidas(self) -> None:
        source = read_source(Path("strategies/alpha101/alpha101_strategy.py"))
        forbidden_fragments = (
            "Alpha001",
            "Alpha002",
            "Alpha003",
            "RiskEngine",
            "DecisionPipeline",
            "ResearchPipeline",
            "Dashboard",
            "streamlit",
            "Broker",
            "MT5",
            "MetaTrader5",
            "order_send",
            "execute_order",
            "send_order",
            "open_position",
            "close_position",
            ".avaliar(",
            ".processar(",
            ".next_candle(",
        )
        leaked = [fragment for fragment in forbidden_fragments if fragment in source]

        self.assertEqual(leaked, [])

    def test_strategy_permanece_desacoplada_de_operacao(self) -> None:
        path = Path("strategies/alpha101/alpha101_strategy.py")
        imports = imports_from(path)
        calls = calls_from(path)

        forbidden_imports = {
            "alpha",
            "alpha.alpha001_config",
            "replay",
            "application.replay_service",
            "risk.risk_engine",
            "core.decision_pipeline",
            "research.research_pipeline",
            "broker",
            "mt5",
            "MetaTrader5",
            "paper",
            "database",
            "dashboard_app",
            "streamlit",
        }
        forbidden_calls = {
            "open",
            "avaliar",
            "processar",
            "execute",
            "run",
            "next_candle",
            "order_send",
            "execute_order",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))

    def _buy_candles(self) -> list[Candle]:
        candles: list[Candle] = []
        for index in range(200):
            close = 100.0 + index * 0.1
            volume = 1000
            if index >= 195:
                close += (index - 194) * 0.8
            if index == 199:
                volume = 3000
            candles.append(
                Candle(
                    data=f"2026-01-{(index % 28) + 1:02d}",
                    abertura=close - 0.2,
                    maxima=close + 0.4,
                    minima=close - 0.5,
                    fechamento=close,
                    volume=volume,
                )
            )
        return candles

    def _estado(self) -> MarketState:
        candle = Candle("2026-06-25", 100.0, 101.0, 99.0, 100.5, 2000)
        return MarketState(candle, vwap=100.0, atr=2.0, pullback_pontos=1.0, horario=10)

    def _snapshot(self) -> MarketSnapshot:
        return MarketSnapshot(
            symbol="PETR4",
            datetime="2026-06-25",
            regime="TREND",
            volatility=0.03,
            liquidity=3000.0,
            trend_strength=0.8,
            market_dna_score=80.0,
        )


if __name__ == "__main__":
    unittest.main()
