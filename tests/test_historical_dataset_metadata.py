"""Contrato de metadados de datasets historicos."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from typing import get_type_hints

from market_data.contracts import HistoricalDatasetMetadata


CONTRACT_PATH = Path("market_data/contracts/historical_dataset_metadata.py")
REQUIRED_FIELDS = [
    "symbol",
    "timeframe",
    "exchange",
    "timezone",
    "source",
    "format",
    "version",
    "first_timestamp",
    "last_timestamp",
    "candle_count",
]
OPTIONAL_FIELDS = [
    "checksum",
    "file_path",
    "dataset_id",
    "description",
    "tags",
]


class HistoricalDatasetMetadataTest(unittest.TestCase):
    """Valida contrato explicito de metadados historicos."""

    def test_contrato_importa_sem_excecao(self) -> None:
        self.assertIsNotNone(HistoricalDatasetMetadata)

    def test_contrato_instancia_com_dados_minimos_validos(self) -> None:
        metadata = self._metadata()

        self.assertEqual(metadata.symbol, "WDO")
        self.assertEqual(metadata.timeframe, "1m")
        self.assertEqual(metadata.candle_count, 10)

    def test_todos_os_campos_obrigatorios_existem(self) -> None:
        metadata = self._metadata()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertTrue(hasattr(metadata, field_name))

    def test_campos_obrigatorios_possuem_type_hints(self) -> None:
        hints = get_type_hints(HistoricalDatasetMetadata)

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)

    def test_campos_opcionais_nao_quebram_instanciacao_minima(self) -> None:
        metadata = self._metadata()

        for field_name in OPTIONAL_FIELDS:
            with self.subTest(field=field_name):
                self.assertTrue(hasattr(metadata, field_name))

    def test_to_dict_serializa_contrato(self) -> None:
        metadata = self._metadata(tags=("intraday", "wdo"))

        serialized = metadata.to_dict()

        self.assertEqual(serialized["symbol"], "WDO")
        self.assertEqual(serialized["tags"], ["intraday", "wdo"])
        self.assertNotIn("candles", serialized)

    def test_from_dict_reconstroi_contrato(self) -> None:
        payload = self._metadata(tags=("intraday",)).to_dict()

        metadata = HistoricalDatasetMetadata.from_dict(payload)

        self.assertEqual(metadata.symbol, "WDO")
        self.assertEqual(metadata.tags, ("intraday",))

    def test_candle_count_aceita_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._metadata(candle_count=0).candle_count, 0)

        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._metadata(candle_count=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._metadata(candle_count="10")  # type: ignore[arg-type]

    def test_campos_textuais_obrigatorios_nao_podem_ser_vazios(self) -> None:
        for field_name in ("symbol", "timeframe", "format", "source", "timezone"):
            with self.subTest(field=field_name):
                with self.assertRaisesRegex(ValueError, "must not be empty"):
                    self._metadata(**{field_name: "   "})

    def test_contrato_nao_depende_de_infraestrutura_fisica(self) -> None:
        imports = self._imports(CONTRACT_PATH)
        calls = self._calls(CONTRACT_PATH)
        source = CONTRACT_PATH.read_text(encoding="utf-8").lower()
        forbidden_imports = {
            "pandas",
            "duckdb",
            "pyarrow",
            "csv",
            "pathlib",
            "dashboard_app",
            "streamlit",
            "replay",
            "research",
            "broker",
            "mt5",
            "metatrader5",
            "market_data.adapters",
            "market_data.historical_data_provider",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertNotIn("open", calls)
        for term in ("corretora", "ReplayService", "ResearchLabService"):
            self.assertNotIn(term.lower(), source)

    def test_domain_dashboard_e_estrategias_nao_importam_contrato(self) -> None:
        paths = [
            *Path("domain").rglob("*.py"),
            Path("dashboard_app.py"),
            *Path("strategies").rglob("*.py"),
        ]

        for path in paths:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("HistoricalDatasetMetadata", source)
                self.assertNotIn("market_data.contracts", source)

    def _metadata(self, **overrides: object) -> HistoricalDatasetMetadata:
        payload: dict[str, object] = {
            "symbol": "WDO",
            "timeframe": "1m",
            "exchange": "B3",
            "timezone": "America/Sao_Paulo",
            "source": "fixture",
            "format": "csv",
            "version": "1.0",
            "first_timestamp": "2025-01-01T09:00:00-03:00",
            "last_timestamp": "2025-01-01T09:09:00-03:00",
            "candle_count": 10,
        }
        payload.update(overrides)
        return HistoricalDatasetMetadata(**payload)  # type: ignore[arg-type]

    def _imports(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name for alias in node.names)
                imports.update(alias.name.split(".", 1)[0] for alias in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module)
                imports.add(node.module.split(".", 1)[0])
                imports.update(alias.name for alias in node.names)
        return imports

    def _calls(self, path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                if isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return calls


if __name__ == "__main__":
    unittest.main()
