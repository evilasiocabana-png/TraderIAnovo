"""Contrato de resumo executivo de validacao historica."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts import HistoricalDatasetValidationSummary


CONTRACT_PATH = Path("historical/contracts/historical_dataset_validation_summary.py")
REQUIRED_FIELDS = [
    "dataset_id",
    "overall_status",
    "quality_score",
    "records_checked",
    "invalid_records",
    "gap_count",
    "duplicate_timestamp_count",
    "critical_error_count",
    "warning_count",
    "validated_at",
    "validator_version",
]


class HistoricalDatasetValidationSummaryContractTest(unittest.TestCase):
    """Protege DTO de resumo de qualidade historica."""

    def test_contrato_importa_e_cria_estado_valido(self) -> None:
        summary = self._summary()

        self.assertIsInstance(summary, HistoricalDatasetValidationSummary)
        self.assertEqual(summary.dataset_id, "WDO_1m_2025")
        self.assertEqual(summary.overall_status, "PASSED")

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetValidationSummary)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetValidationSummary)

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)

    def test_estado_invalido_e_representado_sem_dicionario_livre(self) -> None:
        summary = self._summary(
            overall_status="FAILED",
            quality_score=42.0,
            invalid_records=5,
            critical_error_count=1,
            warning_count=2,
        )

        self.assertEqual(summary.overall_status, "FAILED")
        self.assertEqual(summary.critical_error_count, 1)
        self.assertNotIsInstance(summary, dict)

    def test_nao_aceita_campos_livres_de_erros_ou_alertas(self) -> None:
        contract_fields = {field.name for field in fields(HistoricalDatasetValidationSummary)}

        self.assertNotIn("errors", contract_fields)
        self.assertNotIn("warnings", contract_fields)
        self.assertNotIn("critical_errors", contract_fields)

    def test_contadores_devem_ser_inteiros_nao_negativos(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._summary(gap_count=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._summary(warning_count="1")  # type: ignore[arg-type]

    def test_quality_score_deve_ser_numerico_sem_calculo_automatico(self) -> None:
        self.assertEqual(self._summary(quality_score=80).quality_score, 80)
        with self.assertRaisesRegex(TypeError, "quality_score"):
            self._summary(quality_score="100")  # type: ignore[arg-type]

    def test_contrato_e_dataclass_imutavel(self) -> None:
        summary = self._summary()

        self.assertTrue(is_dataclass(summary))
        with self.assertRaises(FrozenInstanceError):
            summary.quality_score = 0.0  # type: ignore[misc]

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
        for term in ("quality_score =", "read_csv", "read_parquet", "connect", "export"):
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
                self.assertNotIn("HistoricalDatasetValidationSummary", source)
                self.assertNotIn(
                    "historical.contracts.historical_dataset_validation_summary",
                    source,
                )

    def test_nenhum_servico_concreto_foi_criado(self) -> None:
        historical_files = [path.name for path in Path("historical").rglob("*.py")]

        self.assertNotIn("historical_dataset_validation_summary_service.py", historical_files)
        self.assertNotIn("historical_dataset_quality_service.py", historical_files)

    def _summary(self, **overrides: object) -> HistoricalDatasetValidationSummary:
        payload: dict[str, object] = {
            "dataset_id": "WDO_1m_2025",
            "overall_status": "PASSED",
            "quality_score": 100.0,
            "records_checked": 100,
            "invalid_records": 0,
            "gap_count": 0,
            "duplicate_timestamp_count": 0,
            "critical_error_count": 0,
            "warning_count": 0,
            "validated_at": "2026-06-27T04:00:00-03:00",
            "validator_version": "1.0",
        }
        payload.update(overrides)
        return HistoricalDatasetValidationSummary(**payload)  # type: ignore[arg-type]

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
