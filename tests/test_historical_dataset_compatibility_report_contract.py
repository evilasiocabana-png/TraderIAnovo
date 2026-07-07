"""Contrato historico de relatorio de compatibilidade."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts.historical_dataset_compatibility import (
    HistoricalDatasetCompatibility,
)
from historical.contracts.historical_dataset_compatibility_report import (
    HistoricalDatasetCompatibilityReport,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_compatibility_report.py")
REQUIRED_FIELDS = [
    "report_id",
    "report_name",
    "compatibility_results",
    "total_datasets_analyzed",
    "compatible_datasets",
    "incompatible_datasets",
    "generated_at",
    "analyzer_version",
]


class HistoricalDatasetCompatibilityReportContractTest(unittest.TestCase):
    """Protege o DTO oficial de relatorio de compatibilidade historica."""

    def test_contrato_importa_e_cria_com_valores_validos(self) -> None:
        report = self._report(
            compatibility_results=(self._compatibility(),),
            total_datasets_analyzed=1,
            compatible_datasets=1,
            incompatible_datasets=0,
        )

        self.assertIsInstance(report, HistoricalDatasetCompatibilityReport)
        self.assertEqual(report.report_id, "compatibility_report_001")
        self.assertEqual(report.compatibility_results[0].dataset_id, "WDO_1m_2025")

    def test_estado_vazio_e_permitido_quando_explicitamente_definido(self) -> None:
        report = self._report(
            compatibility_results=(),
            total_datasets_analyzed=0,
            compatible_datasets=0,
            incompatible_datasets=0,
        )

        self.assertEqual(report.compatibility_results, ())
        self.assertEqual(report.total_datasets_analyzed, 0)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [
            field.name for field in fields(HistoricalDatasetCompatibilityReport)
        ]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_campos_sao_obrigatorios_no_construtor(self) -> None:
        payload = self._report_payload()

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                partial_payload = dict(payload)
                partial_payload.pop(field_name)
                with self.assertRaises(TypeError):
                    HistoricalDatasetCompatibilityReport(**partial_payload)  # type: ignore[arg-type]

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetCompatibilityReport)
        expected_types = {
            "report_id": str,
            "report_name": str,
            "compatibility_results": tuple[HistoricalDatasetCompatibility, ...],
            "total_datasets_analyzed": int,
            "compatible_datasets": int,
            "incompatible_datasets": int,
            "generated_at": str,
            "analyzer_version": str,
        }

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)
                self.assertEqual(hints[field_name], expected_types[field_name])

    def test_compatibility_results_deve_ser_colecao_tipada(self) -> None:
        compatibility = self._compatibility()

        self.assertEqual(
            self._report(compatibility_results=(compatibility,)).compatibility_results,
            (compatibility,),
        )
        with self.assertRaisesRegex(TypeError, "tuple"):
            self._report(compatibility_results=[compatibility])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetCompatibility"):
            self._report(compatibility_results=({"dataset_id": "WDO"},))  # type: ignore[arg-type]

    def test_contadores_devem_ser_inteiros_nao_negativos(self) -> None:
        self.assertEqual(self._report(total_datasets_analyzed=0).total_datasets_analyzed, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._report(compatible_datasets=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._report(incompatible_datasets="0")  # type: ignore[arg-type]

    def test_nao_usa_dicionarios_livres(self) -> None:
        report = self._report()

        self.assertNotIsInstance(report, dict)
        self.assertFalse(
            any(field.type is dict for field in fields(HistoricalDatasetCompatibilityReport))
        )
        self.assertFalse(
            any(isinstance(result, dict) for result in report.compatibility_results)
        )

    def test_contrato_e_dataclass_imutavel(self) -> None:
        report = self._report()

        self.assertTrue(is_dataclass(report))
        with self.assertRaises(FrozenInstanceError):
            report.report_id = "outro"  # type: ignore[misc]

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
            "persist",
            "cache",
        ):
            self.assertNotIn(term, source)
        for call_name in ("analyze", "run_analysis", "compare_schemas"):
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
                    "historical.contracts.historical_dataset_compatibility_report",
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
            "dataset_schema_comparator.py",
            "compatibility_batch_analyzer.py",
        )
        for file_name in forbidden_names:
            with self.subTest(file=file_name):
                self.assertNotIn(file_name, historical_files)

    def _report(self, **overrides: object) -> HistoricalDatasetCompatibilityReport:
        payload = self._report_payload()
        payload.update(overrides)
        return HistoricalDatasetCompatibilityReport(**payload)  # type: ignore[arg-type]

    def _report_payload(self) -> dict[str, object]:
        return {
            "report_id": "compatibility_report_001",
            "report_name": "Relatorio de compatibilidade historica",
            "compatibility_results": (self._compatibility(),),
            "total_datasets_analyzed": 1,
            "compatible_datasets": 1,
            "incompatible_datasets": 0,
            "generated_at": "2026-06-27T15:15:00-03:00",
            "analyzer_version": "1.0",
        }

    def _compatibility(self) -> HistoricalDatasetCompatibility:
        return HistoricalDatasetCompatibility(
            dataset_id="WDO_1m_2025",
            schema_id="schema_ohlcv",
            schema_version="1.0",
            is_compatible=True,
            compatibility_level="FULL",
            incompatible_columns=(),
            missing_columns=(),
            additional_columns=(),
            compatibility_notes=("Compatibilidade declarada para teste de contrato",),
            analyzed_at="2026-06-27T15:00:00-03:00",
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
