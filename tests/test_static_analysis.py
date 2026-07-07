"""Testes da analise estatica local."""

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import run_static_analysis


class StaticAnalysisTest(unittest.TestCase):
    """Valida o script de analise estatica sem executar correcoes."""

    def test_script_executa_e_retorna_relatorio(self) -> None:
        report = run_static_analysis.run_static_analysis()

        self.assertIn(report["status"], {"OK", "OK_WITH_WARNINGS", "FAILED"})
        self.assertIn("files_analyzed", report)
        self.assertIn("error_count", report)
        self.assertIn("warning_count", report)

    def test_relatorio_e_gerado(self) -> None:
        report = run_static_analysis.run_static_analysis()

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "static_analysis_report.json"
            run_static_analysis.write_report(report, path)
            loaded = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(loaded, report)

    def test_falhas_sao_reportadas_corretamente(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bad_file = root / "bad.py"
            bad_file.write_text("def broken(:\n", encoding="utf-8")

            report = run_static_analysis.run_static_analysis(root)

        self.assertEqual(report["status"], "FAILED")
        self.assertEqual(report["error_count"], 1)
        self.assertIn("bad.py", report["problems"][0]["file"])

    def test_execucao_sem_efeitos_colaterais_em_arquivos_protegidos(self) -> None:
        protected_paths = [
            run_static_analysis.ROOT / "architecture_manifest.json",
            run_static_analysis.ROOT / "architecture_baseline.json",
            run_static_analysis.ROOT / "README.md",
        ]
        before = {path: self._sha256(path) for path in protected_paths}

        report = run_static_analysis.run_static_analysis()

        after = {path: self._sha256(path) for path in protected_paths}

        self.assertGreater(len(report["files_analyzed"]), 0)
        self.assertEqual(before, after)

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
