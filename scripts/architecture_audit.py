"""Auditoria arquitetural baseada no manifesto oficial do projeto."""

from __future__ import annotations

import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "architecture_manifest.json"
BASELINE_PATH = ROOT / "architecture_baseline.json"
REPORTS_DIR = ROOT / "reports"
JSON_REPORT_PATH = REPORTS_DIR / "architecture_audit.json"
MARKDOWN_REPORT_PATH = REPORTS_DIR / "architecture_audit.md"

ARCHITECTURAL_LAYER_CANDIDATES = {
    "alpha",
    "analytics",
    "application",
    "backtest",
    "core",
    "data",
    "database",
    "domain",
    "market",
    "market_data",
    "paper",
    "replay",
    "research",
    "risk",
    "strategies",
    "tests",
}

REQUIRED_LAYERS = {
    "application",
    "core",
    "database",
    "domain",
    "market",
    "replay",
    "research",
    "risk",
    "strategies",
    "tests",
}

EXPECTED_PUBLIC_SERVICES = {
    "ConfigurationService",
    "DashboardService",
    "ReplayService",
    "ResearchLabService",
    "SessionService",
}

EXPECTED_DOMAIN_CONTRACTS = {
    "BacktestResult",
    "DecisionContext",
    "ExecutionOrder",
    "MarketSnapshot",
    "RiskDecision",
    "StrategySignal",
}

ARCHITECTURE_SCAN_ROOTS = {
    "application",
    "core",
    "database",
    "domain",
    "market",
    "market_data",
    "replay",
    "research",
    "risk",
    "strategies",
}

DASHBOARD_FORBIDDEN_DEPENDENCIES = {
    "market_data",
    "replay",
    "research",
    "strategies",
    "database",
    "pandas",
    "duckdb",
    "pathlib",
}

OPERATIONAL_FORBIDDEN_TOKENS = {
    "Broker",
    "MT5",
    "MetaTrader",
}

OPERATIONAL_FORBIDDEN_IMPORT_ROOTS = {
    "broker",
    "corretora",
    "mt5",
}

MARKET_DATA_ABSTRACTIONS = {
    "HistoricalDataSource",
    "HistoricalDataSourceResult",
}

RULE_CHECKS = {
    "adapters_own_physical_formats": {
        "tests/test_application_contracts.py",
        "tests/test_dependency_rules.py",
    },
    "application_api_freeze": {"tests/test_application_api.py"},
    "dashboard_service_facade": {
        "tests/test_dashboard_service_contract.py",
        "tests/test_application_contracts.py",
    },
    "dependency_rules": {"tests/test_dependency_rules.py"},
    "domain_purity": {
        "tests/test_architecture_rules.py",
        "tests/test_dependency_rules.py",
        "tests/test_domain_contracts.py",
    },
    "event_bus_official_events": {"tests/test_event_contracts.py"},
    "replay_no_physical_data_access": {
        "tests/test_replay_contracts.py",
        "tests/test_replay_market_data_provider.py",
    },
    "research_no_physical_data_access": {
        "tests/test_research_market_data_provider.py",
        "tests/test_application_contracts.py",
    },
}


@dataclass(frozen=True)
class ManifestSectionComparison:
    """Resultado de comparacao de uma secao do manifesto."""

    declared: list[str]
    found: list[str]
    present: list[str]
    missing: list[str]
    extra: list[str]
    divergences: list[str]
    status: str

    def to_dict(self) -> dict[str, object]:
        return {
            "declared": self.declared,
            "found": self.found,
            "present": self.present,
            "missing": self.missing,
            "extra": self.extra,
            "divergences": self.divergences,
            "status": self.status,
        }


def load_manifest(path: Path | str = MANIFEST_PATH) -> dict[str, Any]:
    """Carrega o manifesto oficial com erro claro para JSON invalido."""
    manifest_path = Path(path)
    try:
        return json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Manifesto de arquitetura invalido: {manifest_path}: {exc.msg}"
        ) from exc


