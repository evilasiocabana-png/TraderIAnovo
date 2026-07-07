"""Contrato historico de descritor de provider de dataset."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_provider_descriptor import (
    HistoricalDatasetProviderDescriptor,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_provider_descriptor.py")
REQUIRED_FIELDS = [
    "provider_id",
    "provider_name",
    "provider_version",
    "provider_description",
    "supported_symbols",
    "supported_timeframes",
    "supported_formats",
    "supports_streaming",
    "supports_incremental_loading",
    "supports_validation",
    "created_at",
]


class HistoricalDatasetProviderDescriptorContractTest(unittest.TestCase):
    """Protege o DTO oficial de descritor de provider historico."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        descriptor = self._descriptor()

        self.assertIsInstance(descriptor, HistoricalDatasetProviderDescriptor)
        self.assertEqual(descriptor.provider_id, "provider_csv")
        self.assertEqual(descriptor.supported_symbols, ("WDO",))

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [
            field.name for field in fields(HistoricalDatasetProviderDescriptor)
        ]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._descriptor_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetProviderDescriptor(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetProviderDescriptor)
        expected_types = {
            "provider_id": str,
            "provider_name": str,
            "provider_version": str,
            "provider_description": str,
            "supported_symbols": tuple[str, ...],
            "supported_timeframes": tuple[str, ...],
            "supported_formats": tuple[str, ...],
            "supports_streaming": bool,
            "supports_incremental_loading": bool,
            "supports_validation": bool,
            "created_at": str,
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

    def test_flags_de_capacidade_sao_booleanos(self) -> None:
        self.assertFalse(self._descriptor(supports_streaming=False).supports_streaming)
        with self.assertRaisesRegex(TypeError, "supports_streaming"):
            self._descriptor(supports_streaming="false")  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "supports_incremental_loading"):
            self._descriptor(supports_incremental_loading=1)  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "supports_validation"):
            self._descriptor(supports_validation=None)  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        descriptor = self._descriptor()

        self.assertNotIsInstance(descriptor, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetProviderDescriptor))
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
            descriptor.provider_id = "outro"  # type: ignore[misc]

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
            "detect",
            "load_dataset",
            "register",
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
                    "historical.contracts.historical_dataset_provider_descriptor",
                    source,
                )

    def test_nenhum_provider_concreto_foi_criado_em_historical(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        self.assertNotIn("historical_dataset_provider.py", historical_files)
        self.assertNotIn("historical_provider.py", historical_files)
        self.assertNotIn("csv_historical_dataset_provider.py", historical_files)
        self.assertNotIn("parquet_historical_dataset_provider.py", historical_files)
        self.assertNotIn("duckdb_historical_dataset_provider.py", historical_files)

    def _descriptor(
        self, **overrides: object
    ) -> HistoricalDatasetProviderDescriptor:
        payload = self._descriptor_payload()
        payload.update(overrides)
        return HistoricalDatasetProviderDescriptor(**payload)  # type: ignore[arg-type]

    def _descriptor_payload(self) -> dict[str, object]:
        return {
            "provider_id": "provider_csv",
            "provider_name": "CSV Historical Provider Descriptor",
            "provider_version": "1.0",
            "provider_description": "Descritor arquitetural de provider historico",
            "supported_symbols": ("WDO",),
            "supported_timeframes": ("1m",),
            "supported_formats": ("csv",),
            "supports_streaming": False,
            "supports_incremental_loading": False,
            "supports_validation": True,
            "created_at": "2026-06-27T06:00:00-03:00",
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
