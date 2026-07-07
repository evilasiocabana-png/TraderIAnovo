"""Testes da camada oficial de Market Data."""

import ast
import tempfile
from pathlib import Path
import unittest

from data.historical_data_loader import HistoricalDataLoader
from domain.candle import Candle
from market_data import (
    CsvHistoricalDataSource,
    HistoricalDataSource,
    HistoricalDataSourceResult,
    HistoricalDataProvider,
    HistoricalDataset,
    MarketDataProvider,
)


class MarketDataProviderTest(unittest.TestCase):
    """Valida provider historico sem broker ou execucao real."""

    def test_historical_dataset_representa_candles_historicos(self):
        candles = [self._candle("2026-06-26 09:00")]

        dataset = HistoricalDataset(
            symbol="WDO",
            timeframe="1m",
            start_date="2026-06-26 09:00",
            end_date="2026-06-26 09:00",
            candles=candles,
        )

        self.assertEqual(dataset.symbol, "WDO")
        self.assertEqual(dataset.timeframe, "1m")
        self.assertEqual(dataset.total_candles, 1)
        self.assertFalse(dataset.is_empty)

    def test_market_data_provider_define_interface_base(self):
        self.assertTrue(issubclass(HistoricalDataProvider, MarketDataProvider))

    def test_historical_data_provider_depende_de_fonte_historica_abstrata(self):
        source = Path("market_data/historical_data_provider.py").read_text(
            encoding="utf-8",
        )

        self.assertIn("HistoricalDataSource", source)
        self.assertNotIn("HistoricalDataLoader", source)
        self.assertNotIn("CsvHistoricalDataSource", source)
        self.assertNotIn("load_csv", source)

    def test_csv_historical_data_source_reutiliza_loader_existente(self):
        source = Path("market_data/csv_historical_data_source.py").read_text(
            encoding="utf-8",
        )

        self.assertIn("HistoricalDataLoader", source)
        self.assertIn("load_csv", source)

    def test_historical_data_provider_carrega_csv_valido(self):
        dataset = HistoricalDataProvider().load(
            self._historical_csv(3),
            symbol="WDO",
            timeframe="1m",
        )

        self.assertIsInstance(dataset, HistoricalDataset)
        self.assertEqual(dataset.symbol, "WDO")
        self.assertEqual(dataset.timeframe, "1m")
        self.assertEqual(dataset.total_candles, 3)
        self.assertEqual(dataset.start_date, "2026-06-26 09:00")
        self.assertEqual(dataset.end_date, "2026-06-26 09:02")

    def test_historical_data_provider_rejeita_csv_invalido(self):
        provider = HistoricalDataProvider()

        dataset = provider.load(self._invalid_csv(), symbol="WDO")

        self.assertTrue(dataset.is_empty)
        self.assertIn("CSV com estrutura invalida.", provider.errors)

    def test_symbols_retorna_simbolos_carregados(self):
        provider = HistoricalDataProvider()
        provider.load(self._historical_csv(1), symbol="WDO", timeframe="1m")
        provider.load(self._historical_csv(1), symbol="WIN", timeframe="5m")

        self.assertEqual(provider.symbols(), ["WDO", "WIN"])

    def test_available_periods_retorna_timeframes_carregados(self):
        provider = HistoricalDataProvider()
        provider.load(self._historical_csv(1), symbol="WDO", timeframe="1m")
        provider.load(self._historical_csv(1), symbol="WDO", timeframe="5m")

        self.assertEqual(provider.available_periods(), ["1m", "5m"])

    def test_provider_expoe_erros_do_loader(self):
        provider = HistoricalDataProvider(
            data_source=CsvHistoricalDataSource(
                loader_factory=HistoricalDataLoader,
            ),
        )

        provider.load("arquivo_inexistente.csv")

        self.assertIn("Arquivo CSV invalido ou inexistente.", provider.errors)

    def test_provider_aceita_fonte_historica_sem_conhecer_origem(self):
        provider = HistoricalDataProvider(
            data_source=FakeHistoricalDataSource(
                HistoricalDataSourceResult(
                    candles=[self._candle("2026-06-26 09:00")],
                ),
            ),
        )

        dataset = provider.load("qualquer_origem", symbol="WDO", timeframe="1m")

        self.assertEqual(dataset.total_candles, 1)
        self.assertEqual(dataset.start_date, "2026-06-26 09:00")
        self.assertEqual(provider.data_source.loaded_source, "qualquer_origem")

    def test_csv_historical_data_source_carrega_csv_valido(self):
        result = CsvHistoricalDataSource().load(self._historical_csv(2))

        self.assertEqual(len(result.candles), 2)
        self.assertEqual(result.errors, [])

    def test_csv_historical_data_source_retorna_erros_normalizados(self):
        result = CsvHistoricalDataSource().load(self._invalid_csv())

        self.assertEqual(result.candles, [])
        self.assertIn("CSV com estrutura invalida.", result.errors)

    def test_leitura_csv_fica_isolada_no_adaptador_csv(self):
        files_with_csv_loader = []
        for path in Path("market_data").glob("*.py"):
            source = path.read_text(encoding="utf-8")
            if "HistoricalDataLoader" in source or "load_csv" in source:
                files_with_csv_loader.append(path.name)

        self.assertEqual(sorted(files_with_csv_loader), ["csv_historical_data_source.py"])

    def test_market_data_nao_importa_broker_mt5_ou_ordens(self):
        imports = set()
        for path in Path("market_data").glob("*.py"):
            imports.update(self._imports(path))

        self.assertNotIn("core.broker", imports)
        self.assertNotIn("MetaTrader5", imports)
        self.assertNotIn("domain.contracts.execution_order", imports)

    def test_provider_nao_depende_de_replay_research_dashboard_ou_alpha(self):
        imports = set()
        for path in Path("market_data").glob("*.py"):
            imports.update(self._imports(path))

        self.assertNotIn("application.replay_service", imports)
        self.assertNotIn("research.research_lab", imports)
        self.assertNotIn("dashboard_app", imports)
        self.assertNotIn("alpha", imports)

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

    def _candle(self, timestamp: str) -> Candle:
        return Candle(
            data=timestamp,
            abertura=100.0,
            maxima=102.0,
            minima=98.0,
            fechamento=101.0,
            volume=1000,
        )

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports


class FakeHistoricalDataSource(HistoricalDataSource):
    """Fonte fake para validar independencia de origem no provider."""

    def __init__(self, result: HistoricalDataSourceResult) -> None:
        self.result = result
        self.loaded_source: object | None = None

    def load(self, source: object) -> HistoricalDataSourceResult:
        """Registra a origem e retorna resultado controlado."""
        self.loaded_source = source
        return self.result


if __name__ == "__main__":
    unittest.main()
