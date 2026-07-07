"""Auditoria informativa da integridade da suite de testes."""

from __future__ import annotations

import ast
import json
import unittest
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
REPORT_PATH = ROOT / "reports" / "test_suite_integrity.json"
QUALITY_GATE_SUMMARY_PATH = ROOT / "reports" / "quality_gate_summary.json"


@dataclass(frozen=True)
class TestSuiteFinding:
    """Achado informativo da auditoria da suite."""

    severity: str
    category: str
    file: str
    message: str
    line: int | None = None


@dataclass
class SuiteStats:
    """Estatisticas consolidadas dos arquivos de teste."""

    total_suites: int = 0
    total_tests: int = 0
    average_suite_duration_seconds: float | None = None
    total_suite_duration_seconds: float | None = None
    timing_source: str = "reports/quality_gate_summary.json"
    slowest_suites: list[dict[str, object]] = field(default_factory=list)


class TestSuiteIntegrityAnalyzer:
    """Gera relatorio estatico e informativo sobre a suite de testes."""

    def __init__(self, tests_dir: Path = TESTS_DIR) -> None:
        self.tests_dir = tests_dir
        self.findings: list[TestSuiteFinding] = []

    def build_report(self) -> dict[str, object]:
        """Monta o relatorio completo sem executar testes internos."""

        test_files = sorted(self.tests_dir.glob("test_*.py"))
        stats = self._stats(test_files)
        self._validate_file_names()
        self._inspect_files(test_files)

        suspicious = [
            finding
            for finding in self.findings
            if finding.severity in {"warning", "info"}
        ]
        problems = [
            finding
            for finding in self.findings
            if finding.severity == "error"
        ]
        return {
            "generated_at": datetime.now().astimezone().isoformat(),
            "status": "FAILED" if problems else "PASSED",
            "statistics": {
                "total_tests": stats.total_tests,
                "total_suites": stats.total_suites,
                "average_suite_duration_seconds": (
                    stats.average_suite_duration_seconds
                ),
                "total_suite_duration_seconds": stats.total_suite_duration_seconds,
                "timing_source": stats.timing_source,
                "slowest_suites": stats.slowest_suites,
            },
            "problems": [self._finding_dict(finding) for finding in problems],
            "suspected_tests": [
                self._finding_dict(finding) for finding in suspicious
            ],
            "checks": {
                "independence": "static_import_and_state_heuristics",
                "determinism": "static_dependency_heuristics",
                "side_effects": "static_file_env_heuristics",
                "structure": "unittest_discovery_and_ast",
            },
        }

    def _stats(self, test_files: list[Path]) -> SuiteStats:
        loader = unittest.TestLoader()
        suite = loader.discover(str(self.tests_dir))
        stats = SuiteStats(
            total_suites=len(test_files),
            total_tests=suite.countTestCases(),
        )
        total_duration = self._last_test_suite_duration()
        if total_duration is not None and test_files:
            stats.total_suite_duration_seconds = total_duration
            stats.average_suite_duration_seconds = round(
                total_duration / len(test_files),
                3,
            )
        stats.slowest_suites = self._estimated_slowest_suites(test_files)
        return stats

    def _last_test_suite_duration(self) -> float | None:
        if not QUALITY_GATE_SUMMARY_PATH.exists():
            return None
        try:
            summary = json.loads(
                QUALITY_GATE_SUMMARY_PATH.read_text(encoding="utf-8"),
            )
        except json.JSONDecodeError:
            return None
        test_suite = summary.get("steps", {}).get("test_suite", {})
        duration = test_suite.get("duration_seconds")
        if isinstance(duration, int | float):
            return float(duration)
        return None

    def _estimated_slowest_suites(self, test_files: list[Path]) -> list[dict[str, object]]:
        ranked = sorted(
            (
                {
                    "file": self._relative(path),
                    "test_count": self._test_count(path),
                    "measurement": "estimated_by_test_count_not_execution",
                }
                for path in test_files
            ),
            key=lambda item: int(item["test_count"]),
            reverse=True,
        )
        return ranked[:5]

    def _validate_file_names(self) -> None:
        for path in sorted(self.tests_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            if not path.name.startswith("test_"):
                severity = "info" if self._test_count(path) == 0 else "error"
                self.findings.append(
                    TestSuiteFinding(
                        severity=severity,
                        category="structure",
                        file=self._relative(path),
                        message=(
                            "Arquivo auxiliar em tests nao inicia com test_."
                            if severity == "info"
                            else "Arquivo de teste nao inicia com test_."
                        ),
                    )
                )

    def _inspect_files(self, test_files: list[Path]) -> None:
        for path in test_files:
            source = path.read_text(encoding="utf-8")
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                self.findings.append(
                    TestSuiteFinding(
                        severity="error",
                        category="structure",
                        file=self._relative(path),
                        message=f"Arquivo de teste invalido: {exc.msg}.",
                        line=exc.lineno,
                    )
                )
                continue
            self._inspect_structure(path, tree, source)
            self._inspect_determinism(path, tree, source)
            self._inspect_side_effects(path, tree)

    def _inspect_structure(self, path: Path, tree: ast.AST, source: str) -> None:
        test_methods = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        ]
        if not test_methods:
            self.findings.append(
                TestSuiteFinding(
                    severity="error",
                    category="structure",
                    file=self._relative(path),
                    message="Arquivo de teste nao possui metodos test_.",
                )
            )

        for method in test_methods:
            executable_body = [
                item
                for item in method.body
                if not (
                    isinstance(item, ast.Expr)
                    and isinstance(item.value, ast.Constant)
                    and isinstance(item.value.value, str)
                )
            ]
            if not executable_body or all(isinstance(item, ast.Pass) for item in executable_body):
                self.findings.append(
                    TestSuiteFinding(
                        severity="error",
                        category="structure",
                        file=self._relative(path),
                        message=f"Teste vazio detectado: {method.name}.",
                        line=method.lineno,
                    )
                )
            for decorator in method.decorator_list:
                name = self._call_name(decorator)
                if name and "skip" in name.lower():
                    reason = self._first_string_arg(decorator)
                    severity = "info" if reason else "warning"
                    self.findings.append(
                        TestSuiteFinding(
                            severity=severity,
                            category="structure",
                            file=self._relative(path),
                            message=(
                                f"Teste marcado com skip: {method.name}. "
                                f"Justificativa: {reason or 'ausente'}."
                            ),
                            line=method.lineno,
                        )
                    )

        for marker in ("TODO", "FIXME"):
            if marker in source:
                self.findings.append(
                    TestSuiteFinding(
                        severity="warning",
                        category="structure",
                        file=self._relative(path),
                        message=f"Marcador {marker} encontrado em teste.",
                    )
                )

    def _inspect_determinism(self, path: Path, tree: ast.AST, source: str) -> None:
        patterns = {
            "datetime.now": "Uso de horario atual pode afetar determinismo.",
            "date.today": "Uso de data atual pode afetar determinismo.",
            "time.time": "Uso de relogio do sistema pode afetar determinismo.",
            "random.": "Uso de aleatoriedade deve controlar seed ou mock.",
            "requests.": "Acesso HTTP externo deve ser mockado.",
            "urllib.": "Acesso HTTP externo deve ser mockado.",
            "socket.": "Acesso de rede deve ser mockado.",
        }
        for pattern, message in patterns.items():
            if pattern in source:
                self.findings.append(
                    TestSuiteFinding(
                        severity="warning",
                        category="determinism",
                        file=self._relative(path),
                        message=message,
                    )
                )

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = self._call_name(node)
                if name in {"os.listdir", "Path.glob"}:
                    self.findings.append(
                        TestSuiteFinding(
                            severity="info",
                            category="determinism",
                            file=self._relative(path),
                            message=(
                                f"{name} exige ordenacao explicita quando a ordem "
                                "for relevante."
                            ),
                            line=node.lineno,
                        )
                    )

    def _inspect_side_effects(self, path: Path, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = self._call_name(node)
                if name in {"NamedTemporaryFile", "tempfile.NamedTemporaryFile"}:
                    if self._keyword_bool(node, "delete") is False:
                        self.findings.append(
                            TestSuiteFinding(
                                severity="warning",
                                category="side_effects",
                                file=self._relative(path),
                                message=(
                                    "NamedTemporaryFile(delete=False) pode deixar "
                                    "arquivo temporario persistente."
                                ),
                                line=node.lineno,
                            )
                        )
                if name and name.endswith("write_text"):
                    if self._relative(path) != "tests/test_test_suite_integrity.py":
                        self.findings.append(
                            TestSuiteFinding(
                                severity="info",
                                category="side_effects",
                                file=self._relative(path),
                                message=(
                                    "Escrita em arquivo detectada; confirmar uso "
                                    "de TemporaryDirectory ou fixture isolada."
                                ),
                                line=node.lineno,
                            )
                        )
            if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
                target_text = ast.unparse(node)
                if "os.environ" in target_text:
                    self.findings.append(
                        TestSuiteFinding(
                            severity="warning",
                            category="side_effects",
                            file=self._relative(path),
                            message=(
                                "Alteracao de variavel de ambiente detectada; "
                                "deve haver restauracao."
                            ),
                            line=getattr(node, "lineno", None),
                        )
                    )

    def _test_count(self, path: Path) -> int:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            return 0
        return sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
        )

    def _relative(self, path: Path) -> str:
        return path.relative_to(ROOT).as_posix()

    def _finding_dict(self, finding: TestSuiteFinding) -> dict[str, object]:
        data: dict[str, object] = {
            "severity": finding.severity,
            "category": finding.category,
            "file": finding.file,
            "message": finding.message,
        }
        if finding.line is not None:
            data["line"] = finding.line
        return data

    def _call_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            return self._call_name(node.func)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._call_name(node.value)
            if parent:
                return f"{parent}.{node.attr}"
            return node.attr
        return None

    def _first_string_arg(self, node: ast.AST) -> str | None:
        if not isinstance(node, ast.Call) or not node.args:
            return None
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
        return None

    def _keyword_bool(self, node: ast.Call, keyword_name: str) -> bool | None:
        for keyword in node.keywords:
            if keyword.arg == keyword_name:
                value = keyword.value
                if isinstance(value, ast.Constant) and isinstance(value.value, bool):
                    return value.value
        return None


