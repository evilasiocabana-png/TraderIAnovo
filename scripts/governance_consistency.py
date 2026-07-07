"""Valida consistencia entre artefatos de governanca do TraderIA_WDO."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "governance_consistency.json"

REQUIRED_GOVERNANCE_FILES = (
    "architecture_manifest.json",
    "architecture_baseline.json",
    "reports/architecture_audit.json",
    "reports/architecture_metrics.json",
    "README.md",
    "TRADERIA_ARCHITECTURE_BIBLE.md",
    "ARCHITECTURE_RULES.md",
    "docs/ARCHITECTURE_INDEX.md",
    "docs/ARCHITECTURE_CHANGE_WORKFLOW.md",
    "docs/CI_PIPELINE.md",
    "docs/CI_FAILURE_TRIAGE.md",
)

REQUIRED_SCRIPTS = (
    "scripts/run_quality_gate.py",
    "scripts/architecture_audit.py",
    "scripts/architecture_health.py",
    "scripts/architecture_metrics.py",
    "scripts/repository_compliance.py",
    "scripts/ci_readiness.py",
    "scripts/reproducible_build.py",
)

REQUIRED_GOVERNANCE_TESTS = (
    "tests/test_architecture_manifest.py",
    "tests/test_architecture_baseline.py",
    "tests/test_architecture_rules.py",
    "tests/test_architecture_regression.py",
    "tests/test_architecture_metrics.py",
    "tests/test_architecture_health.py",
    "tests/test_ci_configuration.py",
    "tests/test_ci_pipeline_template.py",
)

VALID_ADR_STATUSES = {
    "Proposto",
    "Aprovado",
    "Substituido",
    "Substituído",
    "Rejeitado",
}

REFERENCE_PATTERN = re.compile(r"(?P<path>(?:docs/)?[A-Za-z0-9_.\-/]+(?:\.md|\.json|\.py|\.yml))")


@dataclass(frozen=True)
class Finding:
    """Inconsistencia ou aviso de governanca."""

    component: str
    severity: str
    message: str
    reference: str | None = None


def build_report(root: Path = ROOT) -> dict[str, Any]:
    """Executa todas as validacoes de governanca."""

    components: dict[str, Any] = {}
    findings: list[Finding] = []

    components["required_files"] = check_required_files(root, REQUIRED_GOVERNANCE_FILES, findings)
    manifest = read_json(root / "architecture_manifest.json", findings, "manifest")
    baseline = read_json(root / "architecture_baseline.json", findings, "baseline")
    audit = read_json(root / "reports" / "architecture_audit.json", findings, "architecture_audit")
    metrics = read_json(root / "reports" / "architecture_metrics.json", findings, "architecture_metrics")

    components["manifest"] = validate_manifest(manifest, baseline, audit, metrics, findings)
    components["baseline"] = validate_baseline(baseline, manifest, findings)
    components["adrs"] = validate_adrs(root, findings)
    components["documentation"] = validate_documentation(root, findings)
    components["scripts"] = validate_scripts(root, findings)
    components["tests"] = validate_governance_tests(root, findings)

    findings = unique_findings(findings)
    inconsistencies = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    classification = classify(inconsistencies, warnings)

    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": classification,
        "classification": classification,
        "components_analyzed": components,
        "inconsistencies": [finding_dict(item) for item in inconsistencies],
        "missing_references": [
            finding_dict(item)
            for item in findings
            if item.component in {"required_files", "documentation", "adr_references"}
            and item.severity == "error"
        ],
        "documentation_divergences": [
            finding_dict(item)
            for item in findings
            if item.component in {"documentation", "adr_references"}
            and item.severity in {"error", "warning"}
        ],
        "warnings": [finding_dict(item) for item in warnings],
    }


def check_required_files(
    root: Path,
    paths: tuple[str, ...],
    findings: list[Finding],
) -> dict[str, str]:
    """Confere presenca dos arquivos centrais de governanca."""

    result: dict[str, str] = {}
    for relative in paths:
        exists = (root / relative).exists()
        result[relative] = "FOUND" if exists else "MISSING"
        if not exists:
            findings.append(
                Finding(
                    component="required_files",
                    severity="error",
                    message=f"Arquivo obrigatorio ausente: {relative}",
                    reference=relative,
                )
            )
    return result


def validate_manifest(
    manifest: dict[str, Any],
    baseline: dict[str, Any],
    audit: dict[str, Any],
    metrics: dict[str, Any],
    findings: list[Finding],
) -> dict[str, Any]:
    """Compara manifesto com baseline, auditoria e metricas."""

    result: dict[str, Any] = {}
    comparisons = (
        ("public_services", "services"),
        ("domain_contracts", "contracts"),
        ("providers", "providers"),
        ("adapters", "adapters"),
        ("events", "events"),
    )
    for manifest_key, baseline_key in comparisons:
        manifest_values = set(as_list(manifest.get(manifest_key)))
        baseline_values = set(as_list(baseline.get(baseline_key)))
        missing = sorted(manifest_values - baseline_values)
        extra = sorted(baseline_values - manifest_values)
        result[manifest_key] = {
            "manifest": len(manifest_values),
            "baseline": len(baseline_values),
            "missing_in_baseline": missing,
            "extra_in_baseline": extra,
        }
        if missing or extra:
            findings.append(
                Finding(
                    component="manifest",
                    severity="error",
                    message=(
                        f"Divergencia entre manifest.{manifest_key} "
                        f"e baseline.{baseline_key}."
                    ),
                    reference=f"{manifest_key}/{baseline_key}",
                )
            )

    manifest_layers = set(as_list(manifest.get("layers")))
    baseline_layers = set(as_list(nested_get(baseline, "structure", "layers")))
    missing_layers = sorted(manifest_layers - baseline_layers)
    result["layers"] = {
        "manifest": sorted(manifest_layers),
        "baseline": sorted(baseline_layers),
        "missing_in_baseline": missing_layers,
    }
    if missing_layers:
        findings.append(
            Finding(
                component="manifest",
                severity="warning",
                message="Camadas do manifesto nao aparecem na baseline estrutural.",
                reference=", ".join(missing_layers),
            )
        )

    audit_manifest_status = nested_get(audit, "manifest_compliance", "status")
    result["architecture_audit_manifest_status"] = audit_manifest_status or "UNKNOWN"
    if audit_manifest_status and str(audit_manifest_status).upper() != "OK":
        findings.append(
            Finding(
                component="manifest",
                severity="error",
                message=f"Auditoria arquitetural reporta manifest_compliance={audit_manifest_status}.",
                reference="reports/architecture_audit.json",
            )
        )

    metric_services = nested_get(metrics, "application", "services")
    if isinstance(metric_services, int) and metric_services != len(as_list(manifest.get("public_services"))):
        findings.append(
            Finding(
                component="manifest",
                severity="warning",
                message="Quantidade de servicos em architecture_metrics diverge do manifesto.",
                reference="reports/architecture_metrics.json",
            )
        )
    result["metrics_services"] = metric_services
    return result


def validate_baseline(
    baseline: dict[str, Any],
    manifest: dict[str, Any],
    findings: list[Finding],
) -> dict[str, Any]:
    """Verifica integridade minima da baseline arquitetural."""

    required_sections = ("services", "contracts", "providers", "adapters", "events", "statistics", "structure")
    present = {section: section in baseline for section in required_sections}
    for section, exists in present.items():
        if not exists:
            findings.append(
                Finding(
                    component="baseline",
                    severity="error",
                    message=f"Secao ausente na baseline: {section}",
                    reference="architecture_baseline.json",
                )
            )

    statistics = baseline.get("statistics", {})
    if isinstance(statistics, dict):
        expected_counts = {
            "services": len(as_list(baseline.get("services"))),
            "contracts": len(as_list(baseline.get("contracts"))),
            "providers": len(as_list(baseline.get("providers"))),
            "adapters": len(as_list(baseline.get("adapters"))),
        }
        for key, expected in expected_counts.items():
            actual = statistics.get(key)
            if isinstance(actual, int) and actual != expected:
                findings.append(
                    Finding(
                        component="baseline",
                        severity="warning",
                        message=f"Baseline statistics.{key}={actual}, esperado {expected}.",
                        reference="architecture_baseline.json",
                    )
                )

    manifest_rules = set(as_list(manifest.get("architecture_rules")))
    described_rules = set((manifest.get("architecture_rule_descriptions") or {}).keys())
    missing_descriptions = sorted(manifest_rules - described_rules)
    if missing_descriptions:
        findings.append(
            Finding(
                component="baseline",
                severity="warning",
                message="Regras arquiteturais sem descricao no manifesto.",
                reference=", ".join(missing_descriptions),
            )
        )
    return {"required_sections": present, "statistics": statistics}


def validate_adrs(root: Path, findings: list[Finding]) -> dict[str, Any]:
    """Valida numeracao, status e referencias dos ADRs."""

    adr_dir = root / "docs" / "adr"
    adr_files = sorted(adr_dir.glob("ADR-[0-9][0-9][0-9][0-9]-*.md"))
    numbers: list[int] = []
    duplicates: list[int] = []
    statuses: dict[str, str] = {}

    for path in adr_files:
        match = re.match(r"ADR-(\d{4})-", path.name)
        if not match:
            continue
        number = int(match.group(1))
        if number in numbers:
            duplicates.append(number)
        numbers.append(number)

        text = path.read_text(encoding="utf-8", errors="replace")
        status = extract_adr_status(text)
        statuses[path.name] = status or "MISSING"
        if not status or status not in VALID_ADR_STATUSES:
            findings.append(
                Finding(
                    component="adrs",
                    severity="error",
                    message=f"ADR com status invalido ou ausente: {path.name}",
                    reference=path.name,
                )
            )
        validate_references(root, path, text, findings, component="adr_references")

    expected = list(range(1, max(numbers) + 1)) if numbers else []
    missing_numbers = sorted(set(expected) - set(numbers))
    if missing_numbers:
        findings.append(
            Finding(
                component="adrs",
                severity="error",
                message="Numeracao de ADR nao e continua.",
                reference=", ".join(f"ADR-{number:04d}" for number in missing_numbers),
            )
        )
    if duplicates:
        findings.append(
            Finding(
                component="adrs",
                severity="error",
                message="Numeracao duplicada em ADRs.",
                reference=", ".join(f"ADR-{number:04d}" for number in duplicates),
            )
        )

    return {
        "directory": "docs/adr",
        "files": [path.name for path in adr_files],
        "numbers": numbers,
        "missing_numbers": missing_numbers,
        "duplicates": duplicates,
        "statuses": statuses,
    }


def validate_documentation(root: Path, findings: list[Finding]) -> dict[str, Any]:
    """Valida documentos oficiais e referencias cruzadas."""

    docs = {
        "readme": "README.md",
        "architecture_bible": "TRADERIA_ARCHITECTURE_BIBLE.md",
        "architecture_rules": "ARCHITECTURE_RULES.md",
        "architecture_index": "docs/ARCHITECTURE_INDEX.md",
        "workflow": "docs/ARCHITECTURE_CHANGE_WORKFLOW.md",
        "ci_documentation": "docs/CI_PIPELINE.md",
        "baseline_documentation": "docs/ARCHITECTURE_INDEX.md",
        "audit_documentation": "docs/CI_FAILURE_TRIAGE.md",
    }
    result: dict[str, Any] = {}
    for name, relative in docs.items():
        path = root / relative
        exists = path.exists()
        result[name] = {"path": relative, "exists": exists}
        if exists:
            text = path.read_text(encoding="utf-8", errors="replace")
            result[name]["references_checked"] = validate_references(
                root,
                path,
                text,
                findings,
                component="documentation",
            )
        else:
            findings.append(
                Finding(
                    component="documentation",
                    severity="error",
                    message=f"Documento de governanca ausente: {relative}",
                    reference=relative,
                )
            )

    readme_text = (root / "README.md").read_text(encoding="utf-8", errors="replace")
    for required in ("MANIFEST.md", "TRADERIA_ARCHITECTURE_BIBLE.md", "ARCHITECTURE_RULES.md"):
        if required not in readme_text:
            findings.append(
                Finding(
                    component="documentation",
                    severity="warning",
                    message=f"README nao referencia {required}.",
                    reference="README.md",
                )
            )
    return result


def validate_scripts(root: Path, findings: list[Finding]) -> dict[str, str]:
    """Confere scripts de governanca esperados."""

    result: dict[str, str] = {}
    for relative in REQUIRED_SCRIPTS:
        exists = (root / relative).exists()
        result[relative] = "FOUND" if exists else "MISSING"
        if not exists:
            findings.append(
                Finding(
                    component="scripts",
                    severity="error",
                    message=f"Script de governanca ausente: {relative}",
                    reference=relative,
                )
            )
    return result


def validate_governance_tests(root: Path, findings: list[Finding]) -> dict[str, str]:
    """Confirma suites que protegem governanca."""

    result: dict[str, str] = {}
    for relative in REQUIRED_GOVERNANCE_TESTS:
        exists = (root / relative).exists()
        result[relative] = "FOUND" if exists else "MISSING"
        if not exists:
            findings.append(
                Finding(
                    component="tests",
                    severity="error",
                    message=f"Suite de governanca ausente: {relative}",
                    reference=relative,
                )
            )
    return result


def validate_references(
    root: Path,
    source_path: Path,
    text: str,
    findings: list[Finding],
    *,
    component: str,
) -> int:
    """Valida referencias locais simples citadas em documentos."""

    checked = 0
    for match in REFERENCE_PATTERN.finditer(text):
        reference = match.group("path").rstrip(").,;:")
        if reference.startswith(("http", "https")):
            continue
        candidates = reference_candidates(root, source_path, reference)
        if not any(candidate.exists() for candidate in candidates):
            checked += 1
            findings.append(
                Finding(
                    component=component,
                    severity="error",
                    message=f"Referencia inexistente em {source_path.relative_to(root)}: {reference}",
                    reference=reference,
                )
            )
        else:
            checked += 1
    return checked


def reference_candidates(root: Path, source_path: Path, reference: str) -> tuple[Path, ...]:
    """Gera caminhos plausiveis para referencias documentais locais."""

    candidates = [root / reference, source_path.parent / reference]
    if "/" not in reference and "\\" not in reference:
        candidates.extend(
            [
                root / "docs" / reference,
                root / "docs" / "adr" / reference,
                root / "tests" / reference,
                root / "scripts" / reference,
            ]
        )
    return tuple(candidates)


def read_json(path: Path, findings: list[Finding], component: str) -> dict[str, Any]:
    """Le JSON de governanca e registra problema como achado."""

    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                component=component,
                severity="error",
                message=f"JSON invalido: {exc}",
                reference=str(path.name),
            )
        )
        return {}
    if not isinstance(data, dict):
        findings.append(
            Finding(
                component=component,
                severity="error",
                message="JSON raiz nao e objeto.",
                reference=str(path.name),
            )
        )
        return {}
    return data


def extract_adr_status(text: str) -> str | None:
    """Extrai a linha de status do ADR."""

    match = re.search(r"^- Status:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def as_list(value: Any) -> list[Any]:
    """Normaliza listas JSON."""

    return value if isinstance(value, list) else []


def nested_get(data: dict[str, Any], *keys: str) -> Any:
    """Busca valor aninhado em dicionario."""

    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def classify(inconsistencies: list[Finding], warnings: list[Finding]) -> str:
    """Classifica o estado geral da governanca."""

    if inconsistencies:
        return "INCONSISTENT"
    if warnings:
        return "MINOR INCONSISTENCIES"
    return "CONSISTENT"


def finding_dict(finding: Finding) -> dict[str, str | None]:
    """Serializa achado."""

    return {
        "component": finding.component,
        "severity": finding.severity,
        "message": finding.message,
        "reference": finding.reference,
    }


def unique_findings(findings: list[Finding]) -> list[Finding]:
    """Remove achados duplicados preservando ordem."""

    seen: set[tuple[str, str, str, str | None]] = set()
    unique: list[Finding] = []
    for finding in findings:
        key = (finding.component, finding.severity, finding.message, finding.reference)
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return unique


def write_report(report: dict[str, Any], report_path: Path = REPORT_PATH) -> None:
    """Grava o relatorio consolidado."""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    """Executa validacao e gera reports/governance_consistency.json."""

    report = build_report()
    write_report(report)
    print(f"Governance consistency status: {report['status']}")
    print(f"JSON report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
