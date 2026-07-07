"""Contrato historico de resumo de compatibilidade."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_compatibility_summary import (
    HistoricalDatasetCompatibilitySummary,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_compatibility_summary.py")
REQUIRED_FIELDS = [
    "dataset_id",
    "schema_id",
    "schema_version",
    "compatibility_level",
    "is_compatible",
    "incompatible_column_count",
    "missing_column_count",
    "additional_column_count",
    "analyzed_at",
    "analyzer_version",
]


class HistoricalDatasetCompatibilitySummaryContractTest(unittest.TestCase):
    """Protege o DTO oficial de resumo de compatibilidade historica."""

    def test_contrato_importa_e_cria_estado_compativel(self) -> None:
        summary = self._summary()

        self.assertIsInstance(summary, HistoricalDatasetCompatibilitySummary)
        self.assertTrue(summary.is_compatible)
        self.assertEqual(summary.compatibility_level, "FULL")

    def test_contrato_cria_estado_incompativel(self) -> None:
        summary = self._summary(
            is_compatible=False,
            compatibility_level="INCOMPATIBLE",
            incompatible_column_count=1,
            missing_column_count=1,
            additional_column_count=0,
        )

        self.assertFalse(summary.is_compatible)
        self.assertEqual(summary.missing_column_count, 1)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [
            field.name for field in fields(HistoricalDatasetCompatibilitySummary)
        ]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._summary_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetCompatibilitySummary(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetCompatibilitySummary)
        expected_types = {
            "dataset_id": str,
            "schema_id": str,
            "schema_version": str,
            "compatibility_level": str,
            "is_compatible": bool,
            "incompatible_column_count": int,
            "missing_column_count": int,
            "additional_column_count": int,
            "analyzed_at": str,
            "analyzer_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_contadores_devem_ser_inteiros_nao_negativos(self) -> None:
        self.assertEqual(
            self._summary(incompatible_column_count=0).incompatible_column_count,
            0,
        )
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._summary(missing_column_count=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._summary(additional_column_count="0")  # type: ignore[arg-type]

    def test_is_compatible_deve_ser_booleano(self) -> None:
        self.assertFalse(self._summary(is_compatible=False).is_compatible)
        with self.assertRaisesRegex(TypeError, "is_compatible"):
            self._summary(is_compatible="true")  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        summary = self._summary()

        self.assertNotIsInstance(summary, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetCompatibilitySummary))
        )

    def test_contrato_e_dataclass_imutavel(self) -> None:
        summary = self._summary()

        self.assertTrue(is_dataclass(summary))
        with self.assertRaises(FrozenInstanceError):
            summary.dataset_id = "outro"  # type: ignore[misc]

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
            "calculate",
            "interpret",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("generate_summary", "compare_schemas", "validate_dataset"):
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
                    "historical.contracts.historical_dataset_compatibility_summary",
                    source,
                )

    def test_nenhum_analisador_concreto_foi_criado_em_historical(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_compatibility_analyzer.py",
            "compatibility_analyzer.py",
            "compatibility_summary_generator.py",
            "dataset_schema_comparator.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _summary(self, **overrides: object) -> HistoricalDatasetCompatibilitySummary:
        payload = self._summary_payload()
        payload.update(overrides)
        return HistoricalDatasetCompatibilitySummary(**payload)  # type: ignore[arg-type]

    def _summary_payload(self) -> dict[str, object]:
        return {
            "dataset_id": "WDO_1m_2025",
            "schema_id": "schema_ohlcv",
            "schema_version": "1.0",
            "compatibility_level": "FULL",
            "is_compatible": True,
            "incompatible_column_count": 0,
            "missing_column_count": 0,
            "additional_column_count": 0,
            "analyzed_at": "2026-06-27T15:30:00-03:00",
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
