"""Contrato de resultado de validacao de datasets historicos."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path
from typing import get_type_hints
import unittest

from historical.contracts import HistoricalDatasetValidationResult


CONTRACT_PATH = Path("historical/contracts/historical_dataset_validation.py")
REQUIRED_FIELDS = [
    "dataset_id",
    "is_valid",
    "records_checked",
    "invalid_records",
    "gap_count",
    "duplicate_timestamp_count",
    "critical_errors",
    "warnings",
    "validated_at",
    "validator_version",
]


class HistoricalDatasetValidationContractTest(unittest.TestCase):
    """Protege o DTO oficial de resultado de validacao historica."""

    def test_contrato_importa_e_cria_estado_valido(self) -> None:
        result = self._valid_result()

        self.assertIsInstance(result, HistoricalDatasetValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.dataset_id, "WDO_1m_2025")

    def test_campos_obrigatorios_estao_definidos(self) -> None:
        contract_fields = [field.name for field in fields(HistoricalDatasetValidationResult)]

        self.assertEqual(contract_fields, REQUIRED_FIELDS)

    def test_type_hints_estao_presentes(self) -> None:
        hints = get_type_hints(HistoricalDatasetValidationResult)

        for field_name in REQUIRED_FIELDS:
            with self.subTest(field=field_name):
                self.assertIn(field_name, hints)

    def test_estado_invalido_e_representado_sem_dicionario_livre(self) -> None:
        result = self._valid_result(
            is_valid=False,
            invalid_records=2,
            gap_count=1,
            duplicate_timestamp_count=1,
            critical_errors=("missing column: close",),
            warnings=("gap detected",),
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.critical_errors, ("missing column: close",))
        self.assertEqual(result.warnings, ("gap detected",))
        self.assertNotIsInstance(result.critical_errors, dict)
        self.assertNotIsInstance(result.warnings, dict)

    def test_listas_de_erros_e_alertas_sao_tipadas_como_tuplas(self) -> None:
        with self.assertRaisesRegex(TypeError, "critical_errors"):
            self._valid_result(critical_errors=["erro"])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "warnings"):
            self._valid_result(warnings=["alerta"])  # type: ignore[arg-type]
        with self.assertRaisesRegex(TypeError, "only str"):
            self._valid_result(critical_errors=(object(),))  # type: ignore[arg-type]

    def test_contadores_devem_ser_inteiros_nao_negativos(self) -> None:
        with self.assertRaisesRegex(ValueError, "non-negative"):
            self._valid_result(records_checked=-1)
        with self.assertRaisesRegex(TypeError, "int"):
            self._valid_result(gap_count="1")  # type: ignore[arg-type]

    def test_contrato_e_dataclass_imutavel(self) -> None:
        result = self._valid_result()

        self.assertTrue(is_dataclass(result))
        with self.assertRaises(FrozenInstanceError):
            result.is_valid = False  # type: ignore[misc]

    def test_contrato_nao_contem_logica_de_validacao_ou_io(self) -> None:
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
        for term in ("read_csv", "read_parquet", "connect", "load_candles"):
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
                self.assertNotIn("HistoricalDatasetValidationResult", source)
                self.assertNotIn("historical.contracts.historical_dataset_validation", source)

    def test_nenhum_validador_concreto_foi_criado_em_historical(self) -> None:
        historical_files = [path.name for path in Path("historical").rglob("*.py")]

        self.assertNotIn("historical_dataset_validator.py", historical_files)

    def _valid_result(self, **overrides: object) -> HistoricalDatasetValidationResult:
        payload: dict[str, object] = {
            "dataset_id": "WDO_1m_2025",
            "is_valid": True,
            "records_checked": 100,
            "invalid_records": 0,
            "gap_count": 0,
            "duplicate_timestamp_count": 0,
            "critical_errors": (),
            "warnings": (),
            "validated_at": "2026-06-27T04:00:00-03:00",
            "validator_version": "1.0",
        }
        payload.update(overrides)
        return HistoricalDatasetValidationResult(**payload)  # type: ignore[arg-type]

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
