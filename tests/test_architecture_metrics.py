"""Testes do engine de metricas arquiteturais."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import architecture_metrics


class ArchitectureMetricsTest(unittest.TestCase):
    """Valida o relatorio quantitativo da arquitetura."""

    def test_relatorio_json_e_gerado(self) -> None:
        metrics = architecture_metrics.build_metrics()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "architecture_metrics.json"
            architecture_metrics.write_metrics(metrics, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(loaded, metrics)

    def test_formato_contem_secoes_obrigatorias(self) -> None:
        metrics = architecture_metrics.build_metrics()

        self.assertEqual(
            set(metrics),
            {
                "structure",
                "application",
                "domain",
                "architecture",
                "testing",
                "providers",
                "events",
                "generated_at",
            },
        )

    def test_metricas_sao_calculadas(self) -> None:
        metrics = architecture_metrics.build_metrics()

        self.assertGreater(metrics["structure"]["modules"], 0)
        self.assertGreater(metrics["structure"]["python_files"], 0)
        self.assertGreater(metrics["structure"]["loc"], 0)
        self.assertGreater(metrics["application"]["services"], 0)
        self.assertGreater(metrics["domain"]["contracts"], 0)
        self.assertGreater(metrics["testing"]["total_suites"], 0)
        self.assertGreater(metrics["providers"]["adapters"], 0)
        self.assertGreater(metrics["events"]["official_events"], 0)

    def test_execucao_e_deterministica(self) -> None:
        first = architecture_metrics.serialize_metrics(
            architecture_metrics.build_metrics()
        )
        second = architecture_metrics.serialize_metrics(
            architecture_metrics.build_metrics()
        )

        self.assertEqual(first, second)

    def test_geracao_em_memoria_nao_altera_arquivos_protegidos(self) -> None:
        protected_paths = [
            architecture_metrics.ROOT / "architecture_manifest.json",
            architecture_metrics.ROOT / "architecture_baseline.json",
            architecture_metrics.ROOT / "README.md",
        ]
        before = {path: self._sha256(path) for path in protected_paths}

        metrics = architecture_metrics.build_metrics()
        serialized = architecture_metrics.serialize_metrics(metrics)

        after = {path: self._sha256(path) for path in protected_paths}

        self.assertIn('"structure"', serialized)
        self.assertEqual(before, after)

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
