"""Contrato historico de coluna logica de dataset."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_column import HistoricalDatasetColumn


CONTRACT_PATH = Path("historical/contracts/historical_dataset_column.py")
REQUIRED_FIELDS = [
    "column_name",
    "logical_type",
    "physical_type",
    "nullable",
    "required",
    "description",
    "default_value",
    "metadata_version",
]


class HistoricalDatasetColumnContractTest(unittest.TestCase):
    """Protege o DTO oficial de coluna logica historica."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        column = self._column()

        self.assertIsInstance(column, HistoricalDatasetColumn)
        self.assertEqual(column.column_name, "timestamp")
        self.assertTrue(column.required)

    def test_estado_valido_com_default_value_ausente(self) -> None:
        column = self._column(default_value=None)

        self.assertIsNone(column.default_value)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetColumn)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._column_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetColumn(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetColumn)
        expected_types = {
            "column_name": str,
            "logical_type": str,
            "physical_type": str,
            "nullable": bool,
            "required": bool,
            "description": str,
            "default_value": str | None,
            "metadata_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_flags_sao_booleanos(self) -> None:
        self.assertFalse(self._column(nullable=False).nullable)
        with self.assertRaisesRegex(TypeError, "nullable"):
            self._column(nullable="false")  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "required"):
            self._column(required=1)  # type: ignore[arg-type]

    def test_default_value_deve_ser_string_ou_none(self) -> None:
        self.assertEqual(self._column(default_value="0").default_value, "0")
        self.assertIsNone(self._column(default_value=None).default_value)
        with self.assertRaisesRegex(TypeError, "default_value"):
            self._column(default_value=0)  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        column = self._column()

        self.assertNotIsInstance(column, dict)
        self.assertFalse(any(field.type is dict for field in fields(HistoricalDatasetColumn)))
        self.assertNotIsInstance(column.default_value, dict)

    def test_contrato_e_dataclass_imutavel(self) -> None:
        column = self._column()

        self.assertTrue(is_dataclass(column))
        with self.assertRaises(FrozenInstanceError):
            column.column_name = "outro"  # type: ignore[misc]

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
            "convert",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("validate_column", "validate_value", "infer_type"):
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
                    "historical.contracts.historical_dataset_column",
                    source,
                )

    def test_nenhum_parser_ou_validador_de_coluna_foi_criado_em_historical(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_column_validator.py",
            "column_validator.py",
            "column_parser.py",
            "type_inference.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def test_schema_pode_referenciar_coluna_futuramente_sem_acoplamento_atual(self) -> None:
        schema_source = Path("historical/contracts/historical_dataset_schema.py").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("HistoricalDatasetColumn", schema_source)

    def _column(self, **overrides: object) -> HistoricalDatasetColumn:
        payload = self._column_payload()
        payload.update(overrides)
        return HistoricalDatasetColumn(**payload)  # type: ignore[arg-type]

    def _column_payload(self) -> dict[str, object]:
        return {
            "column_name": "timestamp",
            "logical_type": "datetime",
            "physical_type": "string",
            "nullable": False,
            "required": True,
            "description": "Timestamp principal do candle historico",
            "default_value": None,
            "metadata_version": "1.0",
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