def compare_manifest(
    manifest: dict[str, Any],
    root: Path | str = ROOT,
) -> dict[str, object]:
    """Compara manifesto declarado com a estrutura real do projeto."""
    project_root = Path(root)
    comparisons = {
        "layers": _compare(
            manifest.get("layers", []),
            _discover_layers(project_root),
        ),
        "public_services": _compare(
            manifest.get("public_services", []),
            _discover_public_services(project_root),
        ),
        "domain_contracts": _compare(
            manifest.get("domain_contracts", []),
            _discover_domain_contracts(project_root),
        ),
        "providers": _compare(
            manifest.get("providers", []),
            _discover_market_data_exports(
                project_root,
                ("Provider", "Catalog", "Registry"),
            ),
        ),
        "adapters": _compare(
            manifest.get("adapters", []),
            _discover_market_data_exports(project_root, ("Adapter", "Source")),
        ),
        "events": _compare(
            manifest.get("events", []),
            _discover_events(project_root),
        ),
        "architecture_rules": _compare_rules(
            manifest.get("architecture_rules", []),
            project_root,
        ),
    }
    status = _overall_status(comparisons)
    return {
        "manifest_compliance": {
            "status": status,
            "sections": {
                name: comparison.to_dict()
                for name, comparison in comparisons.items()
            },
        }
    }


def run_audit(
    manifest_path: Path | str = MANIFEST_PATH,
    baseline_path: Path | str = BASELINE_PATH,
    root: Path | str = ROOT,
    write_reports: bool = True,
) -> dict[str, object]:
    """Executa a auditoria e opcionalmente escreve relatorios."""
    manifest = load_manifest(manifest_path)
    report = compare_manifest(manifest, root)
    project_root = Path(root)
    snapshot = build_architecture_snapshot(project_root)
    report["architecture_snapshot"] = snapshot
    report["architecture_baseline_drift"] = compare_baseline(
        load_baseline(baseline_path),
        build_baseline_snapshot(project_root, snapshot),
    )
    if write_reports:
        write_report(report)
    return report


def load_baseline(path: Path | str = BASELINE_PATH) -> dict[str, Any]:
    """Carrega a baseline aprovada com erros claros."""
    baseline_path = Path(path)
    if not baseline_path.exists():
        raise FileNotFoundError(
            f"Baseline arquitetural nao encontrada: {baseline_path}"
        )
    try:
        return json.loads(baseline_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Baseline arquitetural invalida: {baseline_path}: {exc.msg}"
        ) from exc


def build_baseline_snapshot(
    root: Path | str = ROOT,
    snapshot: dict[str, object] | None = None,
) -> dict[str, Any]:
    """Monta o snapshot atual no mesmo formato de architecture_baseline.json."""
    project_root = Path(root)
    current_snapshot = snapshot or build_architecture_snapshot(project_root)
    provider_section = current_snapshot["providers"]
    assert isinstance(provider_section, dict)
    providers = _baseline_providers(provider_section)
    statistics = dict(current_snapshot["statistics"])
    statistics["providers"] = len(providers)
    layers = current_snapshot["layers"]
    services = current_snapshot["public_services"]
    contracts = current_snapshot["domain_contracts"]
    event_bus = current_snapshot["event_bus"]
    assert isinstance(layers, dict)
    assert isinstance(services, dict)
    assert isinstance(contracts, dict)
    assert isinstance(event_bus, dict)
    return {
        "structure": {
            "layers": list(layers["present"]),
            "modules": _baseline_modules(project_root),
            "packages": _baseline_packages(project_root),
        },
        "services": list(services["found"]),
        "contracts": list(contracts["found"]),
        "providers": providers,
        "adapters": list(provider_section["adapters_exported"]),
        "registered_adapters": dict(provider_section["adapters_registered"]),
        "events": list(event_bus["official_events"]),
        "statistics": statistics,
    }


