"""Gera a baseline arquitetural aprovada do TraderIA_WDO."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / "architecture_baseline.json"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import architecture_audit


def build_baseline(root: Path | str = ROOT) -> dict[str, Any]:
    """Monta um snapshot deterministico da arquitetura atual."""

    project_root = Path(root)
    snapshot = architecture_audit.build_architecture_snapshot(project_root)
    packages = _discover_packages(project_root)
    modules = _discover_modules(project_root)
    provider_section = snapshot["providers"]
    providers = _baseline_providers(provider_section)
    statistics = dict(snapshot["statistics"])
    statistics["providers"] = len(providers)

    return {
        "structure": {
            "layers": list(snapshot["layers"]["present"]),
            "modules": modules,
            "packages": packages,
        },
        "services": list(snapshot["public_services"]["found"]),
        "contracts": list(snapshot["domain_contracts"]["found"]),
        "providers": providers,
        "adapters": list(provider_section["adapters_exported"]),
        "registered_adapters": dict(provider_section["adapters_registered"]),
        "events": list(snapshot["event_bus"]["official_events"]),
        "statistics": statistics,
    }


def write_baseline(
    baseline: dict[str, Any] | None = None,
    path: Path | str = BASELINE_PATH,
) -> None:
    """Escreve a baseline em JSON deterministico."""

    baseline_path = Path(path)
    data = baseline if baseline is not None else build_baseline()
    baseline_path.write_text(
        serialize_baseline(data),
        encoding="utf-8",
    )


def serialize_baseline(baseline: dict[str, Any]) -> str:
    """Serializa o snapshot com chaves e listas estaveis."""

    return json.dumps(
        baseline,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def _baseline_providers(provider_section: dict[str, Any]) -> list[str]:
    providers = set(provider_section["providers"])
    dataset_catalog = provider_section.get("dataset_catalog")
    if dataset_catalog:
        providers.add(str(dataset_catalog))
    if provider_section.get("adapters_registered"):
        providers.add("HistoricalDataSourceRegistry")
    return sorted(providers)


def load_baseline(path: Path | str = BASELINE_PATH) -> dict[str, Any]:
    """Carrega a baseline arquitetural existente."""

    baseline_path = Path(path)
    return json.loads(baseline_path.read_text(encoding="utf-8"))


def _discover_modules(root: Path) -> list[str]:
    modules: list[str] = []
    for path in _project_python_files(root):
        if path.name == "__init__.py":
            continue
        modules.append(path.relative_to(root).with_suffix("").as_posix())
    return sorted(modules)


def _discover_packages(root: Path) -> list[str]:
    packages: set[str] = set()
    for path in _project_python_files(root):
        if path.name != "__init__.py":
            continue
        relative_parent = path.parent.relative_to(root)
        if str(relative_parent) == ".":
            continue
        packages.add(relative_parent.as_posix())
    return sorted(packages)


def _project_python_files(root: Path) -> list[Path]:
    ignored_parts = {"__pycache__"}
    return sorted(
        path
        for path in root.rglob("*.py")
        if not ignored_parts.intersection(path.relative_to(root).parts)
    )


def main() -> int:
    write_baseline()
    print(f"Architecture baseline written: {BASELINE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
