"""Testes da baseline arquitetural oficial."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import create_architecture_baseline
from scripts import architecture_audit


REQUIRED_TOP_LEVEL_KEYS = {
    "structure",
    "services",
    "contracts",
    "providers",
    "adapters",
    "registered_adapters",
    "events",
    "statistics",
}

REQUIRED_STRUCTURE_KEYS = {
    "layers",
    "modules",
    "packages",
}

REQUIRED_STATISTICS_KEYS = {
    "python_files",
    "tests",
    "modules",
    "services",
    "contracts",
    "adapters",
    "providers",
}


class ArchitectureBaselineTest(unittest.TestCase):
    """Valida o snapshot aprovado da arquitetura."""

    def test_baseline_existe(self) -> None:
        self.assertTrue(
            create_architecture_baseline.BASELINE_PATH.exists(),
            "architecture_baseline.json deve existir na raiz do projeto.",
        )

    def test_baseline_e_json_valido(self) -> None:
        baseline = architecture_audit.load_baseline()

        self.assertIsInstance(baseline, dict)

    def test_baseline_possui_estrutura_obrigatoria(self) -> None:
        baseline = architecture_audit.load_baseline()

        self.assertTrue(REQUIRED_TOP_LEVEL_KEYS.issubset(baseline))
        self.assertTrue(REQUIRED_STRUCTURE_KEYS.issubset(baseline["structure"]))
        self.assertTrue(REQUIRED_STATISTICS_KEYS.issubset(baseline["statistics"]))

    def test_baseline_registra_componentes_arquiteturais_centrais(self) -> None:
        baseline = architecture_audit.load_baseline()

        self.assertIn("DashboardService", baseline["services"])
        self.assertIn("ReplayService", baseline["services"])
        self.assertIn("ResearchLabService", baseline["services"])
        self.assertIn("StrategySignal", baseline["contracts"])
        self.assertIn("HistoricalDataProvider", baseline["providers"])
        self.assertIn("HistoricalDatasetCatalog", baseline["providers"])
        self.assertIn("HistoricalDataSourceRegistry", baseline["providers"])
        self.assertIn("CsvHistoricalDataSource", baseline["adapters"])
        self.assertIn("ParquetHistoricalDataAdapter", baseline["adapters"])
        self.assertIn("DuckDBHistoricalDataAdapter", baseline["adapters"])
        self.assertIn("SYSTEM_STARTED", baseline["events"])

    def test_geracao_e_deterministica(self) -> None:
        first = create_architecture_baseline.serialize_baseline(
            create_architecture_baseline.build_baseline()
        )
        second = create_architecture_baseline.serialize_baseline(
            create_architecture_baseline.build_baseline()
        )

        self.assertEqual(first, second)

    def test_baseline_recente_e_comparada_com_baseline_existente(self) -> None:
        existing = architecture_audit.load_baseline()
        generated = create_architecture_baseline.build_baseline()

        drift = architecture_audit.compare_baseline(existing, generated)

        self.assertIn(drift["status"], {"OK", "DRIFT"})
        self.assertIn("sections", drift)

    def test_write_baseline_gera_conteudo_deterministico(self) -> None:
        baseline = create_architecture_baseline.build_baseline()
        expected = create_architecture_baseline.serialize_baseline(baseline)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "architecture_baseline.json"
            create_architecture_baseline.write_baseline(baseline, path)
            first = path.read_text(encoding="utf-8")
            create_architecture_baseline.write_baseline(baseline, path)
            second = path.read_text(encoding="utf-8")

        self.assertEqual(first, expected)
        self.assertEqual(second, expected)
        self.assertEqual(json.loads(first), baseline)

    def test_drift_e_detectado(self) -> None:
        baseline = create_architecture_baseline.build_baseline()
        current = json.loads(json.dumps(baseline))
        current["services"] = [*current["services"], "NovoServico"]
        current["events"] = [
            event for event in current["events"] if event != "SYSTEM_STARTED"
        ]
        current["statistics"]["python_files"] += 1

        drift = architecture_audit.compare_baseline(baseline, current)

        self.assertEqual(drift["status"], "DRIFT")
        self.assertIn(
            "NovoServico",
            drift["sections"]["services"]["added"],
        )
        self.assertIn(
            "SYSTEM_STARTED",
            drift["sections"]["events"]["removed"],
        )
        self.assertTrue(drift["sections"]["python_files"]["changed"])

    def test_ausencia_de_baseline_gera_erro_claro(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "architecture_baseline.json"

            with self.assertRaisesRegex(
                FileNotFoundError,
                "Baseline arquitetural nao encontrada",
            ):
                architecture_audit.load_baseline(path)

    def test_baseline_invalido_gera_erro_claro(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "architecture_baseline.json"
            path.write_text("{invalid-json", encoding="utf-8")

            with self.assertRaisesRegex(
                ValueError,
                "Baseline arquitetural invalida",
            ):
                architecture_audit.load_baseline(path)

    def test_relatorio_contem_secao_de_drift(self) -> None:
        report = architecture_audit.run_audit(write_reports=False)
        markdown = architecture_audit._to_markdown(report)

        self.assertIn("architecture_baseline_drift", report)
        self.assertIn("Architecture Baseline Drift", markdown)
        self.assertIn("Status geral", markdown)


if __name__ == "__main__":
    unittest.main()