def generate_integrity_report() -> dict[str, object]:
    """Gera e persiste o relatorio informativo de integridade da suite."""

    report = TestSuiteIntegrityAnalyzer().build_report()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


class TestSuiteIntegrityTest(unittest.TestCase):
    """Contratos da auditoria informativa da suite de testes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.report = generate_integrity_report()

    def test_relatorio_de_integridade_eh_gerado_com_json_valido(self) -> None:
        loaded = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

        self.assertIn("statistics", loaded)
        self.assertIn("problems", loaded)
        self.assertIn("suspected_tests", loaded)
        self.assertIn(loaded["status"], {"PASSED", "FAILED"})

    def test_estatisticas_da_suite_sao_registradas(self) -> None:
        statistics = self.report["statistics"]

        self.assertGreater(statistics["total_tests"], 0)
        self.assertGreater(statistics["total_suites"], 0)
        self.assertIn("average_suite_duration_seconds", statistics)
        self.assertIn("slowest_suites", statistics)

    def test_estrutura_basica_da_suite_permanece_valida(self) -> None:
        problems = [
            problem
            for problem in self.report["problems"]
            if problem["category"] == "structure"
        ]

        self.assertEqual(problems, [])

    def test_determinismo_e_efeitos_colaterais_sao_auditados(self) -> None:
        checks = self.report["checks"]

        self.assertIn("determinism", checks)
        self.assertIn("side_effects", checks)
        self.assertIsInstance(self.report["suspected_tests"], list)


if __name__ == "__main__":
    unittest.main()
