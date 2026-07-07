"""Contrato historico de metadados de dataset."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_metadata import HistoricalDatasetMetadata


CONTRACT_PATH = Path("historical/contracts/historical_dataset_metadata.py")
REQUIRED_FIELDS = [
    "dataset_id",
    "dataset_name",
    "provider_name",
    "symbol",
    "timeframe",
    "start_timestamp",
    "end_timestamp",
    "record_count",
    "timezone",
    "source_description",
    "created_at",
    "metadata_version",
]


class HistoricalDatasetMetadataContractTest(unittest.TestCase):
    """Protege o DTO oficial de metadados historicos."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        metadata = self._metadata()

        self.assertIsInstance(metadata, HistoricalDatasetMetadata)
        self.assertEqual(metadata.dataset_id, "WDO_1m_2025")
        self.assertEqual(metadata.symbol, "WDO")

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetMetadata)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._metadata_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetMetadata(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetMetadata)
        expected_types = {
            "dataset_id": str,
            "dataset_name": str,
            "provider_name": str,
            "symbol": str,
            "timeframe": str,
            "start_timestamp": str,
            "end_timestamp": str,
            "record_count": int,
            "timezone": str,
            "source_description": str,
            "created_at": str,
            "metadata_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertIs(hints[field_name], expected_types[field_name])

    def test_nao_usa_dicionarios_livres(self) -> None:
        metadata = self._metadata()

        self.assertNotIsInstance(metadata, dict)
        self.assertFalse(any(field.type is dict for field in fields(HistoricalDatasetMetadata)))

    def test_record_count_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._metadata(record_count=0).record_count, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._metadata(record_count=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._metadata(record_count="10")  # type: ignore[arg-type]

    def test_contrato_e_dataclass_imutavel(self) -> None:
        metadata = self._metadata()

        self.assertTrue(is_dataclass(metadata))
        with self.assertRaises(FrozenInstanceError):
            metadata.dataset_id = "outro"  # type: ignore[misc]

    def test_contrato_nao_contem_logica_operacional_ou_io(self) -> None:
        imports = self._imports(CONTRACT_PATH)
        calls = self._calls(CONTRACT_PATH)
        source = CONTRACT_PATH.read_text(encoding="utf-8").lower()
        forbidden_imports = {
            "pandas",
            "duckdb",
            "pyarrow",
            "csv",
            "pathlib",
            "market_data",
            "replay",
            "research",
            "dashboard_app",
            "streamlit",
            "domain",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertNotIn("open", calls)
        for term in ("read_csv", "read_parquet", "connect", "cache", "index"):
            self.assertNotIn(term, source)

    def test_camadas_consumidoras_permanecem_desacopladas(self) -> None:
        paths = [
            *Path("domain").rglob("*.py"),
            *Path("application").rglob("*.py"),
            *Path("replay").rglob("*.py"),
            *Path("research").rglob("*.py"),
            Path("dashboard_app.py"),
            *Path("strategies").rglob("*.py"),
        ]

        for path in paths:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("historical.contracts.historical_dataset_metadata", source)

    def test_nenhum_provider_concreto_foi_criado_em_historical(self) -> None:
        historical_files = [path.name for path in Path("historical").rglob("*.py")]

        self.assertNotIn("historical_dataset_provider.py", historical_files)
        self.assertNotIn("historical_metadata_provider.py", historical_files)

    def _metadata(self, **overrides: object) -> HistoricalDatasetMetadata:
        payload = self._metadata_payload()
        payload.update(overrides)
        return HistoricalDatasetMetadata(**payload)  # type: ignore[arg-type]

    def _metadata_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "dataset_id": "WDO_1m_2025",
            "dataset_name": "WDO 1m 2025",
            "provider_name": "historical",
            "symbol": "WDO",
            "timeframe": "1m",
            "start_timestamp": "2025-01-01T09:00:00-03:00",
            "end_timestamp": "2025-12-30T18:00:00-03:00",
            "record_count": 100,
            "timezone": "America/Sao_Paulo",
            "source_description": "Dataset historico de teste",
            "created_at": "2026-06-27T04:00:00-03:00",
            "metadata_version": "1.0",
        }
        return payload

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
