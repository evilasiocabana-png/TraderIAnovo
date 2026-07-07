"""Valida prontidao do projeto para execucao em CI."""

from __future__ import annotations

import importlib.util
import ast
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "reports" / "ci_readiness.json"
MIN_PYTHON_VERSION = (3, 11)
COMMAND_TIMEOUT_SECONDS = 180

EXPECTED_DIRECTORIES = (
    "application",
    "core",
    "domain",
    "market",
    "market_data",
    "replay",
    "research",
    "risk",
    "scripts",
    "tests",
    "reports",
)

COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("app", (sys.executable, "app.py")),
    ("static_analysis", (sys.executable, "scripts/run_static_analysis.py")),
    ("architecture_audit", (sys.executable, "scripts/architecture_audit.py")),
    ("test_suite", (sys.executable, "-m", "unittest", "discover", "-s", "tests")),
)

SOURCE_SCAN_PATHS = (
    "app.py",
    "dashboard_app.py",
    "scripts",
    "application",
    "core",
    "domain",
    "market",
    "market_data",
    "replay",
    "research",
    "risk",
    "tests",
)


@dataclass(frozen=True)
class CheckResult:
    """Resultado de uma checagem de prontidao."""

    name: str
    status: str
    message: str
    severity: str = "info"


@dataclass(frozen=True)
class CommandResult:
    """Resultado de comando executado pelo readiness."""

    name: str
    command: str
    exit_code: int
    duration_seconds: float
    stdout_tail: str = ""
    stderr_tail: str = ""


Runner = Callable[[str, tuple[str, ...]], CommandResult]


def default_runner(name: str, command: tuple[str, ...]) -> CommandResult:
    """Executa comando sem entrada interativa."""

    started_at = time.perf_counter()
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=COMMAND_TIMEOUT_SECONDS,
        input="",
    )
    return CommandResult(
        name=name,
        command=" ".join(command),
        exit_code=result.returncode,
        duration_seconds=round(time.perf_counter() - started_at, 3),
        stdout_tail=_tail(result.stdout),
        stderr_tail=_tail(result.stderr),
    )


def build_report(*, runner: Runner = default_runner) -> dict[str, object]:
    """Executa validacoes de CI e retorna relatorio estruturado."""

    environment_checks = check_environment()
    dependency_checks = check_dependencies()
    structure_checks = check_structure()
    report_write_check = check_reports_write_permission()
    source_checks = scan_sources_for_ci_risks()
    command_results = [runner(name, command) for name, command in COMMANDS]
    command_checks = checks_from_commands(command_results)
    consistency_checks = check_report_consistency()
    checks = (
        environment_checks
        + dependency_checks
        + structure_checks
        + [report_write_check]
        + source_checks
        + command_checks
        + consistency_checks
    )
    problems = [item for item in checks if item.severity == "error"]
    warnings = [item for item in checks if item.severity == "warning"]
    status = classify_status(problems=problems, warnings=warnings)
    return {
        "generated_at": datetime.now().astimezone().isoformat(),
        "status": status,
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": sys.platform,
            "executable": sys.executable,
            "cwd": str(ROOT),
        },
        "checks": [_check_dict(item) for item in checks],
        "commands": [_command_dict(item) for item in command_results],
        "problems": [_check_dict(item) for item in problems],
        "warnings": [_check_dict(item) for item in warnings],
        "recommendations": recommendations(problems, warnings),
    }


def check_environment() -> list[CheckResult]:
    """Verifica versao minima de Python."""

    version_ok = sys.version_info >= MIN_PYTHON_VERSION
    expected = ".".join(str(part) for part in MIN_PYTHON_VERSION)
    return [
        CheckResult(
            name="python_version",
            status="PASSED" if version_ok else "FAILED",
            severity="info" if version_ok else "error",
            message=(
                f"Python {sys.version.split()[0]} atende minimo {expected}."
                if version_ok
                else f"Python minimo requerido: {expected}."
            ),
        )
    ]


