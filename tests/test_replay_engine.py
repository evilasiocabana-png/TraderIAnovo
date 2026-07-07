"""Testes do motor base de replay."""

import unittest

from core.event_bus import EventBus
from core.events import BACKTEST_FINISHED, NEW_CANDLE
from domain.candle import Candle
from replay.replay_engine import ReplayEngine, ReplayState


class ReplayEngineTest(unittest.TestCase):
    """Valida replay candle a candle em memoria."""

    def test_load_candles_carrega_lista_e_reseta_estado(self) -> None:
        """Garante carregamento inicial dos candles."""
        engine = ReplayEngine()

        engine.load_candles(self._candles(3))
        state = engine.get_state()

        self.assertEqual(state.total_candles, 3)
        self.assertEqual(state.current_index, -1)
        self.assertIsNone(state.current_candle)
        self.assertFalse(state.is_running)
        self.assertFalse(state.is_finished)

    def test_start_inicia_replay(self) -> None:
        """Garante estado em execucao."""
        engine = ReplayEngine()
        engine.load_candles(self._candles(1))

        engine.start()

        self.assertTrue(engine.get_state().is_running)

    def test_stop_para_replay(self) -> None:
        """Garante parada do replay."""
        engine = ReplayEngine()
        engine.load_candles(self._candles(1))
        engine.start()

        engine.stop()

        self.assertFalse(engine.get_state().is_running)

    def test_next_candle_avanca_um_candle_por_vez(self) -> None:
        """Garante avancos sequenciais."""
        candles = self._candles(2)
        engine = ReplayEngine()
        engine.load_candles(candles)

        first = engine.next_candle()
        second = engine.next_candle()

        self.assertEqual(first, candles[0])
        self.assertEqual(second, candles[1])
        self.assertEqual(engine.get_state().current_index, 1)

    def test_reset_volta_para_inicio(self) -> None:
        """Garante reinicio do replay."""
        engine = ReplayEngine()
        engine.load_candles(self._candles(2))
        engine.start()
        engine.next_candle()

        engine.reset()
        state = engine.get_state()

        self.assertEqual(state.current_index, -1)
        self.assertIsNone(state.current_candle)
        self.assertFalse(state.is_running)
        self.assertFalse(state.is_finished)

    def test_finaliza_replay_ao_chegar_no_fim(self) -> None:
        """Garante finalizacao no ultimo candle."""
        engine = ReplayEngine()
        engine.load_candles(self._candles(1))
        engine.start()

        candle = engine.next_candle()
        state = engine.get_state()

        self.assertIsNotNone(candle)
        self.assertFalse(state.is_running)
        self.assertTrue(state.is_finished)

    def test_get_state_retorna_replay_state(self) -> None:
        """Garante contrato de estado do replay."""
        state = ReplayEngine().get_state()

        self.assertIsInstance(state, ReplayState)

    def test_publica_new_candle_quando_avanca(self) -> None:
        """Garante publicacao de candle novo no EventBus."""
        bus = EventBus()
        received: list[dict[str, object]] = []
        candles = self._candles(2)
        engine = ReplayEngine(event_bus=bus)
        engine.load_candles(candles)

        bus.subscribe(NEW_CANDLE, received.append)
        engine.next_candle()

        self.assertEqual(received[0]["candle"], candles[0])
        self.assertEqual(received[0]["current_index"], 0)
        self.assertEqual(received[0]["total_candles"], 2)

    def test_publica_backtest_finished_ao_terminar(self) -> None:
        """Garante publicacao de finalizacao no EventBus."""
        bus = EventBus()
        received: list[dict[str, int]] = []
        engine = ReplayEngine(event_bus=bus)
        engine.load_candles(self._candles(1))

        bus.subscribe(BACKTEST_FINISHED, received.append)
        engine.next_candle()

        self.assertEqual(received, [{"total_candles": 1}])

    def test_nao_publica_backtest_finished_duplicado(self) -> None:
        """Garante que finalizacao nao e publicada duas vezes."""
        bus = EventBus()
        received: list[dict[str, int]] = []
        engine = ReplayEngine(event_bus=bus)
        engine.load_candles(self._candles(1))

        bus.subscribe(BACKTEST_FINISHED, received.append)
        engine.next_candle()
        engine.next_candle()

        self.assertEqual(received, [{"total_candles": 1}])

    def test_funciona_sem_event_bus(self) -> None:
        """Garante compatibilidade sem barramento de eventos."""
        engine = ReplayEngine()
        engine.load_candles(self._candles(1))

        candle = engine.next_candle()

        self.assertIsNotNone(candle)
        self.assertTrue(engine.get_state().is_finished)

    def _candles(self, quantity: int) -> list[Candle]:
        return [self._candle(index) for index in range(quantity)]

    def _candle(self, index: int) -> Candle:
        close = 100.0 + index
        return Candle(
            data=f"2026-06-26 09:{index:02d}",
            abertura=close - 1,
            maxima=close + 2,
            minima=close - 2,
            fechamento=close,
            volume=1000 + index,
        )


if __name__ == "__main__":
    unittest.main()
