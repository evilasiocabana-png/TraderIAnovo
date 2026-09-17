"""Initialize only M29 sequence state from a read-only, identity-checked snapshot."""

import argparse
import os
from pathlib import Path
import sys

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--login", required=True, type=int)
    parser.add_argument("--server", required=True)
    parser.add_argument("--portable", action="store_true")
    args = parser.parse_args()
    os.environ["MT5_PATH"] = args.terminal
    os.environ["MT5_PORTABLE"] = "1" if args.portable else "0"
    from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
    from application.model29_sequence_history import sequence_mode
    provider = MT5DemoExecutionProvider()
    payload = provider._external_mt5_read("m29_sequence", portable=args.portable)
    account = payload.get("account") or {}
    if not payload.get("ok") or account.get("login") != args.login or account.get("server") != args.server:
        raise RuntimeError("Leitura nao confirmou a conta solicitada; estado M29 preservado.")

    class Snapshot:
        def _external_mt5_read(self, *unused, **kwargs):
            return payload

    for symbol in ("XAUUSD", "BTCUSD"):
        mode = sequence_mode(Snapshot(), symbol)
        print(f"{symbol}: {mode}; bootstrap consultado sem enviar ordens")


if __name__ == "__main__":
    main()
