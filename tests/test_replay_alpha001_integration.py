"""Testes de integracao da Alpha 001 no ReplayService."""

import unittest

from application.replay_service import ReplayService, ReplayStatus
from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy
from strategies.breakout import BreakoutStrategy


class ReplayAlpha001IntegrationTest(unittest.TestCase):
    """Valida execucao da Alpha 001 candle a candle no replay."""

    def test_replay_executa_alpha001_iorb_strategy_corretamente(self) -> None:
        """ReplayService deve usar Alpha 001 registrada como padrao."""
        service = ReplayService()

        self.assertIsInstance(service.strategy, Alpha001IORBStrategy)

    def test_strategy_signal_e_gerado_durante_replay(self) -> None:
        """Avanco do replay deve gerar StrategySignal."""
        service = self._service_with_candles(self._buy_candles())

        data = self._run_all(service)

        self.assertIsInstance(data.strategy_signal, StrategySignal)

    def test_buy_e_produzido_quando_todas_validacoes_aprovam(self) -> None:
        """Cenario completo de compra deve produzir BUY."""
        service = self._service_with_candles(self._buy_candles())

        data = self._run_all(service)

        self.assertEqual(data.strategy_signal.decision, "BUY")
        self.assertIn("rompimento da maxima", data.strategy_signal.reasons)

    def test_sell_e_produzido_quando_todas_validacoes_aprovam(self) -> None:
        """Cenario completo de venda deve produzir SELL."""
        service = self._service_with_candles(self._sell_candles())

        data = self._run_all(service)

        self.assertEqual(data.strategy_signal.decision, "SELL")
        self.assertIn("rompimento da minima", data.strategy_signal.reasons)

    def test_wait_e_produzido_quando_qualquer_validacao_falha(self) -> None:
        """Sem breakout, a Alpha 001 deve retornar WAIT."""
        service = self._service_with_candles(self._wait_candles())

        data = self._run_all(service)

        self.assertEqual(data.strategy_signal.decision, "WAIT")
        self.assertIn("preco dentro da opening range", data.strategy_signal.reasons)

    def test_wait_quando_regime_for_range(self) -> None:
        """Regime RANGE deve impedir sinal operacional."""
        service = RangeReplayService()
        self._load_candles(service, self._buy_candles())

        data = self._run_all(service)

        self.assertEqual(data.strategy_signal.decision, "WAIT")
        self.assertIn("regime desfavoravel", data.strategy_signal.reasons)

    def test_wait_quando_volatilidade_for_insuficiente(self) -> None:
        """Range menor que o minimo configurado no replay deve gerar WAIT."""
        service = self._service_with_candles(
            self._buy_candles(),
            minimum_range_size=40.0,
        )

        data = self._run_all(service)

        self.assertEqual(data.strategy_signal.decision, "WAIT")
        self.assertIn("volatilidade insuficiente", data.strategy_signal.reasons)

    def test_wait_quando_liquidez_for_insuficiente(self) -> None:
        """Volume abaixo do minimo do replay deve gerar WAIT."""
        service = self._service_with_candles(self._low_liquidity_buy_candles())

        data = self._run_all(service)

        self.assertEqual(data.strategy_signal.decision, "WAIT")
        self.assertIn("liquidez insuficiente", data.strategy_signal.reasons)

    def test_replay_continua_funcionando_para_estrategias_existentes(self) -> None:
        """Estrategias antigas devem continuar usando analisar."""
        service = ReplayService(strategy=BreakoutStrategy())
        self._load_candles(service, self._buy_candles())

        data = service.next_candle()

        self.assertIsInstance(data.strategy_signal, StrategySignal)
        self.assertIn(data.strategy_signal.decision, {"BUY", "SELL", "WAIT"})

    def _service_with_candles(
        self,
        candles: list[Candle],
        minimum_range_size: float = 20.0,
    ) -> ReplayService:
        service = ReplayService()
        service.alpha_minimum_range_size = minimum_range_size
        self._load_candles(service, candles)
        return service

    def _load_candles(
        self,
        service: ReplayService,
        candles: list[Candle],
    ) -> None:
        service.replay_engine.load_candles(candles)
        service.status = ReplayStatus.READY

    def _run_all(self, service: ReplayService):
        data = service.get_replay_data()
        while not data.is_finished:
            data = service.next_candle()
        return data

    def _buy_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 126.0, 128.0, 121.0, 1500),
        ]

    def _sell_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 110.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 94.0, 99.0, 92.0, 1500),
        ]

    def _wait_candles(self) -> list[Candle]:
        return [
            self._candle("09:00", 100.0, 120.0, 95.0, 1500),
            self._candle("09:05", 105.0, 118.0, 98.0, 1500),
            self._candle("09:16", 110.0, 116.0, 104.0, 1500),
        ]

    def _low_liquidity_buy_candles(self) -> list[Candle]:
        candles = self._buy_candles()
        candles[-1] = self._candle("09:16", 126.0, 128.0, 121.0, 500)
        return candles

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


class RangeReplayService(ReplayService):
    """ReplayService de teste que forca MarketSnapshot em RANGE."""

    def _snapshot_regime(self, feature_snapshot: object) -> str:
        return "RANGE"


if __name__ == "__main__":
    unittest.main()
