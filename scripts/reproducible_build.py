"""Valida reproducibilidade dos artefatos gerados pelo projeto."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "reproducible_build.json"

COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("app", (sys.executable, "app.py")),
    ("architecture_audit", (sys.executable, "scripts/architecture_audit.py")),
    ("architecture_health", (sys.executable, "scripts/architecture_health.py")),
    ("architecture_metrics", (sys.executable, "scripts/architecture_metrics.py")),
)

ARTIFACTS: tuple[tuple[str, Path, str], ...] = (
    ("app_stdout", Path("__command_output__/app.stdout"), "text"),
    ("architecture_audit_json", ROOT / "reports" / "architecture_audit.json", "json"),
    ("architecture_audit_md", ROOT / "reports" / "architecture_audit.md", "text"),
    ("architecture_health_md", ROOT / "reports" / "architecture_health.md", "text"),
    ("architecture_metrics_json", ROOT / "reports" / "architecture_metrics.json", "json"),
)

IGNORED_KEYS = {
    "generated_at",
    "executed_at",
    "updated_at",
    "timestamp",
    "duration_seconds",
    "total_duration_seconds",
    "last_execution",
}

IGNORED_TEXT_PATTERNS = (
    re.compile(r"C:\\Users\\[^\\\n]+(?:\\[^\n]+)*"),
    re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[-+]\d{2}:\d{2})?"),
)


@dataclass(frozen=True)
class CommandRun:
    """Resultado de comando executado durante uma rodada."""

    name: str
    command: str
    exit_code: int
    duration_seconds: float
    stdout: str
    stderr: str


@dataclass(frozen=True)
class BuildRun:
    """Snapshot de uma rodada reprodutivel."""

    index: int
    commands: list[CommandRun]
    artifacts: dict[str, object]


Runner = Callable[[str, tuple[str, ...]], CommandRun]


def default_runner(name: str, command: tuple[str, ...]) -> CommandRun:
    """Executa comando e captura saida."""

    started_at = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return CommandRun(
        name=name,
        command=" ".join(command),
        exit_code=result.returncode,
        duration_seconds=round(time.perf_counter() - started_at, 3),
        stdout=result.stdout,
        stderr=result.stderr,
    )


def run_build_round(index: int, *, runner: Runner = default_runner) -> BuildRun:
    """Executa uma rodada e coleta artefatos normalizados."""

    commands = [runner(name, command) for name, command in COMMANDS]
    artifacts = collect_artifacts(commands)
    return BuildRun(index=index, commands=commands, artifacts=artifacts)


def collect_artifacts(commands: list[CommandRun]) -> dict[str, object]:
    """Coleta artefatos comparaveis apos uma rodada."""

    command_output = {command.name: command for command in commands}
    artifacts: dict[str, object] = {}
    for name, path, kind in ARTIFACTS:
        if name == "app_stdout":
            artifacts[name] = normalize_text(command_output["app"].stdout)
            continue
        if not path.exists():
            artifacts[name] = {"missing": True}
            continue
        if kind == "json":
            artifacts[name] = normalize_json(
                json.loads(path.read_text(encoding="utf-8"))
            )
        else:
            artifacts[name] = normalize_text(path.read_text(encoding="utf-8"))
    return artifacts


def normalize_json(value: object) -> object:
    """Remove campos explicitamente nao deterministicos de JSON."""

    if isinstance(value, dict):
        return {
            key: normalize_json(item)
            for key, item in sorted(value.items())
            if key not in IGNORED_KEYS
        }
    if isinstance(value, list):
        return [normalize_json(item) for item in value]
    return value


def normalize_text(text: str) -> str:
    """Normaliza texto removendo caminhos absolutos e timestamps."""

    normalized = text.replace("\r\n", "\n")
    for pattern in IGNORED_TEXT_PATTERNS:
        normalized = pattern.sub("<ignored>", normalized)
    lines = []
    for line in normalized.splitlines():
        if any(key in line for key in ("generated_at", "executed_at", "updated_at")):
            continue
        lines.append(line.rstrip())
    return "\n".join(lines).strip()


def compare_artifacts(
    first: dict[str, object],
    second: dict[str, object],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Compara artefatos normalizados."""

    differences: list[dict[str, object]] = []
    ignored: list[dict[str, object]] = [
        {
            "field": key,
            "reason": "Campo volatil ignorado por normalizacao.",
        }
        for key in sorted(IGNORED_KEYS)
    ]
    artifact_names = sorted(set(first) | set(second))
    for name in artifact_names:
        if first.get(name) != second.get(name):
            differences.append(
                {
                    "artifact": name,
                    "message": "Artefato normalizado divergiu entre execucoes.",
                }
            )
    return differences, ignored


def classify(
    *,
    command_failures: list[dict[str, object]],
    differences: list[dict[str, object]],
    ignored_differences: list[dict[str, object]],
) -> str:
    """Classifica reproducibilidade."""

    if command_failures or differences:
        return "NON-REPRODUCIBLE"
    if ignored_differences:
        return "REPRODUCIBLE WITH WARNINGS"
    return "REPRODUCIBLE"


def build_report(first: BuildRun, second: BuildRun) -> dict[str, object]:
    """Gera relatorio final de reproducibilidade."""

    differences, ignored = compare_artifacts(first.artifacts, second.artifacts)
    command_failures = command_failure_report(first.commands + second.commands)
    classification = classify(
        command_failures=command_failures,
        differences=differences,
        ignored_differences=ignored,
    )
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": classification,
        "classification": classification,
        "artifacts_compared": [name for name, _, _ in ARTIFACTS],
        "differences": differences,
        "ignored_differences": ignored,
        "command_failures": command_failures,
        "runs": [run_summary(first), run_summary(second)],
    }


def command_failure_report(commands: list[CommandRun]) -> list[dict[str, object]]:
    """Lista comandos que falharam."""

    return [
        {
            "name": command.name,
            "command": command.command,
            "exit_code": command.exit_code,
            "stderr_tail": command.stderr[-500:],
        }
        for command in commands
        if command.exit_code != 0
    ]


def run_summary(run: BuildRun) -> dict[str, object]:
    """Resumo serializavel de uma rodada."""

    return {
        "index": run.index,
        "commands": [
            {
                "name": command.name,
                "command": command.command,
                "exit_code": command.exit_code,
                "duration_seconds": command.duration_seconds,
            }
            for command in run.commands
        ],
        "artifact_keys": sorted(run.artifacts),
    }


def write_report(report: dict[str, object], path: Path = REPORT_PATH) -> None:
    """Grava relatorio final."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def run_validation(*, runner: Runner = default_runner, report_path: Path = REPORT_PATH) -> dict[str, object]:
    """Executa duas rodadas e grava relatorio de reproducibilidade."""

    first = run_build_round(1, runner=runner)
    second = run_build_round(2, runner=runner)
    report = build_report(first, second)
    write_report(report, report_path)
    return report


def main() -> int:
    """Ponto de entrada da validacao de build reproduzivel."""

    report = run_validation()
    print(f"Reproducible build: {report['classification']}", flush=True)
    print(f"JSON report: {REPORT_PATH}", flush=True)
    return 1 if report["classification"] == "NON-REPRODUCIBLE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
