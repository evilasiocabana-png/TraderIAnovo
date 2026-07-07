"""Testes da integracao entre dados historicos e Replay."""

import tempfile
import unittest
from pathlib import Path

from application.replay_service import ReplayService, ReplayStatus
from data.historical_data_loader import HistoricalDataLoader
from replay.replay_engine import ReplayEngine


class ReplayHistoricalDataTest(unittest.TestCase):
    """Valida Replay com candles historicos importados."""

    def test_replay_engine_carrega_candles_historicos(self) -> None:
        """ReplayEngine deve aceitar candles do HistoricalDataLoader."""
        loader = HistoricalDataLoader().load_csv(self._historical_csv(3))
        candles = loader.candles()
        engine = ReplayEngine()

        engine.load_candles(candles)

        self.assertEqual(engine.get_state().total_candles, 3)

    def test_replay_service_carrega_csv_historico(self) -> None:
        """ReplayService deve carregar dataset historico completo."""
        data = ReplayService().load_historical_csv(self._historical_csv(4))

        self.assertEqual(data.total_candles, 4)
        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertEqual(data.current_index, -1)
        self.assertEqual(len(data.candles_loaded), 4)

    def test_replay_service_carrega_dataset_historico_real_catalogado(self) -> None:
        """ReplayService deve operar com o primeiro dataset interno disponivel."""
        data = ReplayService().load_real_historical_dataset()

        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertEqual(data.total_candles, 2)
        self.assertEqual(data.candles_loaded[0].data, "2025-01-01 09:00")

    def test_replay_avanca_sobre_dataset_historico_real(self) -> None:
        """Replay deve processar candles do dataset interno catalogado."""
        service = ReplayService()
        service.load_real_historical_dataset()

        first = service.next_candle()
        second = service.next_candle()

        self.assertEqual(first.current_index, 0)
        self.assertEqual(first.current_candle.data, "2025-01-01 09:00")
        self.assertEqual(second.current_index, 1)
        self.assertEqual(second.current_candle.data, "2025-01-01 09:01")

    def test_total_de_candles_corresponde_ao_dataset_importado(self) -> None:
        """Total de candles deve refletir exatamente o CSV."""
        service = ReplayService()

        service.load_historical_csv(self._historical_csv(5))
        data = service.get_replay_data()

        self.assertEqual(data.total_candles, 5)

    def test_replay_avanca_sobre_dados_historicos(self) -> None:
        """Replay deve avancar candle a candle no dataset historico."""
        service = ReplayService()
        service.load_historical_csv(self._historical_csv(3))

        first = service.next_candle()
        second = service.next_candle()

        self.assertEqual(first.current_index, 0)
        self.assertEqual(first.current_candle.data, "2026-06-26 09:00")
        self.assertEqual(second.current_index, 1)
        self.assertEqual(second.current_candle.data, "2026-06-26 09:01")

    def test_replay_continua_carregando_candles_demo(self) -> None:
        """Fluxo demo nao deve ser alterado pela carga historica."""
        data = ReplayService().load_demo_candles()

        self.assertGreater(data.total_candles, 0)
        self.assertEqual(data.status, ReplayStatus.READY)
        self.assertTrue(data.candles_loaded)

    def test_csv_historico_invalido_mantem_replay_empty(self) -> None:
        """CSV invalido deve deixar replay em estado seguro."""
        data = ReplayService().load_historical_csv(self._invalid_csv())

        self.assertEqual(data.total_candles, 0)
        self.assertEqual(data.status, ReplayStatus.EMPTY)
        self.assertEqual(data.candles_loaded, [])

    def _historical_csv(self, quantity: int) -> Path:
        lines = ["datetime,open,high,low,close,volume"]
        for index in range(quantity):
            close = 100.0 + index
            lines.append(
                f"2026-06-26 09:{index:02d},"
                f"{close - 1},{close + 2},{close - 2},{close},1000"
            )
        return self._csv("\n".join(lines) + "\n")

    def _invalid_csv(self) -> Path:
        return self._csv("foo,bar\n1,2\n")

    def _csv(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            suffix=".csv",
            encoding="utf-8",
            newline="",
        )
        with handle:
            handle.write(content)
        return Path(handle.name)


if __name__ == "__main__":
    unittest.main()
