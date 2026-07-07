"""Contrato de relatorio consolidado de validacoes historicas."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts import (
    HistoricalDatasetValidationReport,
    HistoricalDatasetValidationResult,
)


CONTRACT_PATH = Path("historical/contracts/historical_dataset_validation_report.py")
REQUIRED_FIELDS = [
    "report_id",
    "datasets_validated",
    "total_records_checked",
    "total_invalid_records",
    "total_gaps",
    "total_duplicate_timestamps",
    "total_critical_errors",
    "total_warnings",
    "validation_results",
    "generated_at",
    "validator_version",
]


class HistoricalDatasetValidationReportContractTest(unittest.TestCase):
    """Protege o DTO oficial de relatorio de validacao historica."""

    def test_contrato_importa_e_cria_relatorio(self) -> None:
        report = self._report()

        self.assertIsInstance(report, HistoricalDatasetValidationReport)
        self.assertEqual(report.report_id, "validation_report_001")
        self.assertEqual(report.datasets_validated, 1)

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetValidationReport)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetValidationReport)

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)

    def test_validation_results_e_colecao_tipada(self) -> None:
        result = self._result()
        report = self._report(validation_results=(result,))

        self.assertEqual(report.validation_results, (result,))
        self.assertIsInstance(
            report.validation_results[0],
            HistoricalDatasetValidationResult,
        )

    def test_estado_vazio_e_permitido_quando_explicito(self) -> None:
        report = self._report(
            datasets_validated=0,
            total_records_checked=0,
            validation_results=(),
        )

        self.assertEqual(report.datasets_validated, 0)
        self.assertEqual(report.validation_results, ())

    def test_nao_aceita_dicionarios_livres_em_validation_results(self) -> None:
        with self.assertRaisesRegex(TypeError, "validation_results"):
            self._report(validation_results=[self._result()])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "HistoricalDatasetValidationResult"):
            self._report(validation_results=({"dataset_id": "WDO"},))  # type: ignore[arg-type]

    def test_contadores_devem_ser_inteiros_nao_negativos(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._report(total_gaps=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._report(total_warnings="1")  # type: ignore[arg-type]

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
        for term in ("sum(", "read_csv", "read_parquet", "connect", "export"):
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
                self.assertNotIn("HistoricalDatasetValidationReport", source)
                self.assertNotIn(
                    "historical.contracts.historical_dataset_validation_report",
                    source,
                )

    def test_nenhum_agregador_concreto_foi_criado(self) -> None:
        historical_files = [path.name for path in Path("historical").rglob("*.py")]

        self.assertNotIn("historical_dataset_validation_aggregator.py", historical_files)
        self.assertNotIn("historical_dataset_validation_reporter.py", historical_files)

    def _report(self, **overrides: object) -> HistoricalDatasetValidationReport:
        payload: dict[str, object] = {
            "report_id": "validation_report_001",
            "datasets_validated": 1,
            "total_records_checked": 100,
            "total_invalid_records": 0,
            "total_gaps": 0,
            "total_duplicate_timestamps": 0,
            "total_critical_errors": 0,
            "total_warnings": 0,
            "validation_results": (self._result(),),
            "generated_at": "2026-06-27T04:00:00-03:00",
            "validator_version": "1.0",
        }
        payload.update(overrides)
        return HistoricalDatasetValidationReport(**payload)  # type: ignore[arg-type]

    def _result(self) -> HistoricalDatasetValidationResult:
        return HistoricalDatasetValidationResult(
            dataset_id="WDO_1m_2025",
            is_valid=True,
            records_checked=100,
            invalid_records=0,
            gap_count=0,
            duplicate_timestamp_count=0,
            critical_errors=(),
            warnings=(),
            validated_at="2026-06-27T04:00:00-03:00",
            validator_version="1.0",
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
