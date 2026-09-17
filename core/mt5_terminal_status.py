"""Read terminal permissions in a separate process, without account switching."""

import json
import os
from pathlib import Path
import subprocess
import sys

from core.mt5_external_process_gate import (
    get_mt5_external_cache, set_mt5_external_cache, mt5_external_process_slot,
)


def read_demo_terminal_status():
    path = str(Path(os.environ.get("LOCALAPPDATA", "")) / "TraderIANovo/MT5-Demo/terminal64.exe")
    key = "demo-terminal-permissions:" + path
    cached = get_mt5_external_cache(key, ttl_seconds=15)
    if cached is not None:
        return cached
    if not Path(path).is_file():
        return {}
    code = '''
import json, sys
from datetime import datetime, timezone
import MetaTrader5 as mt5
from core.mt5_permissions import read_permissions
try:
    ok = mt5.initialize(path=sys.argv[1], portable=True, timeout=4000)
    account = mt5.account_info() if ok else None
    print(json.dumps({"login": getattr(account, "login", None),
        "server": getattr(account, "server", None),
        "permissions": read_permissions(mt5) if ok else {},
        "updated_at": datetime.now(timezone.utc).isoformat()}))
finally:
    mt5.shutdown()
'''
    with mt5_external_process_slot(timeout=0) as acquired:
        if not acquired:
            return get_mt5_external_cache(key, ttl_seconds=90) or {}
        try:
            result = subprocess.run([sys.executable, "-c", code, path],
                cwd=Path(__file__).resolve().parents[1], capture_output=True,
                text=True, timeout=6, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            payload = json.loads(result.stdout) if result.returncode == 0 else {}
        except (OSError, subprocess.TimeoutExpired, ValueError):
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        set_mt5_external_cache(key, payload)
        return payload
