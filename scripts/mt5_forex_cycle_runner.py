"""Ciclo leve Forex MT5 para manter o JSON visual atualizado."""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from application.dashboard_service import DashboardService


def main() -> None:
    interval = float(os.getenv("TRADERIA_MT5_FOREX_CYCLE_SECONDS", "10"))
    os.environ.setdefault("TRADERIA_MT5_VISUAL_SIGNALS_ENABLED", "1")
    os.environ.setdefault("TRADERIA_MT5_BATCH_ENABLED", "0")
    os.environ.setdefault("TRADERIA_MT5_EXTERNAL_MAX_CANDLES", "500")
    os.environ.setdefault("TRADERIA_MT5_EXTERNAL_TIMEOUT_SECONDS", "30")

    log_path = Path(".traderia") / "mt5_forex_cycle_runner.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    service = DashboardService()

    while True:
        try:
            dashboard = service.load_mt5_forex_signals(timeframe="H1")
            output_path = service._mt5_visual_signals_output_path(None)
            visual_export = service.export_mt5_visual_signals()
            message = (
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} "
                f"status={dashboard.connection_status} "
                f"health={dashboard.connection_health} "
                f"refresh_id={dashboard.refresh_id} "
                f"pairs={len(dashboard.pairs)} "
                f"visual_signals={visual_export.total_signals} "
                f"json={output_path}\n"
            )
        except Exception as exc:  # noqa: BLE001 - runner operacional tolerante
            message = f"{time.strftime('%Y-%m-%d %H:%M:%S')} error={exc}\n"
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(message)
        time.sleep(interval)


if __name__ == "__main__":
    main()
