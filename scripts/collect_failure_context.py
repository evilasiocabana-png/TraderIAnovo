"""Coleta contexto de falhas de validacao sem alterar a aplicacao."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reports"
REPORT_PATH = REPORTS_DIR / "failure_context.json"

FAILURE_STATUSES = {
    "FAILED",
    "ERROR",
    "NOT READY",
    "NON-REPRODUCIBLE",
}
WARNING_STATUSES = {
    "OK_WITH_WARNINGS",
    "READY WITH WARNINGS",
    "REPRODUCIBLE WITH WARNINGS",
    "WARNING",
    "WARNINGS",
}


@dataclass(frozen=True)
class ReportSpec:
    """Contrato minimo de leitura para um relatorio existente."""

    key: str
    path: str
    category: str
    command: str


REPORT_SPECS: tuple[ReportSpec, ...] = (
    ReportSpec(
        "quality_gate_summary",
        "reports/quality_gate_summary.json",
        "quality_gate",
        "python scripts/run_quality_gate.py",
    ),
    ReportSpec(
        "test_failure_diagnostics",
        "reports/test_failure_diagnostics.json",
        "unit_tests",
        "python scripts/test_failure_diagnostics.py",
    ),
    ReportSpec(
        "architecture_audit",
        "reports/architecture_audit.json",
        "architecture",
        "python scripts/architecture_audit.py",
    ),
    ReportSpec(
        "static_analysis",
        "reports/static_analysis_report.json",
        "static_analysis",
        "python scripts/run_static_analysis.py",
    ),
    ReportSpec(
        "ci_readiness",
        "reports/ci_readiness.json",
        "ci_readiness",
        "python scripts/ci_readiness.py",
    ),
    ReportSpec(
        "reproducible_build",
        "reports/reproducible_build.json",
        "reproducible_build",
        "python scripts/reproducible_build.py",
    ),
    ReportSpec(
        "repository_compliance",
        "reports/repository_compliance.json",
        "repository_compliance",
        "python scripts/repository_compliance.py",
    ),
    ReportSpec(
        "architecture_health",
        "reports/architecture_health.md",
        "architecture_health",
        "python scripts/architecture_health.py",
    ),
    ReportSpec(
        "test_performance_budget",
        "reports/test_performance_budget.json",
        "test_performance",
        "python scripts/test_performance_budget.py",
    ),
)

LOCAL_REPRODUCTION_COMMANDS = (
    "python scripts/run_static_analysis.py",
    "python scripts/run_quality_gate.py",
    "python scripts/architecture_audit.py",
    "python scripts/test_failure_diagnostics.py",
    "python scripts/ci_readiness.py",
    "python scripts/reproducible_build.py",
    "python -m unittest discover -s tests",
)

SAFETY_NOTES = (
    "Nao corrigir falhas automaticamente.",
    "Nao mascarar excecoes ou exit codes.",
    "Nao alterar baseline sem aprovacao CTO explicita.",
    "Nao alterar manifesto sem justificativa arquitetural.",
    "Nao executar Streamlit, MT5, corretora ou envio de ordens neste coletor.",
)


def build_failure_context(
    *,
    root: Path = ROOT,
    specs: tuple[ReportSpec, ...] = REPORT_SPECS,
) -> dict[str, Any]:
    """Consolida relatorios existentes em um contexto unico de triagem."""

    found_reports: dict[str, dict[str, Any]] = {}
    missing_reports: list[str] = []
    failures_by_category: dict[str, list[dict[str, Any]]] = {}

    for spec in specs:
        path = root / spec.path
        if not path.exists():
            missing_reports.append(spec.path)
            continue

        report = summarize_report(spec, path)
        found_reports[spec.key] = report
        if is_failure_status(report.get("status")):
            failures_by_category.setdefault(spec.category, []).append(
                {
                    "report": spec.key,
                    "path": spec.path,
                    "status": report.get("status"),
                    "message": report.get("message"),
                    "command": spec.command,
                }
            )

    test_failures = collect_test_failures(found_reports.get("test_failure_diagnostics", {}))
    for failure in test_failures:
        category = str(failure.get("category") or "unit_tests")
        failures_by_category.setdefault(category, []).append(failure)

    overall_status = classify_overall_status(found_reports, missing_reports, failures_by_category)

    return {
        "timestamp": datetime.now().astimezone().isoformat(),
        "overall_status": overall_status,
        "reports_found": found_reports,
        "reports_missing": missing_reports,
        "failures_by_category": failures_by_category,
        "suggested_commands": suggested_commands(found_reports, missing_reports, specs),
        "security_observations": list(SAFETY_NOTES),
    }


def summarize_report(spec: ReportSpec, path: Path) -> dict[str, Any]:
    """Extrai status e mensagem curta de JSON ou Markdown."""

    if path.suffix.lower() == ".json":
        data = read_json(path)
        status = extract_status(data)
        summary = {
            "path": spec.path,
            "status": status,
            "message": extract_message(data, status),
        }
        failures_by_category = data.get("failures_by_category")
        if isinstance(failures_by_category, dict):
            summary["failures_by_category"] = failures_by_category
        return summary

    text = path.read_text(encoding="utf-8", errors="replace")
    status = extract_markdown_status(text)
    return {
        "path": spec.path,
        "status": status,
        "message": first_non_empty_line(text),
    }


def read_json(path: Path) -> dict[str, Any]:
    """Le JSON preservando falha como dado de diagnostico."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "ERROR", "message": f"JSON invalido: {exc}"}
    return data if isinstance(data, dict) else {"status": "ERROR", "message": "JSON sem objeto raiz."}


