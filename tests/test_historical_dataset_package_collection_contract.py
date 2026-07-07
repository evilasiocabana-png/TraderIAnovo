"""Contrato historico de colecao de pacotes de datasets."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_compatibility_summary import (
    HistoricalDatasetCompatibilitySummary,
)
from historical.contracts.historical_dataset_fingerprint import (
    HistoricalDatasetFingerprint,
)
from historical.contracts.historical_dataset_identity import HistoricalDatasetIdentity
from historical.contracts.historical_dataset_manifest import HistoricalDatasetManifest
from historical.contracts.historical_dataset_metadata import HistoricalDatasetMetadata
from historical.contracts.historical_dataset_package import HistoricalDatasetPackage
from historical.contracts.historical_dataset_package_collection import (
    HistoricalDatasetPackageCollection,
)
from historical.contracts.historical_dataset_schema_version import (
    HistoricalDatasetSchemaVersion,
)
from historical.contracts.historical_dataset_validation_summary import (
    HistoricalDatasetValidationSummary,
)

CONTRACT_PATH = Path("historical/contracts/historical_dataset_package_collection.py")
REQUIRED_FIELDS = [
    "collection_id",
    "collection_name",
    "packages",
    "total_packages",
    "created_at",
    "collection_version",
]


class HistoricalDatasetPackageCollectionContractTest(unittest.TestCase):
    """Protege o DTO oficial de colecao de pacotes historicos."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        collection = self._collection(packages=(self._package(),), total_packages=1)

        self.assertIsInstance(collection, HistoricalDatasetPackageCollection)
        self.assertEqual(collection.collection_id, "package_collection_001")
        self.assertEqual(collection.packages[0].package_id, "historical_package_001")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        collection = self._collection(packages=(), total_packages=0)

        self.assertEqual(collection.packages, ())
        self.assertEqual(collection.total_packages, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [
            field.name for field in fields(HistoricalDatasetPackageCollection)
        ]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._collection_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetPackageCollection(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetPackageCollection)
        expected_types = {
            "collection_id": str,
            "collection_name": str,
            "packages": tuple[HistoricalDatasetPackage, ...],
            "total_packages": int,
            "created_at": str,
            "collection_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_packages_deve_ser_colecao_tipada(self) -> None:
        package = self._package()

        self.assertEqual(self._collection(packages=(package,)).packages, (package,))
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._collection(packages=[package])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetPackage"):
            self._collection(packages=({"package_id": "WDO"},))  # type: ignore[arg-type]

    def test_total_packages_deve_ser_inteiro_nao_negativo(self) -> None:
        self.assertEqual(self._collection(total_packages=0).total_packages, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._collection(total_packages=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._collection(total_packages="0")  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        collection = self._collection()

        self.assertNotIsInstance(collection, dict)
        self.assertFalse(
            any(
                field.type is dict
                for field in fields(HistoricalDatasetPackageCollection)
            )
        )
        self.assertFalse(any(isinstance(package, dict) for package in collection.packages))

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
            "compress",
            "zipfile",
            "tarfile",
            "import_dataset",
            "export_dataset",
            "discover",
            "sync",
            "sort",
            "filter",
            "resolve",
            "query",
            "catalog",
            "provider.",
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
                    "historical.contracts.historical_dataset_package_collection",
                    source,
                )

    def test_nenhum_importer_exporter_provider_builder_ou_packager_foi_criado(
        self,
    ) -> None:
        historical_files = [
            path.name
            for path in Path("historical").rglob("*.py")
            if "contracts" not in path.parts
        ]
        forbidden_names = (
            "historical_dataset_importer.py",
            "historical_dataset_exporter.py",
            "historical_dataset_loader.py",
            "historical_dataset_provider.py",
            "historical_dataset_packager.py",
            "historical_dataset_package_collection_builder.py",
            "historical_dataset_package_collection_factory.py",
        )

        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _collection(self, **overrides: object) -> HistoricalDatasetPackageCollection:
        payload = self._collection_payload()
        payload.update(overrides)
        return HistoricalDatasetPackageCollection(**payload)  # type: ignore[arg-type]

    def _collection_payload(self) -> dict[str, object]:
        return {
            "collection_id": "package_collection_001",
            "collection_name": "Colecao historica de pacotes",
            "packages": (self._package(),),
            "total_packages": 1,
            "created_at": "2026-06-27T19:00:00-03:00",
            "collection_version": "1.0",
        }

    def _package(self) -> HistoricalDatasetPackage:
        return HistoricalDatasetPackage(
            package_id="historical_package_001",
            package_name="Pacote historico WDO",
            package_description="Pacote logico de manifests historicos WDO.",
            manifests=(self._manifest(),),
            total_datasets=1,
            package_version="1.0",
            created_at="2026-06-27T18:45:00-03:00",
        )

    def _manifest(self) -> HistoricalDatasetManifest:
        return HistoricalDatasetManifest(
            identity=self._identity(),
            metadata=self._metadata(),
            schema_version=self._schema_version(),
            fingerprint=self._fingerprint(),
            validation_summary=self._validation_summary(),
            compatibility_summary=self._compatibility_summary(),
            manifest_version="1.0",
            generated_at="2026-06-27T18:00:00-03:00",
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

    def _schema_version(self) -> HistoricalDatasetSchemaVersion:
        return HistoricalDatasetSchemaVersion(
            schema_id="schema_ohlcv",
            schema_version="1.0",
            version_description="Versao inicial do schema OHLCV historico",
            effective_from="2026-06-27T14:45:00-03:00",
            effective_until=None,
            is_current=True,
            is_backward_compatible=True,
            created_at="2026-06-27T14:45:00-03:00",
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
