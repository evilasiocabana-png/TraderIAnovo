"""Testes do registry de fontes historicas."""

import ast
import unittest
from pathlib import Path

from domain.candle import Candle
from market_data import (
    CsvHistoricalDataSource,
    DuckDBHistoricalDataAdapter,
    HistoricalDataSource,
    HistoricalDataSourceRegistry,
    HistoricalDataSourceResult,
    create_historical_data_source,
)


class FakeFutureDataSource(HistoricalDataSource):
    """Fonte fake para simular adaptadores futuros."""

    def load(self, source: object) -> HistoricalDataSourceResult:
        """Retorna candle controlado sem depender de formato fisico."""
        return HistoricalDataSourceResult(
            candles=[
                Candle(
                    data="2026-06-26 09:00",
                    abertura=100.0,
                    maxima=102.0,
                    minima=98.0,
                    fechamento=101.0,
                    volume=1000,
                )
            ],
            errors=[],
        )


class HistoricalDataSourceRegistryTest(unittest.TestCase):
    """Valida selecao simples de fontes historicas."""

    def test_csv_e_fonte_default_do_registry(self) -> None:
        source = create_historical_data_source()

        self.assertIsInstance(source, CsvHistoricalDataSource)

    def test_duckdb_e_fonte_registrada_no_registry_default(self) -> None:
        source = create_historical_data_source("duckdb")

        self.assertIsInstance(source, DuckDBHistoricalDataAdapter)

    def test_registry_lista_csv_como_fonte_registrada(self) -> None:
        registry = HistoricalDataSourceRegistry()
        registry.register("csv", CsvHistoricalDataSource)

        self.assertEqual(registry.names(), ["csv"])

    def test_registry_permite_registrar_fonte_futura_por_nome(self) -> None:
        registry = HistoricalDataSourceRegistry()
        registry.register("duckdb", FakeFutureDataSource)

        source = registry.create("DUCKDB")

        self.assertIsInstance(source, FakeFutureDataSource)

    def test_registry_rejeita_fonte_nao_registrada(self) -> None:
        registry = HistoricalDataSourceRegistry()

        with self.assertRaisesRegex(KeyError, "parquet"):
            registry.create("parquet")

    def test_camadas_superiores_nao_conhecem_adaptador_csv(self) -> None:
        """Replay e Research dependem do provider, nao do adaptador fisico."""
        for path in self._upper_layer_files():
            imports = self._imports(path)
            self.assertNotIn("market_data.csv_historical_data_source", imports)

    def _upper_layer_files(self) -> list[Path]:
        return [
            Path("application") / "replay_service.py",
            Path("application") / "research_lab_service.py",
        ]

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
        return imports


if __name__ == "__main__":
    unittest.main()