def check_dependencies(requirements_path: Path = ROOT / "requirements.txt") -> list[CheckResult]:
    """Confere dependencias declaradas sem instalar nada."""

    checks: list[CheckResult] = []
    if not requirements_path.exists():
        return [
            CheckResult(
                name="requirements",
                status="FAILED",
                severity="error",
                message="requirements.txt ausente.",
            )
        ]
    for dependency in _requirements(requirements_path):
        module_name = dependency.split("==", 1)[0].split(">=", 1)[0].split("[", 1)[0]
        installed = importlib.util.find_spec(module_name.replace("-", "_")) is not None
        checks.append(
            CheckResult(
                name=f"dependency:{dependency}",
                status="PASSED" if installed else "FAILED",
                severity="info" if installed else "error",
                message=(
                    f"Dependencia {dependency} instalada."
                    if installed
                    else f"Dependencia {dependency} nao encontrada."
                ),
            )
        )
    return checks


def check_structure(root: Path = ROOT) -> list[CheckResult]:
    """Valida estrutura basica de diretorios."""

    checks: list[CheckResult] = []
    for directory in EXPECTED_DIRECTORIES:
        path = root / directory
        exists = path.is_dir()
        checks.append(
            CheckResult(
                name=f"directory:{directory}",
                status="PASSED" if exists else "FAILED",
                severity="info" if exists else "error",
                message=(
                    f"Diretorio {directory}/ encontrado."
                    if exists
                    else f"Diretorio {directory}/ ausente."
                ),
            )
        )
    return checks


def check_reports_write_permission(reports_dir: Path = ROOT / "reports") -> CheckResult:
    """Confirma permissao de escrita em reports sem deixar arquivo persistente."""

    probe = reports_dir / ".ci_readiness_write_probe"
    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return CheckResult(
            name="reports_write_permission",
            status="FAILED",
            severity="error",
            message=f"Sem permissao de escrita em reports/: {exc}",
        )
    return CheckResult(
        name="reports_write_permission",
        status="PASSED",
        message="reports/ aceita escrita e limpeza de arquivo temporario.",
    )


def scan_sources_for_ci_risks(root: Path = ROOT) -> list[CheckResult]:
    """Procura sinais de dependencia indevida de ambiente."""

    findings: list[CheckResult] = []
    for path in _source_files(root):
        relative = path.relative_to(root).as_posix()
        if relative == "scripts/ci_readiness.py":
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            findings.append(
                CheckResult(
                    name=f"syntax:{relative}",
                    status="WARNING",
                    severity="warning",
                    message="Arquivo nao pode ser analisado por AST durante readiness.",
                )
            )
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                call_name = _call_name(node)
                if call_name == "input":
                    findings.append(_risk("interactive_input", relative, "Entrada interativa detectada."))
                elif call_name in {"getpass", "getpass.getpass"}:
                    findings.append(_risk("getpass", relative, "Uso de senha interativa detectado."))
                elif call_name and call_name.startswith("requests."):
                    findings.append(_risk("internet_access", relative, "Possivel acesso externo via requests."))
                elif call_name and call_name.startswith("urllib."):
                    findings.append(_risk("internet_access", relative, "Possivel acesso externo via urllib."))
                elif call_name and call_name.startswith("socket."):
                    findings.append(_risk("socket_access", relative, "Possivel acesso de rede via socket."))
            elif isinstance(node, ast.Subscript):
                if _call_name(node.value) == "os.environ":
                    findings.append(
                        _risk(
                            "env_required",
                            relative,
                            "Variavel de ambiente obrigatoria detectada.",
                        )
                    )
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "C:\\Users" in node.value or "C:/Users" in node.value:
                    findings.append(
                        _risk(
                            "absolute_user_path",
                            relative,
                            "Caminho absoluto de usuario detectado.",
                        )
                    )
    return findings


def checks_from_commands(command_results: list[CommandResult]) -> list[CheckResult]:
    """Converte execucoes em checks."""

    checks: list[CheckResult] = []
    for result in command_results:
        ok = result.exit_code == 0
        checks.append(
            CheckResult(
                name=f"command:{result.name}",
                status="PASSED" if ok else "FAILED",
                severity="info" if ok else "error",
                message=(
                    f"Comando {result.name} executou sem interacao."
                    if ok
                    else f"Comando {result.name} falhou com exit code {result.exit_code}."
                ),
            )
        )
    return checks


