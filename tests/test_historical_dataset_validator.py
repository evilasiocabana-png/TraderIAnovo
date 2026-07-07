"""Testes do validador de datasets historicos."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

from market_data.contracts import HistoricalDatasetMetadata
from market_data.validation import (
    HistoricalDatasetValidationResult,
    HistoricalDatasetValidator,
)


VALIDATOR_PATH = Path("market_data/validation/historical_dataset_validator.py")


class HistoricalDatasetValidatorTest(unittest.TestCase):
    """Valida metadados historicos sem acesso fisico."""

    def test_validator_importa_sem_excecao(self) -> None:
        self.assertIsNotNone(HistoricalDatasetValidator)

    def test_validator_instancia_sem_excecao(self) -> None:
        validator = HistoricalDatasetValidator()

        self.assertIsInstance(validator, HistoricalDatasetValidator)

    def test_dataset_valido_e_aceito(self) -> None:
        result = HistoricalDatasetValidator().validate(self._metadata())

        self.assertIsInstance(result, HistoricalDatasetValidationResult)
        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, ())

    def test_dataset_sem_symbol_e_rejeitado(self) -> None:
        result = HistoricalDatasetValidator().validate(
            self._payload(symbol=""),
        )

        self.assertFalse(result.is_valid)
        self.assertIn("symbol", result.errors[0])

    def test_dataset_sem_timeframe_e_rejeitado(self) -> None:
        result = HistoricalDatasetValidator().validate(
            self._payload(timeframe=""),
        )

        self.assertFalse(result.is_valid)
        self.assertIn("timeframe", result.errors[0])

    def test_dataset_sem_format_e_rejeitado(self) -> None:
        result = HistoricalDatasetValidator().validate(
            self._payload(format=""),
        )

        self.assertFalse(result.is_valid)
        self.assertIn("format", result.errors[0])

    def test_candle_count_negativo_e_rejeitado(self) -> None:
        result = HistoricalDatasetValidator().validate(
            self._payload(candle_count=-1),
        )

        self.assertFalse(result.is_valid)
        self.assertIn("candle_count", result.errors[0])
        self.assertIn("non-negative", result.errors[0])

    def test_first_timestamp_posterior_a_last_timestamp_e_rejeitado(self) -> None:
        result = HistoricalDatasetValidator().validate(
            self._payload(
                first_timestamp="2025-01-02T09:00:00-03:00",
                last_timestamp="2025-01-01T09:00:00-03:00",
            ),
        )

        self.assertFalse(result.is_valid)
        self.assertIn("first_timestamp", result.errors[0])

    def test_mensagens_de_erro_sao_claras(self) -> None:
        result = HistoricalDatasetValidator().validate(None)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors, ("HistoricalDatasetMetadata is required.",))

    def test_validador_nao_exige_dataset_real_em_disco(self) -> None:
        metadata = self._metadata(file_path="arquivo_inexistente.csv")

        result = HistoricalDatasetValidator().validate(metadata)

        self.assertTrue(result.is_valid)

    def test_is_valid_retorna_boolean(self) -> None:
        validator = HistoricalDatasetValidator()

        self.assertTrue(validator.is_valid(self._metadata()))
        self.assertFalse(validator.is_valid(self._payload(symbol="")))

    def test_validador_nao_importa_acoplamentos_proibidos(self) -> None:
        imports = self._imports(VALIDATOR_PATH)
        calls = self._calls(VALIDATOR_PATH)
        source = VALIDATOR_PATH.read_text(encoding="utf-8").lower()
        forbidden_imports = {
            "pandas",
            "duckdb",
            "pyarrow",
            "csv",
            "dashboard_app",
            "streamlit",
            "replay",
            "research",
            "broker",
            "mt5",
            "metatrader5",
            "market_data.adapters",
        }

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertNotIn("open", calls)
        for term in ("corretora", "ReplayService", "ResearchLabService"):
            self.assertNotIn(term.lower(), source)

    def test_camadas_superiores_nao_importam_validator_diretamente(self) -> None:
        paths = [
            Path("dashboard_app.py"),
            Path("application/replay_service.py"),
            Path("application/research_lab_service.py"),
            *Path("strategies").rglob("*.py"),
        ]

        for path in paths:
            with self.subTest(path=str(path)):
                source = path.read_text(encoding="utf-8")
                self.assertNotIn("HistoricalDatasetValidator", source)
                self.assertNotIn("market_data.validation", source)

    def _metadata(self, **overrides: object) -> HistoricalDatasetMetadata:
        return HistoricalDatasetMetadata(**self._payload(**overrides))  # type: ignore[arg-type]

    def _payload(self, **overrides: object) -> dict[str, object]:
        payload: dict[str, object] = {
            "symbol": "WDO",
            "timeframe": "1m",
            "exchange": "B3",
            "timezone": "America/Sao_Paulo",
            "source": "fixture",
            "format": "csv",
            "version": "1.0",
            "first_timestamp": "2025-01-01T09:00:00-03:00",
            "last_timestamp": "2025-01-01T09:01:00-03:00",
            "candle_count": 2,
        }
        payload.update(overrides)
        return payload

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
