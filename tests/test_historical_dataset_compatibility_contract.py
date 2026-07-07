"""Contrato historico de compatibilidade dataset-schema."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_compatibility import (
    HistoricalDatasetCompatibility,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_compatibility.py")
REQUIRED_FIELDS = [
    "dataset_id",
    "schema_id",
    "schema_version",
    "is_compatible",
    "compatibility_level",
    "incompatible_columns",
    "missing_columns",
    "additional_columns",
    "compatibility_notes",
    "analyzed_at",
    "analyzer_version",
]


class HistoricalDatasetCompatibilityContractTest(unittest.TestCase):
    """Protege o DTO oficial de compatibilidade historica."""

    def test_contrato_importa_e_cria_estado_compativel(self) -> None:
        compatibility = self._compatibility()

        self.assertIsInstance(compatibility, HistoricalDatasetCompatibility)
        self.assertTrue(compatibility.is_compatible)
        self.assertEqual(compatibility.compatibility_level, "FULL")

    def test_contrato_cria_estado_incompativel(self) -> None:
        compatibility = self._compatibility(
            is_compatible=False,
            compatibility_level="INCOMPATIBLE",
            missing_columns=("close",),
            compatibility_notes=("Coluna obrigatoria ausente",),
        )

        self.assertFalse(compatibility.is_compatible)
        self.assertEqual(compatibility.missing_columns, ("close",))

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetCompatibility)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._compatibility_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetCompatibility(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetCompatibility)
        expected_types = {
            "dataset_id": str,
            "schema_id": str,
            "schema_version": str,
            "is_compatible": bool,
            "compatibility_level": str,
            "incompatible_columns": tuple[str, ...],
            "missing_columns": tuple[str, ...],
            "additional_columns": tuple[str, ...],
            "compatibility_notes": tuple[str, ...],
            "analyzed_at": str,
            "analyzer_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_colecoes_sao_fortemente_tipadas(self) -> None:
        self.assertEqual(
            self._compatibility(incompatible_columns=("volume",)).incompatible_columns,
            ("volume",),
        )
        with self.assertRaisesRegex(TypeError, "incompatible_columns"):
            self._compatibility(incompatible_columns=["volume"])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "missing_columns"):
            self._compatibility(missing_columns=("close", 1))  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "additional_columns"):
            self._compatibility(additional_columns=({"column": "x"},))  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "compatibility_notes"):
            self._compatibility(compatibility_notes=("ok", None))  # type: ignore[arg-type]

    def test_is_compatible_deve_ser_booleano(self) -> None:
        self.assertFalse(self._compatibility(is_compatible=False).is_compatible)
        with self.assertRaisesRegex(TypeError, "is_compatible"):
            self._compatibility(is_compatible="true")  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        compatibility = self._compatibility()

        self.assertNotIsInstance(compatibility, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetCompatibility))
        )
        for collection in (
            compatibility.incompatible_columns,
            compatibility.missing_columns,
            compatibility.additional_columns,
            compatibility.compatibility_notes,
        ):
            self.assertFalse(any(isinstance(item, dict) for item in collection))

    def test_contrato_e_dataclass_imutavel(self) -> None:
        compatibility = self._compatibility()

        self.assertTrue(is_dataclass(compatibility))
        with self.assertRaises(FrozenInstanceError):
            compatibility.dataset_id = "outro"  # type: ignore[misc]

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
            "compare",
            "validate",
            "infer",
            "interpret",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("compare_schemas", "validate_dataset", "infer_columns"):
            self.assertNotIn(call_name, calls)

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
                    "historical.contracts.historical_dataset_compatibility",
                    source,
                )

    def test_nenhum_comparador_concreto_foi_criado_em_historical(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_compatibility_checker.py",
            "dataset_schema_comparator.py",
            "schema_comparator.py",
            "compatibility_analyzer.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _compatibility(self, **overrides: object) -> HistoricalDatasetCompatibility:
        payload = self._compatibility_payload()
        payload.update(overrides)
        return HistoricalDatasetCompatibility(**payload)  # type: ignore[arg-type]

    def _compatibility_payload(self) -> dict[str, object]:
        return {
            "dataset_id": "WDO_1m_2025",
            "schema_id": "schema_ohlcv",
            "schema_version": "1.0",
            "is_compatible": True,
            "compatibility_level": "FULL",
            "incompatible_columns": (),
            "missing_columns": (),
            "additional_columns": (),
            "compatibility_notes": ("Compatibilidade declarada para teste de contrato",),
            "analyzed_at": "2026-06-27T15:00:00-03:00",
            "analyzer_version": "1.0",
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
