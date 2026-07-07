"""Consolida indicadores executivos de governanca do TraderIA_WDO."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "governance_dashboard.json"

REPORT_SOURCES = {
    "quality_gate_summary": "reports/quality_gate_summary.json",
    "architecture_audit": "reports/architecture_audit.json",
    "architecture_health_md": "reports/architecture_health.md",
    "architecture_health_json": "reports/architecture_health.json",
    "architecture_metrics": "reports/architecture_metrics.json",
    "repository_compliance": "reports/repository_compliance.json",
    "governance_consistency": "reports/governance_consistency.json",
    "ci_readiness": "reports/ci_readiness.json",
    "reproducible_build": "reports/reproducible_build.json",
    "static_analysis": "reports/static_analysis_report.json",
    "test_performance_budget": "reports/test_performance_budget.json",
    "test_failure_diagnostics": "reports/test_failure_diagnostics.json",
    "failure_context": "reports/failure_context.json",
}

CRITICAL_STATUSES = {
    "FAILED",
    "ERROR",
    "NOT READY",
    "NON-REPRODUCIBLE",
}
ATTENTION_STATUSES = {
    "INCONSISTENT",
    "WARNING",
    "OK_WITH_WARNINGS",
    "READY WITH WARNINGS",
    "REPRODUCIBLE WITH WARNINGS",
    "MINOR INCONSISTENCIES",
}
GOOD_STATUSES = {
    "PASSED",
    "OK",
    "READY",
    "REPRODUCIBLE",
    "CONSISTENT",
    "BOM",
}


def build_dashboard(root: Path = ROOT) -> dict[str, Any]:
    """Consolida relatorios existentes em um dashboard executivo."""

    sources = load_sources(root)
    indicators = {
        "architecture": architecture_indicators(sources),
        "engineering": engineering_indicators(sources),
        "governance": governance_indicators(sources),
        "operation": operation_indicators(sources),
    }
    classification = classify_overall(sources, indicators)
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "overall_classification": classification,
        "reports_consolidated": {
            key: {
                "path": source["path"],
                "found": source["found"],
                "status": source.get("status", "MISSING"),
            }
            for key, source in sources.items()
        },
        "indicators": indicators,
        "executive_summary": executive_summary(classification, indicators, sources),
    }


def load_sources(root: Path) -> dict[str, dict[str, Any]]:
    """Le cada relatorio quando existir."""

    sources: dict[str, dict[str, Any]] = {}
    for key, relative in REPORT_SOURCES.items():
        path = root / relative
        source: dict[str, Any] = {"path": relative, "found": path.exists()}
        if not path.exists():
            source["status"] = "MISSING"
        elif path.suffix.lower() == ".json":
            data = read_json(path)
            source["data"] = data
            source["status"] = extract_status(data)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
            source["text"] = text
            source["status"] = extract_markdown_status(text)
        sources[key] = source
    return sources


def architecture_indicators(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Resume arquitetura sem recalcular metricas."""

    audit = sources["architecture_audit"].get("data", {})
    health_text = sources["architecture_health_md"].get("text", "")
    metrics = sources["architecture_metrics"].get("data", {})
    consistency = sources["governance_consistency"].get("data", {})

    return {
        "status": health_value(health_text, "Status geral") or sources["architecture_audit"]["status"],
        "compliance": nested_get(audit, "manifest_compliance", "status") or "UNKNOWN",
        "baseline": baseline_status(audit, health_text),
        "manifest": nested_get(audit, "manifest_compliance", "status") or "UNKNOWN",
        "drift": health_value(health_text, "Baseline drift")
        or nested_get(audit, "architecture_baseline_drift", "status")
        or "UNKNOWN",
        "architectural_violations": nested_get(
            metrics,
            "architecture",
            "architectural_violations_count",
        ),
        "dependency_cycles": nested_get(metrics, "architecture", "dependency_cycles") or [],
        "modules": nested_get(metrics, "structure", "modules"),
        "public_services": nested_get(metrics, "application", "services"),
        "governance_consistency": consistency.get("status", sources["governance_consistency"]["status"]),
    }


