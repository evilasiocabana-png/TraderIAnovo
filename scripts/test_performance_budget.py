"""Mede o orcamento de performance da suite de testes."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = ROOT / "tests"
REPORT_PATH = ROOT / "reports" / "test_performance_budget.json"

# Limites conservadores e ajustaveis.
MAX_TOTAL_SECONDS = 300.0
EXTREME_TOTAL_SECONDS = 600.0
WARNING_SUITE_SECONDS = 10.0
MAX_SUITE_SECONDS = 60.0
EXTREME_DEGRADATION_RATIO = 2.0
EXTREME_DEGRADATION_SECONDS = 60.0
SLOWEST_SUITES_LIMIT = 10


@dataclass(frozen=True)
class SuiteTiming:
    """Resultado de tempo de uma suite de teste."""

    file: str
    duration_seconds: float
    exit_code: int


@dataclass(frozen=True)
class BudgetIssue:
    """Aviso ou violacao do orcamento."""

    severity: str
    category: str
    message: str
    file: str | None = None
    duration_seconds: float | None = None
    limit_seconds: float | None = None


Runner = Callable[[Path], SuiteTiming]


def default_runner(test_file: Path) -> SuiteTiming:
    """Executa um arquivo de teste isoladamente via unittest."""

    started_at = time.perf_counter()
    result = subprocess.run(
        [sys.executable, "-m", "unittest", _module_name(test_file)],
        cwd=ROOT,
        check=False,
    )
    duration = round(time.perf_counter() - started_at, 3)
    return SuiteTiming(
        file=test_file.relative_to(ROOT).as_posix(),
        duration_seconds=duration,
        exit_code=result.returncode,
    )


def _module_name(test_file: Path) -> str:
    return ".".join(test_file.relative_to(ROOT).with_suffix("").parts)


def load_previous_report(path: Path = REPORT_PATH) -> dict[str, object] | None:
    """Carrega relatorio anterior quando existir."""

    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def run_budget(
    *,
    tests_dir: Path = TESTS_DIR,
    report_path: Path = REPORT_PATH,
    runner: Runner = default_runner,
    previous_report: dict[str, object] | None = None,
) -> dict[str, object]:
    """Mede suites, aplica limites e grava o relatorio."""

    previous = previous_report if previous_report is not None else load_previous_report(
        report_path
    )
    suite_files = sorted(tests_dir.glob("test_*.py"))
    timings = [runner(path) for path in suite_files]
    total_duration = round(sum(item.duration_seconds for item in timings), 3)
    warnings, violations = evaluate_budget(timings, total_duration, previous)
    status = "FAILED" if violations else "PASSED"
    report = build_report(timings, total_duration, warnings, violations, status, previous)
    write_report(report, report_path)
    return report


def evaluate_budget(
    timings: list[SuiteTiming],
    total_duration: float,
    previous_report: dict[str, object] | None,
) -> tuple[list[BudgetIssue], list[BudgetIssue]]:
    """Aplica limites sem falhar por pequenas variacoes de tempo."""

    warnings: list[BudgetIssue] = []
    violations: list[BudgetIssue] = []

    if total_duration > MAX_TOTAL_SECONDS:
        warnings.append(
            BudgetIssue(
                severity="warning",
                category="total_duration",
                message="Tempo total da suite acima do limite recomendado.",
                duration_seconds=total_duration,
                limit_seconds=MAX_TOTAL_SECONDS,
            )
        )

    if total_duration > EXTREME_TOTAL_SECONDS:
        violations.append(
            BudgetIssue(
                severity="error",
                category="total_duration",
                message="Tempo total da suite excedeu limite extremo.",
                duration_seconds=total_duration,
                limit_seconds=EXTREME_TOTAL_SECONDS,
            )
        )

    for timing in timings:
        if timing.exit_code != 0:
            violations.append(
                BudgetIssue(
                    severity="error",
                    category="test_failure",
                    file=timing.file,
                    message="Suite falhou durante medicao de performance.",
                    duration_seconds=timing.duration_seconds,
                )
            )
        if timing.duration_seconds > WARNING_SUITE_SECONDS:
            warnings.append(
                BudgetIssue(
                    severity="warning",
                    category="slow_suite",
                    file=timing.file,
                    message="Suite acima do limite de aviso.",
                    duration_seconds=timing.duration_seconds,
                    limit_seconds=WARNING_SUITE_SECONDS,
                )
            )
        if timing.duration_seconds > MAX_SUITE_SECONDS:
            violations.append(
                BudgetIssue(
                    severity="error",
                    category="slow_suite",
                    file=timing.file,
                    message="Suite excedeu limite maximo por arquivo.",
                    duration_seconds=timing.duration_seconds,
                    limit_seconds=MAX_SUITE_SECONDS,
                )
            )

    previous_total = _previous_total_duration(previous_report)
    if previous_total is not None and previous_total > 0:
        delta = round(total_duration - previous_total, 3)
        ratio = round(total_duration / previous_total, 3)
        if delta > 0:
            warnings.append(
                BudgetIssue(
                    severity="warning",
                    category="trend",
                    message=(
                        "Tempo total aumentou em relacao ao relatorio anterior."
                    ),
                    duration_seconds=delta,
                )
            )
        if ratio >= EXTREME_DEGRADATION_RATIO and delta >= EXTREME_DEGRADATION_SECONDS:
            violations.append(
                BudgetIssue(
                    severity="error",
                    category="trend",
                    message="Degradacao extrema detectada contra relatorio anterior.",
                    duration_seconds=delta,
                )
            )

    return warnings, violations


def build_report(
    timings: list[SuiteTiming],
    total_duration: float,
    warnings: list[BudgetIssue],
    violations: list[BudgetIssue],
    status: str,
    previous_report: dict[str, object] | None,
) -> dict[str, object]:
    """Cria o relatorio JSON do orcamento de performance."""

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": status,
        "limits": {
            "max_total_seconds": MAX_TOTAL_SECONDS,
            "extreme_total_seconds": EXTREME_TOTAL_SECONDS,
            "warning_suite_seconds": WARNING_SUITE_SECONDS,
            "max_suite_seconds": MAX_SUITE_SECONDS,
            "extreme_degradation_ratio": EXTREME_DEGRADATION_RATIO,
            "extreme_degradation_seconds": EXTREME_DEGRADATION_SECONDS,
        },
        "summary": {
            "total_duration_seconds": total_duration,
            "total_suites": len(timings),
            "slowest_suites": [
                _timing_dict(item)
                for item in sorted(
                    timings,
                    key=lambda timing: timing.duration_seconds,
                    reverse=True,
                )[:SLOWEST_SUITES_LIMIT]
            ],
            "trend": _trend(total_duration, previous_report),
        },
        "suites": [_timing_dict(item) for item in timings],
        "warnings": [_issue_dict(item) for item in warnings],
        "violations": [_issue_dict(item) for item in violations],
    }


def write_report(report: dict[str, object], path: Path = REPORT_PATH) -> None:
    """Persiste o relatorio do budget."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def _previous_total_duration(report: dict[str, object] | None) -> float | None:
    if not report:
        return None
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return None
    value = summary.get("total_duration_seconds")
    if isinstance(value, int | float):
        return float(value)
    return None


