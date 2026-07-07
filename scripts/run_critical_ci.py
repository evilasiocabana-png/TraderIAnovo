"""Run the stable TraderIA validation suite used by GitHub Actions.

This script intentionally avoids live MT5/external-environment tests. It is the
single entry point for the critical Lab -> Forex -> MT5 contract checks.
"""

from __future__ import annotations

import subprocess
import sys


CRITICAL_MODULES = [
    "dashboard_app.py",
    "application/dashboard_service.py",
    "application/dashboard_view_model.py",
    "application/mt5_visual_signal_exporter.py",
    "infrastructure/execution/mt5_demo_execution_provider.py",
    "core/mt5_process_probe.py",
]

CRITICAL_TESTS = [
    "tests.test_application_api",
    "tests.test_dashboard_view_model",
    "tests.test_lab_forex_mt5_contract",
    "tests.test_mt5_demo_execution_provider",
    "tests.test_mt5_research_trade_plan",
    "tests.test_mt5_process_probe",
]


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def main() -> int:
    try:
        run([sys.executable, "-m", "py_compile", *CRITICAL_MODULES])
        run([sys.executable, "-m", "unittest", *CRITICAL_TESTS])
    except subprocess.CalledProcessError as exc:
        return int(exc.returncode or 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
