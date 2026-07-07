"""Historico estruturado das execucoes do Quality Gate."""

from __future__ import annotations

import json
import subprocess
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUMMARY_PATH = ROOT / "reports" / "quality_gate_summary.json"
DIAGNOSTICS_PATH = ROOT / "reports" / "test_failure_diagnostics.json"
HISTORY_PATH = ROOT / "reports" / "quality_gate_history.json"
MAX_HISTORY_RECORDS = 50


def load_json(path: Path) -> dict[str, object]:
    """Carrega JSON quando existe, retornando dicionario vazio quando ausente."""

    if not path.exists():
        return {}
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return content if isinstance(content, dict) else {}


def project_version(root: Path = ROOT) -> str | None:
    """Le versao do manifesto quando disponivel."""

    manifest_path = root / "MANIFEST.md"
    if not manifest_path.exists():
        return None
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("| Versao |"):
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) >= 2:
                return parts[1]
    return None


def git_commit(root: Path = ROOT) -> str | None:
    """Retorna hash atual do git quando o repositorio estiver disponivel."""

    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    return commit or None


def build_history_record(
    summary: dict[str, object],
    diagnostics: dict[str, object] | None = None,
    *,
    version: str | None = None,
    commit: str | None = None,
) -> dict[str, object]:
    """Cria registro historico a partir dos relatorios existentes."""

    diagnostics = diagnostics or {}
    steps = summary.get("steps", {})
    if not isinstance(steps, dict):
        steps = {}
    test_summary = diagnostics.get("summary", {})
    if not isinstance(test_summary, dict):
        test_summary = {}
    test_status = _step_status(steps, "test_suite")
    total_tests = int(test_summary.get("total_tests") or 0)
    failures = int(test_summary.get("failures") or 0)
    errors = int(test_summary.get("errors") or 0)
    if test_status == "PASSED":
        total_tests = discovered_test_count()
        failures = 0
        errors = 0
    timestamp = str(
        summary.get("executed_at") or datetime.now().astimezone().isoformat()
    )
    return {
        "timestamp": timestamp,
        "project_version": version,
        "commit": commit,
        "status": summary.get("overall_status", "UNKNOWN"),
        "duration_seconds": summary.get("total_duration_seconds", 0),
        "tests": {
            "status": test_status,
            "duration_seconds": _step_duration(steps, "test_suite"),
            "total": total_tests,
            "failures": failures,
            "errors": errors,
        },
        "architecture": {
            "status": _step_status(steps, "architecture_audit"),
            "duration_seconds": _step_duration(steps, "architecture_audit"),
        },
        "static_analysis": {
            "status": _step_status(steps, "static_analysis"),
            "duration_seconds": _step_duration(steps, "static_analysis"),
        },
        "steps": {
            key: {
                "status": value.get("status"),
                "duration_seconds": value.get("duration_seconds"),
                "exit_code": value.get("exit_code"),
            }
            for key, value in steps.items()
            if isinstance(value, dict)
        },
    }


def append_history_record(
    history: dict[str, object],
    record: dict[str, object],
    *,
    max_records: int = MAX_HISTORY_RECORDS,
) -> dict[str, object]:
    """Adiciona registro preservando ordem cronologica e limite maximo."""

    entries = history.get("history", [])
    if not isinstance(entries, list):
        entries = []
    entries = [entry for entry in entries if isinstance(entry, dict)]
    record_timestamp = record.get("timestamp")
    entries = [
        entry
        for entry in entries
        if entry.get("timestamp") != record_timestamp
    ]
    entries.append(record)
    entries = sorted(entries, key=lambda item: str(item.get("timestamp", "")))
    if max_records > 0:
        entries = entries[-max_records:]
    return {
        "max_records": max_records,
        "updated_at": datetime.now().astimezone().isoformat(),
        "history": entries,
    }


def register_quality_gate_execution(
    *,
    summary_path: Path = SUMMARY_PATH,
    diagnostics_path: Path = DIAGNOSTICS_PATH,
    history_path: Path = HISTORY_PATH,
    max_records: int = MAX_HISTORY_RECORDS,
    version: str | None = None,
    commit: str | None = None,
) -> dict[str, object]:
    """Registra a ultima execucao do Quality Gate no historico."""

    summary = load_json(summary_path)
    diagnostics = load_json(diagnostics_path)
    if _is_older_than_summary(diagnostics, summary):
        diagnostics = {}
    record = build_history_record(
        summary,
        diagnostics,
        version=version if version is not None else project_version(),
        commit=commit if commit is not None else git_commit(),
    )
    history = append_history_record(
        load_json(history_path),
        record,
        max_records=max_records,
    )
    write_history(history, history_path)
    return history


def discovered_test_count(root: Path = ROOT) -> int:
    """Conta testes descobertos sem executa-los."""

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=str(root / "tests"),
        pattern="test*.py",
        top_level_dir=str(root),
    )
    return suite.countTestCases()


def write_history(history: dict[str, object], path: Path = HISTORY_PATH) -> None:
    """Grava historico de forma atomica via arquivo temporario."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(history, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _step_status(steps: dict[str, object], key: str) -> str | None:
    step = steps.get(key)
    if isinstance(step, dict):
        value = step.get("status")
        return str(value) if value is not None else None
    return None


def _step_duration(steps: dict[str, object], key: str) -> float | None:
    step = steps.get(key)
    if isinstance(step, dict):
        value = step.get("duration_seconds")
        if isinstance(value, int | float):
            return float(value)
    return None


def _is_older_than_summary(
    diagnostics: dict[str, object],
    summary: dict[str, object],
) -> bool:
    diagnostics_at = diagnostics.get("generated_at")
    summary_at = summary.get("executed_at")
    if not isinstance(diagnostics_at, str) or not isinstance(summary_at, str):
        return False
    return diagnostics_at < summary_at


def main() -> int:
    """Registra a execucao mais recente a partir dos relatorios atuais."""

    history = register_quality_gate_execution()
    print(f"Quality Gate history: {len(history['history'])} registros", flush=True)
    print(f"JSON report: {HISTORY_PATH}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
