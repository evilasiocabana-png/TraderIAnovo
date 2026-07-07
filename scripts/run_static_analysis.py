"""Analise estatica local e somente leitura do TraderIA_WDO."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "static_analysis_report.json"


def run_static_analysis(root: Path | str = ROOT) -> dict[str, Any]:
    """Executa verificacoes estaticas sem alterar arquivos do projeto."""

    project_root = Path(root)
    files = _python_files(project_root)
    compile_result = _run_in_memory_compile(files, project_root)
    pyflakes_result = _run_optional_pyflakes(files, project_root)
    errors = compile_result["errors"] + pyflakes_result["errors"]
    warnings = compile_result["warnings"] + pyflakes_result["warnings"]
    status = "FAILED" if compile_result["errors"] else "OK"
    if status == "OK" and warnings:
        status = "OK_WITH_WARNINGS"

    return {
        "tool": "compile() + optional pyflakes",
        "tools": [
            compile_result,
            pyflakes_result,
        ],
        "files_analyzed": [path.relative_to(project_root).as_posix() for path in files],
        "problems": errors + warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "status": status,
        "generated_at": "",
    }


def write_report(
    report: dict[str, Any] | None = None,
    path: Path | str = REPORT_PATH,
) -> None:
    """Escreve o relatorio JSON de analise estatica."""

    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    data = report if report is not None else run_static_analysis()
    report_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _python_files(root: Path) -> list[Path]:
    ignored_parts = {"__pycache__", ".git"}
    return sorted(
        path
        for path in root.rglob("*.py")
        if not ignored_parts.intersection(path.relative_to(root).parts)
    )


def _run_in_memory_compile(files: list[Path], root: Path) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            compile(source, str(path), "exec")
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            errors.append(
                {
                    "tool": "compile",
                    "file": path.relative_to(root).as_posix(),
                    "message": str(exc),
                    "severity": "error",
                }
            )
    return {
        "name": "compile",
        "required": True,
        "available": True,
        "files_analyzed": len(files),
        "errors": errors,
        "warnings": [],
        "status": "FAILED" if errors else "OK",
    }


def _run_optional_pyflakes(files: list[Path], root: Path) -> dict[str, Any]:
    availability = subprocess.run(
        [sys.executable, "-m", "pyflakes", "--version"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if availability.returncode != 0:
        return {
            "name": "pyflakes",
            "required": False,
            "available": False,
            "files_analyzed": 0,
            "errors": [],
            "warnings": [
                {
                    "tool": "pyflakes",
                    "file": "",
                    "message": (
                        "pyflakes nao esta instalado; verificacoes opcionais de "
                        "imports nao utilizados, variaveis nao utilizadas e "
                        "codigo inalcançavel nao foram executadas."
                    ),
                    "severity": "warning",
                }
            ],
            "status": "SKIPPED",
        }

    warnings: list[dict[str, str]] = []
    for path in files:
        result = subprocess.run(
            [sys.executable, "-m", "pyflakes", str(path)],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            continue
        output = "\n".join(
            line
            for line in (result.stdout + "\n" + result.stderr).splitlines()
            if line.strip()
        )
        warnings.append(
            {
                "tool": "pyflakes",
                "file": path.relative_to(root).as_posix(),
                "message": output,
                "severity": "warning",
            }
        )

    return {
        "name": "pyflakes",
        "required": False,
        "available": True,
        "files_analyzed": len(files),
        "errors": [],
        "warnings": warnings,
        "status": "OK" if not warnings else "WARNINGS",
    }


def main() -> int:
    report = run_static_analysis()
    write_report(report)
    print(f"Static analysis status: {report['status']}")
    print(f"JSON report: {REPORT_PATH}")
    if report["warning_count"]:
        print(f"Warnings: {report['warning_count']}")
    if report["error_count"]:
        print(f"Errors: {report['error_count']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