def compare_baseline(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, object]:
    """Compara baseline aprovada com o estado arquitetural atual."""
    sections = {
        "layers": _compare_sequence(
            baseline.get("structure", {}).get("layers", []),
            current.get("structure", {}).get("layers", []),
        ),
        "modules": _compare_sequence(
            baseline.get("structure", {}).get("modules", []),
            current.get("structure", {}).get("modules", []),
        ),
        "services": _compare_sequence(
            baseline.get("services", []),
            current.get("services", []),
        ),
        "contracts": _compare_sequence(
            baseline.get("contracts", []),
            current.get("contracts", []),
        ),
        "providers": _compare_sequence(
            baseline.get("providers", []),
            current.get("providers", []),
        ),
        "adapters": _compare_sequence(
            baseline.get("adapters", []),
            current.get("adapters", []),
        ),
        "events": _compare_sequence(
            baseline.get("events", []),
            current.get("events", []),
        ),
        "python_files": _compare_number(
            baseline.get("statistics", {}).get("python_files"),
            current.get("statistics", {}).get("python_files"),
        ),
        "tests": _compare_number(
            baseline.get("statistics", {}).get("tests"),
            current.get("statistics", {}).get("tests"),
        ),
    }
    status = _baseline_drift_status(sections)
    return {
        "status": status,
        "criticality": "INFORMATIVO" if status == "OK" else "INFORMATIVO",
        "note": (
            "Drift de baseline e informativo nesta auditoria. "
            "Falhas criticas continuam sendo tratadas pelas regras arquiteturais."
        ),
        "sections": sections,
    }


def build_architecture_snapshot(root: Path | str = ROOT) -> dict[str, object]:
    """Inspeciona a arquitetura atual sem importar modulos da aplicacao."""
    project_root = Path(root)
    layers = _audit_layers(project_root)
    services = _audit_public_services(project_root)
    contracts = _audit_domain_contracts(project_root)
    providers = _audit_providers(project_root)
    event_bus = _audit_event_bus(project_root)
    dashboard = _audit_dashboard(project_root)
    replay = _audit_package_forbidden_access(project_root, "replay")
    research = _audit_package_forbidden_access(project_root, "research")
    statistics = _audit_statistics(
        project_root,
        services=services,
        contracts=contracts,
        providers=providers,
    )

    return {
        "layers": layers,
        "public_services": services,
        "domain_contracts": contracts,
        "providers": providers,
        "event_bus": event_bus,
        "dashboard": dashboard,
        "replay": replay,
        "research": research,
        "statistics": statistics,
    }