def check_report_consistency(root: Path = ROOT) -> list[CheckResult]:
    """Valida estrutura minima dos relatorios esperados."""

    expected = {
        "reports/static_analysis_report.json": (("status",),),
        "reports/architecture_audit.json": (("manifest_compliance", "status"),),
        "reports/quality_gate_summary.json": (("overall_status",), ("steps",)),
    }
    checks: list[CheckResult] = []
    for relative, keys in expected.items():
        path = root / relative
        if not path.exists():
            checks.append(
                CheckResult(
                    name=f"report:{relative}",
                    status="WARNING",
                    severity="warning",
                    message=f"Relatorio esperado ainda nao existe: {relative}.",
                )
            )
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            checks.append(
                CheckResult(
                    name=f"report:{relative}",
                    status="FAILED",
                    severity="error",
                    message=f"Relatorio invalido: {relative}.",
                )
            )
            continue
        missing = [key for key in keys if not _has_path(data, key)]
        checks.append(
            CheckResult(
                name=f"report:{relative}",
                status="PASSED" if not missing else "FAILED",
                severity="info" if not missing else "error",
                message=(
                    f"Relatorio {relative} possui estrutura esperada."
                    if not missing
                    else f"Relatorio {relative} sem chaves: {missing}."
                ),
            )
        )
    return checks


def classify_status(
    *,
    problems: list[CheckResult],
    warnings: list[CheckResult],
) -> str:
    """Classifica prontidao para CI."""

    if problems:
        return "NOT READY"
    if warnings:
        return "READY WITH WARNINGS"
    return "READY"


def recommendations(
    problems: list[CheckResult],
    warnings: list[CheckResult],
) -> list[str]:
    """Gera recomendacoes operacionais para CI."""

    items: list[str] = []
    if problems:
        items.append("Corrigir checks com severidade error antes de ativar CI.")
    if warnings:
        items.append(
            "Revisar warnings e documentar excecoes aceitaveis antes de endurecer o pipeline."
        )
    if not problems:
        items.append("Manter comandos de CI sem entrada interativa e com timeouts.")
    return items


def write_report(report: dict[str, object], path: Path = REPORT_PATH) -> None:
    """Grava o relatorio de readiness."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


def run_readiness(*, runner: Runner = default_runner, report_path: Path = REPORT_PATH) -> dict[str, object]:
    """Executa readiness e persiste relatorio."""

    report = build_report(runner=runner)
    write_report(report, report_path)
    return report


def _requirements(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def _source_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in SOURCE_SCAN_PATHS:
        path = root / relative
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(
                item
                for item in path.rglob("*.py")
                if "__pycache__" not in item.parts
            )
    return sorted(set(files))


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _call_name(node.value)
        if parent:
            return f"{parent}.{node.attr}"
        return node.attr
    return None


def _risk(name: str, relative_path: str, message: str) -> CheckResult:
    return CheckResult(
        name=f"{name}:{relative_path}",
        status="WARNING",
        severity="warning",
        message=message,
    )


def _has_path(data: dict[str, object], path: tuple[str, ...]) -> bool:
    current: object = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return True


def _check_dict(check: CheckResult) -> dict[str, str]:
    return {
        "name": check.name,
        "status": check.status,
        "severity": check.severity,
        "message": check.message,
    }


def _command_dict(result: CommandResult) -> dict[str, object]:
    return {
        "name": result.name,
        "command": result.command,
        "exit_code": result.exit_code,
        "duration_seconds": result.duration_seconds,
        "stdout_tail": result.stdout_tail,
        "stderr_tail": result.stderr_tail,
    }


def _tail(text: str, limit: int = 1000) -> str:
    return text[-limit:] if len(text) > limit else text


def main() -> int:
    """Executa validacao de prontidao para CI."""

    report = run_readiness()
    print(f"CI readiness: {report['status']}", flush=True)
    print(f"JSON report: {REPORT_PATH}", flush=True)
    return 1 if report["status"] == "NOT READY" else 0


if __name__ == "__main__":
    raise SystemExit(main())