def extract_status(data: dict[str, Any]) -> str:
    """Busca campos comuns de status nos relatorios existentes."""

    for key in ("overall_status", "status", "classification"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()

    architecture_status = extract_architecture_audit_status(data)
    if architecture_status:
        return architecture_status

    steps = data.get("steps")
    if isinstance(steps, dict):
        statuses = [
            str(step.get("status", "")).upper()
            for step in steps.values()
            if isinstance(step, dict)
        ]
        if any(is_failure_status(status) for status in statuses):
            return "FAILED"
        if any(status in WARNING_STATUSES for status in statuses):
            return "OK_WITH_WARNINGS"
        if statuses:
            return "PASSED"

    return "UNKNOWN"


def extract_architecture_audit_status(data: dict[str, Any]) -> str | None:
    """Reconhece o formato atual do architecture_audit.json."""

    manifest = data.get("manifest_compliance")
    drift = data.get("architecture_baseline_drift")
    if not isinstance(manifest, dict):
        return None

    manifest_status = str(manifest.get("status", "")).upper()
    drift_status = str(drift.get("status", "")).upper() if isinstance(drift, dict) else ""
    drift_criticality = (
        str(drift.get("criticality", "")).upper() if isinstance(drift, dict) else ""
    )
    if manifest_status in FAILURE_STATUSES:
        return "FAILED"
    if drift_status == "DRIFT" and drift_criticality not in {"", "INFORMATIVO", "INFO"}:
        return "FAILED"
    if manifest_status == "OK":
        return "OK"
    return manifest_status or None


def extract_markdown_status(text: str) -> str:
    """Extrai status de relatorios Markdown simples."""

    for line in text.splitlines():
        normalized = line.strip().lower()
        if normalized.startswith("- status geral:"):
            return line.split(":", 1)[1].strip().upper()
        if normalized.startswith("status:"):
            return line.split(":", 1)[1].strip().upper()
    return "UNKNOWN"


def extract_message(data: dict[str, Any], status: str) -> str:
    """Cria mensagem compacta para triagem."""

    for key in ("message", "summary", "recommendation"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:500]

    if isinstance(data.get("steps"), dict):
        failed_steps = [
            name
            for name, step in data["steps"].items()
            if isinstance(step, dict) and is_failure_status(step.get("status"))
        ]
        if failed_steps:
            return "Etapas com falha: " + ", ".join(failed_steps)

    drift = data.get("architecture_baseline_drift")
    if isinstance(drift, dict) and drift.get("status"):
        return (
            f"Manifest compliance: "
            f"{data.get('manifest_compliance', {}).get('status', 'UNKNOWN')}; "
            f"baseline drift: {drift.get('status')} "
            f"({drift.get('criticality', 'sem criticidade')})."
        )

    if isinstance(data.get("problems"), list) and data["problems"]:
        return f"Problemas registrados: {len(data['problems'])}"
    if isinstance(data.get("warnings"), list) and data["warnings"]:
        return f"Avisos registrados: {len(data['warnings'])}"
    return f"Status registrado: {status}"


def collect_test_failures(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Inclui falhas do diagnostico de testes agrupadas pela categoria original."""

    failures: list[dict[str, Any]] = []
    grouped = report.get("raw_failures_by_category") or report.get("failures_by_category")
    if not isinstance(grouped, dict):
        return failures

    for category, items in grouped.items():
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            failures.append(
                {
                    "report": "test_failure_diagnostics",
                    "category": str(category),
                    "test": item.get("test"),
                    "file": item.get("file"),
                    "message": item.get("message") or item.get("traceback_summary"),
                    "command": "python scripts/test_failure_diagnostics.py",
                }
            )
    return failures


def classify_overall_status(
    found_reports: dict[str, dict[str, Any]],
    missing_reports: list[str],
    failures_by_category: dict[str, list[dict[str, Any]]],
) -> str:
    """Classifica o contexto sem mascarar falhas existentes."""

    if failures_by_category:
        return "FAILED"

    statuses = {str(report.get("status", "")).upper() for report in found_reports.values()}
    if any(status in WARNING_STATUSES for status in statuses) or missing_reports:
        return "WARNING"
    return "PASSED"


def suggested_commands(
    found_reports: dict[str, dict[str, Any]],
    missing_reports: list[str],
    specs: tuple[ReportSpec, ...],
) -> list[str]:
    """Sugere comandos locais relevantes para reproduzir diagnostico."""

    commands = list(LOCAL_REPRODUCTION_COMMANDS)
    missing_by_path = {spec.path: spec.command for spec in specs}
    for missing in missing_reports:
        command = missing_by_path.get(missing)
        if command and command not in commands:
            commands.append(command)

    failed_commands = [
        spec.command
        for spec in specs
        if is_failure_status(found_reports.get(spec.key, {}).get("status"))
    ]
    for command in failed_commands:
        if command not in commands:
            commands.insert(0, command)
    return commands


def is_failure_status(value: Any) -> bool:
    """Retorna True para classificacoes de falha conhecidas."""

    return str(value or "").strip().upper() in FAILURE_STATUSES


def first_non_empty_line(text: str) -> str:
    """Retorna a primeira linha util de um Markdown."""

    for line in text.splitlines():
        if line.strip():
            return line.strip()[:500]
    return ""


def write_report(report: dict[str, Any], report_path: Path = REPORT_PATH) -> None:
    """Persiste o contexto em JSON."""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Gera reports/failure_context.json."""

    report = build_failure_context()
    write_report(report)
    print(f"Failure context status: {report['overall_status']}")
    print(f"JSON report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
