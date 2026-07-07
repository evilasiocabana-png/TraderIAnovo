"""Contrato historico de registry logico de schemas."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_schema import HistoricalDatasetSchema
from historical.contracts.historical_dataset_schema_registry import (
    HistoricalDatasetSchemaRegistry,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_schema_registry.py")
REQUIRED_FIELDS = [
    "registry_id",
    "registry_name",
    "schemas",
    "total_schemas",
    "registry_version",
    "generated_at",
]


class HistoricalDatasetSchemaRegistryContractTest(unittest.TestCase):
    """Protege o DTO oficial de registry historico de schemas."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        registry = self._registry(schemas=(self._schema(),), total_schemas=1)

        self.assertIsInstance(registry, HistoricalDatasetSchemaRegistry)
        self.assertEqual(registry.registry_id, "schema_registry_001")
        self.assertEqual(registry.schemas[0].schema_id, "schema_ohlcv")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        registry = self._registry(schemas=(), total_schemas=0)

        self.assertEqual(registry.schemas, ())
        self.assertEqual(registry.total_schemas, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetSchemaRegistry)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._registry_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetSchemaRegistry(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetSchemaRegistry)
        expected_types = {
            "registry_id": str,
            "registry_name": str,
            "schemas": tuple[HistoricalDatasetSchema, ...],
            "total_schemas": int,
            "registry_version": str,
            "generated_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_schemas_deve_ser_colecao_tipada_de_historical_dataset_schema(self) -> None:
        schema = self._schema()

        self.assertEqual(self._registry(schemas=(schema,)).schemas, (schema,))
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._registry(schemas=[schema])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetSchema"):
            self._registry(schemas=({"schema_id": "schema_ohlcv"},))  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        registry = self._registry()

        self.assertNotIsInstance(registry, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetSchemaRegistry))
        )
        self.assertFalse(any(isinstance(schema, dict) for schema in registry.schemas))

    def test_total_schemas_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._registry(total_schemas=0).total_schemas, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._registry(total_schemas=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._registry(total_schemas="1")  # type: ignore[arg-type]

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
            "parse",
            "infer",
            "detect",
            "register",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("validate_schema", "infer_schema", "discover_schema"):
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
                    "historical.contracts.historical_dataset_schema_registry",
                    source,
                )

    def test_nenhum_mecanismo_concreto_de_registry_foi_criado_fora_de_contracts(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_schema_registry.py",
            "schema_registry.py",
            "schema_discovery.py",
            "schema_inference.py",
            "schema_validator.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _registry(self, **overrides: object) -> HistoricalDatasetSchemaRegistry:
        payload = self._registry_payload()
        payload.update(overrides)
        return HistoricalDatasetSchemaRegistry(**payload)  # type: ignore[arg-type]

    def _registry_payload(self) -> dict[str, object]:
        return {
            "registry_id": "schema_registry_001",
            "registry_name": "Registry historico de schemas",
            "schemas": (self._schema(),),
            "total_schemas": 1,
            "registry_version": "1.0",
            "generated_at": "2026-06-27T14:30:00-03:00",
        }

    def _schema(self) -> HistoricalDatasetSchema:
        return HistoricalDatasetSchema(
            schema_id="schema_ohlcv",
            schema_name="OHLCV historico",
            schema_version="1.0",
            columns=("timestamp", "open", "high", "low", "close", "volume"),
            primary_timestamp_column="timestamp",
            required_columns=("timestamp", "open", "high", "low", "close"),
            optional_columns=("volume",),
            created_at="2026-06-27T14:00:00-03:00",
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
