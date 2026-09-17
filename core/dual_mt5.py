"""Separate Real runtime control. This module never connects to MetaTrader."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PROJECT = Path(__file__).resolve().parents[1]
CONTROL = PROJECT / ".traderia" / "additional_real.json"
REAL_ROOT = PROJECT / ".traderia" / "accounts" / "real-51517136"
STATUS = REAL_ROOT / "status.json"
REAL_LOGIN = "51517136"
REAL_SERVER = "PepperstoneBS-MT5-Live01"
REAL_TERMINAL = Path("C:/Program Files/MetaTrader 5/terminal64.exe")


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=True)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def set_real_enabled(enabled: bool, path: Path = CONTROL) -> None:
    previous = read_json(path)
    write_json(path, {
        "enabled": bool(enabled),
        "authorized": bool(enabled or previous.get("authorized") is True),
        "login": REAL_LOGIN, "server": REAL_SERVER,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    })


def real_control_allows(*, entry: bool, path: Path = CONTROL) -> bool:
    state = read_json(path)
    return bool(
        state.get("authorized") is True
        and state.get("login") == REAL_LOGIN and state.get("server") == REAL_SERVER
        and (not entry or state.get("enabled") is True)
    )


def real_worker_environment() -> dict[str, str]:
    env = dict(os.environ)
    # No credentials or primary-terminal overrides may leak to the child.
    for key in ("MT5_LOGIN", "MT5_PASSWORD", "MT5_SERVER", "TRADERIA_EXECUTION_ACCOUNT_REVISION"):
        env.pop(key, None)
    env.update({
        "TRADERIA_EXECUTION_ACCOUNT_MODE": "REAL",
        "TRADERIA_REAL_EXECUTION_ENABLED": "1",
        "TRADERIA_REAL_ACCOUNT_LOGIN": REAL_LOGIN,
        "TRADERIA_REAL_ACCOUNT_SERVER": REAL_SERVER,
        "TRADERIA_ADDITIONAL_REAL_CONTROL": str(CONTROL),
        "TRADERIA_ACCOUNT_RUNTIME_ROOT": str(REAL_ROOT),
        "MT5_PATH": str(REAL_TERMINAL),
        "MT5_PORTABLE": "0",
        "TRADERIA_MT5_VISUAL_SIGNALS_ENABLED": "1",
        "TRADERIA_MT5_VISUAL_SIGNALS_PATH": str(REAL_ROOT / ".traderia" / "traderia_signals.json"),
        "TRADERIA_MT5_INPROCESS_ENABLED": "1",
        "TRADERIA_MT5_MARKET_DATA_EXTERNAL_PROCESS_ENABLED": "0",
        "TRADERIA_MT5_REPORT_EXTERNAL_PROCESS_ENABLED": "0",
        "TRADERIA_MT5_EXECUTION_READ_EXTERNAL_PROCESS_ENABLED": "0",
    })
    return env


def ensure_real_worker() -> None:
    state = read_json(STATUS)
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(state["updated_at"])).total_seconds()
        if 0 <= age < 30:
            return
    except (KeyError, TypeError, ValueError):
        pass
    REAL_ROOT.mkdir(parents=True, exist_ok=True)
    with (REAL_ROOT / "worker.log").open("a", encoding="utf-8") as log:
        subprocess.Popen(
            [sys.executable, str(PROJECT / "scripts" / "run_additional_real.py")],
            cwd=REAL_ROOT, env=real_worker_environment(), stdin=subprocess.DEVNULL,
            stdout=log, stderr=log,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
