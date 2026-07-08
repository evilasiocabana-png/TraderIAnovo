"""Guarda local para impedir TraderIA legado concorrendo com TraderIA Novo."""

from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import sys


@dataclass(frozen=True)
class LegacyTraderIAProcess:
    """Processo legado identificado em porta monitorada."""

    pid: int
    port: int
    command_line: str


def legacy_guard_enabled() -> bool:
    """Controla a protecao por variavel de ambiente."""
    return os.getenv("TRADERIA_LEGACY_PROCESS_GUARD_ENABLED", "1").strip() == "1"


def legacy_ports_from_env() -> tuple[int, ...]:
    """Retorna portas antigas do TraderIA que devem ficar livres."""
    raw = os.getenv("TRADERIA_LEGACY_PROCESS_GUARD_PORTS", "8530")
    ports: list[int] = []
    for item in raw.split(","):
        try:
            port = int(item.strip())
        except ValueError:
            continue
        if port > 0:
            ports.append(port)
    return tuple(dict.fromkeys(ports))


def cleanup_legacy_traderia_processes() -> list[LegacyTraderIAProcess]:
    """Encerra processos Streamlit do TraderIA_WDO nas portas legadas."""
    if not legacy_guard_enabled():
        return []
    killed: list[LegacyTraderIAProcess] = []
    for process in find_legacy_traderia_processes(legacy_ports_from_env()):
        if _terminate_process(process.pid):
            killed.append(process)
    return killed


def find_legacy_traderia_processes(
    ports: tuple[int, ...],
) -> list[LegacyTraderIAProcess]:
    """Localiza processos legados por porta e command line."""
    if not ports or not sys.platform.startswith("win"):
        return []
    rows = _run_powershell_json(
        _legacy_process_query_script(ports),
    )
    processes: list[LegacyTraderIAProcess] = []
    for row in rows:
        try:
            pid = int(row.get("Pid", 0) or 0)
            port = int(row.get("Port", 0) or 0)
        except (TypeError, ValueError):
            continue
        command_line = str(row.get("CommandLine", "") or "")
        if pid > 0 and port > 0 and _is_legacy_traderia_command(command_line):
            processes.append(
                LegacyTraderIAProcess(
                    pid=pid,
                    port=port,
                    command_line=command_line,
                )
            )
    return processes


def _legacy_process_query_script(ports: tuple[int, ...]) -> str:
    joined_ports = ",".join(str(port) for port in ports)
    return (
        "$ports = @("
        f"{joined_ports}"
        "); "
        "$connections = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue "
        "| Where-Object { $ports -contains $_.LocalPort }; "
        "$rows = foreach ($conn in $connections) { "
        "$proc = Get-CimInstance Win32_Process -Filter "
        "\"ProcessId=$($conn.OwningProcess)\" -ErrorAction SilentlyContinue; "
        "if ($proc) { "
        "[PSCustomObject]@{ Pid=$conn.OwningProcess; Port=$conn.LocalPort; "
        "CommandLine=$proc.CommandLine } "
        "} "
        "}; "
        "$rows | ConvertTo-Json -Compress"
    )


def _run_powershell_json(script: str) -> list[dict[str, object]]:
    import json

    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    output = completed.stdout.strip()
    if not output:
        return []
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        return [parsed]
    if isinstance(parsed, list):
        return [item for item in parsed if isinstance(item, dict)]
    return []


def _is_legacy_traderia_command(command_line: str) -> bool:
    normalized = command_line.lower()
    if "streamlit" not in normalized or "dashboard_app.py" not in normalized:
        return False
    if "traderia_wdo" not in normalized:
        return False
    if "traderiaianovo" in normalized:
        return False
    return True


def _terminate_process(pid: int) -> bool:
    if pid <= 0 or pid == os.getpid():
        return False
    try:
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return True
