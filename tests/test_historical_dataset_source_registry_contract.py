"""Contrato historico de registry logico de origens."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_source_descriptor import (
    HistoricalDatasetSourceDescriptor,
)
from historical.contracts.historical_dataset_source_registry import (
    HistoricalDatasetSourceRegistry,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_source_registry.py")
REQUIRED_FIELDS = [
    "registry_id",
    "registry_name",
    "sources",
    "total_sources",
    "registry_version",
    "generated_at",
]


class HistoricalDatasetSourceRegistryContractTest(unittest.TestCase):
    """Protege o DTO oficial de registry historico de origens."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        registry = self._registry(sources=(self._source(),), total_sources=1)

        self.assertIsInstance(registry, HistoricalDatasetSourceRegistry)
        self.assertEqual(registry.registry_id, "source_registry_001")
        self.assertEqual(registry.sources[0].source_id, "source_local_history")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        registry = self._registry(sources=(), total_sources=0)

        self.assertEqual(registry.sources, ())
        self.assertEqual(registry.total_sources, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetSourceRegistry)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._registry_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetSourceRegistry(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetSourceRegistry)
        expected_types = {
            "registry_id": str,
            "registry_name": str,
            "sources": tuple[HistoricalDatasetSourceDescriptor, ...],
            "total_sources": int,
            "registry_version": str,
            "generated_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_sources_deve_ser_colecao_tipada_de_descriptor(self) -> None:
        source = self._source()

        self.assertEqual(self._registry(sources=(source,)).sources, (source,))
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._registry(sources=[source])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetSourceDescriptor"):
            self._registry(sources=({"source_id": "source_local_history"},))  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        registry = self._registry()

        self.assertNotIsInstance(registry, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetSourceRegistry))
        )
        self.assertFalse(any(isinstance(source, dict) for source in registry.sources))

    def test_total_sources_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._registry(total_sources=0).total_sources, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._registry(total_sources=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._registry(total_sources="1")  # type: ignore[arg-type]

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
            "connect",
            "discover",
            "sync",
            "availability",
            "register",
            "persist",
            "cache",
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
                self.assertNotIn(
                    "historical.contracts.historical_dataset_source_registry",
                    source,
                )

    def test_nenhum_registry_concreto_foi_criado_fora_de_contracts(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        self.assertNotIn("historical_dataset_source_registry.py", historical_files)
        self.assertNotIn("historical_source_registry.py", historical_files)
        self.assertNotIn("source_registry.py", historical_files)

    def _registry(self, **overrides: object) -> HistoricalDatasetSourceRegistry:
        payload = self._registry_payload()
        payload.update(overrides)
        return HistoricalDatasetSourceRegistry(**payload)  # type: ignore[arg-type]

    def _registry_payload(self) -> dict[str, object]:
        return {
            "registry_id": "source_registry_001",
            "registry_name": "Registry historico de origens",
            "sources": (self._source(),),
            "total_sources": 1,
            "registry_version": "1.0",
            "generated_at": "2026-06-27T12:45:00-03:00",
        }

    def _source(self) -> HistoricalDatasetSourceDescriptor:
        return HistoricalDatasetSourceDescriptor(
            source_id="source_local_history",
            source_name="Origem historica local",
            source_description="Descritor arquitetural de origem historica",
            provider_id="provider_csv",
            supported_symbols=("WDO",),
            supported_timeframes=("1m",),
            supported_formats=("csv",),
            is_read_only=True,
            is_available=True,
            created_at="2026-06-27T12:30:00-03:00",
            source_version="1.0",
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
