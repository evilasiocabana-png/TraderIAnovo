"""Sonda isolada para evitar travas do MetaTrader5.initialize()."""

from __future__ import annotations

from dataclasses import dataclass
import subprocess
import sys


@dataclass(frozen=True)
class MT5ProcessProbeResult:
    """Resultado da sonda MT5 executada em subprocesso."""

    ok: bool
    message: str


def probe_mt5_initialize(timeout_seconds: float = 5.0) -> MT5ProcessProbeResult:
    """Executa MetaTrader5.initialize() fora do processo principal."""
    code = (
        "import MetaTrader5 as mt5\n"
        "ok = bool(mt5.initialize())\n"
        "print(('OK' if ok else 'FAIL'), mt5.last_error())\n"
        "mt5.shutdown()\n"
    )
    process = subprocess.Popen(
        [sys.executable, "-c", code],
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
            message="Timeout na sonda MT5 initialize().",
        )

    output = (stdout or stderr or "").strip()
    return MT5ProcessProbeResult(
        ok=process.returncode == 0 and output.startswith("OK"),
        message=output or f"Sonda MT5 retornou codigo {process.returncode}.",
    )


def _terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Finaliza a sonda sem deixar subprocesso pendurado."""
    try:
        process.kill()
    except OSError:
        return
