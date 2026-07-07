"""Contrato historico de fingerprint estrutural de dataset."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_fingerprint import (
    HistoricalDatasetFingerprint,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_fingerprint.py")
REQUIRED_FIELDS = [
    "dataset_id",
    "schema_id",
    "schema_version",
    "fingerprint_algorithm",
    "fingerprint_value",
    "generated_at",
    "generator_version",
]


class HistoricalDatasetFingerprintContractTest(unittest.TestCase):
    """Protege o DTO oficial de fingerprint historico."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        fingerprint = self._fingerprint()

        self.assertIsInstance(fingerprint, HistoricalDatasetFingerprint)
        self.assertEqual(fingerprint.dataset_id, "WDO_1m_2025")
        self.assertEqual(fingerprint.fingerprint_algorithm, "declared")

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetFingerprint)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._fingerprint_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetFingerprint(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetFingerprint)
        expected_types = {
            "dataset_id": str,
            "schema_id": str,
            "schema_version": str,
            "fingerprint_algorithm": str,
            "fingerprint_value": str,
            "generated_at": str,
            "generator_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_nao_usa_dicionarios_livres(self) -> None:
        fingerprint = self._fingerprint()

        self.assertNotIsInstance(fingerprint, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetFingerprint))
        )

    def test_contrato_e_dataclass_imutavel(self) -> None:
        fingerprint = self._fingerprint()

        self.assertTrue(is_dataclass(fingerprint))
        with self.assertRaises(FrozenInstanceError):
            fingerprint.dataset_id = "outro"  # type: ignore[misc]

    def test_contrato_nao_contem_logica_operacional_ou_io(self) -> None:
        imports = self._imports(CONTRACT_PATH)
        calls = self._calls(CONTRACT_PATH)
        source = CONTRACT_PATH.read_text(encoding="utf-8").lower()
        forbidden_imports = {
            "hashlib",
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
            "detect",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("hash", "sha256", "md5", "calculate_fingerprint"):
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
                    "historical.contracts.historical_dataset_fingerprint",
                    source,
                )

    def test_nenhum_gerador_de_fingerprint_foi_criado_em_historical(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_fingerprint_generator.py",
            "dataset_fingerprint_generator.py",
            "fingerprint_generator.py",
            "fingerprint_comparator.py",
            "change_detector.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _fingerprint(self, **overrides: object) -> HistoricalDatasetFingerprint:
        payload = self._fingerprint_payload()
        payload.update(overrides)
        return HistoricalDatasetFingerprint(**payload)  # type: ignore[arg-type]

    def _fingerprint_payload(self) -> dict[str, object]:
        return {
            "dataset_id": "WDO_1m_2025",
            "schema_id": "schema_ohlcv",
            "schema_version": "1.0",
            "fingerprint_algorithm": "declared",
            "fingerprint_value": "WDO_1m_2025_schema_ohlcv_1.0",
            "generated_at": "2026-06-27T15:45:00-03:00",
            "generator_version": "1.0",
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
