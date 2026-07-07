"""Contrato historico de versao de schema."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_schema_version import (
    HistoricalDatasetSchemaVersion,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_schema_version.py")
REQUIRED_FIELDS = [
    "schema_id",
    "schema_version",
    "version_description",
    "effective_from",
    "effective_until",
    "is_current",
    "is_backward_compatible",
    "created_at",
]


class HistoricalDatasetSchemaVersionContractTest(unittest.TestCase):
    """Protege o DTO oficial de versao de schema historico."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        version = self._version()

        self.assertIsInstance(version, HistoricalDatasetSchemaVersion)
        self.assertEqual(version.schema_id, "schema_ohlcv")
        self.assertTrue(version.is_current)

    def test_estado_valido_com_effective_until_ausente(self) -> None:
        version = self._version(effective_until=None)

        self.assertIsNone(version.effective_until)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetSchemaVersion)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._version_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetSchemaVersion(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetSchemaVersion)
        expected_types = {
            "schema_id": str,
            "schema_version": str,
            "version_description": str,
            "effective_from": str,
            "effective_until": str | None,
            "is_current": bool,
            "is_backward_compatible": bool,
            "created_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_flags_sao_booleanos(self) -> None:
        self.assertFalse(self._version(is_current=False).is_current)
        with self.assertRaisesRegex(TypeError, "is_current"):
            self._version(is_current="true")  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "is_backward_compatible"):
            self._version(is_backward_compatible=1)  # type: ignore[arg-type]

    def test_effective_until_deve_ser_string_ou_none(self) -> None:
        self.assertEqual(self._version(effective_until="2026-12-31").effective_until, "2026-12-31")
        self.assertIsNone(self._version(effective_until=None).effective_until)
        with self.assertRaisesRegex(TypeError, "effective_until"):
            self._version(effective_until=20261231)  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        version = self._version()

        self.assertNotIsInstance(version, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetSchemaVersion))
        )
        self.assertNotIsInstance(version.effective_until, dict)

    def test_contrato_e_dataclass_imutavel(self) -> None:
        version = self._version()

        self.assertTrue(is_dataclass(version))
        with self.assertRaises(FrozenInstanceError):
            version.schema_id = "outro"  # type: ignore[misc]

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
            "migrate",
            "compare",
            "validate",
            "interpret",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("migrate_schema", "compare_versions", "validate_compatibility"):
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
                    "historical.contracts.historical_dataset_schema_version",
                    source,
                )

    def test_nenhum_versionador_concreto_foi_criado_em_historical(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_schema_versioner.py",
            "schema_versioner.py",
            "schema_migration.py",
            "schema_compatibility_validator.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _version(self, **overrides: object) -> HistoricalDatasetSchemaVersion:
        payload = self._version_payload()
        payload.update(overrides)
        return HistoricalDatasetSchemaVersion(**payload)  # type: ignore[arg-type]

    def _version_payload(self) -> dict[str, object]:
        return {
            "schema_id": "schema_ohlcv",
            "schema_version": "1.0",
            "version_description": "Versao inicial do schema OHLCV historico",
            "effective_from": "2026-06-27T14:45:00-03:00",
            "effective_until": None,
            "is_current": True,
            "is_backward_compatible": True,
            "created_at": "2026-06-27T14:45:00-03:00",
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
