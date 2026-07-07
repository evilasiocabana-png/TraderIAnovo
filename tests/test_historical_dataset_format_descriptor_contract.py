"""Contrato historico de descritor de formato de dataset."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_format_descriptor import (
    HistoricalDatasetFormatDescriptor,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_format_descriptor.py")
REQUIRED_FIELDS = [
    "format_id",
    "format_name",
    "format_version",
    "file_extensions",
    "supports_compression",
    "supports_schema_validation",
    "supports_columnar_storage",
    "supports_random_access",
    "created_at",
]


class HistoricalDatasetFormatDescriptorContractTest(unittest.TestCase):
    """Protege o DTO oficial de descritor de formato historico."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        descriptor = self._descriptor()

        self.assertIsInstance(descriptor, HistoricalDatasetFormatDescriptor)
        self.assertEqual(descriptor.format_id, "format_csv")
        self.assertEqual(descriptor.file_extensions, (".csv",))

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [
            field.name for field in fields(HistoricalDatasetFormatDescriptor)
        ]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._descriptor_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetFormatDescriptor(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetFormatDescriptor)
        expected_types = {
            "format_id": str,
            "format_name": str,
            "format_version": str,
            "file_extensions": tuple[str, ...],
            "supports_compression": bool,
            "supports_schema_validation": bool,
            "supports_columnar_storage": bool,
            "supports_random_access": bool,
            "created_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_file_extensions_e_colecao_fortemente_tipada(self) -> None:
        self.assertEqual(self._descriptor(file_extensions=(".csv",)).file_extensions, (".csv",))
        with self.assertRaisesRegex(TypeError, "file_extensions"):
            self._descriptor(file_extensions=[".csv"])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "file_extensions"):
            self._descriptor(file_extensions=(".csv", 1))  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "file_extensions"):
            self._descriptor(file_extensions=({"extension": ".csv"},))  # type: ignore[arg-type]

    def test_flags_de_capacidade_sao_booleanos(self) -> None:
        self.assertTrue(
            self._descriptor(supports_schema_validation=True).supports_schema_validation
        )
        with self.assertRaisesRegex(TypeError, "supports_compression"):
            self._descriptor(supports_compression="false")  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "supports_columnar_storage"):
            self._descriptor(supports_columnar_storage=1)  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "supports_random_access"):
            self._descriptor(supports_random_access=None)  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        descriptor = self._descriptor()

        self.assertNotIsInstance(descriptor, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetFormatDescriptor))
        )
        self.assertFalse(
            any(isinstance(extension, dict) for extension in descriptor.file_extensions)
        )

    def test_contrato_e_dataclass_imutavel(self) -> None:
        descriptor = self._descriptor()

        self.assertTrue(is_dataclass(descriptor))
        with self.assertRaises(FrozenInstanceError):
            descriptor.format_id = "outro"  # type: ignore[misc]

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
            "write",
            "parse",
            "detect",
            "validate_schema",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        self.assertNotIn("compress", calls)

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
                    "historical.contracts.historical_dataset_format_descriptor",
                    source,
                )

    def test_nenhum_parser_reader_ou_writer_foi_criado_em_historical(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_parser.py",
            "historical_dataset_reader.py",
            "historical_dataset_writer.py",
            "format_detector.py",
            "schema_validator.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _descriptor(self, **overrides: object) -> HistoricalDatasetFormatDescriptor:
        payload = self._descriptor_payload()
        payload.update(overrides)
        return HistoricalDatasetFormatDescriptor(**payload)  # type: ignore[arg-type]

    def _descriptor_payload(self) -> dict[str, object]:
        return {
            "format_id": "format_csv",
            "format_name": "CSV",
            "format_version": "1.0",
            "file_extensions": (".csv",),
            "supports_compression": False,
            "supports_schema_validation": True,
            "supports_columnar_storage": False,
            "supports_random_access": False,
            "created_at": "2026-06-27T13:00:00-03:00",
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