def write_report(report: dict[str, object]) -> None:
    """Escreve relatorios JSON e Markdown da auditoria."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    JSON_REPORT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    MARKDOWN_REPORT_PATH.write_text(
        _to_markdown(report),
        encoding="utf-8",
    )


def _compare(
    declared_values: Any,
    found_values: set[str],
) -> ManifestSectionComparison:
    declared = sorted(str(value) for value in declared_values)
    found = sorted(found_values)
    declared_set = set(declared)
    found_set = set(found)
    missing = sorted(declared_set - found_set)
    extra = sorted(found_set - declared_set)
    divergences = [
        *[f"Ausente no projeto: {item}" for item in missing],
        *[f"Extra no projeto: {item}" for item in extra],
    ]
    return ManifestSectionComparison(
        declared=declared,
        found=found,
        present=sorted(declared_set & found_set),
        missing=missing,
        extra=extra,
        divergences=divergences,
        status="OK" if not missing and not extra else "DIVERGENT",
    )


def _compare_sequence(
    baseline_values: Any,
    current_values: Any,
) -> dict[str, object]:
    baseline_set = {str(value) for value in baseline_values}
    current_set = {str(value) for value in current_values}
    added = sorted(current_set - baseline_set)
    removed = sorted(baseline_set - current_set)
    return {
        "baseline": sorted(baseline_set),
        "current": sorted(current_set),
        "added": added,
        "removed": removed,
        "changed": bool(added or removed),
        "status": "OK" if not added and not removed else "DRIFT",
    }


def _compare_number(
    baseline_value: Any,
    current_value: Any,
) -> dict[str, object]:
    changed = baseline_value != current_value
    return {
        "baseline": baseline_value,
        "current": current_value,
        "added": [],
        "removed": [],
        "changed": changed,
        "delta": (
            current_value - baseline_value
            if isinstance(current_value, int) and isinstance(baseline_value, int)
            else None
        ),
        "status": "OK" if not changed else "DRIFT",
    }


def _baseline_drift_status(sections: dict[str, dict[str, object]]) -> str:
    if any(section["status"] == "DRIFT" for section in sections.values()):
        return "DRIFT"
    return "OK"


def _compare_rules(
    declared_values: Any,
    root: Path,
) -> ManifestSectionComparison:
    implemented = {
        rule_id
        for rule_id, paths in RULE_CHECKS.items()
        if any((root / path).exists() for path in paths)
    }
    return _compare(declared_values, implemented)


def _overall_status(
    comparisons: dict[str, ManifestSectionComparison],
) -> str:
    if all(comparison.status == "OK" for comparison in comparisons.values()):
        return "OK"
    return "DIVERGENT"


def _discover_layers(root: Path) -> set[str]:
    return {
        path.name
        for path in root.iterdir()
        if path.is_dir() and path.name in ARCHITECTURAL_LAYER_CANDIDATES
    }


def _discover_public_services(root: Path) -> set[str]:
    services: set[str] = set()
    for path in (root / "application").glob("*_service.py"):
        for class_name in _module_defined_classes(path):
            if class_name.endswith("Service"):
                services.add(class_name)
    return services


def _discover_domain_contracts(root: Path) -> set[str]:
    contracts: set[str] = set()
    contracts_root = root / "domain" / "contracts"
    for path in contracts_root.glob("*.py"):
        if path.name == "__init__.py":
            continue
        contracts.update(_module_defined_classes(path))
    return contracts


def _discover_market_data_exports(
    root: Path,
    suffixes: str | tuple[str, ...],
) -> set[str]:
    init_path = root / "market_data" / "__init__.py"
    if not init_path.exists():
        return set()
    tree = ast.parse(init_path.read_text(encoding="utf-8"))
    exports: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, ast.List):
                    for item in node.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(
                            item.value,
                            str,
                        ):
                            if (
                                item.value.endswith(suffixes)
                                and item.value not in MARKET_DATA_ABSTRACTIONS
                            ):
                                exports.add(item.value)
    return exports


def _discover_events(root: Path) -> set[str]:
    events_path = root / "core" / "events.py"
    tree = ast.parse(events_path.read_text(encoding="utf-8"))
    events: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id.isupper() and target.id != "OFFICIAL_EVENTS":
                events.add(target.id)
    return events


def _module_defined_classes(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


def _audit_layers(root: Path) -> dict[str, object]:
    existing = {
        path.name
        for path in root.iterdir()
        if path.is_dir() and path.name in REQUIRED_LAYERS
    }
    missing = sorted(REQUIRED_LAYERS - existing)
    return {
        "required": sorted(REQUIRED_LAYERS),
        "present": sorted(existing),
        "missing": missing,
        "status": "OK" if not missing else "MISSING",
    }


def _audit_public_services(root: Path) -> dict[str, object]:
    found = _discover_public_services(root)
    missing = sorted(EXPECTED_PUBLIC_SERVICES - found)
    return {
        "expected": sorted(EXPECTED_PUBLIC_SERVICES),
        "found": sorted(found),
        "missing": missing,
        "status": "OK" if not missing else "MISSING",
    }


def _audit_domain_contracts(root: Path) -> dict[str, object]:
    found = _discover_domain_contracts(root)
    missing = sorted(EXPECTED_DOMAIN_CONTRACTS - found)
    return {
        "expected": sorted(EXPECTED_DOMAIN_CONTRACTS),
        "found": sorted(found),
        "missing": missing,
        "status": "OK" if not missing else "MISSING",
    }


def _audit_providers(root: Path) -> dict[str, object]:
    provider_exports = _discover_market_data_exports(root, "Provider")
    adapter_exports = _discover_market_data_exports(root, ("Adapter", "Source"))
    registered_adapters = _discover_registered_adapters(root)
    catalog_found = "HistoricalDatasetCatalog" in _discover_market_data_all(root)
    return {
        "providers": sorted(provider_exports),
        "dataset_catalog": "HistoricalDatasetCatalog" if catalog_found else None,
        "adapters_exported": sorted(adapter_exports),
        "adapters_registered": registered_adapters,
        "status": "OK" if catalog_found and registered_adapters else "REVIEW",
    }


def _discover_market_data_all(root: Path) -> set[str]:
    init_path = root / "market_data" / "__init__.py"
    if not init_path.exists():
        return set()
    tree = ast.parse(init_path.read_text(encoding="utf-8"))
    exports: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, ast.List):
                    for item in node.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(
                            item.value,
                            str,
                        ):
                            exports.add(item.value)
    return exports


def _discover_registered_adapters(root: Path) -> dict[str, str]:
    registry_path = root / "market_data" / "historical_data_source_registry.py"
    if not registry_path.exists():
        return {}
    tree = ast.parse(registry_path.read_text(encoding="utf-8"))
    registered: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "register"
            and len(node.args) >= 2
        ):
            continue
        name_node, adapter_node = node.args[0], node.args[1]
        if isinstance(name_node, ast.Constant) and isinstance(name_node.value, str):
            if isinstance(adapter_node, ast.Name):
                registered[name_node.value] = adapter_node.id
    return dict(sorted(registered.items()))


def _audit_event_bus(root: Path) -> dict[str, object]:
    events = _discover_events(root)
    publisher_files: set[str] = set()
    subscriber_files: set[str] = set()
    for path in _project_python_files(root):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and node.func.attr == "publish":
                publisher_files.add(_relative(path, root))
            if isinstance(node.func, ast.Attribute) and node.func.attr == "subscribe":
                subscriber_files.add(_relative(path, root))
    return {
        "official_events_count": len(events),
        "official_events": sorted(events),
        "publishers_found": sorted(publisher_files),
        "subscribers_found": sorted(subscriber_files),
    }


def _audit_dashboard(root: Path) -> dict[str, object]:
    dashboard_path = root / "dashboard_app.py"
    imports = _imports_from_file(dashboard_path)
    forbidden = sorted(
        imported
        for imported in imports
        if imported.split(".", 1)[0] in DASHBOARD_FORBIDDEN_DEPENDENCIES
    )
    uses_dashboard_service = "application.dashboard_service" in imports
    return {
        "file": "dashboard_app.py",
        "uses_dashboard_service": uses_dashboard_service,
        "forbidden_dependencies": forbidden,
        "depends_only_on_dashboard_service": uses_dashboard_service
        and not forbidden,
        "status": "OK" if uses_dashboard_service and not forbidden else "REVIEW",
    }


def _audit_package_forbidden_access(root: Path, package_name: str) -> dict[str, object]:
    package_root = root / package_name
    violations: list[str] = []
    if not package_root.exists():
        return {
            "package": package_name,
            "forbidden_tokens": sorted(OPERATIONAL_FORBIDDEN_TOKENS),
            "violations": [f"Pacote ausente: {package_name}"],
            "status": "MISSING",
        }
    for path in package_root.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = _imports_from_file(path)
        for imported in sorted(imports):
            if imported.split(".", 1)[0].lower() in OPERATIONAL_FORBIDDEN_IMPORT_ROOTS:
                violations.append(f"{_relative(path, root)} importa {imported}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in OPERATIONAL_FORBIDDEN_TOKENS:
                violations.append(f"{_relative(path, root)} referencia {node.id}")
            elif (
                isinstance(node, ast.Attribute)
                and node.attr in OPERATIONAL_FORBIDDEN_TOKENS
            ):
                violations.append(f"{_relative(path, root)} acessa {node.attr}")
    return {
        "package": package_name,
        "forbidden_tokens": sorted(
            OPERATIONAL_FORBIDDEN_TOKENS | OPERATIONAL_FORBIDDEN_IMPORT_ROOTS
        ),
        "violations": violations,
        "status": "OK" if not violations else "REVIEW",
    }


def _audit_statistics(
    root: Path,
    *,
    services: dict[str, object],
    contracts: dict[str, object],
    providers: dict[str, object],
) -> dict[str, int]:
    python_files = _project_python_files(root)
    modules = [
        path
        for path in python_files
        if path.parent.name != "tests" and "tests" not in path.parts
    ]
    adapters = providers.get("adapters_exported", [])
    return {
        "modules": len(modules),
        "services": len(services.get("found", [])),
        "contracts": len(contracts.get("found", [])),
        "adapters": len(adapters) if isinstance(adapters, list) else 0,
        "tests": len(list((root / "tests").glob("test_*.py"))),
        "python_files": len(python_files),
    }


def _baseline_providers(provider_section: dict[str, Any]) -> list[str]:
    providers = set(provider_section["providers"])
    dataset_catalog = provider_section.get("dataset_catalog")
    if dataset_catalog:
        providers.add(str(dataset_catalog))
    if provider_section.get("adapters_registered"):
        providers.add("HistoricalDataSourceRegistry")
    return sorted(providers)


def _baseline_modules(root: Path) -> list[str]:
    modules: list[str] = []
    for path in _baseline_python_files(root):
        if path.name == "__init__.py":
            continue
        modules.append(path.relative_to(root).with_suffix("").as_posix())
    return sorted(modules)


def _baseline_packages(root: Path) -> list[str]:
    packages: set[str] = set()
    for path in _baseline_python_files(root):
        if path.name != "__init__.py":
            continue
        relative_parent = path.parent.relative_to(root)
        if str(relative_parent) == ".":
            continue
        packages.add(relative_parent.as_posix())
    return sorted(packages)


def _baseline_python_files(root: Path) -> list[Path]:
    ignored_parts = {"__pycache__"}
    return sorted(
        path
        for path in root.rglob("*.py")
        if not ignored_parts.intersection(path.relative_to(root).parts)
    )


def _project_python_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for root_name in ARCHITECTURE_SCAN_ROOTS | {"tests"}:
        path = root / root_name
        if path.exists():
            files.extend(path.rglob("*.py"))
    dashboard = root / "dashboard_app.py"
    app = root / "app.py"
    if dashboard.exists():
        files.append(dashboard)
    if app.exists():
        files.append(app)
    return sorted(set(files))


def _imports_from_file(path: Path) -> set[str]:
    if not path.exists():
        return set()
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _to_markdown(report: dict[str, object]) -> str:
    compliance = report["manifest_compliance"]
    assert isinstance(compliance, dict)
    sections = compliance["sections"]
    assert isinstance(sections, dict)
    lines = [
        "# Architecture Audit",
        "",
        "## Manifest Compliance",
        "",
        f"- Status geral: {compliance['status']}",
        "",
    ]
    for name, raw_section in sections.items():
        section = raw_section
        assert isinstance(section, dict)
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Status: {section['status']}",
                f"- Presentes: {', '.join(section['present']) or 'nenhum'}",
                f"- Ausentes: {', '.join(section['missing']) or 'nenhum'}",
                f"- Extras: {', '.join(section['extra']) or 'nenhum'}",
                f"- Divergencias: {'; '.join(section['divergences']) or 'nenhuma'}",
                "",
            ]
        )
    snapshot = report.get("architecture_snapshot")
    if isinstance(snapshot, dict):
        lines.extend(_snapshot_to_markdown(snapshot))
    drift = report.get("architecture_baseline_drift")
    if isinstance(drift, dict):
        lines.extend(_baseline_drift_to_markdown(drift))
    return "\n".join(lines)


def _snapshot_to_markdown(snapshot: dict[str, object]) -> list[str]:
    lines = [
        "## Architecture Snapshot",
        "",
    ]
    layers = snapshot.get("layers")
    if isinstance(layers, dict):
        lines.extend(
            [
                "### Camadas",
                "",
                f"- Status: {layers['status']}",
                f"- Presentes: {', '.join(layers['present']) or 'nenhuma'}",
                f"- Ausentes: {', '.join(layers['missing']) or 'nenhuma'}",
                "",
            ]
        )
    services = snapshot.get("public_services")
    if isinstance(services, dict):
        lines.extend(
            [
                "### Servicos publicos",
                "",
                f"- Status: {services['status']}",
                f"- Encontrados: {', '.join(services['found']) or 'nenhum'}",
                f"- Ausentes esperados: {', '.join(services['missing']) or 'nenhum'}",
                "",
            ]
        )
    contracts = snapshot.get("domain_contracts")
    if isinstance(contracts, dict):
        lines.extend(
            [
                "### Contratos do dominio",
                "",
                f"- Status: {contracts['status']}",
                f"- Encontrados: {', '.join(contracts['found']) or 'nenhum'}",
                f"- Ausentes esperados: {', '.join(contracts['missing']) or 'nenhum'}",
                "",
            ]
        )
    providers = snapshot.get("providers")
    if isinstance(providers, dict):
        registered = providers.get("adapters_registered", {})
        registered_text = ", ".join(
            f"{name}: {adapter}"
            for name, adapter in registered.items()
        )
        lines.extend(
            [
                "### Providers e adapters",
                "",
                f"- Status: {providers['status']}",
                f"- Providers: {', '.join(providers['providers']) or 'nenhum'}",
                f"- DatasetCatalog: {providers['dataset_catalog'] or 'ausente'}",
                f"- Adapters exportados: {', '.join(providers['adapters_exported']) or 'nenhum'}",
                f"- Adapters registrados: {registered_text or 'nenhum'}",
                "",
            ]
        )
    event_bus = snapshot.get("event_bus")
    if isinstance(event_bus, dict):
        lines.extend(
            [
                "### EventBus",
                "",
                f"- Eventos oficiais: {event_bus['official_events_count']}",
                f"- Publishers encontrados: {', '.join(event_bus['publishers_found']) or 'nenhum'}",
                f"- Subscribers encontrados: {', '.join(event_bus['subscribers_found']) or 'nenhum'}",
                "",
            ]
        )
    dashboard = snapshot.get("dashboard")
    if isinstance(dashboard, dict):
        lines.extend(
            [
                "### Dashboard",
                "",
                f"- Status: {dashboard['status']}",
                f"- Usa DashboardService: {dashboard['uses_dashboard_service']}",
                f"- Depende apenas da fachada esperada: {dashboard['depends_only_on_dashboard_service']}",
                f"- Dependencias proibidas: {', '.join(dashboard['forbidden_dependencies']) or 'nenhuma'}",
                "",
            ]
        )
    for section_name, title in (("replay", "Replay"), ("research", "Research")):
        section = snapshot.get(section_name)
        if isinstance(section, dict):
            lines.extend(
                [
                    f"### {title}",
                    "",
                    f"- Status: {section['status']}",
                    f"- Acessos proibidos encontrados: {', '.join(section['violations']) or 'nenhum'}",
                    "",
                ]
            )
    statistics = snapshot.get("statistics")
    if isinstance(statistics, dict):
        lines.extend(
            [
                "### Estatisticas",
                "",
                f"- Modulos: {statistics['modules']}",
                f"- Servicos: {statistics['services']}",
                f"- Contratos: {statistics['contracts']}",
                f"- Adapters: {statistics['adapters']}",
                f"- Testes: {statistics['tests']}",
                f"- Arquivos Python: {statistics['python_files']}",
                "",
            ]
        )
    return lines


def _baseline_drift_to_markdown(drift: dict[str, object]) -> list[str]:
    sections = drift["sections"]
    assert isinstance(sections, dict)
    lines = [
        "## Architecture Baseline Drift",
        "",
        f"- Status geral: {drift['status']}",
        f"- Criticidade: {drift['criticality']}",
        f"- Nota: {drift['note']}",
        "",
    ]
    for name, raw_section in sections.items():
        section = raw_section
        assert isinstance(section, dict)
        lines.extend(
            [
                f"### {name}",
                "",
                f"- Status: {section['status']}",
                f"- Itens adicionados: {', '.join(section['added']) or 'nenhum'}",
                f"- Itens removidos: {', '.join(section['removed']) or 'nenhum'}",
                f"- Itens alterados: {'sim' if section['changed'] else 'nao'}",
            ]
        )
        if "delta" in section:
            lines.append(f"- Delta: {section['delta']}")
        lines.append("")
    return lines


def main() -> int:
    report = run_audit()
    compliance = report["manifest_compliance"]
    assert isinstance(compliance, dict)
    print(f"Architecture audit status: {compliance['status']}")
    print(f"JSON report: {JSON_REPORT_PATH}")
    print(f"Markdown report: {MARKDOWN_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
