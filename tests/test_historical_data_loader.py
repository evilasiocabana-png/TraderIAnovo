"""Testes do importador de candles historicos do WDO."""

import tempfile
import unittest
from pathlib import Path

from data.historical_data_loader import HistoricalDataLoader
from domain.candle import Candle


class HistoricalDataLoaderTest(unittest.TestCase):
    """Valida carga e validacao de CSV historico."""

    def test_importa_csv_valido(self) -> None:
        """CSV valido deve ser carregado e validado."""
        path = self._csv(
            "datetime,open,high,low,close,volume\n"
            "2026-06-26 09:00,100,110,95,105,1000\n"
            "2026-06-26 09:01,105,112,100,108,1200\n"
        )

        loader = HistoricalDataLoader().load_csv(path)

        self.assertTrue(loader.validate())
        self.assertEqual(len(loader.candles()), 2)

    def test_rejeita_csv_invalido(self) -> None:
        """CSV sem estrutura OHLCV deve ser rejeitado."""
        path = self._csv("foo,bar\n1,2\n")

        loader = HistoricalDataLoader().load_csv(path)

        self.assertFalse(loader.validate())
        self.assertIn("CSV com estrutura invalida.", loader.errors)

    def test_rejeita_arquivo_inexistente(self) -> None:
        """Arquivo inexistente deve ser reportado como invalido."""
        loader = HistoricalDataLoader().load_csv("arquivo_inexistente.csv")

        self.assertFalse(loader.validate())
        self.assertIn("CSV sem dados.", loader.errors)

    def test_rejeita_timestamps_invalidos(self) -> None:
        """Timestamp fora dos formatos aceitos deve ser rejeitado."""
        path = self._csv(
            "datetime,open,high,low,close,volume\n"
            "timestamp-ruim,100,110,95,105,1000\n"
        )

        loader = HistoricalDataLoader().load_csv(path)

        self.assertFalse(loader.validate())
        self.assertIn("Timestamp invalido na linha 2.", loader.errors)

    def test_rejeita_candles_incompletos(self) -> None:
        """Linha com campo vazio deve ser rejeitada."""
        path = self._csv(
            "datetime,open,high,low,close,volume\n"
            "2026-06-26 09:00,100,110,,105,1000\n"
        )

        loader = HistoricalDataLoader().load_csv(path)

        self.assertFalse(loader.validate())
        self.assertIn("Candle incompleto na linha 2.", loader.errors)

    def test_rejeita_ohlc_invalido(self) -> None:
        """High menor que close deve invalidar candle."""
        path = self._csv(
            "datetime,open,high,low,close,volume\n"
            "2026-06-26 09:00,100,101,95,105,1000\n"
        )

        loader = HistoricalDataLoader().load_csv(path)

        self.assertFalse(loader.validate())
        self.assertIn("OHLC invalido na linha 2.", loader.errors)

    def test_retorna_lista_de_candle(self) -> None:
        """candles deve retornar objetos Candle."""
        path = self._csv(
            "datetime,open,high,low,close,volume\n"
            "2026-06-26 09:00,100,110,95,105,1000\n"
        )

        candles = HistoricalDataLoader().load_csv(path).candles()

        self.assertIsInstance(candles, list)
        self.assertIsInstance(candles[0], Candle)
        self.assertEqual(candles[0].fechamento, 105.0)

    def test_aceita_colunas_em_portugues(self) -> None:
        """Loader deve aceitar aliases usados no projeto."""
        path = self._csv(
            "data,abertura,maxima,minima,fechamento,volume\n"
            "26/06/2026 09:00,100,110,95,105,1000\n"
        )

        candles = HistoricalDataLoader().load_csv(path).candles()

        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].data, "26/06/2026 09:00")

    def test_nao_importa_camadas_proibidas(self) -> None:
        """Loader nao deve acessar Replay, Strategy, Broker ou Dashboard."""
        source = Path("data/historical_data_loader.py").read_text(
            encoding="utf-8",
        )

        self.assertNotIn("replay", source)
        self.assertNotIn("strateg", source.lower())
        self.assertNotIn("broker", source.lower())
        self.assertNotIn("dashboard", source.lower())

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
