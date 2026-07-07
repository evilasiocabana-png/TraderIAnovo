"""Contrato historico de registry de fingerprints."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_fingerprint import (
    HistoricalDatasetFingerprint,
)
from historical.contracts.historical_dataset_fingerprint_registry import (
    HistoricalDatasetFingerprintRegistry,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_fingerprint_registry.py")
REQUIRED_FIELDS = [
    "registry_id",
    "registry_name",
    "fingerprints",
    "total_fingerprints",
    "registry_version",
    "generated_at",
]


class HistoricalDatasetFingerprintRegistryContractTest(unittest.TestCase):
    """Protege o DTO oficial de registry historico de fingerprints."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        registry = self._registry(fingerprints=(self._fingerprint(),), total_fingerprints=1)

        self.assertIsInstance(registry, HistoricalDatasetFingerprintRegistry)
        self.assertEqual(registry.registry_id, "fingerprint_registry_001")
        self.assertEqual(registry.fingerprints[0].dataset_id, "WDO_1m_2025")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        registry = self._registry(fingerprints=(), total_fingerprints=0)

        self.assertEqual(registry.fingerprints, ())
        self.assertEqual(registry.total_fingerprints, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetFingerprintRegistry)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._registry_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetFingerprintRegistry(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetFingerprintRegistry)
        expected_types = {
            "registry_id": str,
            "registry_name": str,
            "fingerprints": tuple[HistoricalDatasetFingerprint, ...],
            "total_fingerprints": int,
            "registry_version": str,
            "generated_at": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_fingerprints_deve_ser_colecao_tipada(self) -> None:
        fingerprint = self._fingerprint()

        self.assertEqual(
            self._registry(fingerprints=(fingerprint,)).fingerprints,
            (fingerprint,),
        )
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._registry(fingerprints=[fingerprint])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetFingerprint"):
            self._registry(fingerprints=({"dataset_id": "WDO"},))  # type: ignore[arg-type]

    def test_total_fingerprints_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._registry(total_fingerprints=0).total_fingerprints, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._registry(total_fingerprints=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._registry(total_fingerprints="0")  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        registry = self._registry()

        self.assertNotIsInstance(registry, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetFingerprintRegistry))
        )
        self.assertFalse(any(isinstance(fingerprint, dict) for fingerprint in registry.fingerprints))

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
            "detect",
            "sync",
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("hash", "sha256", "md5", "calculate_fingerprint", "audit"):
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
                    "historical.contracts.historical_dataset_fingerprint_registry",
                    source,
                )

    def test_nenhum_registry_gerador_ou_comparador_concreto_foi_criado(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_fingerprint_registry.py",
            "fingerprint_registry.py",
            "historical_dataset_fingerprint_generator.py",
            "dataset_fingerprint_generator.py",
            "fingerprint_generator.py",
            "fingerprint_comparator.py",
            "fingerprint_auditor.py",
            "change_detector.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _registry(self, **overrides: object) -> HistoricalDatasetFingerprintRegistry:
        payload = self._registry_payload()
        payload.update(overrides)
        return HistoricalDatasetFingerprintRegistry(**payload)  # type: ignore[arg-type]

    def _registry_payload(self) -> dict[str, object]:
        return {
            "registry_id": "fingerprint_registry_001",
            "registry_name": "Registry historico de fingerprints",
            "fingerprints": (self._fingerprint(),),
            "total_fingerprints": 1,
            "registry_version": "1.0",
            "generated_at": "2026-06-27T16:15:00-03:00",
        }

    def _fingerprint(self) -> HistoricalDatasetFingerprint:
        return HistoricalDatasetFingerprint(
            dataset_id="WDO_1m_2025",
            schema_id="schema_ohlcv",
            schema_version="1.0",
            fingerprint_algorithm="declared",
            fingerprint_value="WDO_1m_2025_schema_ohlcv_1.0",
            generated_at="2026-06-27T15:45:00-03:00",
            generator_version="1.0",
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