def _trend(
    total_duration: float,
    previous_report: dict[str, object] | None,
) -> dict[str, object]:
    previous_total = _previous_total_duration(previous_report)
    if previous_total is None or previous_total <= 0:
        return {
            "available": False,
            "previous_total_duration_seconds": None,
            "delta_seconds": None,
            "ratio": None,
        }
    delta = round(total_duration - previous_total, 3)
    ratio = round(total_duration / previous_total, 3)
    return {
        "available": True,
        "previous_total_duration_seconds": previous_total,
        "delta_seconds": delta,
        "ratio": ratio,
    }


def _timing_dict(timing: SuiteTiming) -> dict[str, object]:
    return {
        "file": timing.file,
        "duration_seconds": timing.duration_seconds,
        "exit_code": timing.exit_code,
    }


def _issue_dict(issue: BudgetIssue) -> dict[str, object]:
    data: dict[str, object] = {
        "severity": issue.severity,
        "category": issue.category,
        "message": issue.message,
    }
    if issue.file is not None:
        data["file"] = issue.file
    if issue.duration_seconds is not None:
        data["duration_seconds"] = issue.duration_seconds
    if issue.limit_seconds is not None:
        data["limit_seconds"] = issue.limit_seconds
    return data


def main() -> int:
    """Executa a medicao de performance da suite."""

    report = run_budget()
    print(
        "Test performance budget: "
        f"{report['status']} | "
        f"{report['summary']['total_suites']} suites | "
        f"{report['summary']['total_duration_seconds']}s",
        flush=True,
    )
    print(f"JSON report: {REPORT_PATH}", flush=True)
    return 1 if report["status"] == "FAILED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