def engineering_indicators(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Resume indicadores de engenharia."""

    quality_gate = sources["quality_gate_summary"].get("data", {})
    static_analysis = sources["static_analysis"].get("data", {})
    metrics = sources["architecture_metrics"].get("data", {})
    test_diagnostics = sources["test_failure_diagnostics"].get("data", {})
    performance = sources["test_performance_budget"].get("data", {})

    return {
        "static_analysis": sources["static_analysis"]["status"],
        "static_analysis_errors": static_analysis.get("error_count"),
        "quality_gate": quality_gate.get("overall_status", sources["quality_gate_summary"]["status"]),
        "quality_gate_duration_seconds": quality_gate.get("total_duration_seconds"),
        "tests": nested_get(quality_gate, "steps", "test_suite", "status")
        or sources["test_failure_diagnostics"]["status"],
        "test_failures": nested_get(test_diagnostics, "summary", "failures"),
        "test_errors": nested_get(test_diagnostics, "summary", "errors"),
        "test_performance_budget": sources["test_performance_budget"]["status"],
        "test_performance_duration_seconds": nested_get(
            performance,
            "summary",
            "total_duration_seconds",
        ),
        "architectural_test_coverage_percent": nested_get(
            metrics,
            "testing",
            "architectural_tests_percentage",
        ),
        "architectural_tests": nested_get(metrics, "testing", "architectural_tests"),
    }


def governance_indicators(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Resume governanca documental e de CI."""

    consistency = sources["governance_consistency"].get("data", {})
    consistency_components = consistency.get("components_analyzed", {})
    adrs = consistency_components.get("adrs", {}) if isinstance(consistency_components, dict) else {}
    documentation = (
        consistency_components.get("documentation", {})
        if isinstance(consistency_components, dict)
        else {}
    )

    return {
        "adrs": {
            "count": len(adrs.get("files", [])) if isinstance(adrs, dict) else None,
            "missing_numbers": adrs.get("missing_numbers", []) if isinstance(adrs, dict) else [],
            "duplicates": adrs.get("duplicates", []) if isinstance(adrs, dict) else [],
        },
        "documentation": {
            "status": documentation_status(consistency),
            "divergences": len(consistency.get("documentation_divergences", [])),
            "missing_references": len(consistency.get("missing_references", [])),
        },
        "workflow": workflow_status(consistency),
        "ci": {
            "readiness": sources["ci_readiness"]["status"],
            "reproducible_build": sources["reproducible_build"]["status"],
        },
        "audit": {
            "architecture_audit": sources["architecture_audit"]["status"],
            "governance_consistency": consistency.get(
                "status",
                sources["governance_consistency"]["status"],
            ),
            "failure_context": sources["failure_context"]["status"],
            "repository_compliance": sources["repository_compliance"]["status"],
        },
    }


def operation_indicators(sources: dict[str, dict[str, Any]]) -> dict[str, str]:
    """Confirma restricoes operacionais a partir dos relatorios consolidados."""

    health_text = sources["architecture_health_md"].get("text", "")
    consistency = sources["governance_consistency"].get("data", {})
    adr_files = (
        consistency.get("components_analyzed", {})
        .get("adrs", {})
        .get("files", [])
        if isinstance(consistency, dict)
        else []
    )

    return {
        "real_operation_disabled": confirmation_from_adr(
            adr_files,
            "operacao-real-desabilitada",
        ),
        "replay_remains_simulated": (
            "CONFIRMED"
            if "Replay protegido: OK" in health_text
            and "Sem acesso a infraestrutura operacional: OK" in health_text
            else "UNKNOWN"
        ),
        "research_remains_laboratory": (
            "CONFIRMED"
            if "Research protegido: OK" in health_text
            and "Sem acesso a infraestrutura operacional: OK" in health_text
            else "UNKNOWN"
        ),
        "ai_does_not_execute_orders": confirmation_from_adr(
            adr_files,
            "ia-nao-executa-ordens",
        ),
    }


def classify_overall(
    sources: dict[str, dict[str, Any]],
    indicators: dict[str, Any],
) -> str:
    """Classifica o dashboard executivo."""

    statuses = [str(source.get("status", "UNKNOWN")).upper() for source in sources.values()]
    required_missing = [
        key
        for key in (
            "quality_gate_summary",
            "architecture_audit",
            "architecture_metrics",
            "governance_consistency",
        )
        if not sources[key]["found"]
    ]
    if required_missing or any(status in CRITICAL_STATUSES for status in statuses):
        return "CRITICAL"

    governance_status = str(
        indicators["governance"]["audit"]["governance_consistency"]
    ).upper()
    failure_categories = nested_get(
        sources["failure_context"].get("data", {}),
        "failures_by_category",
    )
    if governance_status == "INCONSISTENT" or failure_categories:
        return "ATTENTION"

    effective_missing = [
        key
        for key, source in sources.items()
        if is_effectively_missing(key, source, sources)
    ]
    if any(status in ATTENTION_STATUSES for status in statuses) or effective_missing:
        return "GOOD"
    return "EXCELLENT"


def executive_summary(
    classification: str,
    indicators: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Cria resumo textual curto para leitura executiva."""

    missing = [
        source["path"]
        for key, source in sources.items()
        if is_effectively_missing(key, source, sources)
    ]
    return {
        "classification": classification,
        "architecture": (
            f"Compliance {indicators['architecture']['compliance']}; "
            f"drift {indicators['architecture']['drift']}."
        ),
        "engineering": (
            f"Quality Gate {indicators['engineering']['quality_gate']}; "
            f"static analysis {indicators['engineering']['static_analysis']}."
        ),
        "governance": (
            f"Governance consistency "
            f"{indicators['governance']['audit']['governance_consistency']}."
        ),
        "missing_reports": missing,
    }


def read_json(path: Path) -> dict[str, Any]:
    """Le JSON; erro de leitura vira status consolidavel."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"status": "ERROR", "message": f"JSON invalido: {exc}"}
    return data if isinstance(data, dict) else {"status": "ERROR", "message": "JSON sem objeto raiz."}


def extract_status(data: dict[str, Any]) -> str:
    """Extrai status dos formatos de relatorio ja existentes."""

    for key in ("overall_status", "status", "classification"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().upper()

    audit_status = nested_get(data, "manifest_compliance", "status")
    if audit_status:
        return str(audit_status).upper()
    violations = nested_get(data, "architecture", "architectural_violations_count")
    if isinstance(violations, int):
        return "OK" if violations == 0 else "FAILED"
    return "UNKNOWN"


def extract_markdown_status(text: str) -> str:
    """Extrai status simples de Markdown."""

    value = health_value(text, "Status geral")
    return value.upper() if value else "UNKNOWN"


def health_value(text: str, label: str) -> str | None:
    """Busca '- Label: valor' em Markdown."""

    pattern = re.compile(rf"^- {re.escape(label)}:\s*(.+)$", re.MULTILINE)
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def baseline_status(audit: dict[str, Any], health_text: str) -> str:
    """Resume baseline a partir de auditoria e health report."""

    drift = health_value(health_text, "Baseline drift") or nested_get(
        audit,
        "architecture_baseline_drift",
        "status",
    )
    criticality = health_value(health_text, "Criticidade do drift") or nested_get(
        audit,
        "architecture_baseline_drift",
        "criticality",
    )
    if not drift:
        return "UNKNOWN"
    return f"{drift} ({criticality or 'sem criticidade'})"


def documentation_status(consistency: dict[str, Any]) -> str:
    """Classifica documentacao a partir do relatorio de consistencia."""

    if consistency.get("documentation_divergences"):
        return "DIVERGENT"
    return "OK" if consistency else "UNKNOWN"


def workflow_status(consistency: dict[str, Any]) -> str:
    """Resume workflow a partir da consistencia documental."""

    documentation = nested_get(consistency, "components_analyzed", "documentation")
    workflow = documentation.get("workflow") if isinstance(documentation, dict) else None
    if isinstance(workflow, dict) and workflow.get("exists") is True:
        return "PRESENT"
    return "UNKNOWN"


def confirmation_from_adr(adr_files: list[Any], token: str) -> str:
    """Confirma decisao operacional pela presenca de ADR oficial."""

    return (
        "CONFIRMED"
        if any(token in str(filename) for filename in adr_files)
        else "UNKNOWN"
    )


def is_effectively_missing(
    key: str,
    source: dict[str, Any],
    sources: dict[str, dict[str, Any]],
) -> bool:
    """Trata alternativas equivalentes como nao ausentes."""

    if source["found"]:
        return False
    if key == "architecture_health_json" and sources["architecture_health_md"]["found"]:
        return False
    return True


def nested_get(data: Any, *keys: str) -> Any:
    """Busca valor aninhado em dicionarios."""

    current = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def write_report(report: dict[str, Any], report_path: Path = REPORT_PATH) -> None:
    """Grava o dashboard consolidado."""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Gera reports/governance_dashboard.json."""

    report = build_dashboard()
    write_report(report)
    print(f"Governance dashboard classification: {report['overall_classification']}")
    print(f"JSON report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
