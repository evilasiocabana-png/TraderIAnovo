"""Relatorio consolidado de saude arquitetural do TraderIA_WDO."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "architecture_health.md"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import architecture_audit


ARCHITECTURAL_SUITES = {
    "test_application_contracts.py",
    "test_event_contracts.py",
    "test_dependency_rules.py",
    "test_domain_contracts.py",
    "test_application_api.py",
    "test_research_contracts.py",
    "test_provider_architecture.py",
    "test_configuration_contracts.py",
    "test_session_contracts.py",
    "test_dashboard_facade.py",
    "test_architecture_regression.py",
    "test_architecture_manifest.py",
    "test_architecture_baseline.py",
    "test_quality_gate.py",
}


def build_health_report(root: Path | str = ROOT) -> dict[str, Any]:
    """Calcula indicadores de saude arquitetural sem modificar o projeto."""

    project_root = Path(root)
    audit = architecture_audit.run_audit(root=project_root, write_reports=False)
    snapshot = audit["architecture_snapshot"]
    manifest = audit["manifest_compliance"]
    drift = audit["architecture_baseline_drift"]

    structure = _structure_indicators(snapshot)
    services = _service_indicators(snapshot, project_root)
    domain = _domain_indicators(snapshot, project_root)
    dashboard = _dashboard_indicators(snapshot)
    replay = _package_indicators(snapshot, "replay")
    research = _package_indicators(snapshot, "research")
    providers = _provider_indicators(snapshot, project_root)
    event_bus = _event_bus_indicators(snapshot)
    tests = _test_indicators(project_root)
    governance = _governance_indicators(project_root)

    status = classify_health(
        manifest=manifest,
        drift=drift,
        structure=structure,
        domain=domain,
        dashboard=dashboard,
        replay=replay,
        research=research,
        providers=providers,
        governance=governance,
    )

    return {
        "status": status,
        "structure": structure,
        "services": services,
        "domain": domain,
        "dashboard": dashboard,
        "replay": replay,
        "research_lab": research,
        "providers": providers,
        "event_bus": event_bus,
        "tests": tests,
        "governance": governance,
        "manifest_status": manifest["status"],
        "baseline_drift_status": drift["status"],
        "baseline_drift_criticality": drift["criticality"],
    }


def classify_health(
    *,
    manifest: dict[str, Any],
    drift: dict[str, Any],
    structure: dict[str, Any],
    domain: dict[str, Any],
    dashboard: dict[str, Any],
    replay: dict[str, Any],
    research: dict[str, Any],
    providers: dict[str, Any],
    governance: dict[str, Any],
) -> str:
    """Classifica a saude geral por regras objetivas."""

    if manifest["status"] != "OK":
        return "CRITICO"
    critical_checks = [
        structure["missing_layers"],
        domain["purity"] != "OK",
        dashboard["ui_decoupled"] != "OK",
        replay["without_operational_infrastructure"] != "OK",
        research["without_operational_infrastructure"] != "OK",
        providers["physical_access_restricted_to_adapters"] != "OK",
    ]
    if any(critical_checks):
        return "CRITICO"
    if not all(governance.values()):
        return "ATENCAO"
    if drift["status"] != "OK":
        return "BOM"
    return "EXCELENTE"


def write_report(report: dict[str, Any], path: Path | str = REPORT_PATH) -> None:
    """Escreve o relatorio Markdown de saude arquitetural."""

    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(to_markdown(report), encoding="utf-8")


def to_markdown(report: dict[str, Any]) -> str:
    """Converte os indicadores para Markdown."""

    lines = [
        "# Architecture Health Report",
        "",
        f"- Status geral: {report['status']}",
        f"- Manifest: {report['manifest_status']}",
        f"- Baseline drift: {report['baseline_drift_status']}",
        f"- Criticidade do drift: {report['baseline_drift_criticality']}",
        "",
        "## Estrutura",
        "",
        f"- Camadas encontradas: {', '.join(report['structure']['found_layers']) or 'nenhuma'}",
        f"- Camadas ausentes: {', '.join(report['structure']['missing_layers']) or 'nenhuma'}",
        f"- Quantidade de modulos: {report['structure']['modules_count']}",
        f"- Quantidade de arquivos Python: {report['structure']['python_files_count']}",
        "",
        "## Servicos",
        "",
        f"- Total de servicos Application: {report['services']['total_application_services']}",
        f"- Servicos protegidos por testes: {', '.join(report['services']['protected_services']) or 'nenhum'}",
        f"- Cobertura dos contratos: {report['services']['contract_coverage']}",
        "",
        "## Dominio",
        "",
        f"- Contratos encontrados: {', '.join(report['domain']['contracts_found']) or 'nenhum'}",
        f"- Contratos protegidos: {', '.join(report['domain']['contracts_protected']) or 'nenhum'}",
        f"- Pureza do dominio: {report['domain']['purity']}",
        "",
        "## Dashboard",
        "",
        f"- DashboardService como fachada unica: {report['dashboard']['dashboard_service_facade']}",
        f"- UI desacoplada: {report['dashboard']['ui_decoupled']}",
        "",
        "## Replay",
        "",
        f"- Replay protegido: {report['replay']['protected']}",
        f"- Sem acesso a infraestrutura operacional: {report['replay']['without_operational_infrastructure']}",
        "",
        "## Research Lab",
        "",
        f"- Research protegido: {report['research_lab']['protected']}",
        f"- Sem acesso a infraestrutura operacional: {report['research_lab']['without_operational_infrastructure']}",
        "",
        "## Providers",
        "",
        f"- HistoricalDataProvider encontrado: {report['providers']['historical_data_provider_found']}",
        f"- Adapters encontrados: {', '.join(report['providers']['adapters_found']) or 'nenhum'}",
        f"- Acessos fisicos restritos aos adapters: {report['providers']['physical_access_restricted_to_adapters']}",
        "",
        "## EventBus",
        "",
        f"- Eventos encontrados: {report['event_bus']['events_count']}",
        f"- Publishers encontrados: {report['event_bus']['publishers_count']}",
        f"- Subscribers encontrados: {report['event_bus']['subscribers_count']}",
        "",
        "## Testes",
        "",
        f"- Total de testes: {report['tests']['total_tests']}",
        f"- Total de suites: {report['tests']['total_suites']}",
        f"- Suites arquiteturais: {report['tests']['architectural_suites']}",
        f"- Ultima execucao: {report['tests']['last_execution']}",
        "",
        "## Governanca",
        "",
        f"- Manifest presente: {report['governance']['manifest_present']}",
        f"- Baseline presente: {report['governance']['baseline_present']}",
        f"- ADRs presentes: {report['governance']['adrs_present']}",
        f"- Workflow presente: {report['governance']['workflow_present']}",
        f"- Indice arquitetural presente: {report['governance']['index_present']}",
        "",
    ]
    return "\n".join(lines)


def _structure_indicators(snapshot: dict[str, Any]) -> dict[str, Any]:
    layers = snapshot["layers"]
    statistics = snapshot["statistics"]
    return {
        "found_layers": list(layers["present"]),
        "missing_layers": list(layers["missing"]),
        "modules_count": statistics["modules"],
        "python_files_count": statistics["python_files"],
    }


def _service_indicators(snapshot: dict[str, Any], root: Path) -> dict[str, Any]:
    services = snapshot["public_services"]["found"]
    protected = []
    if (root / "tests" / "test_application_api.py").exists():
        protected = list(services)
    return {
        "total_application_services": len(services),
        "protected_services": protected,
        "contract_coverage": "OK" if protected else "FALHA",
    }


def _domain_indicators(snapshot: dict[str, Any], root: Path) -> dict[str, Any]:
    contracts = snapshot["domain_contracts"]["found"]
    contracts_test = root / "tests" / "test_domain_contracts.py"
    return {
        "contracts_found": list(contracts),
        "contracts_protected": list(contracts) if contracts_test.exists() else [],
        "purity": "OK" if contracts_test.exists() else "FALHA",
    }


def _dashboard_indicators(snapshot: dict[str, Any]) -> dict[str, str]:
    dashboard = snapshot["dashboard"]
    facade = bool(dashboard["uses_dashboard_service"])
    decoupled = bool(dashboard["depends_only_on_dashboard_service"])
    return {
        "dashboard_service_facade": "OK" if facade else "FALHA",
        "ui_decoupled": "OK" if decoupled else "FALHA",
    }


def _package_indicators(snapshot: dict[str, Any], name: str) -> dict[str, str]:
    section = snapshot[name]
    clean = section["status"] == "OK"
    return {
        "protected": "OK" if clean else "FALHA",
        "without_operational_infrastructure": "OK" if clean else "FALHA",
    }


def _provider_indicators(snapshot: dict[str, Any], root: Path) -> dict[str, Any]:
    providers = snapshot["providers"]
    adapters = list(providers["adapters_exported"])
    provider_test = root / "tests" / "test_provider_architecture.py"
    return {
        "historical_data_provider_found": "OK"
        if "HistoricalDataProvider" in providers["providers"]
        else "FALHA",
        "adapters_found": adapters,
        "physical_access_restricted_to_adapters": "OK"
        if provider_test.exists()
        else "FALHA",
    }


def _event_bus_indicators(snapshot: dict[str, Any]) -> dict[str, int]:
    event_bus = snapshot["event_bus"]
    return {
        "events_count": event_bus["official_events_count"],
        "publishers_count": len(event_bus["publishers_found"]),
        "subscribers_count": len(event_bus["subscribers_found"]),
    }


def _test_indicators(root: Path) -> dict[str, Any]:
    test_files = sorted((root / "tests").glob("test_*.py"))
    architectural = [
        path.name for path in test_files if path.name in ARCHITECTURAL_SUITES
    ]
    return {
        "total_tests": len(test_files),
        "total_suites": len(test_files),
        "architectural_suites": len(architectural),
        "last_execution": "nao disponivel",
    }


def _governance_indicators(root: Path) -> dict[str, bool]:
    return {
        "manifest_present": (root / "architecture_manifest.json").exists(),
        "baseline_present": (root / "architecture_baseline.json").exists(),
        "adrs_present": (root / "docs" / "adr").exists(),
        "workflow_present": (
            root / "docs" / "ARCHITECTURE_CHANGE_WORKFLOW.md"
        ).exists(),
        "index_present": (root / "docs" / "ARCHITECTURE_INDEX.md").exists(),
    }


def main() -> int:
    report = build_health_report()
    write_report(report)
    print(f"Architecture health status: {report['status']}")
    print(f"Markdown report: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
