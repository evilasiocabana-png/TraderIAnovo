"""Independent Real account runtime using the same DashboardService strategies."""

import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))

from core.dual_mt5 import (
    CONTROL, REAL_ROOT, STATUS, REAL_LOGIN, REAL_SERVER,
    read_json, write_json, real_control_allows, real_worker_environment,
)


def synchronize_inputs() -> None:
    # Only strategy inputs are copied. Never copy tickets, P/L or live state.
    names = (
        "mt5_operational_model.json", "mt5_research_snapshot.json",
        "mt5_research_runtime_index.json",
        "research/m23_pattern_filter/report.json",
    )
    for name in names:
        source = PROJECT / ".traderia" / name
        target = REAL_ROOT / ".traderia" / name
        if source.exists() and (not target.exists() or source.stat().st_mtime_ns > target.stat().st_mtime_ns):
            payload = read_json(source)
            if not payload:
                raise RuntimeError(f"Configuracao de estrategia indisponivel: {name}")
            write_json(target, payload)


def apply_models(service) -> None:
    state = read_json(PROJECT / ".traderia" / "mt5_operational_model.json")
    selected = state.get("selections")
    if not isinstance(selected, list) or not selected:
        raise RuntimeError("Selecao de modelos indisponivel; novas entradas bloqueadas.")
    from application.dashboard_service import MT5_OPERATIONAL_MODEL_23, MT5_OPERATIONAL_MODEL_29, MT5_ACTIVE_SOURCE_MODEL_IDS
    direct = tuple(model for model in selected if model in MT5_ACTIVE_SOURCE_MODEL_IDS)
    baskets = tuple(model for model in selected if model in {MT5_OPERATIONAL_MODEL_23, MT5_OPERATIONAL_MODEL_29})
    service.set_mt5_operational_models(direct, basket_models=baskets, direct_models_enabled=bool(direct))


def cycle(service, mt5) -> dict:
    from core.mt5_execution_account import MT5ExecutionAccount
    from core.mt5_permissions import read_permissions, permissions_label
    from core.weekly_robot_schedule import weekly_robot_schedule_decision

    permissions = read_permissions(mt5)
    account = mt5.account_info()
    rejection = MT5ExecutionAccount.from_env().rejection(mt5, account)
    base = {
        "permissions": permissions,
        "login": getattr(account, "login", None),
        "server": getattr(account, "server", None),
        "balance": getattr(account, "balance", None),
    }
    if rejection:
        return {**base, "status": "ACCOUNT_BLOCKED", "message": rejection + " " + permissions_label(permissions)}
    if not real_control_allows(entry=False):
        return {**base, "status": "DISABLED", "message": "Real desabilitada; nenhuma ordem autorizada."}
    configuration_error = ""
    try:
        synchronize_inputs()
        apply_models(service)
    except (OSError, ValueError, RuntimeError) as exc:
        configuration_error = str(exc)
    online = read_json(PROJECT / ".traderia" / "mt5_demo_robot_online_state.json")
    timeframe = str(online.get("timeframe") or "M1")
    schedule_ok = (
        os.getenv("TRADERIA_WEEKLY_ROBOT_SCHEDULE_ENABLED", "1") == "0"
        or weekly_robot_schedule_decision().operating
    )
    if not schedule_ok:
        closed = service.close_all_demo_positions(reason="WEEKLY_FRIDAY_1730_BRT")
        return {**base, "status": "WEEKLY_WINDOW_CLOSED", "message": str(closed.get("message", "Agenda fechada.")), "close_result": closed}
    pair = str(online.get("pair") or "TODOS")
    if not configuration_error and real_control_allows(entry=True) and online.get("online") is True:
        service.arm_demo_robot(pair=pair, timeframe=timeframe)
        result = service.run_online_demo_robot_cycle(pair=pair, timeframe=timeframe)
        return {**base, "status": result.status, "message": result.result_message}
    # Turning Real off stops entries, not protection of its existing positions.
    service._enable_mt5_demo_provider()
    service.load_mt5_forex_signals(timeframe=timeframe)
    service.export_mt5_visual_signals()
    if configuration_error:
        return {**base, "status": "CONFIG_BLOCKED", "message": configuration_error}
    return {**base, "status": "MANAGEMENT_ONLY", "message": "Novas entradas Real desligadas; gestao de posicoes mantida."}


def main() -> None:
    REAL_ROOT.mkdir(parents=True, exist_ok=True)
    os.chdir(REAL_ROOT)
    environment = real_worker_environment()
    os.environ.clear()
    os.environ.update(environment)
    # OS lock is automatically released if the worker dies; duplicate launches
    # never produce a second trading loop for the same account.
    lock = (REAL_ROOT / "worker.lock").open("a+b")
    try:
        if os.name == "nt":
            import msvcrt
            lock.seek(0)
            if not lock.read(1):
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        lock.close()
        return
    import MetaTrader5 as mt5
    from application.dashboard_service import DashboardService
    service = DashboardService()
    while True:
        try:
            if not mt5.initialize(path=os.environ["MT5_PATH"], timeout=5000):
                result = {"status": "OFFLINE", "message": str(mt5.last_error())}
            else:
                result = cycle(service, mt5)
        except Exception as exc:
            result = {"status": "ERROR", "message": str(exc)}
        write_json(STATUS, {**result, "pid": os.getpid(), "updated_at": datetime.now(timezone.utc).isoformat()})
        time.sleep(10)


if __name__ == "__main__":
    main()
