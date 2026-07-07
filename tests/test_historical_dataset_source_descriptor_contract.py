"""Contrato historico de descritor de origem de dataset."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_source_descriptor import (
    HistoricalDatasetSourceDescriptor,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_source_descriptor.py")
REQUIRED_FIELDS = [
    "source_id",
    "source_name",
    "source_description",
    "provider_id",
    "supported_symbols",
    "supported_timeframes",
    "supported_formats",
    "is_read_only",
    "is_available",
    "created_at",
    "source_version",
]


class HistoricalDatasetSourceDescriptorContractTest(unittest.TestCase):
    """Protege o DTO oficial de descritor de origem historica."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        descriptor = self._descriptor()

        self.assertIsInstance(descriptor, HistoricalDatasetSourceDescriptor)
        self.assertEqual(descriptor.source_id, "source_local_history")
        self.assertEqual(descriptor.provider_id, "provider_csv")

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [
            field.name for field in fields(HistoricalDatasetSourceDescriptor)
        ]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._descriptor_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetSourceDescriptor(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetSourceDescriptor)
        expected_types = {
            "source_id": str,
            "source_name": str,
            "source_description": str,
            "provider_id": str,
            "supported_symbols": tuple[str, ...],
            "supported_timeframes": tuple[str, ...],
            "supported_formats": tuple[str, ...],
            "is_read_only": bool,
            "is_available": bool,
            "created_at": str,
            "source_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_colecoes_sao_fortemente_tipadas(self) -> None:
        self.assertEqual(self._descriptor(supported_symbols=("WDO",)).supported_symbols, ("WDO",))
        with self.assertRaisesRegex(TypeError, "supported_symbols"):
            self._descriptor(supported_symbols=["WDO"])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "supported_timeframes"):
            self._descriptor(supported_timeframes=("1m", 5))  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "supported_formats"):
            self._descriptor(supported_formats=("csv", {"format": "parquet"}))  # type: ignore[arg-type]

    def test_flags_de_estado_sao_booleanos(self) -> None:
        self.assertTrue(self._descriptor(is_read_only=True).is_read_only)
        self.assertFalse(self._descriptor(is_available=False).is_available)
        with self.assertRaisesRegex(TypeError, "is_read_only"):
            self._descriptor(is_read_only="true")  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "is_available"):
            self._descriptor(is_available=1)  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        descriptor = self._descriptor()

        self.assertNotIsInstance(descriptor, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetSourceDescriptor))
        )
        for collection in (
            descriptor.supported_symbols,
            descriptor.supported_timeframes,
            descriptor.supported_formats,
        ):
            self.assertFalse(any(isinstance(item, dict) for item in collection))

    def test_contrato_e_dataclass_imutavel(self) -> None:
        descriptor = self._descriptor()

        self.assertTrue(is_dataclass(descriptor))
        with self.assertRaises(FrozenInstanceError):
            descriptor.source_id = "outro"  # type: ignore[misc]

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
        for term in (
            "read_csv",
            "read_parquet",
            "connect",
            "query",
            "detect",
            "authenticate",
            "login",
            "persist",
            "cache",
        ):
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
                self.assertNotIn(
                    "historical.contracts.historical_dataset_source_descriptor",
                    source,
                )

    def test_nenhuma_origem_concreta_foi_criada_fora_de_contracts(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        self.assertNotIn("historical_dataset_source.py", historical_files)
        self.assertNotIn("historical_source.py", historical_files)
        self.assertNotIn("csv_historical_dataset_source.py", historical_files)
        self.assertNotIn("parquet_historical_dataset_source.py", historical_files)
        self.assertNotIn("duckdb_historical_dataset_source.py", historical_files)

    def _descriptor(self, **overrides: object) -> HistoricalDatasetSourceDescriptor:
        payload = self._descriptor_payload()
        payload.update(overrides)
        return HistoricalDatasetSourceDescriptor(**payload)  # type: ignore[arg-type]

    def _descriptor_payload(self) -> dict[str, object]:
        return {
            "source_id": "source_local_history",
            "source_name": "Origem historica local",
            "source_description": "Descritor arquitetural de origem historica",
            "provider_id": "provider_csv",
            "supported_symbols": ("WDO",),
            "supported_timeframes": ("1m",),
            "supported_formats": ("csv",),
            "is_read_only": True,
            "is_available": True,
            "created_at": "2026-06-27T12:30:00-03:00",
            "source_version": "1.0",
        }

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
