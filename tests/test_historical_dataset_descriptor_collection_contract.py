"""Contrato historico de colecao de descritores."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_compatibility_summary import (
    HistoricalDatasetCompatibilitySummary,
)
from historical.contracts.historical_dataset_descriptor import HistoricalDatasetDescriptor
from historical.contracts.historical_dataset_descriptor_collection import (
    HistoricalDatasetDescriptorCollection,
)
from historical.contracts.historical_dataset_fingerprint import (
    HistoricalDatasetFingerprint,
)
from historical.contracts.historical_dataset_identity import HistoricalDatasetIdentity
from historical.contracts.historical_dataset_metadata import HistoricalDatasetMetadata
from historical.contracts.historical_dataset_reference import HistoricalDatasetReference
from historical.contracts.historical_dataset_validation_summary import (
    HistoricalDatasetValidationSummary,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_descriptor_collection.py")
REQUIRED_FIELDS = [
    "collection_id",
    "collection_name",
    "descriptors",
    "total_descriptors",
    "created_at",
    "collection_version",
]


class HistoricalDatasetDescriptorCollectionContractTest(unittest.TestCase):
    """Protege o DTO oficial de colecao de descritores historicos."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        collection = self._collection(descriptors=(self._descriptor(),), total_descriptors=1)

        self.assertIsInstance(collection, HistoricalDatasetDescriptorCollection)
        self.assertEqual(collection.collection_id, "descriptor_collection_001")
        self.assertEqual(collection.descriptors[0].identity.dataset_id, "WDO_1m_2025")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        collection = self._collection(descriptors=(), total_descriptors=0)

        self.assertEqual(collection.descriptors, ())
        self.assertEqual(collection.total_descriptors, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [
            field.name for field in fields(HistoricalDatasetDescriptorCollection)
        ]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._collection_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetDescriptorCollection(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetDescriptorCollection)
        expected_types = {
            "collection_id": str,
            "collection_name": str,
            "descriptors": tuple[HistoricalDatasetDescriptor, ...],
            "total_descriptors": int,
            "created_at": str,
            "collection_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_descriptors_deve_ser_colecao_tipada(self) -> None:
        descriptor = self._descriptor()

        self.assertEqual(self._collection(descriptors=(descriptor,)).descriptors, (descriptor,))
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._collection(descriptors=[descriptor])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetDescriptor"):
            self._collection(descriptors=({"dataset_id": "WDO"},))  # type: ignore[arg-type]

    def test_total_descriptors_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._collection(total_descriptors=0).total_descriptors, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._collection(total_descriptors=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._collection(total_descriptors="0")  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        collection = self._collection()

        self.assertNotIsInstance(collection, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetDescriptorCollection))
        )
        self.assertFalse(any(isinstance(descriptor, dict) for descriptor in collection.descriptors))

    def test_contrato_e_dataclass_imutavel(self) -> None:
        collection = self._collection()

        self.assertTrue(is_dataclass(collection))
        with self.assertRaises(FrozenInstanceError):
            collection.collection_id = "outro"  # type: ignore[misc]

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
            "validate_dataset",
            "filter",
            "sort",
            "persist",
            "cache",
            "factory",
            "builder",
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
                    "historical.contracts.historical_dataset_descriptor_collection",
                    source,
                )

    def test_nenhum_builder_provider_validator_resolver_foi_criado(self) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]

        forbidden_names = (
            "historical_dataset_descriptor_collection_builder.py",
            "dataset_descriptor_collection_builder.py",
            "historical_dataset_descriptor_factory.py",
            "dataset_descriptor_factory.py",
            "historical_dataset_provider.py",
            "historical_dataset_validator.py",
            "historical_dataset_reference_resolver.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _collection(self, **overrides: object) -> HistoricalDatasetDescriptorCollection:
        payload = self._collection_payload()
        payload.update(overrides)
        return HistoricalDatasetDescriptorCollection(**payload)  # type: ignore[arg-type]

    def _collection_payload(self) -> dict[str, object]:
        return {
            "collection_id": "descriptor_collection_001",
            "collection_name": "Colecao historica de descritores",
            "descriptors": (self._descriptor(),),
            "total_descriptors": 1,
            "created_at": "2026-06-27T17:45:00-03:00",
            "collection_version": "1.0",
        }

    def _descriptor(self) -> HistoricalDatasetDescriptor:
        return HistoricalDatasetDescriptor(
            identity=self._identity(),
            reference=self._reference(),
            metadata=self._metadata(),
            validation_summary=self._validation_summary(),
            compatibility_summary=self._compatibility_summary(),
            fingerprint=self._fingerprint(),
            descriptor_version="1.0",
            created_at="2026-06-27T17:30:00-03:00",
        )

    def _identity(self) -> HistoricalDatasetIdentity:
        return HistoricalDatasetIdentity(
            dataset_id="WDO_1m_2025",
            dataset_name="WDO 1m 2025",
            provider_id="provider_csv",
            source_id="source_local_history",
            symbol="WDO",
            timeframe="1m",
            dataset_version="1.0",
            created_at="2026-06-27T16:30:00-03:00",
            identity_version="1.0",
        )

    def _reference(self) -> HistoricalDatasetReference:
        return HistoricalDatasetReference(
            dataset_id="WDO_1m_2025",
            dataset_name="WDO 1m 2025",
            dataset_version="1.0",
            symbol="WDO",
            timeframe="1m",
            reference_version="1.0",
        )

    def _metadata(self) -> HistoricalDatasetMetadata:
        return HistoricalDatasetMetadata(
            dataset_id="WDO_1m_2025",
            dataset_name="WDO 1m 2025",
            provider_name="historical",
            symbol="WDO",
            timeframe="1m",
            start_timestamp="2025-01-01T09:00:00-03:00",
            end_timestamp="2025-12-30T18:00:00-03:00",
            record_count=100,
            timezone="America/Sao_Paulo",
            source_description="Dataset historico de teste",
            created_at="2026-06-27T04:00:00-03:00",
            metadata_version="1.0",
        )

    def _validation_summary(self) -> HistoricalDatasetValidationSummary:
        return HistoricalDatasetValidationSummary(
            dataset_id="WDO_1m_2025",
            overall_status="VALID",
            quality_score=1.0,
            records_checked=100,
            invalid_records=0,
            gap_count=0,
            duplicate_timestamp_count=0,
            critical_error_count=0,
            warning_count=0,
            validated_at="2026-06-27T15:30:00-03:00",
            validator_version="1.0",
        )

    def _compatibility_summary(self) -> HistoricalDatasetCompatibilitySummary:
        return HistoricalDatasetCompatibilitySummary(
            dataset_id="WDO_1m_2025",
            schema_id="schema_ohlcv",
            schema_version="1.0",
            compatibility_level="FULL",
            is_compatible=True,
            incompatible_column_count=0,
            missing_column_count=0,
            additional_column_count=0,
            analyzed_at="2026-06-27T15:30:00-03:00",
            analyzer_version="1.0",
        )

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
