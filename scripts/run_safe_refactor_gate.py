"""Executa o gate deterministico para refatoracoes seguras do TraderIA Novo.

O gate nao conecta ao MT5, nao usa ambiente externo e nao executa o Lab pesado.
Ele protege arquitetura, API publica e os contratos operacionais caracterizados.
"""

from __future__ import annotations

import subprocess
import sys


COMPILE_TARGETS = [
    "dashboard_app.py",
    "application/dashboard_service.py",
    "application/mt5_market_data_service.py",
    "domain/operational_model_policy.py",
]

SAFE_TESTS = [
    "tests/test_architecture_manifest.py",
    "tests/test_architecture_baseline.py",
    "tests/test_application_api.py",
    (
        "tests/test_application_services.py::ApplicationServicesTest::"
        "test_dashboard_app_importa_apenas_dashboard_service"
    ),
    "tests/test_operational_model_policy.py",
    "tests/test_lab_forex_mt5_contract.py",
    "tests/test_dashboard_view_model.py",
    "tests/test_mt5_market_data_service.py",
    "tests/test_mt5_demo_robot_service.py",
    "tests/test_mt5_demo_execution_provider.py",
    "tests/test_model23_basket_accumulator.py",
    "tests/test_position_manager_service.py",
    "tests/test_operational_indicator_window.py",
    "tests/test_runtime_lock_service.py",
    "tests/test_weekly_robot_schedule.py",
]


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, check=True)


def main() -> int:
    try:
        run([sys.executable, "-m", "py_compile", *COMPILE_TARGETS])
        run([sys.executable, "-m", "pytest", "-q", *SAFE_TESTS])
    except subprocess.CalledProcessError as exc:
        return int(exc.returncode or 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
