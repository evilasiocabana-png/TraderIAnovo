"""Sonda isolada para evitar travas do MetaTrader5.initialize()."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys


DEFAULT_MT5_TERMINAL_PATHS = (
    Path(r"C:\Program Files\MetaTrader 5\terminal64.exe"),
    Path(r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe"),
)


@dataclass(frozen=True)
class MT5ProcessProbeResult:
    """Resultado da sonda MT5 executada em subprocesso."""

    ok: bool
    message: str


def resolve_mt5_terminal_path(explicit_path: str | None = None) -> str | None:
    """Resolve o terminal conhecido sem acionar a descoberta lenta do MT5."""
    candidates = [
        Path(value)
        for value in (
            explicit_path,
            os.getenv("MT5_PATH"),
        )
        if str(value or "").strip()
    ]
    candidates.extend(DEFAULT_MT5_TERMINAL_PATHS)
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return None


def probe_mt5_initialize(
    timeout_seconds: float = 5.0,
    terminal_path: str | None = None,
) -> MT5ProcessProbeResult:
    """Executa MetaTrader5.initialize() fora do processo principal."""
    code = (
        "import sys\n"
        "import MetaTrader5 as mt5\n"
        "path = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else None\n"
        "ok = bool(mt5.initialize(path=path) if path else mt5.initialize())\n"
        "print(('OK' if ok else 'FAIL'), mt5.last_error())\n"
        "mt5.shutdown()\n"
    )
    resolved_path = resolve_mt5_terminal_path(terminal_path)
    process = subprocess.Popen(
        [sys.executable, "-c", code, resolved_path or ""],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        _terminate_process_tree(process)
        try:
            process.communicate(timeout=1.0)
        except (subprocess.TimeoutExpired, OSError):
            pass
        return MT5ProcessProbeResult(
            ok=False,
            message=(
                "Timeout na sonda MT5 initialize(); "
                "o terminal pode estar aquecendo ou ocupado."
            ),
        )

    output = (stdout or stderr or "").strip()
    return MT5ProcessProbeResult(
        ok=process.returncode == 0 and output.startswith("OK"),
        message=output or f"Sonda MT5 retornou codigo {process.returncode}.",
    )


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Finaliza a sonda MT5 e confirma que nenhum filho ficou pendurado."""
    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            pass
    try:
        process.kill()
    except OSError:
        pass
    try:
        process.wait(timeout=1.0)
    except (OSError, subprocess.TimeoutExpired):
        pass


_terminate_process_tree = terminate_process_tree
