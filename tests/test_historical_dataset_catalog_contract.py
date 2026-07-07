"""Contrato historico de catalogo logico de datasets."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_catalog import HistoricalDatasetCatalog
from historical.contracts.historical_dataset_catalog_entry import (
    HistoricalDatasetCatalogEntry,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_catalog.py")
REQUIRED_FIELDS = [
    "catalog_id",
    "catalog_name",
    "entries",
    "total_datasets",
    "catalog_version",
    "generated_at",
]


class HistoricalDatasetCatalogContractTest(unittest.TestCase):
    """Protege o DTO oficial de catalogo historico."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        catalog = self._catalog(entries=(self._entry(),), total_datasets=1)

        self.assertIsInstance(catalog, HistoricalDatasetCatalog)
        self.assertEqual(catalog.catalog_id, "catalog_001")
        self.assertEqual(catalog.entries[0].dataset_id, "WDO_1m_2025")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        catalog = self._catalog(entries=(), total_datasets=0)

        self.assertEqual(catalog.entries, ())
        self.assertEqual(catalog.total_datasets, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetCatalog)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._catalog_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetCatalog(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetCatalog)
        expected_types = {
            "catalog_id": str,
            "catalog_name": str,
            "entries": tuple[HistoricalDatasetCatalogEntry, ...],
            "total_datasets": int,
            "catalog_version": str,
            "generated_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_entries_deve_ser_colecao_tipada_de_catalog_entry(self) -> None:
        entry = self._entry()

        self.assertEqual(self._catalog(entries=(entry,)).entries, (entry,))
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._catalog(entries=[entry])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetCatalogEntry"):
            self._catalog(entries=({"dataset_id": "WDO"},))  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        catalog = self._catalog()

        self.assertNotIsInstance(catalog, dict)
        self.assertFalse(any(field.type is dict for field in fields(HistoricalDatasetCatalog)))
        self.assertFalse(any(isinstance(entry, dict) for entry in catalog.entries))

    def test_total_datasets_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._catalog(total_datasets=0).total_datasets, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._catalog(total_datasets=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._catalog(total_datasets="1")  # type: ignore[arg-type]

    def test_contrato_e_dataclass_imutavel(self) -> None:
        catalog = self._catalog()

        self.assertTrue(is_dataclass(catalog))
        with self.assertRaises(FrozenInstanceError):
            catalog.catalog_id = "outro"  # type: ignore[misc]

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
            "connect",
            "filter",
            "search",
            "persist",
            "cache",
            "index",
            "sort",
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
                self.assertNotIn("historical.contracts.historical_dataset_catalog", source)

    def test_nenhum_catalogo_concreto_foi_criado_fora_de_contracts(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        self.assertNotIn("historical_dataset_catalog.py", historical_files)
        self.assertNotIn("historical_catalog.py", historical_files)

    def _catalog(self, **overrides: object) -> HistoricalDatasetCatalog:
        payload = self._catalog_payload()
        payload.update(overrides)
        return HistoricalDatasetCatalog(**payload)  # type: ignore[arg-type]

    def _catalog_payload(self) -> dict[str, object]:
        return {
            "catalog_id": "catalog_001",
            "catalog_name": "Catalogo historico oficial",
            "entries": (self._entry(),),
            "total_datasets": 1,
            "catalog_version": "1.0",
            "generated_at": "2026-06-27T05:45:00-03:00",
        }

    def _entry(self) -> HistoricalDatasetCatalogEntry:
        return HistoricalDatasetCatalogEntry(
            dataset_id="WDO_1m_2025",
            dataset_name="WDO 1m 2025",
            provider_name="historical",
            symbol="WDO",
            timeframe="1m",
            start_timestamp="2025-01-01T09:00:00-03:00",
            end_timestamp="2025-12-30T18:00:00-03:00",
            record_count=100,
            validation_status="VALIDATED",
            cataloged_at="2026-06-27T05:30:00-03:00",
            metadata_version="1.0",
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
