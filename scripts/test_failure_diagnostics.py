"""Diagnostico estruturado de falhas da suite de testes."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "test_failure_diagnostics.json"

CATEGORIES: tuple[str, ...] = (
    "import",
    "contrato",
    "arquitetura",
    "replay",
    "research",
    "provider",
    "dashboard",
    "configuracao",
    "sessao",
    "desconhecida",
)

CATEGORY_PATTERNS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("import", ("importerror", "modulenotfounderror", "cannot import")),
    ("contrato", ("contract", "contrato", "dto", "signature", "assinatura")),
    ("arquitetura", ("architecture", "arquitetura", "dependency", "baseline")),
    ("replay", ("replay",)),
    ("research", ("research", "pesquisa")),
    ("provider", ("provider", "adapter", "dataset", "duckdb", "parquet", "csv")),
    ("dashboard", ("dashboard", "streamlit")),
    ("configuracao", ("configuration", "configuracao", "configuração", "config")),
    ("sessao", ("session", "sessao", "sessão")),
)


@dataclass(frozen=True)
class TestRunResult:
    """Resultado bruto da execucao da suite."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[], TestRunResult]


def default_runner() -> TestRunResult:
    """Executa a suite completa de testes sem mascarar falhas."""

    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )
    return TestRunResult(
        command=command,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
    )


def run_diagnostics(
    *,
    runner: Runner = default_runner,
    report_path: Path = REPORT_PATH,
) -> dict[str, object]:
    """Executa testes, gera diagnostico e persiste JSON."""

    result = runner()
    report = build_report(result)
    write_report(report, report_path)
    return report


def build_report(result: TestRunResult) -> dict[str, object]:
    """Monta relatorio estruturado a partir da saida do unittest."""

    output = f"{result.stdout}\n{result.stderr}"
    failures = parse_failures(output)
    summary = parse_summary(output, result.returncode, failures)
    grouped = group_by_category(failures)
    status = "PASSED" if result.returncode == 0 and not failures else "FAILED"
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": status,
        "command": " ".join(result.command),
        "summary": summary,
        "failures_by_category": grouped,
        "files_involved": sorted(
            {
                failure["file"]
                for failure in failures
                if isinstance(failure.get("file"), str) and failure.get("file")
            }
        ),
        "messages": [failure["message"] for failure in failures],
    }


def parse_summary(
    output: str,
    returncode: int,
    failures: list[dict[str, object]],
) -> dict[str, object]:
    """Extrai resumo numerico da execucao."""

    ran_match = re.search(r"Ran (\d+) tests?", output)
    failed_match = re.search(
        r"FAILED \((?P<items>[^)]+)\)",
        output,
    )
    total_tests = int(ran_match.group(1)) if ran_match else 0
    failure_count = 0
    error_count = 0
    if failed_match:
        for item in failed_match.group("items").split(","):
            key, _, value = item.strip().partition("=")
            if key == "failures":
                failure_count = int(value)
            if key == "errors":
                error_count = int(value)
    if returncode != 0 and not failed_match and failures:
        error_count = len(failures)
    return {
        "total_tests": total_tests,
        "failures": failure_count,
        "errors": error_count,
        "returncode": returncode,
        "failed_tests": [failure["test"] for failure in failures],
    }


def parse_failures(output: str) -> list[dict[str, object]]:
    """Extrai blocos de falha/erro da saida textual do unittest."""

    pattern = re.compile(
        r"=+\n(?P<kind>FAIL|ERROR): (?P<test>[^\n]+)\n-+\n(?P<body>.*?)(?=\n=+\n|\n-+\nRan \d+ tests?|\Z)",
        re.DOTALL,
    )
    failures: list[dict[str, object]] = []
    for match in pattern.finditer(output):
        body = match.group("body").strip()
        message = summarize_traceback(body)
        file_path = extract_file(body)
        category = categorize_failure(match.group("test"), body)
        failures.append(
            {
                "kind": match.group("kind"),
                "test": match.group("test").strip(),
                "category": category,
                "file": file_path,
                "message": message,
                "traceback_summary": message,
            }
        )
    return failures


def summarize_traceback(traceback_text: str) -> str:
    """Reduz traceback ao trecho mais util para triagem."""

    lines = [line.rstrip() for line in traceback_text.splitlines() if line.strip()]
    for line in reversed(lines):
        stripped = line.strip()
        if re.match(r"^[A-Za-z_][\w.]*Error:", stripped) or stripped.startswith(
            "AssertionError:"
        ):
            return stripped[:500]
    return lines[-1][:500] if lines else ""


def extract_file(traceback_text: str) -> str | None:
    """Extrai o primeiro arquivo de teste citado no traceback."""

    matches = re.findall(r'File "([^"]+)", line \d+', traceback_text)
    for item in matches:
        normalized = item.replace("\\", "/")
        if "/tests/" in normalized or normalized.startswith("tests/"):
            return normalized.split("/tests/", 1)[-1].join(("tests/", ""))
    if matches:
        return matches[-1].replace("\\", "/")
    return None


def categorize_failure(test_name: str, traceback_text: str) -> str:
    """Classifica falha pela area mais provavel."""

    haystack = f"{test_name}\n{traceback_text}".lower()
    for category, patterns in CATEGORY_PATTERNS:
        if any(pattern in haystack for pattern in patterns):
            return category
    return "desconhecida"


def group_by_category(
    failures: list[dict[str, object]],
) -> dict[str, list[dict[str, object]]]:
    """Agrupa falhas pelas categorias oficiais."""

    grouped: dict[str, list[dict[str, object]]] = {category: [] for category in CATEGORIES}
    for failure in failures:
        category = str(failure.get("category") or "desconhecida")
        grouped.setdefault(category, []).append(failure)
    return {category: items for category, items in grouped.items() if items}


def write_report(report: dict[str, object], path: Path = REPORT_PATH) -> None:
    """Grava o relatorio de diagnostico."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Executa diagnostico e preserva o codigo de falha dos testes."""

    report = run_diagnostics()
    summary = report["summary"]
    print(
        "Test failure diagnostics: "
        f"{report['status']} | "
        f"{summary['total_tests']} tests | "
        f"{summary['failures']} failures | "
        f"{summary['errors']} errors",
        flush=True,
    )
    print(f"JSON report: {REPORT_PATH}", flush=True)
    return 1 if report["status"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
