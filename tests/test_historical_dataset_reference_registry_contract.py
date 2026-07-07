"""Contrato historico de registry de referencias."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_reference import HistoricalDatasetReference
from historical.contracts.historical_dataset_reference_registry import (
    HistoricalDatasetReferenceRegistry,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_reference_registry.py")
REQUIRED_FIELDS = [
    "registry_id",
    "registry_name",
    "references",
    "total_references",
    "registry_version",
    "generated_at",
]


class HistoricalDatasetReferenceRegistryContractTest(unittest.TestCase):
    """Protege o DTO oficial de registry historico de referencias."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        registry = self._registry(references=(self._reference(),), total_references=1)

        self.assertIsInstance(registry, HistoricalDatasetReferenceRegistry)
        self.assertEqual(registry.registry_id, "reference_registry_001")
        self.assertEqual(registry.references[0].dataset_id, "WDO_1m_2025")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        registry = self._registry(references=(), total_references=0)

        self.assertEqual(registry.references, ())
        self.assertEqual(registry.total_references, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetReferenceRegistry)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._registry_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetReferenceRegistry(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetReferenceRegistry)
        expected_types = {
            "registry_id": str,
            "registry_name": str,
            "references": tuple[HistoricalDatasetReference, ...],
            "total_references": int,
            "registry_version": str,
            "generated_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_references_deve_ser_colecao_tipada(self) -> None:
        reference = self._reference()

        self.assertEqual(self._registry(references=(reference,)).references, (reference,))
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._registry(references=[reference])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetReference"):
            self._registry(references=({"dataset_id": "WDO"},))  # type: ignore[arg-type]

    def test_total_references_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._registry(total_references=0).total_references, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._registry(total_references=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._registry(total_references="0")  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        registry = self._registry()

        self.assertNotIsInstance(registry, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetReferenceRegistry))
        )
        self.assertFalse(any(isinstance(reference, dict) for reference in registry.references))

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
            "resolve",
            "discover",
            "sync",
            "query",
            "catalog",
            "provider.",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("resolve_reference", "sync_registry", "discover_references"):
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
                    "historical.contracts.historical_dataset_reference_registry",
                    source,
                )

    def test_nenhum_registry_concreto_foi_criado_fora_de_contracts(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_reference_registry.py",
            "reference_registry.py",
            "historical_dataset_reference_resolver.py",
            "dataset_reference_resolver.py",
            "reference_resolver.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _registry(self, **overrides: object) -> HistoricalDatasetReferenceRegistry:
        payload = self._registry_payload()
        payload.update(overrides)
        return HistoricalDatasetReferenceRegistry(**payload)  # type: ignore[arg-type]

    def _registry_payload(self) -> dict[str, object]:
        return {
            "registry_id": "reference_registry_001",
            "registry_name": "Registry historico de referencias",
            "references": (self._reference(),),
            "total_references": 1,
            "registry_version": "1.0",
            "generated_at": "2026-06-27T17:00:00-03:00",
        }

    def _reference(self) -> HistoricalDatasetReference:
        return HistoricalDatasetReference(
            dataset_id="WDO_1m_2025",
            dataset_name="WDO 1m 2025",
            dataset_version="1.0",
            symbol="WDO",
            timeframe="1m",
            reference_version="1.0",
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
