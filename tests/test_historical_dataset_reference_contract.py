"""Contrato historico de referencia logica de dataset."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_reference import HistoricalDatasetReference


CONTRACT_PATH = Path("historical/contracts/historical_dataset_reference.py")
REQUIRED_FIELDS = [
    "dataset_id",
    "dataset_name",
    "dataset_version",
    "symbol",
    "timeframe",
    "reference_version",
]


class HistoricalDatasetReferenceContractTest(unittest.TestCase):
    """Protege o DTO oficial de referencia historica."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        reference = self._reference()

        self.assertIsInstance(reference, HistoricalDatasetReference)
        self.assertEqual(reference.dataset_id, "WDO_1m_2025")
        self.assertEqual(reference.symbol, "WDO")

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetReference)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._reference_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetReference(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetReference)
        expected_types = {
            "dataset_id": str,
            "dataset_name": str,
            "dataset_version": str,
            "symbol": str,
            "timeframe": str,
            "reference_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_nao_usa_dicionarios_livres(self) -> None:
        reference = self._reference()

        self.assertNotIsInstance(reference, dict)
        self.assertFalse(any(field.type is dict for field in fields(HistoricalDatasetReference)))

    def test_contrato_e_dataclass_imutavel(self) -> None:
        reference = self._reference()

        self.assertTrue(is_dataclass(reference))
        with self.assertRaises(FrozenInstanceError):
            reference.dataset_id = "outro"  # type: ignore[misc]

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
            "resolve",
            "query",
            "catalog",
            "provider.",
            "generate",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("resolve_reference", "query_provider", "query_catalog"):
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
                    "historical.contracts.historical_dataset_reference",
                    source,
                )

    def test_nenhum_resolvedor_concreto_foi_criado(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_reference_resolver.py",
            "dataset_reference_resolver.py",
            "reference_resolver.py",
            "catalog_lookup.py",
            "provider_lookup.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _reference(self, **overrides: object) -> HistoricalDatasetReference:
        payload = self._reference_payload()
        payload.update(overrides)
        return HistoricalDatasetReference(**payload)  # type: ignore[arg-type]

    def _reference_payload(self) -> dict[str, object]:
        return {
            "dataset_id": "WDO_1m_2025",
            "dataset_name": "WDO 1m 2025",
            "dataset_version": "1.0",
            "symbol": "WDO",
            "timeframe": "1m",
            "reference_version": "1.0",
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
