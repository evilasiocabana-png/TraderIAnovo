"""Contrato historico de registry logico de formatos."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_format_descriptor import (
    HistoricalDatasetFormatDescriptor,
)
from historical.contracts.historical_dataset_format_registry import (
    HistoricalDatasetFormatRegistry,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_format_registry.py")
REQUIRED_FIELDS = [
    "registry_id",
    "registry_name",
    "supported_formats",
    "total_formats",
    "registry_version",
    "generated_at",
]


class HistoricalDatasetFormatRegistryContractTest(unittest.TestCase):
    """Protege o DTO oficial de registry historico de formatos."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        registry = self._registry(supported_formats=(self._format(),), total_formats=1)

        self.assertIsInstance(registry, HistoricalDatasetFormatRegistry)
        self.assertEqual(registry.registry_id, "format_registry_001")
        self.assertEqual(registry.supported_formats[0].format_id, "format_csv")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        registry = self._registry(supported_formats=(), total_formats=0)

        self.assertEqual(registry.supported_formats, ())
        self.assertEqual(registry.total_formats, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetFormatRegistry)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._registry_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetFormatRegistry(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetFormatRegistry)
        expected_types = {
            "registry_id": str,
            "registry_name": str,
            "supported_formats": tuple[HistoricalDatasetFormatDescriptor, ...],
            "total_formats": int,
            "registry_version": str,
            "generated_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_supported_formats_deve_ser_colecao_tipada_de_descriptor(self) -> None:
        descriptor = self._format()

        self.assertEqual(
            self._registry(supported_formats=(descriptor,)).supported_formats,
            (descriptor,),
        )
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._registry(supported_formats=[descriptor])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetFormatDescriptor"):
            self._registry(supported_formats=({"format_id": "format_csv"},))  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        registry = self._registry()

        self.assertNotIsInstance(registry, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetFormatRegistry))
        )
        self.assertFalse(
            any(isinstance(format_descriptor, dict) for format_descriptor in registry.supported_formats)
        )

    def test_total_formats_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._registry(total_formats=0).total_formats, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._registry(total_formats=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._registry(total_formats="1")  # type: ignore[arg-type]

    def test_contrato_e_dataclass_imutavel(self) -> None:
        registry = self._registry()

        self.assertTrue(is_dataclass(registry))
        with self.assertRaises(FrozenInstanceError):
            registry.registry_id = "outro"  # type: ignore[misc]

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
                    "historical.contracts.historical_dataset_format_registry",
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

    def _registry(self, **overrides: object) -> HistoricalDatasetFormatRegistry:
        payload = self._registry_payload()
        payload.update(overrides)
        return HistoricalDatasetFormatRegistry(**payload)  # type: ignore[arg-type]

    def _registry_payload(self) -> dict[str, object]:
        return {
            "registry_id": "format_registry_001",
            "registry_name": "Registry historico de formatos",
            "supported_formats": (self._format(),),
            "total_formats": 1,
            "registry_version": "1.0",
            "generated_at": "2026-06-27T13:30:00-03:00",
        }

    def _format(self) -> HistoricalDatasetFormatDescriptor:
        return HistoricalDatasetFormatDescriptor(
            format_id="format_csv",
            format_name="CSV",
            format_version="1.0",
            file_extensions=(".csv",),
            supports_compression=False,
            supports_schema_validation=True,
            supports_columnar_storage=False,
            supports_random_access=False,
            created_at="2026-06-27T13:00:00-03:00",
        )

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
