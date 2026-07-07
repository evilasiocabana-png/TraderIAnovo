"""Calcula metricas arquiteturais quantitativas do TraderIA_WDO."""

from __future__ import annotations

import ast
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "architecture_metrics.json"

LAYER_ROOTS = {
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

ARCHITECTURAL_TEST_SUITES = {
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
    "test_architecture_health.py",
    "test_quality_gate.py",
}

FORBIDDEN_IMPORTS_BY_LAYER = {
    "domain": {
        "application",
        "dashboard_app",
        "streamlit",
        "database",
        "market_data",
        "pandas",
        "duckdb",
        "broker",
        "mt5",
    },
    "application": {"dashboard_app", "streamlit", "mt5", "broker"},
    "replay": {"dashboard_app", "streamlit", "mt5", "broker", "pandas", "duckdb"},
    "research": {"dashboard_app", "streamlit", "mt5", "broker", "pandas", "duckdb"},
    "strategies": {"dashboard_app", "streamlit", "mt5", "broker"},
}


def build_metrics(root: Path | str = ROOT) -> dict[str, Any]:
    """Calcula todas as metricas por analise estatica."""

    project_root = Path(root)
    files = _python_files(project_root)
    trees = {path: _parse(path) for path in files}
    layer_dependencies = _layer_dependencies(project_root, files)
    forbidden_imports = _forbidden_imports(project_root, files)
    cycles = _dependency_cycles(layer_dependencies)
    violations = [
        f"{layer}:{path}:{imported}"
        for layer, entries in forbidden_imports.items()
        for path, imported in entries
    ]

    return {
        "structure": _structure_metrics(project_root, files, trees),
        "application": _application_metrics(project_root, trees),
        "domain": _domain_metrics(project_root, trees),
        "architecture": {
            "layer_dependencies": {
                layer: sorted(dependencies)
                for layer, dependencies in sorted(layer_dependencies.items())
            },
            "forbidden_imports_found": {
                layer: [
                    {"file": path, "import": imported}
                    for path, imported in entries
                ]
                for layer, entries in sorted(forbidden_imports.items())
            },
            "dependency_cycles": cycles,
            "architectural_violations": violations,
            "architectural_violations_count": len(violations),
        },
        "testing": _testing_metrics(project_root, trees),
        "providers": _provider_metrics(project_root, trees),
        "events": _event_metrics(project_root, trees),
        "generated_at": "",
    }


def write_metrics(
    metrics: dict[str, Any] | None = None,
    path: Path | str = REPORT_PATH,
) -> None:
    """Escreve o relatorio JSON de forma deterministica."""

    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    data = metrics if metrics is not None else build_metrics()
    report_path.write_text(serialize_metrics(data), encoding="utf-8")


def serialize_metrics(metrics: dict[str, Any]) -> str:
    """Serializa metricas com chaves ordenadas e sem campos volateis."""

    return json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _python_files(root: Path) -> list[Path]:
    ignored_parts = {"__pycache__", ".git"}
    return sorted(
        path
        for path in root.rglob("*.py")
        if not ignored_parts.intersection(path.relative_to(root).parts)
    )


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"))


def _structure_metrics(
    root: Path,
    files: list[Path],
    trees: dict[Path, ast.AST],
) -> dict[str, int]:
    packages = {
        path.parent.relative_to(root).as_posix()
        for path in files
        if path.name == "__init__.py"
    }
    modules = [path for path in files if path.name != "__init__.py"]
    return {
        "modules": len(modules),
        "packages": len(packages),
        "python_files": len(files),
        "loc": sum(_loc(path) for path in files),
        "classes": sum(_class_count(tree) for tree in trees.values()),
        "public_functions": sum(_public_function_count(tree) for tree in trees.values()),
    }


def _application_metrics(root: Path, trees: dict[Path, ast.AST]) -> dict[str, Any]:
    service_methods: dict[str, int] = {}
    for path, tree in trees.items():
        if not _is_under(root, path, "application"):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.endswith("Service"):
                service_methods[node.name] = len(_public_methods(node))
    total_services = len(service_methods)
    public_methods = sum(service_methods.values())
    average = public_methods / total_services if total_services else 0.0
    return {
        "services": total_services,
        "public_methods": public_methods,
        "average_methods_per_service": round(average, 2),
        "methods_by_service": dict(sorted(service_methods.items())),
    }


def _domain_metrics(root: Path, trees: dict[Path, ast.AST]) -> dict[str, int]:
    entity_count = 0
    contract_count = 0
    dataclass_count = 0
    enum_count = 0
    for path, tree in trees.items():
        if not _is_under(root, path, "domain"):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if "contracts" in path.relative_to(root).parts:
                contract_count += 1
            else:
                entity_count += 1
            if _is_dataclass(node):
                dataclass_count += 1
            if _inherits_enum(node):
                enum_count += 1
    return {
        "entities": entity_count,
        "contracts": contract_count,
        "dataclasses": dataclass_count,
        "enums": enum_count,
    }


def _testing_metrics(root: Path, trees: dict[Path, ast.AST]) -> dict[str, Any]:
    test_files = sorted((root / "tests").glob("test_*.py"))
    total_tests = 0
    for path in test_files:
        tree = trees.get(path)
        if tree is None:
            continue
        total_tests += sum(
            1
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
        )
    architectural = [path for path in test_files if path.name in ARCHITECTURAL_TEST_SUITES]
    percentage = (len(architectural) / len(test_files) * 100) if test_files else 0.0
    return {
        "total_suites": len(test_files),
        "total_tests": total_tests,
        "architectural_tests": len(architectural),
        "architectural_tests_percentage": round(percentage, 2),
    }


def _provider_metrics(root: Path, trees: dict[Path, ast.AST]) -> dict[str, int]:
    init_path = root / "market_data" / "__init__.py"
    exports = _all_exports(init_path) if init_path.exists() else set()
    providers = {
        item
        for item in exports
        if item.endswith(("Provider", "Catalog", "Registry"))
    }
    adapters = {
        item
        for item in exports
        if item.endswith(("Adapter", "Source"))
        and item not in {"HistoricalDataSource", "HistoricalDataSourceResult"}
    }
    registry_path = root / "market_data" / "historical_data_source_registry.py"
    formats = set()
    if registry_path in trees:
        for node in ast.walk(trees[registry_path]):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "register" and node.args:
                    first = node.args[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        formats.add(first.value)
    return {
        "providers": len(providers),
        "adapters": len(adapters),
        "supported_formats": len(formats),
    }


def _event_metrics(root: Path, trees: dict[Path, ast.AST]) -> dict[str, int]:
    events_path = root / "core" / "events.py"
    events = set()
    if events_path in trees:
        for node in ast.walk(trees[events_path]):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    if target.id != "OFFICIAL_EVENTS":
                        events.add(target.id)
    publishers = set()
    subscribers = set()
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "publish":
                    publishers.add(path.relative_to(root).as_posix())
                if node.func.attr == "subscribe":
                    subscribers.add(path.relative_to(root).as_posix())
    return {
        "official_events": len(events),
        "publishers": len(publishers),
        "subscribers": len(subscribers),
    }


def _layer_dependencies(root: Path, files: list[Path]) -> dict[str, set[str]]:
    dependencies: dict[str, set[str]] = defaultdict(set)
    for path in files:
        layer = _layer_for(root, path)
        if layer is None:
            continue
        for imported in _imports(path):
            imported_layer = imported.split(".", 1)[0]
            if imported_layer in LAYER_ROOTS and imported_layer != layer:
                dependencies[layer].add(imported_layer)
    return dependencies


def _forbidden_imports(root: Path, files: list[Path]) -> dict[str, list[tuple[str, str]]]:
    violations: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for path in files:
        layer = _layer_for(root, path)
        if layer not in FORBIDDEN_IMPORTS_BY_LAYER:
            continue
        forbidden = FORBIDDEN_IMPORTS_BY_LAYER[layer]
        for imported in sorted(_imports(path)):
            root_import = imported.split(".", 1)[0]
            if imported in forbidden or root_import in forbidden:
                violations[layer].append((path.relative_to(root).as_posix(), imported))
    return violations


def _dependency_cycles(dependencies: dict[str, set[str]]) -> list[list[str]]:
    cycles: set[tuple[str, ...]] = set()
    for source, targets in dependencies.items():
        for target in targets:
            if source in dependencies.get(target, set()):
                cycles.add(tuple(sorted((source, target))))
    return [list(cycle) for cycle in sorted(cycles)]


def _imports(path: Path) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(_parse(path)):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def _all_exports(path: Path) -> set[str]:
    exports: set[str] = set()
    for node in ast.walk(_parse(path)):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "__all__":
                if isinstance(node.value, ast.List):
                    for item in node.value.elts:
                        if isinstance(item, ast.Constant) and isinstance(item.value, str):
                            exports.add(item.value)
    return exports


def _loc(path: Path) -> int:
    return sum(
        1
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    )


def _class_count(tree: ast.AST) -> int:
    return sum(1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef))


def _public_function_count(tree: ast.AST) -> int:
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not node.name.startswith("_")
    )


def _public_methods(node: ast.ClassDef) -> list[str]:
    return [
        item.name
        for item in node.body
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
        and not item.name.startswith("_")
    ]


def _is_dataclass(node: ast.ClassDef) -> bool:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Name) and decorator.id == "dataclass":
            return True
        if isinstance(decorator, ast.Attribute) and decorator.attr == "dataclass":
            return True
    return False


def _inherits_enum(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id in {"Enum", "StrEnum", "IntEnum"}:
            return True
        if isinstance(base, ast.Attribute) and base.attr in {"Enum", "StrEnum", "IntEnum"}:
            return True
    return False


def _is_under(root: Path, path: Path, layer: str) -> bool:
    return path.relative_to(root).parts[0] == layer


def _layer_for(root: Path, path: Path) -> str | None:
    relative = path.relative_to(root)
    first = relative.parts[0]
    return first if first in LAYER_ROOTS else None


def main() -> int:
    metrics = build_metrics()
    write_metrics(metrics)
    print(f"Architecture metrics written: {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
