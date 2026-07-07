"""Contrato historico de schema logico de dataset."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_schema import HistoricalDatasetSchema


CONTRACT_PATH = Path("historical/contracts/historical_dataset_schema.py")
REQUIRED_FIELDS = [
    "schema_id",
    "schema_name",
    "schema_version",
    "columns",
    "primary_timestamp_column",
    "required_columns",
    "optional_columns",
    "created_at",
]


class HistoricalDatasetSchemaContractTest(unittest.TestCase):
    """Protege o DTO oficial de schema logico historico."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        schema = self._schema()

        self.assertIsInstance(schema, HistoricalDatasetSchema)
        self.assertEqual(schema.schema_id, "schema_ohlcv")
        self.assertEqual(schema.primary_timestamp_column, "timestamp")

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetSchema)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._schema_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetSchema(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetSchema)
        expected_types = {
            "schema_id": str,
            "schema_name": str,
            "schema_version": str,
            "columns": tuple[str, ...],
            "primary_timestamp_column": str,
            "required_columns": tuple[str, ...],
            "optional_columns": tuple[str, ...],
            "created_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_colecoes_sao_fortemente_tipadas(self) -> None:
        self.assertEqual(self._schema(columns=("timestamp",)).columns, ("timestamp",))
        with self.assertRaisesRegex(TypeError, "columns"):
            self._schema(columns=["timestamp"])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "required_columns"):
            self._schema(required_columns=("timestamp", 1))  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "optional_columns"):
            self._schema(optional_columns=({"column": "volume"},))  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        schema = self._schema()

        self.assertNotIsInstance(schema, dict)
        self.assertFalse(any(field.type is dict for field in fields(HistoricalDatasetSchema)))
        for collection in (
            schema.columns,
            schema.required_columns,
            schema.optional_columns,
        ):
            self.assertFalse(any(isinstance(column, dict) for column in collection))

    def test_contrato_e_dataclass_imutavel(self) -> None:
        schema = self._schema()

        self.assertTrue(is_dataclass(schema))
        with self.assertRaises(FrozenInstanceError):
            schema.schema_id = "outro"  # type: ignore[misc]

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
            "parse",
            "infer",
            "detect",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("validate_schema", "infer_columns", "detect_columns"):
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
                    "historical.contracts.historical_dataset_schema",
                    source,
                )

    def test_nenhum_validador_de_schema_foi_criado_em_historical(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_schema_validator.py",
            "schema_validator.py",
            "column_inference.py",
            "schema_inference.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _schema(self, **overrides: object) -> HistoricalDatasetSchema:
        payload = self._schema_payload()
        payload.update(overrides)
        return HistoricalDatasetSchema(**payload)  # type: ignore[arg-type]

    def _schema_payload(self) -> dict[str, object]:
        return {
            "schema_id": "schema_ohlcv",
            "schema_name": "OHLCV historico",
            "schema_version": "1.0",
            "columns": ("timestamp", "open", "high", "low", "close", "volume"),
            "primary_timestamp_column": "timestamp",
            "required_columns": ("timestamp", "open", "high", "low", "close"),
            "optional_columns": ("volume",),
            "created_at": "2026-06-27T14:00:00-03:00",
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
