"""Dashboard Streamlit do TraderIA Novo."""

import csv
from dataclasses import replace
from datetime import date, datetime, timezone
import io
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
import unicodedata
from types import SimpleNamespace

import streamlit as st
import streamlit.components.v1 as components

from application.dashboard_service import DashboardService
from application.dashboard_view_model import (
    DASHBOARD_VIEW_MODEL_CONTRACT_VERSION,
    DashboardMT5ForexSignalRowViewModel,
    DashboardMT5ForexSignalViewModel,
)
from application.market_regime_pipeline import MarketRegimePipeline
from application.price_action_simple_model import (
    PriceActionInput,
    PriceActionSimpleModel,
)
from application.runtime_guard_service import RuntimeGuardService
from core.legacy_traderia_process_guard import cleanup_legacy_traderia_processes
from core.runtime_lock_service import RuntimeLockService


REPLAY_PENDING_ACTION_KEY = "replay_pending_action"
REPLAY_PENDING_DATASET_KEY = "replay_pending_dataset_id"
REPLAY_PENDING_MESSAGE_KEY = "replay_pending_message"
MT5_DEMO_ROBOT_ONLINE_KEY = "mt5_demo_robot_online_enabled"
MT5_DEMO_ROBOT_LAST_CYCLE_KEY = "mt5_demo_robot_last_cycle_at"
MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY = "mt5_demo_robot_last_cycle_monotonic"
MT5_DEMO_ROBOT_MESSAGE_KEY = "mt5_demo_robot_runtime_message"
MT5_DEMO_ROBOT_LAST_VISIBLE_SNAPSHOT_KEY = "mt5_demo_robot_last_visible_snapshot"
UI_LAST_CRITICAL_INTERACTION_KEY = "ui_last_critical_interaction_at"
MT5_FOREX_INITIAL_LOAD_ERROR_KEY = "mt5_forex_initial_load_error"
MT5_FOREX_LAST_AUTO_LOAD_KEY = "mt5_forex_last_auto_load_at"
MT5_FOREX_AUTO_CYCLE_UI_KEY = "mt5_forex_auto_cycle_enabled_ui"
MT5_REPORT_LAST_AUTO_LOAD_KEY = "mt5_report_last_auto_load_at"
MT5_REPORT_AUDIT_CACHE_KEY = "mt5_trade_audit_report_cache"
MT5_FOREX_MANUAL_DIAGNOSTIC_KEY = "mt5_forex_manual_diagnostic"
MT5_FOREX_MANUAL_DIAGNOSTIC_MESSAGE_KEY = "mt5_forex_manual_diagnostic_message"
MT5_FOREX_LAST_VALID_SNAPSHOT_KEY = "mt5_forex_last_valid_snapshot"
MT5_LAB_LAST_VALID_SUGGESTIONS_KEY = "mt5_lab_last_valid_suggestions"
FOREX_SESSION_FILTER_UI_KEY = "forex_session_filter_enabled_ui"
RUNTIME_RENDER_DURATIONS_KEY = "runtime_render_durations_ms"
RUNTIME_CLEANUP_MESSAGE_KEY = "runtime_cleanup_message"
RUNTIME_EVENT_LOG_KEY = "runtime_event_log"
RUNTIME_GUARD_SERVICE_KEY = "runtime_guard_service"
LEGACY_PROCESS_GUARD_RAN_KEY = "legacy_traderia_process_guard_ran"
LEGACY_PROCESS_GUARD_MESSAGE_KEY = "legacy_traderia_process_guard_message"
MT5_DEMO_ROBOT_INTERVAL_SECONDS = float(
    os.getenv("TRADERIA_MT5_FOREX_AUTO_REFRESH_SECONDS", "10")
)
MT5_FOREX_AUTO_REFRESH_SECONDS = float(
    os.getenv("TRADERIA_MT5_FOREX_AUTO_REFRESH_SECONDS", "10")
)
MT5_REPORT_AUTO_REFRESH_SECONDS = float(
    os.getenv("TRADERIA_MT5_REPORT_REFRESH_SECONDS", "30")
)
MT5_FOREX_FRAGMENT_RUN_EVERY = f"{int(MT5_FOREX_AUTO_REFRESH_SECONDS)}s"
MT5_REPORT_FRAGMENT_RUN_EVERY = f"{int(MT5_REPORT_AUTO_REFRESH_SECONDS)}s"
MT5_LAB_TARGET_CONFIDENCE = 0.70
MT5_ENTRY_FILTER_ADX_LOW_THRESHOLD = 20.0
MT5_ENTRY_FILTER_MIN_EDGE = 0.02
MT5_ENTRY_FILTER_MIN_SAMPLE_SIZE = 300
MT5_ENTRY_FILTER_MODE_KEY = "mt5_entry_filter_mode"
MT5_ENTRY_FILTER_RULES_CACHE_KEY = "mt5_entry_filter_rules_cache"
MT5_OPERATIONAL_MODEL_KEY = "mt5_operational_model"
MT5_LAB_RR3_EXPERIMENTAL_SNAPSHOT_KEY = "mt5_lab_rr3_experimental_snapshot"
MT5_LAB_RR3_EXPERIMENTAL_SNAPSHOT_PATH = (
    Path(".traderia") / "research" / "mt5_research_snapshot_rr3_experimental.json"
)
MT5_RR3_MIN_SAMPLE_SIZE = 150
MT5_RR3_MIN_PROFIT_FACTOR = 1.20
MT5_RR3_MIN_CONFIDENCE = 0.50
MT5_RR3_MIN_SCORE = 0.60
MT5_OPERATIONAL_MODEL_1 = "MODELO_1_ALPHA_ATUAL"
MT5_OPERATIONAL_MODEL_2 = "MODELO_2_ESPELHO_BETA2_RR1"
MT5_OPERATIONAL_MODEL_3 = "MODELO_3_RR3"
MT5_OPERATIONAL_MODEL_4 = "MODELO_4_ESPELHO_M1"
MT5_OPERATIONAL_MODEL_5 = "MODELO_5_PRICE_ACTION"
MT5_OPERATIONAL_MODEL_6 = "MODELO_6_ESPELHO_M5"
MT5_OPERATIONAL_MODEL_ALL = "TODOS_MODELOS"
MT5_OPERATIONAL_MODEL_5_ENTRY_TIMEFRAME = "M5"
MT5_OPERATIONAL_MODEL_STATE_PATH = Path(".traderia") / "mt5_operational_model.json"
MT5_DEMO_ROBOT_ONLINE_STATE_PATH = (
    Path(".traderia") / "mt5_demo_robot_online_state.json"
)
MT5_DEMO_EXECUTION_LOG_PATH = Path(".traderia") / "mt5_demo_execution.jsonl"
MT5_ENTRY_FILTER_SUPPORTED_INDICATORS = {
    "ADX baixo",
    "ATR em queda",
    "ATR subindo",
    "Momentum contra",
    "MACD hist divergente",
}
MT5_LAB_ALPHA_IDS = tuple(f"ALPHA{index:03d}" for index in range(1, 17))
MT5_LAB_CALCULATION_SNAPSHOT_KEY = "mt5_lab_calculation_snapshot"
MT5_ALPHA_LIBRARY_SEARCH_SPACE_SIZE = 839
MT5_FOREX_CYCLE_LOCK = threading.Lock()
MT5_FOREX_BACKGROUND_THREAD_STARTED = False
MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED = False
MT5_RUNTIME_LOCK = RuntimeLockService()
MT5_ENTRY_REGIME_PIPELINE = MarketRegimePipeline()


def get_dashboard_service() -> DashboardService:
    """Retorna a instancia persistente da fachada do dashboard."""
    _cleanup_legacy_traderia_processes_once()
    _start_mt5_forex_background_cycle_once()
    _start_demo_robot_background_cycle_once()
    service = st.session_state.get("dashboard_service")
    if service is None or not _dashboard_service_valido(service):
        _clear_streamlit_resource_cache_if_available()
        st.session_state["dashboard_service"] = DashboardService()
    return st.session_state["dashboard_service"]


def _cleanup_legacy_traderia_processes_once() -> None:
    """Fecha TraderIA_WDO legado para evitar sobrecarga concorrente."""
    if bool(st.session_state.get(LEGACY_PROCESS_GUARD_RAN_KEY, False)):
        return
    st.session_state[LEGACY_PROCESS_GUARD_RAN_KEY] = True
    killed = cleanup_legacy_traderia_processes()
    if killed:
        ports = ", ".join(str(process.port) for process in killed)
        pids = ", ".join(str(process.pid) for process in killed)
        st.session_state[LEGACY_PROCESS_GUARD_MESSAGE_KEY] = (
            f"TraderIA legado encerrado automaticamente nas portas {ports} "
            f"(PID {pids})."
        )


def get_runtime_guard_service() -> RuntimeGuardService:
    """Retorna a fachada Runtime Guard persistente na sessao."""
    guard = st.session_state.get(RUNTIME_GUARD_SERVICE_KEY)
    if not isinstance(guard, RuntimeGuardService):
        guard = RuntimeGuardService()
        st.session_state[RUNTIME_GUARD_SERVICE_KEY] = guard
        guard.event_log.record("RUNTIME_STARTED")
    return guard


def _start_mt5_forex_background_cycle_once(force: bool = False) -> None:
    global MT5_FOREX_BACKGROUND_THREAD_STARTED
    if MT5_FOREX_BACKGROUND_THREAD_STARTED:
        return
    env_enabled = _mt5_forex_background_cycle_env_enabled()
    if not (force or env_enabled):
        return
    if not _mt5_forex_market_cycle_allowed_now():
        return
    MT5_FOREX_BACKGROUND_THREAD_STARTED = True
    thread = threading.Thread(
        target=_mt5_forex_background_cycle,
        name="TraderIA-MT5-Forex-Cycle",
        daemon=True,
    )
    thread.start()


def _mt5_forex_background_cycle() -> None:
    service = DashboardService()
    while True:
        if _mt5_forex_market_cycle_allowed_now():
            try:
                _load_mt5_forex_signals_locked(service, "H1")
            except Exception:
                pass
        time.sleep(MT5_FOREX_AUTO_REFRESH_SECONDS)


def _mt5_forex_background_cycle_env_enabled() -> bool:
    return (
        os.getenv("TRADERIA_BACKGROUND_CYCLE_ENABLED", "0").strip() == "1"
        or os.getenv("TRADERIA_MT5_BACKGROUND_CYCLE_ENABLED", "0").strip() == "1"
    )


def _start_demo_robot_background_cycle_once(force: bool = False) -> None:
    """Mantem o robo demo vivo mesmo quando a aba Streamlit deixa de renderizar."""
    global MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED
    if MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED:
        return
    if not (force or _demo_robot_background_cycle_should_start()):
        return
    MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED = True
    thread = threading.Thread(
        target=_demo_robot_background_cycle,
        name="TraderIA-MT5-Demo-Robot-Cycle",
        daemon=True,
    )
    thread.start()


def _demo_robot_background_cycle_should_start() -> bool:
    if os.getenv("TRADERIA_DEMO_EXECUTION_ENABLED", "0").strip() != "1":
        return False
    if os.getenv("TRADERIA_DEMO_ROBOT_BACKGROUND_CYCLE_ENABLED", "1").strip() != "1":
        return False
    return bool(_load_demo_robot_online_state().get("online", False))


def _demo_robot_background_cycle_active() -> bool:
    """Indica se a entrada automatica ja esta sob responsabilidade do thread."""
    return (
        MT5_DEMO_ROBOT_BACKGROUND_THREAD_STARTED
        and _demo_robot_background_cycle_should_start()
    )


def _demo_robot_background_cycle() -> None:
    service = DashboardService()
    while True:
        state = _load_demo_robot_online_state()
        online = bool(state.get("online", False))
        if online and _mt5_forex_market_cycle_allowed_now():
            pair = str(state.get("pair") or "TODOS")
            timeframe = str(state.get("timeframe") or "M1")
            try:
                _apply_persisted_operational_model_to_service(service)
                service.arm_demo_robot(pair=pair, timeframe=timeframe)
                robot = service.run_online_demo_robot_cycle(
                    pair=pair,
                    timeframe=timeframe,
                )
                _write_demo_robot_background_state(
                    online=True,
                    pair=pair,
                    timeframe=timeframe,
                    status=str(getattr(robot, "status", "N/D")),
                    result_status=str(getattr(robot, "result_status", "N/D")),
                    message=str(getattr(robot, "result_message", "")),
                )
            except Exception as exc:  # noqa: BLE001 - ciclo externo nao deve derrubar app
                _write_demo_robot_background_state(
                    online=True,
                    pair=pair,
                    timeframe=timeframe,
                    status="ERROR",
                    result_status="ERROR",
                    message=str(exc),
                )
        time.sleep(MT5_DEMO_ROBOT_INTERVAL_SECONDS)


def _apply_persisted_operational_model_to_service(service: DashboardService) -> None:
    try:
        payload = json.loads(MT5_OPERATIONAL_MODEL_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    model = str(payload.get("model") or "").strip().upper()
    if not model:
        return
    setter = getattr(service, "set_mt5_operational_model", None)
    if callable(setter):
        setter(model)


def _write_demo_robot_background_state(
    *,
    online: bool,
    pair: str,
    timeframe: str,
    status: str,
    result_status: str,
    message: str,
) -> None:
    path = Path(".traderia") / "mt5_demo_robot_background_state.json"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "online": bool(online),
                    "pair": str(pair or "TODOS"),
                    "timeframe": str(timeframe or "M1"),
                    "status": status,
                    "result_status": result_status,
                    "message": message,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


def _forex_session_filter_ui_value() -> bool:
    if FOREX_SESSION_FILTER_UI_KEY not in st.session_state:
        st.session_state[FOREX_SESSION_FILTER_UI_KEY] = False
    return bool(st.session_state[FOREX_SESSION_FILTER_UI_KEY])


def _render_forex_session_filter_checkbox(container: object, key: str) -> bool:
    value = container.checkbox(
        "Operar somente durante as sessoes oficiais do Forex",
        value=_forex_session_filter_ui_value(),
        key=key,
    )
    st.session_state[FOREX_SESSION_FILTER_UI_KEY] = bool(value)
    return bool(value)


def _apply_forex_session_filter_preference(
    service: DashboardService,
    enabled: bool,
) -> None:
    service.update_configuration(forex_session_filter_enabled=bool(enabled))


def _load_mt5_forex_signals_locked(
    service: DashboardService,
    timeframe: str,
) -> object:
    with MT5_FOREX_CYCLE_LOCK:
        runtime_lock = MT5_RUNTIME_LOCK.acquire_active()
        if not runtime_lock.acquired:
            return service.get_light_dashboard_view_model()
        return service.load_mt5_forex_signals(timeframe=timeframe)


def _load_mt5_trade_audit_report_locked(service: DashboardService) -> object | None:
    with MT5_FOREX_CYCLE_LOCK:
        runtime_lock = MT5_RUNTIME_LOCK.acquire_active()
        if not runtime_lock.acquired:
            return None
        return service.get_mt5_trade_audit_report()


def _record_runtime_event(event: str) -> None:
    guard = get_runtime_guard_service()
    guard.event_log.record(event)
    st.session_state[RUNTIME_EVENT_LOG_KEY] = guard.event_log.as_strings()


def _dashboard_service_valido(service: object) -> bool:
    """Mantem compatibilidade sem descartar estado em reruns."""
    if not isinstance(service, DashboardService):
        return False
    required_methods = (
        "analyze_selected_historical_dataset_quality",
        "arm_demo_robot",
        "clear_research_experiments",
        "compare_research_benchmarks",
        "delete_configuration_preset",
        "disarm_demo_robot",
        "disable_replay_auto_run",
        "enable_replay_auto_run",
        "evaluate_armed_demo_robot_once",
        "export_alpha001_results_to_csv",
        "filter_alpha001_parameter_ranking",
        "get_active_replay_strategy_name",
        "get_dashboard_contract_version",
        "get_dashboard_data",
        "get_dashboard_view_model",
        "get_light_dashboard_view_model",
        "get_demo_robot_status",
        "get_data_readiness_gate_metrics",
        "get_historical_dataset_health_summary",
        "get_historical_provider_metrics",
        "get_mt5_forex_signals",
        "get_mt5_market_data",
        "get_mt5_alpha_research_ranking",
        "get_mt5_alpha_research_report",
        "get_mt5_research_constants",
        "get_research_layer_definitions",
        "get_selected_historical_dataset",
        "get_selected_historical_dataset_readiness",
        "list_configuration_presets",
        "list_data_readiness_gate_logs",
        "list_historical_dataset_quality_validations",
        "list_historical_datasets",
        "list_available_replay_strategies",
        "load_configuration_preset",
        "load_demo_replay_candles",
        "load_mt5_forex_signals",
        "load_mt5_market_data",
        "load_timeframe_optimization_results",
        "load_selected_historical_dataset_to_replay",
        "next_replay_candle",
        "reset_replay",
        "run_alpha001_parameter_ranking",
        "run_demo_parameter_grid",
        "run_demo_research_benchmarks",
        "run_demo_research_experiment",
        "run_demo_robot_for_all",
        "run_demo_robot_once",
        "run_mt5_research_calibration",
        "run_mt5_research_calibration_for_pair",
        "run_online_demo_robot_cycle",
        "run_selected_historical_dataset_research_experiment",
        "save_configuration_preset",
        "select_historical_dataset",
        "select_replay_strategy",
        "start_replay",
        "stop_replay",
        "suggest_mt5_lab_setups",
        "validate_research_benchmarks",
        "_get_active_dataset_dashboard_data",
    )
    if not all(callable(getattr(service, method, None)) for method in required_methods):
        return False
    return (
        service.get_dashboard_contract_version()
        == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
    )


def _clear_streamlit_resource_cache_if_available() -> None:
    """Limpa cache resource se o runtime Streamlit disponibilizar a API."""
    cache_resource = getattr(st, "cache_resource", None)
    clear = getattr(cache_resource, "clear", None)
    if callable(clear):
        clear()


def dashboard_service_diagnostics(service: DashboardService) -> dict[str, object]:
    """Retorna diagnostico seguro do contrato carregado em runtime."""
    method = getattr(service, "get_dashboard_view_model", None)
    version_method = getattr(service, "get_dashboard_contract_version", None)
    loaded_version = version_method() if callable(version_method) else "MISSING"
    return {
        "module": service.__class__.__module__,
        "file": inspect.getfile(service.__class__),
        "has_get_dashboard_view_model": callable(method),
        "expected_contract_version": DASHBOARD_VIEW_MODEL_CONTRACT_VERSION,
        "loaded_contract_version": loaded_version,
    }


def render_contract_diagnostics(service: DashboardService) -> None:
    """Exibe diagnostico seguro de contrato na barra lateral."""
    diagnostics = dashboard_service_diagnostics(service)
    with st.sidebar.expander("Diagnostico de contrato", expanded=False):
        for key, value in diagnostics.items():
            st.caption(f"{key}: {value}")


def _session_state_size_hint() -> dict[str, object]:
    """Resume estado de sessao sem serializar objetos pesados."""
    keys = list(getattr(st.session_state, "keys", lambda: [])())
    relevant_prefixes = (
        "mt5_",
        "replay_",
        "runtime_",
        "dashboard_",
    )
    relevant_keys = [
        key for key in keys if str(key).startswith(relevant_prefixes)
    ]
    return {
        "total_keys": len(keys),
        "relevant_keys": len(relevant_keys),
        "relevant_key_names": ", ".join(sorted(map(str, relevant_keys))[:12]),
    }


def _runtime_performance_snapshot(
    service: DashboardService,
    data: object,
) -> dict[str, object]:
    """Coleta diagnostico leve sem disparar leitura externa."""
    del service
    forex = getattr(data, "mt5_forex_signals", None)
    robot = getattr(data, "demo_robot", None)
    rows = list(getattr(forex, "pairs", []) or [])
    last_load = float(st.session_state.get(MT5_FOREX_LAST_AUTO_LOAD_KEY, 0.0) or 0.0)
    now = time.monotonic()
    lock_busy = _mt5_forex_cycle_lock_busy()
    state_hint = _session_state_size_hint()
    report_cache_key = _mt5_trade_audit_report_cache_key(data)
    guard = get_runtime_guard_service()
    health = guard.health_snapshot(
        mode="LIGHT",
        lock_status="BUSY" if lock_busy else "AVAILABLE",
        forex_cycle_status="ENABLED" if _mt5_forex_auto_cycle_enabled() else "PAUSED",
        report_cycle_status="ENABLED" if _mt5_report_auto_refresh_enabled() else "PAUSED",
        demo_robot_cycle_status=getattr(robot, "status", "N/D"),
        cache_status="REPORT_CACHED" if report_cache_key in st.session_state else "EMPTY",
        render_durations=dict(st.session_state.get(RUNTIME_RENDER_DURATIONS_KEY, {}) or {}),
    )
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "runtime_guard_mode": health.mode,
        "runtime_guard_lock": health.lock_status,
        "runtime_guard_cache": health.cache_status,
        "refresh_id": int(getattr(forex, "refresh_id", 0) or 0),
        "last_mt5_read": getattr(forex, "last_mt5_read", "N/D"),
        "seconds_since_last_auto_load": round(now - last_load, 2) if last_load else "N/D",
        "connection_status": getattr(forex, "connection_status", "N/D"),
        "fast_refresh_duration_ms": round(
            float(getattr(forex, "fast_refresh_duration_ms", 0.0) or 0.0),
            2,
        ),
        "research_refresh_duration_ms": round(
            float(getattr(forex, "research_refresh_duration_ms", 0.0) or 0.0),
            2,
        ),
        "latency_breakdown": dict(getattr(forex, "latency_breakdown", {}) or {}),
        "pairs_loaded": len(rows),
        "received_candles_total": sum(
            int(getattr(row, "received_candles", 0) or 0) for row in rows
        ),
        "auto_cycle_ui": bool(st.session_state.get(MT5_FOREX_AUTO_CYCLE_UI_KEY, False)),
        "background_cycle_started": bool(MT5_FOREX_BACKGROUND_THREAD_STARTED),
        "cycle_lock_busy": lock_busy,
        "session_state_total_keys": state_hint["total_keys"],
        "session_state_relevant_keys": state_hint["relevant_keys"],
        "session_state_relevant_key_names": state_hint["relevant_key_names"],
        "mt5_trade_audit_cached": report_cache_key in st.session_state,
        "demo_robot_status": getattr(robot, "status", "N/D"),
        "health_message": getattr(forex, "health_message", "N/D"),
        "runtime_guard_last_events": " | ".join(
            event.name for event in health.last_events[-5:]
        ),
        "render_durations_ms": dict(
            st.session_state.get(RUNTIME_RENDER_DURATIONS_KEY, {}) or {}
        ),
    }


def _mt5_forex_cycle_lock_busy() -> bool:
    acquired = MT5_FOREX_CYCLE_LOCK.acquire(blocking=False)
    if acquired:
        MT5_FOREX_CYCLE_LOCK.release()
        return False
    return True


def _mt5_trade_audit_report_cache_key(data: object) -> str:
    forex = getattr(data, "mt5_forex_signals", None)
    return f"mt5_trade_audit_report_{int(getattr(forex, 'refresh_id', 0) or 0)}"


def _clear_runtime_queues_and_temporary_caches() -> list[str]:
    """Limpa somente estado temporario de UI/runtime."""
    result = get_runtime_guard_service().cleanup_temporary(st.session_state)
    removed = list(result.removed_keys)
    temporary_prefixes = (
        "mt5_trade_audit_report_",
        "runtime_temp_",
    )
    for key in list(getattr(st.session_state, "keys", lambda: [])()):
        key_text = str(key)
        if key_text.startswith(temporary_prefixes) and key_text in st.session_state:
            st.session_state.pop(key_text, None)
            removed.append(key_text)
    for cache_name in ("cache_data", "cache_resource"):
        cache = getattr(st, cache_name, None)
        clear = getattr(cache, "clear", None)
        if callable(clear):
            clear()
            removed.append(f"st.{cache_name}.clear")
    return removed


def _runtime_repair_scanner_snapshot() -> dict[str, object]:
    """Identifica sintomas conhecidos de lentidao/travamento no runtime atual."""
    render_durations = dict(st.session_state.get(RUNTIME_RENDER_DURATIONS_KEY, {}) or {})
    slow_tabs = [
        str(tab)
        for tab, duration in render_durations.items()
        if float(duration or 0.0) >= 3000.0
    ]
    temporary_keys = [
        str(key)
        for key in getattr(st.session_state, "keys", lambda: [])()
        if str(key).startswith(("runtime_temp_", "replay_pending_"))
        or str(key).startswith("mt5_trade_audit_report_")
    ]
    return {
        "auto_cycle_enabled": bool(
            st.session_state.get(MT5_FOREX_AUTO_CYCLE_UI_KEY, False)
        ),
        "cycle_lock_busy": _mt5_forex_cycle_lock_busy(),
        "dashboard_service_cached": "dashboard_service" in st.session_state,
        "initial_load_error": bool(
            st.session_state.get(MT5_FOREX_INITIAL_LOAD_ERROR_KEY)
        ),
        "manual_diagnostic_message": bool(
            st.session_state.get(MT5_FOREX_MANUAL_DIAGNOSTIC_MESSAGE_KEY)
        ),
        "legacy_guard_pending": not bool(
            st.session_state.get(LEGACY_PROCESS_GUARD_RAN_KEY, False)
        ),
        "slow_tabs": slow_tabs,
        "temporary_key_count": len(temporary_keys),
    }


def _runtime_repair_plan_from_snapshot(
    snapshot: dict[str, object],
) -> dict[str, list[str]]:
    """Converte sintomas conhecidos em remedios seguros e auditaveis."""
    symptoms: list[str] = []
    actions: list[str] = []

    if snapshot.get("auto_cycle_enabled"):
        symptoms.append("ciclo automatico MT5 Forex ativo")
        actions.append("pause_auto_cycle")
    if snapshot.get("cycle_lock_busy"):
        symptoms.append("ciclo MT5 Forex ocupado ou preso")
        actions.append("clear_cycle_timestamps")
        actions.append("pause_auto_cycle")
    if snapshot.get("dashboard_service_cached"):
        symptoms.append("DashboardService em cache de sessao")
        actions.append("recreate_dashboard_service")
    if snapshot.get("initial_load_error") or snapshot.get("manual_diagnostic_message"):
        symptoms.append("erro temporario de leitura/diagnostico MT5 registrado")
        actions.append("clear_runtime_errors")
    if snapshot.get("legacy_guard_pending"):
        symptoms.append("varredura de processos legados ainda nao executada")
        actions.append("run_legacy_guard")
    if int(snapshot.get("temporary_key_count", 0) or 0) > 0:
        symptoms.append("filas, caches ou relatorios temporarios acumulados")
        actions.append("clear_temporary_caches")
    slow_tabs = list(snapshot.get("slow_tabs", []) or [])
    if slow_tabs:
        symptoms.append("abas lentas detectadas: " + ", ".join(slow_tabs[:3]))
        actions.append("clear_render_metrics")

    unique_actions = list(dict.fromkeys(actions))
    if not symptoms:
        symptoms.append("nenhum sintoma conhecido detectado pelo scanner")
        unique_actions.append("maintenance_required")
    return {"symptoms": symptoms, "actions": unique_actions}


def _apply_runtime_repair_plan(plan: dict[str, list[str]]) -> list[str]:
    """Executa somente remedios conhecidos de runtime, sem alterar operacao."""
    removed: list[str] = []
    actions = set(plan.get("actions", []))

    if "clear_temporary_caches" in actions:
        removed.extend(_clear_runtime_queues_and_temporary_caches())
    if "clear_cycle_timestamps" in actions:
        for key in (
            MT5_FOREX_LAST_AUTO_LOAD_KEY,
            MT5_REPORT_LAST_AUTO_LOAD_KEY,
            MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY,
        ):
            if key in st.session_state:
                st.session_state.pop(key, None)
                removed.append(key)
    if "clear_runtime_errors" in actions:
        for key in (
            MT5_FOREX_INITIAL_LOAD_ERROR_KEY,
            MT5_FOREX_MANUAL_DIAGNOSTIC_KEY,
            MT5_FOREX_MANUAL_DIAGNOSTIC_MESSAGE_KEY,
        ):
            if key in st.session_state:
                st.session_state.pop(key, None)
                removed.append(key)
    if "clear_render_metrics" in actions and RUNTIME_RENDER_DURATIONS_KEY in st.session_state:
        st.session_state.pop(RUNTIME_RENDER_DURATIONS_KEY, None)
        removed.append(RUNTIME_RENDER_DURATIONS_KEY)
    if "recreate_dashboard_service" in actions and "dashboard_service" in st.session_state:
        st.session_state.pop("dashboard_service", None)
        removed.append("dashboard_service")
    if "pause_auto_cycle" in actions:
        st.session_state[MT5_FOREX_AUTO_CYCLE_UI_KEY] = False
        removed.append(MT5_FOREX_AUTO_CYCLE_UI_KEY)
    if "run_legacy_guard" in actions:
        _cleanup_legacy_traderia_processes_once()
        removed.append("legacy_process_guard")

    return list(dict.fromkeys(removed))


def _reset_dashboard_runtime_from_top() -> None:
    """Escaneia o runtime e aplica remedios conhecidos de lentidao/travamento."""
    snapshot = _runtime_repair_scanner_snapshot()
    plan = _runtime_repair_plan_from_snapshot(snapshot)
    removed = _apply_runtime_repair_plan(plan)
    if "maintenance_required" in set(plan.get("actions", [])):
        message = (
            "Scanner executado: nenhum problema conhecido foi identificado. "
            "Se o TraderIA continuar lento ou travado, precisa de manutencao."
        )
    else:
        message = (
            "Scanner executado: "
            + "; ".join(plan.get("symptoms", []))
            + ". Remedios aplicados: "
            + ", ".join(plan.get("actions", []))
            + "."
        )
    st.session_state[RUNTIME_CLEANUP_MESSAGE_KEY] = message
    st.session_state["runtime_top_reset_scan"] = " | ".join(plan.get("symptoms", []))
    st.session_state["runtime_top_reset_actions"] = ", ".join(plan.get("actions", []))
    st.session_state["runtime_top_reset_removed_count"] = len(set(removed))
    st.rerun()


def _powershell_quote(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _current_streamlit_port(default: str = "8532") -> str:
    args = list(sys.argv)
    for index, arg in enumerate(args):
        if arg == "--server.port" and index + 1 < len(args):
            return str(args[index + 1])
        if arg.startswith("--server.port="):
            return arg.split("=", 1)[1]
    return default


def _restart_dashboard_process_from_top() -> None:
    """Reinicia o processo Streamlit atual para liberar RAM acumulada."""
    app_path = Path(__file__).resolve()
    cwd = Path.cwd()
    port = _current_streamlit_port()
    restart_dir = Path(".traderia") / "runtime"
    restart_dir.mkdir(parents=True, exist_ok=True)
    script_path = restart_dir / "restart_traderianovo_streamlit.ps1"
    argument_line = subprocess.list2cmdline(
        [
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.port",
            port,
            "--server.headless",
            "true",
        ]
    )
    script_path.write_text(
        "\n".join(
            [
                "$ErrorActionPreference = 'SilentlyContinue'",
                f"$pidToWait = {os.getpid()}",
                "Wait-Process -Id $pidToWait -Timeout 20",
                "Start-Sleep -Seconds 1",
                "Start-Process "
                f"-FilePath {_powershell_quote(sys.executable)} "
                f"-ArgumentList {_powershell_quote(argument_line)} "
                f"-WorkingDirectory {_powershell_quote(cwd)} "
                "-WindowStyle Hidden",
            ]
        ),
        encoding="utf-8",
    )
    subprocess.Popen(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(script_path),
        ],
        close_fds=True,
    )
    os._exit(0)


def _render_top_runtime_reset() -> None:
    """Exibe reset rapido logo abaixo do nome do TraderIA Novo."""
    cols = st.columns([1, 5])
    if cols[0].button("Reiniciar", key="traderia_top_runtime_reset"):
        _mark_ui_critical_interaction()
        _restart_dashboard_process_from_top()
    message = st.session_state.get(RUNTIME_CLEANUP_MESSAGE_KEY)
    removed_count = st.session_state.get("runtime_top_reset_removed_count")
    if message and removed_count is not None:
        cols[1].caption(f"{message} Itens limpos: {removed_count}.")


def _record_runtime_render_duration(tab_name: str, started_at: float) -> None:
    durations = dict(st.session_state.get(RUNTIME_RENDER_DURATIONS_KEY, {}) or {})
    durations[tab_name] = round((time.perf_counter() - started_at) * 1000.0, 2)
    st.session_state[RUNTIME_RENDER_DURATIONS_KEY] = durations


def _persist_demo_robot_online_state(
    *,
    online: bool,
    pair: str = "TODOS",
    timeframe: str = "M1",
    message: str = "",
) -> None:
    try:
        MT5_DEMO_ROBOT_ONLINE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        MT5_DEMO_ROBOT_ONLINE_STATE_PATH.write_text(
            json.dumps(
                {
                    "online": bool(online),
                    "pair": str(pair or "TODOS"),
                    "timeframe": str(timeframe or "M1"),
                    "message": str(message or ""),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        return


def _load_demo_robot_online_state() -> dict[str, object]:
    if not MT5_DEMO_ROBOT_ONLINE_STATE_PATH.exists():
        return {}
    try:
        payload = json.loads(
            MT5_DEMO_ROBOT_ONLINE_STATE_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def ensure_mt5_forex_initial_load(service: DashboardService) -> None:
    """Carrega MT5 uma vez antes do dashboard leve renderizar estado vazio."""
    if os.getenv("TRADERIA_MT5_INITIAL_LOAD_ENABLED", "0").strip() != "1":
        return
    forex = service.get_mt5_forex_signals()
    if int(getattr(forex, "refresh_id", 0) or 0) > 0:
        return
    try:
        _load_mt5_forex_signals_locked(
            service,
            timeframe=str(getattr(forex, "timeframe", "H1") or "H1"),
        )
        st.session_state[MT5_FOREX_LAST_AUTO_LOAD_KEY] = time.monotonic()
        st.session_state.pop(MT5_FOREX_INITIAL_LOAD_ERROR_KEY, None)
    except Exception as exc:  # noqa: BLE001 - falha externa MT5 nao deve quebrar UI
        st.session_state[MT5_FOREX_INITIAL_LOAD_ERROR_KEY] = str(exc)


def _mt5_forex_auto_cycle_enabled() -> bool:
    env_enabled = os.getenv("TRADERIA_MT5_FOREX_AUTO_CYCLE_ENABLED", "1").strip() == "1"
    ui_enabled = bool(st.session_state.get(MT5_FOREX_AUTO_CYCLE_UI_KEY, False))
    if not (env_enabled or ui_enabled):
        return False
    return _mt5_forex_market_cycle_allowed_now()


def _mt5_report_auto_refresh_enabled() -> bool:
    if os.getenv("TRADERIA_MT5_REPORT_AUTO_REFRESH_ENABLED", "1").strip() != "1":
        return False
    return _mt5_forex_market_cycle_allowed_now()


def _ui_light_refresh_enabled() -> bool:
    return os.getenv("TRADERIA_UI_LIGHT_REFRESH_ENABLED", "1").strip() == "1"


def _ui_full_page_reload_enabled() -> bool:
    return os.getenv("TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED", "0").strip() == "1"


def _ui_interaction_grace_seconds() -> float:
    return float(os.getenv("TRADERIA_UI_INTERACTION_GRACE_SECONDS", "20"))


def _mark_ui_critical_interaction() -> None:
    st.session_state[UI_LAST_CRITICAL_INTERACTION_KEY] = time.monotonic()


def _ui_in_critical_interaction_grace() -> bool:
    last_interaction = float(
        st.session_state.get(UI_LAST_CRITICAL_INTERACTION_KEY, 0.0) or 0.0
    )
    return (
        last_interaction > 0.0
        and time.monotonic() - last_interaction < _ui_interaction_grace_seconds()
    )


def _mt5_forex_market_cycle_allowed_now(moment: datetime | None = None) -> bool:
    """Bloqueia ciclo automatico quando Forex esta fechado."""
    now = moment or datetime.now(timezone.utc).replace(tzinfo=None)
    if _is_mt5_forex_closed_holiday(now):
        return False
    weekday = now.weekday()
    if weekday == 5:
        return False
    if weekday == 6 and now.hour < 21:
        return False
    if weekday == 4 and now.hour >= 22:
        return False
    return True


def _is_mt5_forex_closed_holiday(moment: datetime) -> bool:
    """Feriados globais em que o Forex costuma ficar fechado."""
    fixed_closed_days = {(1, 1), (12, 25)}
    if (moment.month, moment.day) in fixed_closed_days:
        return True
    full_closed_days = {
        date(2026, 4, 3),  # Good Friday 2026
    }
    return moment.date() in full_closed_days


def _mt5_fast_snapshot_enabled() -> bool:
    return os.getenv("TRADERIA_MT5_FAST_SNAPSHOT_ENABLED", "1").strip() == "1"


def _apply_fast_mt5_snapshot_if_available(
    service: DashboardService,
    data: object,
) -> object:
    """Preenche MT5 Forex com leitura direta rapida sem disparar pesquisa pesada."""
    if not _mt5_fast_snapshot_enabled():
        return data

    current = getattr(data, "mt5_forex_signals", None)
    if current is not None and getattr(current, "connection_status", "") == "ONLINE":
        return data

    snapshot = _build_fast_mt5_forex_snapshot(service)
    if snapshot is None:
        return data
    try:
        return replace(data, mt5_forex_signals=snapshot)
    except TypeError:
        return data


def _build_fast_mt5_forex_snapshot(
    service: DashboardService,
) -> DashboardMT5ForexSignalViewModel | None:
    if os.getenv("TRADERIA_MT5_FAST_DIRECT_ENABLED", "0").strip() != "1":
        return None
    try:
        return service.get_fast_mt5_forex_snapshot()
    except Exception:
        return None


def _forex_pairs_count(data_or_forex: object) -> int:
    forex = getattr(data_or_forex, "mt5_forex_signals", data_or_forex)
    return len(list(getattr(forex, "pairs", []) or []))


def _preserve_mt5_forex_snapshot_if_empty(
    previous_data: object,
    refreshed_data: object,
) -> object:
    """Nao deixa snapshot leve vazio apagar a parte operacional da tela."""
    previous_forex = getattr(previous_data, "mt5_forex_signals", None)
    refreshed_forex = getattr(refreshed_data, "mt5_forex_signals", None)
    if previous_forex is None or refreshed_forex is None:
        return refreshed_data
    if _forex_pairs_count(refreshed_forex) > 0:
        return refreshed_data
    if _forex_pairs_count(previous_forex) <= 0:
        return refreshed_data
    try:
        return replace(refreshed_data, mt5_forex_signals=previous_forex)
    except TypeError:
        return previous_data


def _remember_valid_mt5_forex_snapshot(forex: object) -> object:
    if _forex_pairs_count(forex) > 0:
        st.session_state[MT5_FOREX_LAST_VALID_SNAPSHOT_KEY] = forex
        get_runtime_guard_service().preserve_snapshot(
            MT5_FOREX_LAST_VALID_SNAPSHOT_KEY,
            forex,
            validator=lambda value: _forex_pairs_count(value) > 0,
        )
    return forex


def _stable_mt5_forex_snapshot(forex: object) -> object:
    if _forex_pairs_count(forex) > 0:
        return _remember_valid_mt5_forex_snapshot(forex)
    previous = get_runtime_guard_service().preserve_snapshot(
        MT5_FOREX_LAST_VALID_SNAPSHOT_KEY,
        forex,
        validator=lambda value: _forex_pairs_count(value) > 0,
    )
    if previous is forex:
        previous = st.session_state.get(MT5_FOREX_LAST_VALID_SNAPSHOT_KEY)
    if previous is not None and _forex_pairs_count(previous) > 0:
        st.session_state[MT5_FOREX_LAST_VALID_SNAPSHOT_KEY] = previous
        return previous
    return forex


def _replace_mt5_forex_snapshot(data: object, forex: object) -> object:
    try:
        return replace(data, mt5_forex_signals=forex)
    except TypeError:
        return data


def _mt5_visual_signals_enabled() -> bool:
    return os.getenv("TRADERIA_MT5_VISUAL_SIGNALS_ENABLED", "1").strip() == "1"


def _inject_mt5_forex_auto_refresh() -> None:
    if not _ui_light_refresh_enabled():
        return
    if not (_mt5_forex_auto_cycle_enabled() or _mt5_report_auto_refresh_enabled()):
        return
    _render_mt5_light_refresh_indicator()
    if not _ui_full_page_reload_enabled() or _ui_in_critical_interaction_grace():
        return
    interval_ms = int(MT5_FOREX_AUTO_REFRESH_SECONDS * 1000)
    components.html(
        (
            "<script>"
            f"setTimeout(function() {{ window.parent.location.reload(); }}, {interval_ms});"
            "</script>"
        ),
        height=0,
        width=0,
    )


def _render_mt5_light_refresh_indicator() -> None:
    last_load = float(st.session_state.get(MT5_FOREX_LAST_AUTO_LOAD_KEY, 0.0) or 0.0)
    now = time.monotonic()
    remaining = (
        max(0, int(MT5_FOREX_AUTO_REFRESH_SECONDS - (now - last_load)))
        if last_load
        else 0
    )
    last_label = (
        st.session_state.get(MT5_DEMO_ROBOT_LAST_CYCLE_KEY)
        or time.strftime("%H:%M:%S")
    )
    st.caption(
        "Ultima atualizacao MT5: "
        f"{last_label} | Proxima atualizacao leve em: {remaining}s | "
        "Refresh de pagina inteira: "
        f"{'LIGADO' if _ui_full_page_reload_enabled() else 'DESLIGADO'}"
    )


def _maybe_run_mt5_forex_auto_cycle(
    service: DashboardService,
    data: object,
    forex: object,
) -> tuple[object, object]:
    if not _mt5_forex_auto_cycle_enabled():
        return data, forex
    guard = get_runtime_guard_service()
    now = time.monotonic()
    decision = guard.should_run_cycle(
        "forex_auto_cycle",
        interval_seconds=MT5_FOREX_AUTO_REFRESH_SECONDS,
        now=now,
        in_grace_period=_ui_in_critical_interaction_grace(),
    )
    if not decision.allowed:
        return data, forex
    _load_mt5_forex_signals_locked(
        service,
        timeframe=str(getattr(forex, "timeframe", "M1") or "M1"),
    )
    guard.mark_cycle_completed("forex_auto_cycle", now=now)
    st.session_state[MT5_FOREX_LAST_AUTO_LOAD_KEY] = now
    refreshed_data = service.get_light_dashboard_view_model()
    refreshed_data = _preserve_mt5_forex_snapshot_if_empty(data, refreshed_data)
    return refreshed_data, getattr(refreshed_data, "mt5_forex_signals", forex)


def _maybe_refresh_mt5_trade_audit_report(
    service: DashboardService,
    cached_report: object | None,
    *,
    force: bool = False,
) -> object | None:
    guard = get_runtime_guard_service()
    if not force and cached_report is not None:
        if not _mt5_report_auto_refresh_enabled():
            return cached_report
        now = time.monotonic()
        decision = guard.should_run_cycle(
            "report_refresh",
            interval_seconds=MT5_REPORT_AUTO_REFRESH_SECONDS,
            now=now,
            in_grace_period=_ui_in_critical_interaction_grace(),
        )
        if not decision.allowed:
            return cached_report
    else:
        now = time.monotonic()
    with st.spinner("Atualizando auditoria MT5..."):
        report = _load_mt5_trade_audit_report_locked(service)
    if report is None:
        return cached_report
    st.session_state[MT5_REPORT_AUDIT_CACHE_KEY] = report
    guard.mark_cycle_completed("report_refresh", now=now)
    st.session_state[MT5_REPORT_LAST_AUTO_LOAD_KEY] = now
    return report


def get_dashboard_view_model_or_stop(service: DashboardService) -> object:
    """Retorna o ViewModel ou exibe erro arquitetural sem stacktrace."""
    method = getattr(service, "get_dashboard_view_model", None)
    version_method = getattr(service, "get_dashboard_contract_version", None)
    if (
        callable(method)
        and callable(version_method)
        and version_method() == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
    ):
        view_model = method()
        if (
            getattr(view_model, "contract_version", None)
            == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
        ):
            return view_model

    st.session_state.pop("dashboard_service", None)
    _clear_streamlit_resource_cache_if_available()
    refreshed_service = DashboardService()
    st.session_state["dashboard_service"] = refreshed_service
    refreshed_method = getattr(refreshed_service, "get_dashboard_view_model", None)
    refreshed_version = getattr(
        refreshed_service,
        "get_dashboard_contract_version",
        None,
    )
    if (
        callable(refreshed_method)
        and callable(refreshed_version)
        and refreshed_version() == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
    ):
        view_model = refreshed_method()
        if (
            getattr(view_model, "contract_version", None)
            == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
        ):
            return view_model

    st.error(
        "Erro arquitetural: DashboardService ativo nao expoe "
        "get_dashboard_view_model() compativel com "
        f"DashboardViewModel contract {DASHBOARD_VIEW_MODEL_CONTRACT_VERSION}. "
        "Reinicie o Streamlit e valide a camada application.dashboard_service."
    )
    st.stop()


def get_light_dashboard_view_model_or_stop(service: DashboardService) -> object:
    """Retorna o ViewModel leve ou exibe erro arquitetural sem stacktrace."""
    method = getattr(service, "get_light_dashboard_view_model", None)
    version_method = getattr(service, "get_dashboard_contract_version", None)
    if (
        callable(method)
        and callable(version_method)
        and version_method() == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
    ):
        view_model = method()
        if (
            getattr(view_model, "contract_version", None)
            == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
        ):
            return view_model

    st.session_state.pop("dashboard_service", None)
    _clear_streamlit_resource_cache_if_available()
    refreshed_service = DashboardService()
    st.session_state["dashboard_service"] = refreshed_service
    refreshed_method = getattr(refreshed_service, "get_light_dashboard_view_model", None)
    refreshed_version = getattr(
        refreshed_service,
        "get_dashboard_contract_version",
        None,
    )
    if (
        callable(refreshed_method)
        and callable(refreshed_version)
        and refreshed_version() == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
    ):
        view_model = refreshed_method()
        if (
            getattr(view_model, "contract_version", None)
            == DASHBOARD_VIEW_MODEL_CONTRACT_VERSION
        ):
            return view_model

    st.error(
        "Erro arquitetural: DashboardService ativo nao expoe "
        "get_light_dashboard_view_model() compativel com "
        f"DashboardViewModel contract {DASHBOARD_VIEW_MODEL_CONTRACT_VERSION}. "
        "Reinicie o Streamlit e valide a camada application.dashboard_service."
    )
    st.stop()


def rerender_dashboard() -> None:
    """Forca novo ciclo de renderizacao do Streamlit."""
    st.rerun()


def request_replay_action(action: str, dataset_id: str | None = None) -> None:
    """Agenda uma acao de replay para o proximo ciclo de renderizacao."""
    st.session_state[REPLAY_PENDING_ACTION_KEY] = action
    if dataset_id is not None:
        st.session_state[REPLAY_PENDING_DATASET_KEY] = dataset_id
    st.rerun()
    st.stop()


def apply_pending_replay_action(service: DashboardService) -> object | None:
    """Aplica a acao pendente antes de desenhar os componentes do Replay."""
    action = st.session_state.pop(REPLAY_PENDING_ACTION_KEY, None)
    dataset_id = st.session_state.pop(REPLAY_PENDING_DATASET_KEY, None)
    if action is None:
        return None

    try:
        if action == "select_dataset":
            selected = service.select_historical_dataset(dataset_id)
            st.session_state[REPLAY_PENDING_MESSAGE_KEY] = (
                "success",
                f"Dataset historico de pesquisa ativo: {selected.dataset_id}",
            )
            return None
        if action == "load_dataset":
            service.disable_replay_auto_run()
            replay_data = service.load_selected_historical_dataset_to_replay()
            st.session_state[REPLAY_PENDING_MESSAGE_KEY] = (
                "success",
                f"Replay carregado com {replay_data.total_candles} candles.",
            )
            return replay_data
    except ValueError as exc:
        st.session_state[REPLAY_PENDING_MESSAGE_KEY] = ("error", str(exc))
        return None

    st.session_state[REPLAY_PENDING_MESSAGE_KEY] = (
        "error",
        f"Acao de Replay desconhecida: {action}",
    )
    return None


def show_pending_replay_message() -> None:
    """Exibe feedback produzido antes da renderizacao visual do Replay."""
    message = st.session_state.pop(REPLAY_PENDING_MESSAGE_KEY, None)
    if message is None:
        return
    message_type, text = message
    if message_type == "success":
        st.success(text)
    else:
        st.error(text)


def replay_control_disabled(replay_data: object) -> dict[str, bool]:
    """Retorna as regras de habilitacao dos controles do replay."""
    has_candles = getattr(replay_data, "total_candles", 0) > 0
    is_finished = _replay_status(replay_data) == "FINISHED"
    is_running = bool(getattr(replay_data, "is_running", False))
    return {
        "start": not has_candles or is_finished,
        "next": not has_candles or is_finished,
        "auto": not has_candles or is_finished,
        "stop": not is_running,
        "reset": not has_candles,
    }


def valor_ou_indisponivel(valor: object) -> object:
    """Retorna um valor existente ou N/D."""
    if valor is None:
        return "N/D"
    return valor


def indicador_nivel(valor: float | int | None, medio: float, alto: float) -> str:
    """Classifica um valor para exibicao visual."""
    if valor is None:
        return "🔴 Baixo"
    if valor >= alto:
        return "🟢 Alto"
    if valor >= medio:
        return "🟡 Médio"
    return "🔴 Baixo"


def exibir_card(
    titulo: str,
    valor: object,
    descricao: str,
    indicador: str = "",
) -> None:
    """Exibe um card operacional simples."""
    with st.container(border=True):
        st.caption(titulo)
        st.metric(titulo, valor_ou_indisponivel(valor))
        if indicador:
            st.write(indicador)
        st.caption(descricao)


def exibir_registros_readonly(
    rows: object,
    empty_message: str = "Nenhum registro disponivel.",
    max_items: int = 12,
) -> None:
    """Exibe registros read-only com chaves estaveis e sem tabelas dinamicas."""
    registros = _normalizar_registros_readonly(rows)
    if not registros:
        st.info(empty_message)
        return

    for indice, registro in enumerate(registros[:max_items], start=1):
        with st.container(border=True):
            st.caption(_titulo_registro_readonly(indice, registro))
            itens = list(registro.items())
            colunas = st.columns(min(4, max(1, len(itens))))
            for posicao, (campo, valor) in enumerate(itens):
                with colunas[posicao % len(colunas)]:
                    st.caption(str(campo))
                    st.write(valor_ou_indisponivel(valor))

    restantes = len(registros) - max_items
    if restantes > 0:
        st.caption(f"{restantes} registros adicionais omitidos nesta visao.")


def _normalizar_registros_readonly(rows: object) -> list[dict[str, object]]:
    """Normaliza dados tabulares para cards read-only."""
    if rows is None:
        return []
    if isinstance(rows, dict):
        return [{"campo": campo, "valor": valor} for campo, valor in rows.items()]
    return [dict(row) for row in rows]


def _titulo_registro_readonly(indice: int, registro: dict[str, object]) -> str:
    """Escolhe um titulo estavel para o card de registro."""
    campos_preferidos = (
        "dataset_id",
        "strategy",
        "estrategia",
        "experimento",
        "event",
        "evento",
        "timestamp",
        "data",
        "status",
    )
    for campo in campos_preferidos:
        valor = registro.get(campo)
        if valor is not None:
            return str(valor)
    return f"Registro {indice}"


def exibir_card_aguardando(titulo: str) -> None:
    """Exibe card vazio quando nao ha leitura de mercado."""
    exibir_card(titulo, "N/D", "Aguardando leitura do Market DNA.")


def exibir_cards_aguardando() -> None:
    """Exibe painel vazio aguardando MARKET DNA."""
    colunas = st.columns(5)
    for coluna, titulo in zip(colunas, _titulos_painel_mercado()):
        with coluna:
            exibir_card_aguardando(titulo)


def exibir_home(data: object) -> None:
    """Exibe a aba inicial do sistema."""
    status = data.system_status
    st.subheader("HOME")
    st.subheader("TraderIA Novo")
    exibir_dataset_ativo(data)
    exibir_perfil_dataset(data)
    colunas = st.columns(3)
    colunas[0].metric("Ativo operacional", status.active_symbol)
    colunas[1].metric("Status", status.status)
    colunas[2].metric("Versão", status.version)


def exibir_dashboard_layout(service: DashboardService, data: object) -> None:
    """Organiza o Dashboard como plataforma de pesquisa quantitativa."""
    st.subheader("MT5 Forex")
    st.caption(
        "Fluxo Forex MT5: leitura online leve, pesquisa sob demanda e "
        "execucao demo controlada."
    )
    _restore_demo_robot_online_state_if_needed()
    _global_demo_robot_cycle_fragment(service, data)
    selected_tab = _dashboard_tab_selector(
        (
            "MT5 Forex",
            "Laboratorio de Pesquisa",
            "Replay",
            "Historico MT5",
            "Relatorios",
            "Sistema Forex",
        )
    )
    data = _maybe_run_demo_robot_global_cycle(service, data)

    render_started_at = time.perf_counter()
    if selected_tab == "MT5 Forex":
        exibir_mt5_forex_dashboard(service, data)
    elif selected_tab == "Laboratorio de Pesquisa":
        exibir_research_dashboard(service, data)
    elif selected_tab == "Replay":
        exibir_replay_dashboard(service, data)
    elif selected_tab == "Historico MT5":
        exibir_mt5_history_comparison_dashboard(service, data)
    elif selected_tab == "Relatorios":
        exibir_relatorios_dashboard(service, data)
    elif selected_tab == "Sistema Forex":
        exibir_sistema_dashboard(data, service)
    else:
        st.error(f"Aba desconhecida: {selected_tab}")
    _record_runtime_render_duration(str(selected_tab), render_started_at)


def _maybe_run_demo_robot_global_cycle(
    service: DashboardService,
    data: object,
) -> object:
    """Mantem o robo demo vivo mesmo quando o usuario esta fora da aba MT5."""
    if not bool(st.session_state.get(MT5_DEMO_ROBOT_ONLINE_KEY, False)):
        return data
    if _demo_robot_background_cycle_active():
        return data
    forex = getattr(data, "mt5_forex_signals", None)
    timeframe = str(getattr(forex, "timeframe", "M1") or "M1")
    updated_data, _ = _run_demo_robot_online_cycle_if_due(
        service,
        data,
        selected_pair="TODOS",
        timeframe=timeframe,
    )
    return updated_data


@st.fragment(run_every=MT5_FOREX_FRAGMENT_RUN_EVERY)
def _global_demo_robot_cycle_fragment(
    service: DashboardService,
    data: object,
) -> None:
    """Mantem o robo demo em ciclo leve mesmo fora da aba MT5."""
    _maybe_run_demo_robot_global_cycle(service, data)


def _restore_demo_robot_online_state_if_needed() -> None:
    if bool(st.session_state.get(MT5_DEMO_ROBOT_ONLINE_KEY, False)):
        return
    state = _load_demo_robot_online_state()
    if not bool(state.get("online", False)):
        return
    st.session_state[MT5_DEMO_ROBOT_ONLINE_KEY] = True
    st.session_state[MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY] = 0.0
    message = str(state.get("message") or "").strip()
    st.session_state[MT5_DEMO_ROBOT_MESSAGE_KEY] = (
        message or "Monitoramento online restaurado do estado persistido."
    )


def _keep_demo_robot_online_requested(
    *,
    pair: str,
    timeframe: str,
    message: str,
) -> None:
    """Mantem a ultima escolha manual do usuario mesmo se o backend oscilar."""
    st.session_state[MT5_DEMO_ROBOT_ONLINE_KEY] = True
    st.session_state[MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY] = 0.0
    st.session_state[MT5_DEMO_ROBOT_MESSAGE_KEY] = message
    _persist_demo_robot_online_state(
        online=True,
        pair=pair,
        timeframe=timeframe,
        message=message,
    )


def _dashboard_tab_selector(options: tuple[str, ...]) -> str:
    """Renderiza navegacao leve com aparencia de abas."""
    state_key = "dashboard_selected_tab"
    widget_key = "dashboard_selected_tab_widget"
    query_tab = str(st.query_params.get("tab", "") or "")
    if query_tab in options and widget_key not in st.session_state:
        st.session_state[state_key] = query_tab
    if st.session_state.get(state_key) not in options:
        st.session_state[state_key] = options[0]
    if st.session_state.get(widget_key) not in options:
        st.session_state[widget_key] = st.session_state[state_key]

    selected_tab = st.segmented_control(
        "Abas do dashboard",
        options=list(options),
        selection_mode="single",
        key=widget_key,
        label_visibility="collapsed",
        width="stretch",
    )
    if selected_tab not in options:
        selected_tab = options[0]
    st.session_state[state_key] = str(selected_tab)
    if st.query_params.get("tab") != selected_tab:
        st.query_params["tab"] = str(selected_tab)
    return str(selected_tab)


@st.fragment(run_every=MT5_FOREX_FRAGMENT_RUN_EVERY)
def exibir_mt5_forex_dashboard(
    service: DashboardService,
    data: object,
) -> object:
    """Exibe painel principal Forex com sinais MT5 read-only."""
    forex = getattr(data, "mt5_forex_signals", None)
    if forex is None:
        st.error("Contrato MT5 Forex indisponivel na fachada do dashboard.")
        return data
    data, forex = _maybe_run_mt5_forex_auto_cycle(service, data, forex)
    _inject_mt5_forex_auto_refresh()

    st.subheader("MT5 Forex")
    st.warning(
        "SOMENTE ANALISE DE MERCADO. NENHUMA ORDEM REAL SERA ENVIADA."
    )
    st.caption(
        "Leitura pelo ultimo estado local do TraderIA."
    )
    configuration = data.configuration_data
    st.info(
        "Saida dinamica em SIMULACAO/PAPER. Nenhum SL/TP e modificado no MT5."
        if bool(getattr(configuration, "dynamic_exit_simulation_enabled", False))
        else "Saida dinamica simulada desligada. Recomendacoes seguem auditaveis e sem execucao."
    )
    assisted_sl_enabled = bool(
        getattr(configuration, "dynamic_exit_demo_sl_assisted_execution_enabled", False)
    )
    if assisted_sl_enabled:
        st.warning(
            "Modo DEMO ASSISTIDO habilitado: esta acao modifica SOMENTE o SL "
            "de uma posicao existente em conta DEMO, mediante confirmacao manual. "
            "Nao abre ordem, nao fecha posicao e nao altera TP."
        )
    else:
        st.info(
            "Modo DEMO ASSISTIDO de SL desligado. Nenhum stop e movido pelo dashboard."
        )
    if bool(getattr(forex, "mt5_safe_mode", True)):
        st.info(
            getattr(
                forex,
                "safe_mode_message",
                "MT5 Safe Mode ativo: usando leitura simples e heuristica. "
                "Research Quantitativo temporariamente desativado.",
            )
        )
    forex = _stable_mt5_forex_snapshot(forex)
    data = _replace_mt5_forex_snapshot(data, forex)
    pares = list(getattr(forex, "pairs", []) or [])
    received_by_pair = [
        int(getattr(row, "received_candles", 0) or 0)
        for row in pares
        if int(getattr(row, "received_candles", 0) or 0) > 0
    ]
    candles_per_pair = min(received_by_pair) if received_by_pair else 0
    controles = st.columns([1, 1, 1])
    controles[0].metric(
        "Velas configuradas",
        int(configuration.mt5_safe_mode_candles_loaded),
    )
    controles[1].metric("Velas lidas", candles_per_pair)
    visual_enabled = _mt5_visual_signals_enabled()
    controles[2].metric("Visual MT5", "LIGADO" if visual_enabled else "DESLIGADO")
    controles[2].caption(
        "JSON visual desligado por variavel de ambiente."
        if not visual_enabled
        else "JSON visual mantido pelo ultimo estado local."
    )

    colunas = st.columns(5)
    colunas[0].metric("Status MT5", getattr(forex, "connection_status", "N/D"))
    colunas[1].metric("Servidor", getattr(forex, "server", "N/D"))
    colunas[2].metric("Conta", getattr(forex, "account", "N/D"))
    colunas[3].metric("Timeframe MT5 lido", getattr(forex, "timeframe", "M1"))
    colunas[4].metric("Modo", getattr(forex, "read_only_status", "READ ONLY"))
    _exibir_mt5_safe_mode_minimal_diagnostic(forex)
    _exibir_mt5_connection_health(forex)
    # Atualizacao manual usa load_mt5_forex_signals no helper.
    data = _exibir_mt5_manual_diagnostic_controls(service, data, forex)
    forex = getattr(data, "mt5_forex_signals", forex)
    forex = _stable_mt5_forex_snapshot(forex)
    data = _replace_mt5_forex_snapshot(data, forex)
    pares = list(getattr(forex, "pairs", []) or [])

    if not pares:
        st.info(
            "Aguardando primeira leitura MT5 valida. "
            "Quando existir um snapshot valido, esta area permanecera visivel."
        )
        return data

    st.caption(getattr(forex, "message", "N/D"))
    filter_mode = str(st.session_state.get(MT5_ENTRY_FILTER_MODE_KEY, "Top 2"))
    _sync_mt5_entry_filter_mode_with_service(service, filter_mode)
    filter_rules_by_pair = _mt5_entry_filter_rules_by_pair(service, filter_mode)
    display_rows = [
        _forex_signal_row(
            row,
            filter_rules=filter_rules_by_pair.get(
                str(getattr(row, "pair", "") or "").upper(),
                [],
            ),
        )
        for row in pares
    ]
    _render_stable_forex_table(display_rows)
    _render_mt5_entry_filter_mode_selector()
    operational_model = _render_mt5_operational_model_selector()
    _sync_mt5_operational_model_with_service(service)
    data = _exibir_robo_demo_mt5(service, data, forex, display_rows)
    _exibir_entradas_teoricas_mt5(
        display_rows,
        robot_online=_demo_robot_online_status(data),
        mt5_status=getattr(forex, "connection_status", "N/D"),
        operational_model=operational_model,
    )
    report = _maybe_refresh_mt5_trade_audit_report(
        service,
        st.session_state.get(MT5_REPORT_AUDIT_CACHE_KEY),
    )
    if report is None:
        report = getattr(data, "mt5_trade_audit", None)
    _exibir_saidas_teoricas_mt5(service, report, display_rows)
    colunas = st.columns(4)
    decision_counts = _forex_decision_counts(display_rows)
    colunas[0].metric("BUY", decision_counts["BUY"])
    colunas[1].metric("SELL", decision_counts["SELL"])
    colunas[2].metric("WAIT", decision_counts["WAIT"])
    colunas[3].metric(
        "Indisponiveis",
        len(getattr(forex, "unavailable_pairs", []) or []),
    )

    return data


def _render_mt5_entry_filter_mode_selector() -> str:
    """Escolhe quantos filtros positivos NV-V entram no gate visual."""
    with st.container(border=True):
        st.markdown("#### Filtro de liberacao da entrada")
        colunas = st.columns([1.3, 1.0, 3.0])
        mode = colunas[0].selectbox(
            "Quantidade de filtros",
            ["Top 1", "Top 2", "Top 3", "Todos positivos"],
            index=1,
            key=MT5_ENTRY_FILTER_MODE_KEY,
            help=(
                "Escolhe quantos filtros discriminativos do Lab entram no gate "
                "da Entrada Teorica."
            ),
        )
        if colunas[1].button("Atualizar filtros", key="mt5_entry_filter_refresh"):
            st.session_state.pop(MT5_ENTRY_FILTER_RULES_CACHE_KEY, None)
        colunas[2].caption(
            "Usa somente NV-V positivo: se algo aparece mais nos nao vencedores, "
            "a entrada so libera quando esse indicador estiver ausente. "
            "Isso so filtra entrada; nao altera Alpha, "
            "score, confirmacao historica ou calculos do Lab."
        )
    return str(mode)


def _render_mt5_operational_model_selector() -> str:
    labels = {
        MT5_OPERATIONAL_MODEL_1: "Modelo 1 - Lab vencedor",
        MT5_OPERATIONAL_MODEL_2: "Modelo 2 - espelho definido por voce",
        MT5_OPERATIONAL_MODEL_3: "Modelo 3 - M3 RR3",
        MT5_OPERATIONAL_MODEL_4: "Modelo 4 - espelho do M1",
        MT5_OPERATIONAL_MODEL_5: "Modelo 5 - Price Action",
        MT5_OPERATIONAL_MODEL_6: "Modelo 6 - espelho do M5",
        MT5_OPERATIONAL_MODEL_ALL: "Todos - M1, M2, M3, M4, M5 e M6",
    }
    current = str(
        st.session_state.get(
            MT5_OPERATIONAL_MODEL_KEY,
            _load_persisted_mt5_operational_model(),
        )
        or MT5_OPERATIONAL_MODEL_1
    ).upper()
    if current not in labels:
        current = MT5_OPERATIONAL_MODEL_1
    st.session_state[MT5_OPERATIONAL_MODEL_KEY] = current
    with st.container(border=True):
        st.markdown("#### Chaveamento operacional")
        columns = st.columns([1.4, 1.2, 2.4])
        selected_label = columns[0].selectbox(
            "Modelo ativo para envio",
            list(labels.values()),
            index=list(labels).index(current),
            key="mt5_operational_model_selector",
            on_change=_mark_ui_critical_interaction,
            help=(
                "Somente o modelo selecionado pode enviar ordem. O outro fica "
                "apenas como conferencia visual."
            ),
        )
        selected = next(key for key, value in labels.items() if value == selected_label)
        columns[1].metric(
            "Modelo operacional",
            _mt5_operational_model_short_label(selected),
        )
        columns[2].caption(
            "MODELO 1 executa o plano vencedor vindo do Lab. MODELO 2 e a regra "
            "manual definida por voce: inverte BUY/SELL, usa o TP da BETA2 "
            "invertida no ponto do stop original e calcula o loss em RR 1. "
            "MODELO 3 e o fluxo M3 RR3: usa snapshot RR3 e so envia quando "
            "o sinal vivo confirma a direcao. MODELO 4 copia o M1 e espelha "
            "direcao, stop e alvo: stop original vira alvo e alvo original vira "
            "stop. MODELO 5 usa Price Action simples com estrutura, zona e "
            "confirmacao. MODELO 6 espelha o M5: inverte direcao e troca stop "
            "por alvo. Em TODOS, os seis modelos podem enviar ordem, mas "
            "cada modelo so pode ter uma posicao aberta por par."
        )
    st.session_state[MT5_OPERATIONAL_MODEL_KEY] = selected
    _persist_mt5_operational_model(selected)
    if selected == MT5_OPERATIONAL_MODEL_2:
        st.warning(
            "Modelo 2 experimental ativo: BUY vira SELL, SELL vira BUY, TP usa "
            "a BETA2 invertida no ponto do stop original e o loss fica em RR 1."
        )
    if selected == MT5_OPERATIONAL_MODEL_ALL:
        st.warning(
            "Todos os modelos ativo: M1, M2, M3, M4, M5 e M6 podem enviar ordem. "
            "O mesmo par pode ter uma posicao por modelo."
        )
    if selected == MT5_OPERATIONAL_MODEL_3:
        st.warning(
            "M3 RR3 ativo: usa o snapshot RR3 e so envia quando o sinal vivo "
            "confirmar a direcao do candidato M3."
        )
    if selected == MT5_OPERATIONAL_MODEL_4:
        st.warning(
            "Modelo 4 ativo: espelho do M1. Nao recalcula Lab; inverte BUY/SELL, "
            "usa o stop original como alvo e o alvo original como stop."
        )
    if selected == MT5_OPERATIONAL_MODEL_5:
        st.warning(
            "Modelo 5 ativo: Price Action simples. Usa estrutura, zona de "
            "interesse, confirmacao viva, stop estrutural e alvo estrutural/projecao."
        )
    if selected == MT5_OPERATIONAL_MODEL_6:
        st.warning(
            "Modelo 6 ativo: espelho do M5. Calcula o Price Action do M5, "
            "inverte BUY/SELL e usa o stop do M5 como alvo."
        )
    return selected


def _valid_mt5_operational_model(model: object) -> str:
    normalized = str(model or MT5_OPERATIONAL_MODEL_1).upper()
    if normalized in {
        MT5_OPERATIONAL_MODEL_1,
        MT5_OPERATIONAL_MODEL_2,
        MT5_OPERATIONAL_MODEL_3,
        MT5_OPERATIONAL_MODEL_4,
        MT5_OPERATIONAL_MODEL_5,
        MT5_OPERATIONAL_MODEL_6,
        MT5_OPERATIONAL_MODEL_ALL,
    }:
        return normalized
    return MT5_OPERATIONAL_MODEL_1


def _load_persisted_mt5_operational_model() -> str:
    try:
        data = json.loads(MT5_OPERATIONAL_MODEL_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return MT5_OPERATIONAL_MODEL_1
    return _valid_mt5_operational_model(data.get("model"))


def _persist_mt5_operational_model(model: object) -> None:
    normalized = _valid_mt5_operational_model(model)
    try:
        MT5_OPERATIONAL_MODEL_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        MT5_OPERATIONAL_MODEL_STATE_PATH.write_text(
            json.dumps(
                {
                    "model": normalized,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        return


def _sync_mt5_operational_model_with_service(service: DashboardService) -> str:
    model = str(
        st.session_state.get(
            MT5_OPERATIONAL_MODEL_KEY,
            _load_persisted_mt5_operational_model(),
        )
        or MT5_OPERATIONAL_MODEL_1
    ).upper()
    model = _valid_mt5_operational_model(model)
    st.session_state[MT5_OPERATIONAL_MODEL_KEY] = model
    setter = getattr(service, "set_mt5_operational_model", None)
    if callable(setter):
        setter(model)
    return model


def _mt5_operational_model_short_label(model: str) -> str:
    normalized = str(model or "").upper()
    if normalized == MT5_OPERATIONAL_MODEL_2:
        return "MODELO 2"
    if normalized == MT5_OPERATIONAL_MODEL_3:
        return "M3"
    if normalized == MT5_OPERATIONAL_MODEL_4:
        return "M4"
    if normalized == MT5_OPERATIONAL_MODEL_5:
        return "M5"
    if normalized == MT5_OPERATIONAL_MODEL_6:
        return "M6"
    if normalized == MT5_OPERATIONAL_MODEL_ALL:
        return "TODOS"
    return "MODELO 1"


def _mt5_operational_model_enabled(selected: str, model: str) -> bool:
    normalized = str(selected or MT5_OPERATIONAL_MODEL_1).upper()
    return normalized == MT5_OPERATIONAL_MODEL_ALL or normalized == model


def _sync_mt5_entry_filter_mode_with_service(
    service: DashboardService,
    mode: str,
) -> None:
    limit = _mt5_entry_filter_mode_limit(mode)
    setter = getattr(service, "_set_entry_filter_max_rules", None)
    if callable(setter):
        setter(limit)


def _sync_current_mt5_entry_filter_mode_with_service(
    service: DashboardService,
) -> None:
    _sync_mt5_entry_filter_mode_with_service(
        service,
        str(st.session_state.get(MT5_ENTRY_FILTER_MODE_KEY, "Top 2")),
    )


def _mt5_entry_filter_rules_by_pair(
    service: DashboardService,
    mode: str,
) -> dict[str, list[dict[str, object]]]:
    """Carrega filtros positivos NV-V ja calculados pelo Lab."""
    cache = st.session_state.get(MT5_ENTRY_FILTER_RULES_CACHE_KEY)
    if isinstance(cache, dict):
        all_rules = dict(cache)
    else:
        research = service.get_mt5_research_report_snapshot()
        all_rules = _mt5_entry_filter_rules_from_research(research)
        st.session_state[MT5_ENTRY_FILTER_RULES_CACHE_KEY] = all_rules
    limit = _mt5_entry_filter_mode_limit(mode)
    if limit is None:
        return {pair: list(rules) for pair, rules in all_rules.items()}
    return {pair: list(rules)[:limit] for pair, rules in all_rules.items()}


def _mt5_entry_filter_mode_limit(mode: str) -> int | None:
    normalized = str(mode or "").upper()
    if "TODOS" in normalized:
        return None
    if "3" in normalized:
        return 3
    if "2" in normalized:
        return 2
    return 1


def _mt5_entry_filter_rules_from_research(
    research: object,
) -> dict[str, list[dict[str, object]]]:
    """Seleciona filtros pela melhor Alpha do par, usando NV-V positivo."""
    scenarios = list(getattr(research, "scenario_ranking", []) or [])
    best_by_pair: dict[str, object] = {}
    for scenario in scenarios:
        pair = str(getattr(scenario, "pair", "") or "").upper()
        if not pair:
            continue
        current = best_by_pair.get(pair)
        if current is None or _historical_confirmation_rank(
            scenario
        ) > _historical_confirmation_rank(current):
            best_by_pair[pair] = scenario
    return {
        pair: _mt5_entry_filter_rules_from_scenario(scenario)
        for pair, scenario in best_by_pair.items()
    }


def _mt5_entry_filter_rules_from_scenario(
    scenario: object,
) -> list[dict[str, object]]:
    metrics = dict(getattr(scenario, "lab_discrimination_metrics", {}) or {})
    sample_size = int(getattr(scenario, "lab_confidence_sample_size", 0) or 0)
    if sample_size < MT5_ENTRY_FILTER_MIN_SAMPLE_SIZE:
        return []
    rules: list[dict[str, object]] = []
    for indicator, metric in metrics.items():
        if indicator not in MT5_ENTRY_FILTER_SUPPORTED_INDICATORS:
            continue
        if not isinstance(metric, dict):
            continue
        try:
            winner_rate = float(metric.get("winner_rate", 0.0) or 0.0)
            loser_rate = float(metric.get("loser_rate", 0.0) or 0.0)
        except (TypeError, ValueError):
            continue
        loser_edge = loser_rate - winner_rate
        if loser_edge < MT5_ENTRY_FILTER_MIN_EDGE:
            continue
        rules.append(
            {
                "indicator": str(indicator),
                "entry_edge": loser_edge,
                "source": "NV-V",
                "required_present": False,
                "action": "EXIGIR_AUSENTE",
                "winner_rate": winner_rate,
                "loser_rate": loser_rate,
                "sample_size": sample_size,
            }
        )
    return sorted(
        rules,
        key=lambda rule: (
            float(rule.get("entry_edge", 0.0) or 0.0),
            int(rule.get("sample_size", 0) or 0),
        ),
        reverse=True,
    )


def exibir_mt5_history_comparison_dashboard(
    service: DashboardService,
    data: object,
) -> None:
    """Exibe historico MT5 Forex sem comparar com datasets externos."""
    st.subheader("Historico MT5 Forex")
    st.caption(
        "Mostra somente pares Forex carregados do MT5 nesta sessao. "
        "Nenhum dataset legado participa desta tela."
    )
    forex = getattr(data, "mt5_forex_signals", None)
    if forex is None:
        st.info("MT5 Forex ainda nao carregado.")
        return

    colunas = st.columns(4)
    colunas[0].metric("Fonte MT5", "MetaTrader 5")
    colunas[1].metric("Timeframe MT5", getattr(forex, "timeframe", "N/D"))
    colunas[2].metric("Pares MT5", len(list(getattr(forex, "pairs", []) or [])))
    colunas[3].metric("Status", getattr(forex, "connection_status", "N/D"))

    research = getattr(data, "mt5_heuristic_research", None)
    if research is not None:
        st.subheader("Historico de Pesquisa MT5")
        pesquisa = st.columns(4)
        pesquisa[0].metric(
            "Ultima atualizacao",
            _friendly_candle_time(getattr(research, "last_update", "N/D")),
        )
        pesquisa[0].caption(
            f"Banco local: {service.get_mt5_research_history_database_path()}"
        )
        pesquisa[1].metric(
            "Candles historicos",
            int(getattr(research, "candles_loaded", 0) or 0),
        )
        pesquisa[2].metric("Timeframe pesquisa", getattr(research, "timeframe", "M1"))
        pesquisa[3].metric("Status pesquisa", getattr(research, "status", "N/D"))
        st.caption(
            "Este snapshot so muda quando voce executa a atualizacao historica "
            "de 5000 candles no Laboratorio de Pesquisa."
        )

    _render_stable_readonly_table(
        [_mt5_history_row(row) for row in list(getattr(forex, "pairs", []) or [])]
    )
    st.info(
        "Historico explicativo em modo Forex-only. Para pesquisa, use a aba "
        "Laboratorio de Pesquisa."
    )


def _mt5_history_row(row: object) -> dict[str, object]:
    return {
        "Par": str(getattr(row, "pair", "N/D")),
        "Timeframe": str(getattr(row, "timeframe", "N/D")).upper(),
        "Candles recebidos": int(getattr(row, "received_candles", 0) or 0),
        "Ultima vela": _friendly_candle_time(
            getattr(row, "last_candle_time", "N/D")
        ),
        "Ultimo preco": _price_label(float(getattr(row, "last_price", 0.0) or 0.0)),
        "Decisao": str(getattr(row, "decision", "WAIT")),
        "Status": str(getattr(row, "status", "N/D")),
    }


@st.fragment(run_every=MT5_REPORT_FRAGMENT_RUN_EVERY)
def exibir_relatorios_dashboard(service: DashboardService, data: object) -> None:
    """Exibe auditoria das negociacoes TraderIA x historico MT5."""
    data = _maybe_run_demo_robot_global_cycle(service, data)
    forex = getattr(data, "mt5_forex_signals", None)
    if os.getenv("TRADERIA_MT5_REPORT_FORCE_LOAD_ENABLED", "0").strip() == "1":
        try:
            _load_mt5_forex_signals_locked(
                service,
                timeframe=str(getattr(forex, "timeframe", "H1") or "H1"),
            )
        except Exception:
            pass
    st.subheader("Relatorios")
    if st.button("Atualizar auditoria MT5", key="mt5_report_refresh_audit"):
        st.session_state[MT5_REPORT_AUDIT_CACHE_KEY] = _maybe_refresh_mt5_trade_audit_report(
            service,
            st.session_state.get(MT5_REPORT_AUDIT_CACHE_KEY),
            force=True,
        )
    cached_report = _maybe_refresh_mt5_trade_audit_report(
        service,
        st.session_state.get(MT5_REPORT_AUDIT_CACHE_KEY),
    )
    if cached_report is not None:
        light_data = _preserve_mt5_forex_snapshot_if_empty(
            data,
            service.get_light_dashboard_view_model(),
        )
        data = replace(
            light_data,
            mt5_trade_audit=cached_report,
        )
    _inject_mt5_forex_auto_refresh()
    online_status = _demo_robot_online_status(data)
    status_columns = st.columns([0.12, 0.9, 1.8])
    with status_columns[0]:
        st.markdown(
            _demo_robot_status_dot_html(online_status),
            unsafe_allow_html=True,
        )
    with status_columns[1]:
        if st.button("Armar todos", key="mt5_report_arm_all"):
            _apply_forex_session_filter_preference(
                service,
                _forex_session_filter_ui_value(),
            )
            _arm_all_demo_robot_from_reports(service, data)
            st.session_state[MT5_REPORT_AUDIT_CACHE_KEY] = (
                _maybe_refresh_mt5_trade_audit_report(
                    service,
                    st.session_state.get(MT5_REPORT_AUDIT_CACHE_KEY),
                    force=True,
                )
            )
            light_data = _preserve_mt5_forex_snapshot_if_empty(
                data,
                service.get_light_dashboard_view_model(),
            )
            data = replace(
                light_data,
                mt5_trade_audit=st.session_state[MT5_REPORT_AUDIT_CACHE_KEY],
            )
    _render_forex_session_filter_checkbox(
        status_columns[2],
        key="mt5_report_forex_session_filter_enabled",
    )
    st.caption(
        "Historico das negociacoes originadas no TraderIA confrontado com o "
        "historico da plataforma MT5. Esta aba e somente leitura."
    )
    st.caption(
        "Auditoria MT5 atualiza em ciclo leve, sem recalcular Lab pesado e "
        "sem criar thread de fundo."
    )
    report = getattr(data, "mt5_trade_audit", None)
    if report is None:
        st.info("Relatorio de negociacoes MT5 indisponivel no ViewModel.")
        return

    colunas = st.columns(5)
    colunas[0].metric("Registros locais", getattr(report, "total_local_records", 0))
    colunas[1].metric("Aceitos localmente", getattr(report, "total_accepted_local", 0))
    colunas[2].metric("Auditados", getattr(report, "total_audited", 0))
    colunas[3].metric("Conferem", getattr(report, "total_matched", 0))
    colunas[4].metric("Divergencias", getattr(report, "total_mismatched", 0))

    status = getattr(report, "mt5_connection_status", "N/D")
    if status == "CONNECTED":
        st.success(getattr(report, "message", "Historico MT5 carregado."))
    else:
        st.warning(getattr(report, "message", "Historico MT5 nao confirmado."))
    st.caption(
        "Fonte TraderIA: "
        f"{getattr(report, 'source', 'N/D')} | Fonte MT5: "
        f"{getattr(report, 'mt5_source', 'N/D')} | Ultima auditoria: "
        f"{_friendly_candle_time(getattr(report, 'last_update', 'N/D'))}"
    )

    rows = list(getattr(report, "rows", []) or [])
    st.info(_mt5_position_manager_status_message(rows))
    if not rows:
        st.info("Nenhuma negociacao aceita pelo TraderIA foi encontrada para auditar.")
        return

    open_rows = [row for row in rows if _is_mt5_open_operation(row)]
    history_rows = [row for row in rows if not _is_mt5_open_operation(row)]
    signal_metrics = _mt5_signal_metrics_by_pair(data)

    st.markdown("#### Em negociacao")
    open_rows = _sorted_mt5_rows_like_mt5(open_rows)
    if open_rows:
        _exibir_resumo_lucro_em_negociacao_mt5(open_rows)
        _render_mt5_trade_audit_table(
            [_mt5_open_trade_compact_row(row) for row in open_rows],
            color_by_model=True,
        )
    else:
        st.info("Nenhuma operacao aberta ou ordem aberta encontrada no MT5.")

    _exibir_evolucao_patrimonial_mt5(report, history_rows)

    st.markdown("#### Historico")
    history_rows = _sorted_mt5_rows_like_mt5(history_rows)
    if history_rows:
        st.markdown("##### Ultima negociacao")
        _render_mt5_trade_audit_table(
            [
                _mt5_trade_audit_compact_row(_latest_mt5_history_row(history_rows))
            ],
            color_by_model=True,
        )
        st.markdown("##### Historico completo")
        _render_mt5_trade_audit_history_table(
            _sorted_mt5_history_rows_newest_first(history_rows),
            signal_metrics,
        )
    else:
        st.info("Nenhuma operacao encerrada encontrada no historico MT5.")

    st.info(
        "Em negociacao mostra POSITION e ORDER_OPEN. Historico mostra operacoes "
        "fechadas, divergentes ou nao encontradas no MT5."
    )
    st.info(
        "Uma linha marcada como CONFERE significa que o ticket aceito pelo "
        "TraderIA foi encontrado no historico MT5 com simbolo, lado e volume "
        "compativeis."
    )


def _is_mt5_open_operation(row: object) -> bool:
    return str(getattr(row, "operation_status", "")).upper() in {
        "ABERTA",
        "ORDEM_ABERTA",
    }


def _mt5_position_manager_status_message(rows: list[object]) -> str:
    """Resume o estado do Position Manager sem acionar leitura pesada."""
    open_rows = [row for row in rows if _is_mt5_open_operation(row)]
    if not open_rows:
        return (
            "Position Manager: sem posicao aberta para acompanhar | "
            "Saida atual: N/D"
        )

    active_rows = [
        row
        for row in open_rows
        if str(getattr(row, "dynamic_exit_policy", "N/D") or "N/D").upper()
        not in {"N/D", "NONE", ""}
    ]
    selected = active_rows[0] if active_rows else open_rows[0]
    policy = str(getattr(selected, "dynamic_exit_policy", "N/D") or "N/D")
    action = str(getattr(selected, "dynamic_exit_action", "N/D") or "N/D")
    mode = _mt5_trade_audit_stop_mode_label(selected)
    candidate = _optional_price(getattr(selected, "dynamic_exit_candidate_stop", None))
    return (
        "Position Manager: ATIVO monitorando "
        f"{len(open_rows)} posicao(oes) | Modo: {mode} | "
        f"Saida atual: {policy} / {action} | Stop candidato: {candidate}"
    )


def _mt5_open_profit_summary(rows: list[object]) -> dict[str, str]:
    projected_profit = sum(float(getattr(row, "projected_profit", 0.0) or 0.0) for row in rows)
    projected_loss = sum(float(getattr(row, "projected_loss", 0.0) or 0.0) for row in rows)
    open_cost = sum(float(getattr(row, "mt5_open_cost", 0.0) or 0.0) for row in rows)
    projected_open_cost = sum(
        float(getattr(row, "mt5_projected_open_cost", 0.0) or 0.0)
        for row in rows
    )
    mt5_profit = sum(float(getattr(row, "mt5_realized_profit", 0.0) or 0.0) for row in rows)
    has_rollover = any(bool(getattr(row, "session_is_rollover", False)) for row in rows)
    return {
        "Lucro projetado aberto": f"{projected_profit:.2f}",
        "Custo aberto": f"{open_cost:.2f}",
        "Custo aberto projetado": f"{projected_open_cost:.2f}",
        "Risco em aberto": f"{projected_loss:.2f}",
        "Resultado MT5": f"{mt5_profit:.2f}",
        "Rollover custo": "COM ROLLOVER" if has_rollover else "SEM ROLLOVER",
    }


def _exibir_resumo_lucro_em_negociacao_mt5(rows: list[object]) -> None:
    summary = _mt5_open_profit_summary(rows)
    colunas = st.columns(6)
    colunas[0].metric("Lucro projetado aberto", summary["Lucro projetado aberto"])
    colunas[1].metric("Resultado MT5", summary["Resultado MT5"])
    colunas[2].metric("Custo aberto", summary["Custo aberto"])
    colunas[3].metric("Risco em aberto", summary["Risco em aberto"])
    colunas[4].metric("Custo aberto projetado", summary["Custo aberto projetado"])
    colunas[5].metric("Rollover custo", summary["Rollover custo"])


def _mt5_signal_metrics_by_pair(data: object) -> dict[str, dict[str, object]]:
    forex = getattr(data, "mt5_forex_signals", None)
    pairs = list(getattr(forex, "pairs", []) or [])
    metrics: dict[str, dict[str, object]] = {}
    for row in pairs:
        pair = str(getattr(row, "pair", "") or "").upper()
        if not pair:
            continue
        metrics[pair] = {
            "score": getattr(row, "active_model_score", None),
            "current_confidence": getattr(row, "confidence", None),
            "lab_confidence": getattr(row, "lab_confidence", None),
        }
    research = getattr(data, "mt5_heuristic_research", None)
    for row in list(getattr(research, "rows", []) or []):
        pair = str(getattr(row, "pair", "") or "").upper()
        if not pair:
            continue
        pair_metrics = metrics.setdefault(pair, {})
        pair_metrics["score"] = getattr(row, "score", pair_metrics.get("score"))
        pair_metrics["lab_confidence"] = getattr(
            row,
            "confidence",
            pair_metrics.get("lab_confidence"),
        )
    return metrics


def _styled_mt5_history_rows(
    rows: list[object],
    signal_metrics: dict[str, dict[str, object]] | None = None,
) -> object:
    pd = __import__("pandas")
    dataframe = pd.DataFrame([_mt5_trade_audit_row(row, signal_metrics) for row in rows])
    return dataframe.style.apply(_mt5_history_result_row_style, axis=1)


def _render_mt5_trade_audit_table(
    rows: list[dict[str, object]],
    *,
    color_by_result: bool = False,
    color_by_model: bool = False,
) -> None:
    if not rows:
        st.info("Nenhum registro disponivel.")
        return

    columns = list(rows[0].keys())
    header = "".join(f"<th>{_html_escape(column)}</th>" for column in columns)
    body = []
    for row in rows:
        row_class = "traderia-row-wait"
        if color_by_model:
            row_class = _mt5_trade_audit_model_row_class(row)
        elif color_by_result:
            realized_profit = _safe_float(
                row.get("Lucro realizado MT5", row.get("Resultado MT5", 0.0))
            )
            if realized_profit > 0:
                row_class = "traderia-row-buy"
            elif realized_profit < 0:
                row_class = "traderia-row-sell"
        cells = []
        for column in columns:
            cell_class = _mt5_trade_audit_cell_class(row, column)
            cells.append(
                "<td"
                f"{f' class={cell_class!r}' if cell_class else ''}"
                ">"
                f"{_html_escape(row.get(column, ''))}"
                "</td>"
            )
        cells_html = "".join(cells)
        body.append(f"<tr class='{row_class}'>{cells_html}</tr>")

    st.markdown(
        (
            "<div class='traderia-table-wrap'>"
            "<table class='traderia-stable-table'>"
            f"<thead><tr>{header}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody>"
            "</table>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _render_mt5_trade_audit_history_table(
    history_rows: list[object],
    signal_metrics: dict[str, dict[str, object]],
) -> None:
    """Renderiza historico fechado em paginas curtas para evitar travar a UI."""
    if not history_rows:
        st.info("Nenhum registro disponivel.")
        return
    filters = st.columns([1, 1, 1, 1])
    pairs = sorted(
        {
            str(getattr(row, "symbol", "") or "").upper()
            for row in history_rows
            if str(getattr(row, "symbol", "") or "").strip()
        }
    )
    selected_pair = filters[0].selectbox(
        "Par historico",
        ["TODOS", *pairs],
        index=0,
        key="mt5_report_history_pair_filter",
    )
    result_filter = filters[1].selectbox(
        "Resultado",
        ["TODOS", "LUCRO", "PREJUIZO", "ZERO"],
        index=0,
        key="mt5_report_history_result_filter",
    )
    page_size = int(
        filters[2].selectbox(
            "Linhas por pagina",
            [10, 25, 50, 100],
            index=1,
            key="mt5_report_history_page_size",
            help="Limite visual para manter a aba Relatorio leve durante a rolagem.",
        )
    )
    filtered = [
        row
        for row in history_rows
        if (
            selected_pair == "TODOS"
            or str(getattr(row, "symbol", "") or "").upper() == selected_pair
        )
        and _mt5_history_result_matches(row, result_filter)
    ]
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page = int(
        filters[3].number_input(
            "Pagina",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key="mt5_report_history_page",
        )
    )
    start = (page - 1) * page_size
    end = start + page_size
    st.caption(
        f"Exibindo {start + 1 if filtered else 0}-{min(end, len(filtered))} "
        f"de {len(filtered)} filtrados; total historico: {len(history_rows)}. "
        "Historico paginado do mais recente para o mais antigo para preservar "
        "a leveza da aba Relatorio."
    )
    paged_rows = filtered[start:end]
    _render_mt5_trade_audit_table(
        [_mt5_trade_audit_compact_row(row) for row in paged_rows],
        color_by_model=True,
    )
    with st.expander("Baixar historico completo filtrado", expanded=False):
        st.caption(
            "Por padrao, o Relatorio monta apenas a pagina visivel. Marque a "
            "opcao abaixo somente quando quiser gerar o CSV completo filtrado."
        )
        prepare_full_csv = st.checkbox(
            "Preparar CSV completo filtrado",
            value=False,
            key="mt5_report_history_prepare_full_csv",
        )
        if prepare_full_csv:
            csv_rows = [
                _mt5_trade_audit_csv_row(row, signal_metrics)
                for row in filtered
            ]
            st.download_button(
                "Baixar historico filtrado CSV",
                data=_table_rows_to_csv_bytes(csv_rows),
                file_name="traderianovo_historico_mt5.csv",
                mime="text/csv",
                disabled=not csv_rows,
                key="mt5_report_history_download_csv",
            )
        else:
            st.info("CSV completo ainda nao foi preparado para preservar velocidade.")


def _table_rows_to_csv_bytes(rows: list[dict[str, object]]) -> bytes:
    if not rows:
        return b""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8-sig")


def _mt5_trade_audit_csv_row(
    row: object,
    signal_metrics: dict[str, dict[str, object]],
) -> dict[str, object]:
    payload = _mt5_trade_audit_row(row, signal_metrics)
    snapshot = getattr(row, "plan_snapshot", {}) or {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    payload["Snapshot plano JSON"] = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
    )
    for key, value in sorted(snapshot.items()):
        payload[f"Plano {key}"] = value
    return payload


def _mt5_open_trade_compact_row(row: object) -> dict[str, object]:
    """Linha leve para operacoes abertas na aba Relatorio."""
    return {
        "Modelo": _mt5_sender_model_label(row),
        "Par": str(getattr(row, "symbol", "N/D")),
        "Lado": str(getattr(row, "mt5_side", None) or getattr(row, "side", "N/D")),
        "Resultado MT5": _mt5_open_trade_money(row, "mt5_realized_profit"),
        "Lucro projetado": _mt5_open_trade_money(row, "projected_profit"),
        "Risco atual": _mt5_open_trade_money(row, "projected_loss"),
        "Entrada": _optional_price(
            getattr(row, "mt5_price", None) or getattr(row, "entry_price", None)
        ),
        "Stop atual": _optional_price(getattr(row, "mt5_stop", None)),
        "Alvo": _optional_price(getattr(row, "target", None)),
        "Acao PM": str(getattr(row, "position_manager_action", "N/D")),
        "Status PM": str(getattr(row, "position_manager_status", "N/D")),
        "Motivo": _mt5_trade_audit_position_manager_message(row),
    }


def _mt5_trade_audit_compact_row(row: object) -> dict[str, object]:
    """Linha paginada e compacta para o historico visual."""
    return {
        "Confere": "SIM" if getattr(row, "audit_status", "") == "CONFERE" else "NAO",
        "Modelo": _mt5_sender_model_label(row),
        "Par": str(getattr(row, "symbol", "N/D")),
        "Lado": str(getattr(row, "mt5_side", None) or getattr(row, "side", "N/D")),
        "Resultado MT5": f"{float(getattr(row, 'mt5_realized_profit', 0.0) or 0.0):.2f}",
        "Lucro projetado": f"{float(getattr(row, 'projected_profit', 0.0) or 0.0):.2f}",
        "Risco projetado": f"{float(getattr(row, 'projected_loss', 0.0) or 0.0):.2f}",
        "Setup entrada": str(getattr(row, "entry_setup", "N/D")),
        "Alpha": str(getattr(row, "alpha_id", "N/D")),
        "Beta": str(getattr(row, "beta_id", "N/D")),
        "Saida/Protecao": _mt5_trade_audit_exit_management_label(row),
        "Modo": _mt5_trade_audit_exit_management_mode(row),
        "Status": str(getattr(row, "operation_status", "N/D")),
        "Auditoria": str(getattr(row, "audit_status", "PENDENTE")),
        "Horario MT5": str(getattr(row, "mt5_time", "N/D")),
        "Motivo": _mt5_trade_audit_position_manager_message(row),
    }


def _mt5_history_result_matches(row: object, result_filter: str) -> bool:
    if result_filter == "TODOS":
        return True
    realized_profit = float(getattr(row, "mt5_realized_profit", 0.0) or 0.0)
    if result_filter == "LUCRO":
        return realized_profit > 0.0
    if result_filter == "PREJUIZO":
        return realized_profit < 0.0
    return abs(realized_profit) <= 1e-9


def _sorted_mt5_rows_like_mt5(rows: list[object]) -> list[object]:
    return sorted(rows, key=_mt5_trade_time_key)


def _sorted_mt5_history_rows_newest_first(rows: list[object]) -> list[object]:
    return sorted(rows, key=_mt5_trade_time_key, reverse=True)


def _latest_mt5_history_row(rows: list[object]) -> object:
    return _sorted_mt5_rows_like_mt5(rows)[-1]


def _mt5_history_result_row_style(row: object) -> list[str]:
    realized_profit = _safe_float(getattr(row, "get", lambda key, default=None: default)("Lucro realizado MT5", 0.0))
    if realized_profit > 0:
        row_style = "background-color: #DDF7E3; color: #0F3D24; font-weight: 600;"
    elif realized_profit < 0:
        row_style = "background-color: #FDE0E0; color: #5C1A1A; font-weight: 600;"
    else:
        row_style = "background-color: #FFFFFF; color: #111827;"
    return [row_style for _ in row]


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _exibir_evolucao_patrimonial_mt5(report: object, rows: list[object]) -> None:
    st.markdown("#### Evolucao patrimonial")
    default_start_date = _parse_dashboard_date(
        getattr(report, "equity_curve_default_start_date", "2026-07-01")
    )
    default_balance = 0.0
    controles = st.columns(2)
    start_date = controles[0].date_input(
        "Data inicial do patrimonio",
        value=default_start_date,
        format="DD/MM/YYYY",
    )
    initial_balance = controles[1].number_input(
        "Saldo inicial MT5",
        value=default_balance,
        step=10.0,
        format="%.2f",
    )
    main_chart_selection = _mt5_equity_main_chart_model_selection()
    main_chart_rows = _mt5_rows_for_equity_model_selection(
        rows,
        main_chart_selection,
    )
    main_curve = _mt5_realized_equity_curve(
        main_chart_rows,
        initial_balance=float(initial_balance),
        start_date=start_date,
    )
    model_curves = {
        model: _mt5_realized_equity_curve(
            _mt5_rows_for_equity_model_filter(rows, model),
            initial_balance=float(initial_balance),
            start_date=start_date,
        )
        for model in [
            "MODELO 1",
            "MODELO 2",
            "MODELO 3",
            "MODELO 4",
            "MODELO 5",
            "MODELO 6",
        ]
    }
    max_chart_start_index = max(
        [
            max(len(main_curve) - 2, 0),
            *[max(len(curve) - 2, 0) for curve in model_curves.values()],
        ]
    )
    chart_start_index = st.number_input(
        "Indice inicial do grafico",
        min_value=0,
        max_value=max_chart_start_index,
        value=0,
        step=1,
        help=(
            "Use para iniciar a curva a partir de uma operacao especifica. "
            "O trecho exibido sempre comeca em 0."
        ),
    )
    st.caption(
        _mt5_equity_model_filter_caption(
            rows,
            main_chart_rows,
            str(main_chart_selection),
        )
    )
    _render_mt5_equity_chart(
        f"Grafico principal - {main_chart_selection}",
        main_curve,
        chart_start_index=int(chart_start_index),
        model_filter=str(main_chart_selection),
    )
    for model_filter in [
        "MODELO 1",
        "MODELO 2",
        "MODELO 3",
        "MODELO 4",
        "MODELO 5",
        "MODELO 6",
    ]:
        _render_mt5_equity_chart(
            model_filter,
            model_curves[model_filter],
            chart_start_index=int(chart_start_index),
            model_filter=model_filter,
    )


def _mt5_equity_main_chart_model_selection() -> str:
    st.caption("Grafico principal")
    colunas = st.columns(7)
    all_selected = colunas[0].checkbox(
        "Todos",
        value=True,
        key="mt5_report_equity_main_all",
        help="Marca M1, M2, M3, M4, M5 e M6 no grafico principal.",
    )
    selected_models: list[str] = []
    for index, model in enumerate(("M1", "M2", "M3", "M4", "M5", "M6"), start=1):
        checked = colunas[index].checkbox(
            model,
            value=all_selected,
            disabled=all_selected,
            key=f"mt5_report_equity_main_{model.lower()}",
        )
        if all_selected or checked:
            selected_models.append(model)
    if not selected_models:
        st.warning("Selecione pelo menos um modelo para o grafico principal.")
        return "TODOS"
    return " + ".join(selected_models)


def _mt5_rows_for_equity_model_selection(
    rows: list[object],
    selection: str,
) -> list[object]:
    normalized = str(selection or "TODOS").upper().replace(" ", "")
    if normalized == "TODOS":
        return list(rows)
    selected_keys = {
        part
        for part in normalized.split("+")
        if part in {
            "M1",
            "M2",
            "M3",
            "M4",
            "M5",
            "M6",
            "MODELO1",
            "MODELO2",
            "MODELO3",
            "MODELO4",
            "MODELO5",
            "MODELO6",
        }
    }
    model_keys = {
        "M1": "MODELO1",
        "M2": "MODELO2",
        "M3": "MODELO3",
        "M4": "MODELO4",
        "M5": "MODELO5",
        "M6": "MODELO6",
        "MODELO1": "MODELO1",
        "MODELO2": "MODELO2",
        "MODELO3": "MODELO3",
        "MODELO4": "MODELO4",
        "MODELO5": "MODELO5",
        "MODELO6": "MODELO6",
    }
    targets = {model_keys[key] for key in selected_keys}
    if not targets:
        return list(rows)
    return [row for row in rows if _mt5_equity_row_model_key(row) in targets]


def _render_mt5_equity_chart(
    title: str,
    curve: list[float],
    *,
    chart_start_index: int,
    model_filter: str,
) -> None:
    st.markdown(f"##### {title}")
    if len(curve) <= 1:
        st.info(
            "Ainda nao ha operacoes encerradas suficientes para montar a curva "
            f"com o filtro {model_filter}."
        )
        return
    chart_curve = _mt5_equity_curve_rebased_from_index(
        curve,
        int(chart_start_index),
    )
    colunas = st.columns(3)
    colunas[0].metric("Patrimonio final", f"{curve[-1]:.2f}")
    colunas[1].metric("Operacoes na curva", str(len(curve) - 1))
    colunas[2].metric(
        "Base",
        f"{model_filter} desde indice {int(chart_start_index)}",
    )
    st.line_chart({"Patrimonio": chart_curve})


def _mt5_rows_for_equity_model_filter(
    rows: list[object],
    model_filter: str,
) -> list[object]:
    normalized = str(model_filter or "TODOS").upper()
    if normalized == "TODOS":
        return list(rows)
    target = normalized.replace(" ", "")
    return [
        row
        for row in rows
        if _mt5_equity_row_model_key(row) == target
    ]


def _mt5_equity_model_filter_caption(
    rows: list[object],
    filtered_rows: list[object],
    model_filter: str,
) -> str:
    counts = {
        "MODELO0": 0,
        "MODELO1": 0,
        "MODELO2": 0,
        "MODELO3": 0,
        "MODELO4": 0,
        "MODELO5": 0,
        "MODELO6": 0,
    }
    for row in rows:
        key = _mt5_equity_row_model_key(row)
        counts[key if key in counts else "MODELO0"] += 1
    return (
        f"Filtro aplicado: {model_filter} | linhas na curva: {len(filtered_rows)} | "
        f"M0: {counts['MODELO0']} | M1: {counts['MODELO1']} | "
        f"M2: {counts['MODELO2']} | M3: {counts['MODELO3']} | "
        f"M4: {counts['MODELO4']} | M5: {counts['MODELO5']} | "
        f"M6: {counts['MODELO6']}"
    )


def _mt5_equity_row_model_key(row: object) -> str:
    model = str(getattr(row, "operational_model", "") or "").upper()
    if not model or model in {"N/D", "NONE"}:
        snapshot = getattr(row, "plan_snapshot", {}) or {}
        if isinstance(snapshot, dict):
            model = str(snapshot.get("operational_model", "") or "").upper()
    if not model or model in {"N/D", "NONE"}:
        identity = str(getattr(row, "plan_identity", "") or "").upper()
        if not identity:
            snapshot = getattr(row, "plan_snapshot", {}) or {}
            if isinstance(snapshot, dict):
                identity = str(snapshot.get("plan_identity", "") or "").upper()
        model = identity
    if "MODELO_2" in model or "MODELO 2" in model or model == "M2":
        return "MODELO2"
    if "MODELO_3" in model or "MODELO 3" in model or model == "M3":
        return "MODELO3"
    if "MODELO_4" in model or "MODELO 4" in model or model == "M4":
        return "MODELO4"
    if "MODELO_5" in model or "MODELO 5" in model or model == "M5":
        return "MODELO5"
    if "MODELO_6" in model or "MODELO 6" in model or model == "M6":
        return "MODELO6"
    if "MODELO_1" in model or "MODELO 1" in model or model == "M1":
        return "MODELO1"
    if "MODELO2" in model:
        return "MODELO2"
    if "MODELO3" in model:
        return "MODELO3"
    if "MODELO4" in model:
        return "MODELO4"
    if "MODELO5" in model:
        return "MODELO5"
    if "MODELO6" in model:
        return "MODELO6"
    if "MODELO1" in model:
        return "MODELO1"
    return "MODELO0"


def _parse_dashboard_date(value: object) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return date(2026, 7, 1)


def _mt5_realized_equity_curve(
    rows: list[object],
    initial_balance: float = 0.0,
    start_date: date | None = None,
) -> list[float]:
    closed_rows = [
        row
        for row in rows
        if str(getattr(row, "operation_status", "")).upper() == "FECHADA/HISTORICO"
        and bool(getattr(row, "mt5_found", False))
        and _mt5_trade_date_in_range(row, start_date)
    ]
    closed_rows.sort(key=_mt5_trade_time_key)
    curve = [round(float(initial_balance), 2)]
    running_total = float(initial_balance)
    for row in closed_rows:
        running_total += float(getattr(row, "mt5_realized_profit", 0.0) or 0.0)
        curve.append(round(running_total, 2))
    return curve


def _mt5_equity_curve_rebased_from_index(
    curve: list[float],
    start_index: int,
) -> list[float]:
    if not curve:
        return [0.0]
    safe_start_index = max(0, min(int(start_index), len(curve) - 1))
    segment = curve[safe_start_index:]
    if not segment:
        return [0.0]
    baseline = float(segment[0])
    return [round(float(value) - baseline, 2) for value in segment]


def _mt5_trade_date_in_range(row: object, start_date: date | None) -> bool:
    if start_date is None:
        return True
    row_date = _mt5_trade_date(row)
    if row_date is None:
        return True
    return row_date >= start_date


def _mt5_trade_date(row: object) -> date | None:
    text = _mt5_trade_time_key(row)
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _mt5_trade_time_key(row: object) -> str:
    mt5_time = str(getattr(row, "mt5_time", "") or "")
    if mt5_time and mt5_time != "N/D":
        return mt5_time
    return str(getattr(row, "timestamp", "") or "")


def _mt5_trade_audit_row(
    row: object,
    signal_metrics: dict[str, dict[str, object]] | None = None,
) -> dict[str, object]:
    metrics = _mt5_signal_metrics_for_row(row, signal_metrics)
    return {
        "Confere": "SIM" if getattr(row, "audit_status", "") == "CONFERE" else "NAO",
        "Par": str(getattr(row, "symbol", "N/D")),
        "Lucro projetado app": f"{float(getattr(row, 'projected_profit', 0.0) or 0.0):.2f}",
        "Lucro realizado MT5": f"{float(getattr(row, 'mt5_realized_profit', 0.0) or 0.0):.2f}",
        "Prejuizo projetado app": f"{float(getattr(row, 'projected_loss', 0.0) or 0.0):.2f}",
        "Modelo envio": _mt5_sender_model_label(row),
        "Parametros": _mt5_trade_audit_parameters_label(row),
        "Protecao/Saida usada": _mt5_trade_audit_exit_management_label(row),
        "Modo dentro grupo": _mt5_trade_audit_exit_management_mode(row),
        "Modo saida": _mt5_trade_audit_beta_mode_label(row),
        "Mercado aberto": _forex_market_session_status(row),
        "Lucro projetado aberto": _mt5_open_trade_money(row, "projected_profit"),
        "Custo aberto projetado": _mt5_open_trade_money(row, "mt5_projected_open_cost"),
        "Custo aberto": _mt5_open_trade_money(row, "mt5_open_cost"),
        "Corretagem aberta": _mt5_open_trade_money(row, "mt5_commission"),
        "Swap aberto": _mt5_open_trade_money(row, "mt5_swap"),
        "Fee aberta": _mt5_open_trade_money(row, "mt5_fee"),
        "Risco em aberto": _mt5_open_trade_money(row, "projected_loss"),
        "Resultado MT5": _mt5_open_trade_money(row, "mt5_realized_profit"),
        "Rollover custo": _mt5_open_trade_rollover_label(row),
        "Operacao MT5": str(getattr(row, "operation_status", "N/D")),
        "Fonte MT5": str(getattr(row, "mt5_source", "N/D")),
        "Auditoria": str(getattr(row, "audit_status", "PENDENTE")),
        "Lado TraderIA": str(getattr(row, "side", "N/D")),
        "Volume TraderIA": float(getattr(row, "quantity", 0.0) or 0.0),
        "Setup entrada": str(getattr(row, "entry_setup", "N/D")),
        "Alpha entrada": str(getattr(row, "alpha_id", "ALPHA001")),
        "Setup saida": str(getattr(row, "exit_setup", "DYNAMIC_POSITION_MANAGER")),
        "Beta saida": str(getattr(row, "beta_id", "BETA001")),
        "Versao Beta": str(getattr(row, "beta_version", "BETA v1")),
        "Modo Beta": str(getattr(row, "beta_mode", "PROTECT_ONLY")),
        "Score Beta": _optional_number(getattr(row, "beta_strength_score", 0.0)),
        "Confirmacoes Beta": int(getattr(row, "beta_confirmation_count", 0) or 0),
        "Duracao Estado Beta": int(getattr(row, "beta_state_duration", 0) or 0),
        "EMA14 Beta": _optional_price(getattr(row, "beta_ema14_value", None)),
        "Slope EMA14 Beta": _optional_number(
            getattr(row, "beta_ema14_slope", None)
        ),
        "Momentum14 Beta": _optional_number(
            getattr(row, "beta_momentum_14", None)
        ),
        "ATR14 Beta": _optional_number(getattr(row, "beta_atr_14", None)),
        "ATR Rel Beta": _optional_percent(
            getattr(row, "beta_atr_relative_change", None)
        ),
        "Estrutura Beta": str(getattr(row, "beta_structure_signal", "N/D")),
        "Horario Beta": _friendly_candle_time(
            getattr(row, "beta_evaluated_at", "N/D")
        ),
        "Stop movel acionado": "SIM"
        if bool(getattr(row, "stop_movel_acionado", False))
        else "NAO",
        "Acao stop movel": str(getattr(row, "position_manager_action", "N/D")),
        "Status stop movel": str(getattr(row, "position_manager_status", "N/D")),
        "Pontuacao Lab": metrics["score"],
        "Confianca Lab": metrics["lab_confidence"],
        "Politica Saida Lab": str(getattr(row, "dynamic_exit_policy", "N/D")),
        "Recomendacao Saida": str(getattr(row, "dynamic_exit_action", "N/D")),
        "Motivo Saida Dinamica": str(getattr(row, "dynamic_exit_reason", "N/D")),
        "Confianca Saida Dinamica": _optional_percent(
            getattr(row, "dynamic_exit_confidence", 0.0)
        ),
        "Estado Mercado Saida": str(
            getattr(row, "dynamic_exit_market_state", "NO_POSITION")
        ),
        "R Atual Saida": _optional_number(
            getattr(row, "dynamic_exit_r_multiple", 0.0)
        ),
        "Stop Candidato": _optional_price(
            getattr(row, "dynamic_exit_candidate_stop", None)
        ),
        "Acao saida executada": str(
            getattr(row, "dynamic_exit_executed_action", "NONE")
        ),
        "Resultado saida": str(getattr(row, "dynamic_exit_final_result", "N/D")),
        "Motivo final saida": str(getattr(row, "final_exit_reason", "N/D")),
        "Execucao saida permitida": "SIM"
        if bool(getattr(row, "dynamic_exit_allowed_to_execute_demo", False))
        else "NAO",
        "Motor stop ativo": _mt5_trade_audit_stop_engine_label(row),
        "Modo gestao stop": _mt5_trade_audit_stop_mode_label(row),
        "Stop movel monitorado": "SIM"
        if _mt5_trade_audit_has_active_position(row)
        else "NAO",
        "Mensagem gestao stop": _mt5_trade_audit_position_manager_message(row),
        "Stop candidato ativo": _optional_price(
            getattr(row, "dynamic_exit_candidate_stop", None)
        ),
        "Sessao Forex": getattr(row, "forex_session", "N/D"),
        "Filtro sessao": "LIGADO"
        if bool(getattr(row, "session_filter_enabled", True))
        else "IGNORADO",
        "Resultado sessao": getattr(row, "session_filter_result", "N/D"),
        "Motivo sessao": getattr(row, "session_reason", "N/D"),
        "Horario TraderIA": _friendly_candle_time(getattr(row, "timestamp", "N/D")),
        "Horario MT5": _friendly_candle_time(getattr(row, "mt5_time", "N/D")),
        "Horario UTC": getattr(row, "session_timestamp_utc", "N/D"),
        "Horario local": getattr(row, "session_timestamp_brt", "N/D"),
        "Dia semana": getattr(row, "session_weekday", "N/D"),
        "Ticket TraderIA": str(getattr(row, "local_ticket", None) or "N/D"),
        "Status local": str(getattr(row, "local_status", "N/D")),
        "Ticket MT5": str(getattr(row, "mt5_ticket", None) or "N/D"),
        "Par MT5": str(getattr(row, "mt5_symbol", "N/D")),
        "Lado MT5": str(getattr(row, "mt5_side", "N/D")),
        "Volume MT5": float(getattr(row, "mt5_volume", 0.0) or 0.0),
        "Preco MT5": _price_label(float(getattr(row, "mt5_price", 0.0) or 0.0)),
        "Stop MT5 atual": _optional_price(getattr(row, "mt5_stop", None)),
        "Rollover": bool(getattr(row, "session_is_rollover", False)),
        "Overlap Londres NY": bool(
            getattr(row, "session_is_london_ny_overlap", False)
        ),
        "Abertura semanal": bool(getattr(row, "session_is_sunday_open", False)),
        "Fechamento semanal": bool(getattr(row, "session_is_friday_late", False)),
        "Versao politica sessao": getattr(row, "session_policy_version", "N/D"),
        "Versao pipeline execucao": getattr(row, "execution_pipeline_version", "N/D"),
        "Versao config Lab": getattr(row, "lab_configuration_version", "N/D"),
        "Versao Alpha": getattr(row, "alpha_version", "N/D"),
        "Versao Trade Plan": getattr(row, "trade_plan_version", "N/D"),
        "Versao motor execucao": getattr(row, "execution_engine_version", "N/D"),
        "Versao indicadores": getattr(row, "indicator_bundle_version", "N/D"),
        "Versao microestrutura": getattr(row, "microstructure_version", "N/D"),
        "Versao validacao": getattr(row, "validation_pipeline_version", "N/D"),
        "Versao estrategia": getattr(row, "strategy_definition_version", "N/D"),
        "Mensagem": str(getattr(row, "audit_message", "N/D")),
    }


def _mt5_open_trade_money(row: object, attr: str) -> str:
    """Mostra custo/lucro aberto somente para posicoes ou ordens abertas."""
    if not _is_mt5_open_operation(row):
        return "N/D"
    return f"{float(getattr(row, attr, 0.0) or 0.0):.2f}"


def _mt5_open_trade_rollover_label(row: object) -> str:
    """Indica se o custo aberto esta dentro da janela de rollover."""
    if not _is_mt5_open_operation(row):
        return "N/D"
    return "COM ROLLOVER" if bool(getattr(row, "session_is_rollover", False)) else "SEM ROLLOVER"


def _mt5_trade_audit_has_active_position(row: object) -> bool:
    """Indica se a linha representa uma posicao aberta acompanhavel."""
    final_result = str(getattr(row, "dynamic_exit_final_result", "") or "").upper()
    operation_status = str(getattr(row, "operation_status", "") or "").upper()
    mt5_found = bool(getattr(row, "mt5_found", False))
    return (
        final_result == "POSICAO_ABERTA"
        or operation_status in {"ABERTA", "OPEN", "POSICAO_ABERTA"}
        or (mt5_found and str(getattr(row, "mt5_ticket", "") or ""))
    )


def _forex_market_session_status(row: object) -> str:
    """Mostra status operacional de mercado sem expor booleano cru."""
    open_status = (
        "ABERTO" if bool(getattr(row, "forex_session_open", False)) else "FECHADO"
    )
    session = str(getattr(row, "forex_session", "N/D") or "N/D")
    filter_result = str(getattr(row, "session_filter_result", "N/D") or "N/D")
    reason = str(getattr(row, "session_reason", "") or "").strip()
    label = f"{open_status} | Sessao: {session}"
    if filter_result and filter_result.upper() not in {"N/D", "NONE"}:
        label = f"{label} | {filter_result}"
    if reason and reason.upper() not in {"N/D", "NONE"}:
        label = f"{label} | {reason}"
    return label


def _mt5_trade_audit_stop_engine_label(row: object) -> str:
    """Mostra somente o motor vigente de gestao de stop."""
    if not _mt5_trade_audit_has_active_position(row):
        return "INATIVO"
    policy = str(getattr(row, "dynamic_exit_policy", "") or "").upper()
    if policy and policy not in {"N/D", "NONE", "FIXED_STOP"}:
        return "POSITION_MANAGER"
    return "STOP_INICIAL"


def _mt5_trade_audit_stop_mode_label(row: object) -> str:
    """Resume o modo operacional sem expor fluxos legados desativados."""
    if not _mt5_trade_audit_has_active_position(row):
        return "SEM_POSICAO"
    if bool(getattr(row, "dynamic_exit_allowed_to_execute_demo", False)):
        return "DEMO_AUTORIZADO"
    if getattr(row, "dynamic_exit_candidate_stop", None) is not None:
        return "READ_ONLY_CANDIDATO"
    return "READ_ONLY"


def _mt5_trade_audit_exit_management_label(row: object) -> str:
    """Resume se a gestao foi HOLD, protecao de stop ou saida completa."""
    action = str(getattr(row, "position_manager_action", "") or "").upper()
    status = str(getattr(row, "position_manager_status", "") or "").upper()
    final_reason = str(getattr(row, "final_exit_reason", "") or "").upper()
    executed_action = str(
        getattr(row, "dynamic_exit_executed_action", "") or ""
    ).upper()
    candidate_stop = getattr(row, "dynamic_exit_candidate_stop", None)
    stop_moved = bool(getattr(row, "stop_movel_acionado", False))

    if (
        action in {"FULL_EXIT", "EARLY_EXIT", "CLOSE_POSITION"}
        or executed_action in {"FULL_EXIT", "EARLY_EXIT", "CLOSE_POSITION"}
        or status in {"POSITION_CLOSED", "CLOSE_EXECUTED"}
        or final_reason.startswith("EARLY_EXIT")
        or final_reason.startswith("FULL_EXIT")
    ):
        return "FULL_EXIT"
    if (
        action in {"STOP_MOVED", "MOVE_TO_BREAK_EVEN", "ATR_TRAILING", "PROTECT_POSITION"}
        or status in {"STOP_MOVED", "PROTECTED_POSITION"}
        or candidate_stop is not None
        or stop_moved
    ):
        return "PROTECT"
    return "STOP_HOLD"


def _mt5_trade_audit_exit_management_mode(row: object) -> str:
    """Detalha o modo usado dentro de FULL_EXIT, PROTECT ou STOP_HOLD."""
    group = _mt5_trade_audit_exit_management_label(row)
    action = str(getattr(row, "position_manager_action", "") or "").upper()
    final_reason = str(getattr(row, "final_exit_reason", "") or "").upper()
    executed_action = str(
        getattr(row, "dynamic_exit_executed_action", "") or ""
    ).upper()
    policy = str(getattr(row, "dynamic_exit_policy", "") or "").upper()
    recommendation = str(getattr(row, "dynamic_exit_action", "") or "").upper()

    if group == "FULL_EXIT":
        for value in (final_reason, executed_action, action, recommendation):
            if value and value not in {"N/D", "NONE", "HOLD_POSITION"}:
                return value
        return "FULL_EXIT_CANDIDATE"

    if group == "PROTECT":
        for value in (action, recommendation, policy):
            if value in {
                "BREAK_EVEN",
                "MOVE_TO_BREAK_EVEN",
                "ATR_TRAILING",
                "ATR_TRAILING_STOP",
                "TRAIL_BY_ATR",
                "STOP_MOVED",
                "PROTECT_POSITION",
                "PROTECT_TO_BREAK_EVEN",
            }:
                return value
        if getattr(row, "dynamic_exit_candidate_stop", None) is not None:
            return "STOP_CANDIDATO"
        return "PROTECAO_ATIVA"

    for value in (action, recommendation, policy):
        if value and value not in {"N/D", "NONE"}:
            return value
    return "HOLD_POSITION"


def _mt5_trade_audit_beta_mode_label(row: object) -> str:
    """Mostra o modo Beta em portugues operacional curto."""
    mode = str(getattr(row, "beta_mode", "PROTECT_ONLY") or "PROTECT_ONLY").upper()
    if mode in {"PROTECT_ONLY", "PROTEGER_SOMENTE"}:
        return "PROTEGER_SOMENTE"
    if mode in {"ADAPTIVE_FULL_EXIT", "FULL_EXIT", "SAIDA_COMPLETA"}:
        return "FULL_EXIT_ADAPTATIVO"
    return mode


def _mt5_trade_audit_position_manager_message(row: object) -> str:
    """Usa a mensagem auditavel do Position Manager quando ela existe."""
    message = str(getattr(row, "position_manager_message", "") or "").strip()
    if message and message.upper() not in {"N/D", "NONE"}:
        return message
    return _mt5_trade_audit_stop_message(row)


def _mt5_trade_audit_stop_message(row: object) -> str:
    """Mensagem curta e fiel ao estado ativo do Position Manager."""
    if not _mt5_trade_audit_has_active_position(row):
        return "Sem posicao aberta para acompanhar."
    if bool(getattr(row, "dynamic_exit_allowed_to_execute_demo", False)):
        return "Position Manager pode mover somente SL mais protetivo em Demo."
    if getattr(row, "dynamic_exit_candidate_stop", None) is not None:
        return "Stop candidato calculado; execucao demo nao autorizada neste registro."
    return "Position Manager acompanha sem alterar SL neste registro."


def _mt5_trade_audit_parameters_label(row: object) -> str:
    """Resume os parametros gravados na ordem para conferencia no historico."""
    pieces: list[str] = []
    snapshot = getattr(row, "plan_snapshot", {}) or {}
    if not isinstance(snapshot, dict):
        snapshot = {}
    alpha = str(
        snapshot.get("alpha_id") or getattr(row, "alpha_id", "") or ""
    ).strip()
    alpha_version = str(
        snapshot.get("alpha_version") or getattr(row, "alpha_version", "") or ""
    ).strip()
    if alpha and alpha.upper() not in {"N/D", "NONE"}:
        label = f"Alpha {alpha}"
        if alpha_version and alpha_version.upper() not in {"N/D", "NONE"}:
            label = f"{label} {alpha_version}"
        pieces.append(label)

    entry_setup = str(
        snapshot.get("entry_setup") or getattr(row, "entry_setup", "") or ""
    ).strip()
    if entry_setup and entry_setup.upper() not in {"N/D", "NONE"}:
        pieces.append(f"Entrada {entry_setup}")

    beta = str(snapshot.get("beta_id") or getattr(row, "beta_id", "") or "").strip()
    beta_version = str(
        snapshot.get("beta_version") or getattr(row, "beta_version", "") or ""
    ).strip()
    beta_mode = str(
        snapshot.get("beta_mode") or getattr(row, "beta_mode", "") or ""
    ).strip()
    if beta and beta.upper() not in {"N/D", "NONE"}:
        beta_label = f"Beta {beta}"
        if beta_version and beta_version.upper() not in {"N/D", "NONE"}:
            beta_label = f"{beta_label} {beta_version}"
        if beta_mode and beta_mode.upper() not in {"N/D", "NONE"}:
            beta_label = f"{beta_label} ({beta_mode})"
        pieces.append(beta_label)

    timeframe = str(snapshot.get("timeframe") or "").strip()
    if not timeframe or timeframe.upper() in {"N/D", "NONE"}:
        timeframe = str(getattr(row, "session_timeframe", "") or "").strip()
    if not timeframe or timeframe.upper() in {"N/D", "NONE"}:
        timeframe = str(getattr(row, "timeframe", "") or "").strip()
    if timeframe and timeframe.upper() not in {"N/D", "NONE"}:
        pieces.append(f"TF {timeframe}")

    risk_reward = _safe_float_or_none(
        snapshot.get("risk_reward") or getattr(row, "risk_reward", None)
    )
    if risk_reward is not None and risk_reward > 0:
        pieces.append(f"RR {risk_reward:.2f}")

    entry_price = _safe_float_or_none(
        snapshot.get("entry_price") or getattr(row, "entry_price", None)
    )
    if entry_price is not None and entry_price > 0:
        pieces.append(f"Entrada {_price_label(entry_price)}")
    stop = _safe_float_or_none(
        snapshot.get("initial_stop") or getattr(row, "stop", None)
    )
    if stop is not None:
        pieces.append(f"Stop {_price_label(stop)}")
    target = _safe_float_or_none(
        snapshot.get("target") or getattr(row, "target", None)
    )
    if target is not None:
        pieces.append(f"Alvo {_price_label(target)}")

    trade_plan = str(
        snapshot.get("trade_plan_version")
        or getattr(row, "trade_plan_version", "")
        or ""
    ).strip()
    if trade_plan and trade_plan.upper() not in {"N/D", "NONE"}:
        pieces.append(trade_plan)
    return " | ".join(pieces) if pieces else "N/D"


def _mt5_signal_metrics_for_row(
    row: object,
    signal_metrics: dict[str, dict[str, object]] | None,
) -> dict[str, str]:
    pair = str(getattr(row, "symbol", "") or "").upper()
    metrics = (signal_metrics or {}).get(pair, {})
    return {
        "score": _optional_percent(metrics.get("score")),
        "current_confidence": _optional_percent(metrics.get("current_confidence")),
        "lab_confidence": _optional_percent(metrics.get("lab_confidence")),
    }


def _exibir_robo_demo_mt5(
    service: DashboardService,
    data: object,
    forex: object,
    rows: list[dict[str, object]],
) -> object:
    st.subheader("Robo Demo MT5")
    st.warning(
        "Execucao MT5 Demo real somente com TRADERIA_DEMO_EXECUTION_ENABLED=1 "
        "e conta MT5 DEMO. Conta real permanece bloqueada."
    )
    pair_options = [
        str(row.get("Par", "")).strip()
        for row in rows
        if str(row.get("Par", "")).strip()
    ]
    monitor_options = ["TODOS"] + pair_options if pair_options else ["TODOS"]
    selected_pair = monitor_options[0]
    if pair_options:
        selected_pair = st.selectbox(
            "Pares monitorados pelo robo demo",
            monitor_options,
            key="mt5_demo_robot_pair",
            on_change=_mark_ui_critical_interaction,
        )
    st.caption(
        "Modo temporal: o robo fica armado e aguarda entrada teorica do "
        "Research Lab. Em TODOS, processa todos os candidatos prontos; "
        "em par individual, avalia apenas o ativo selecionado."
    )
    controls = st.columns([0.12, 1, 1.8, 1, 1, 2])
    status_dot_slot = controls[0].empty()
    timeframe = getattr(forex, "timeframe", "M1")
    selected_session_filter = _render_forex_session_filter_checkbox(
        controls[2],
        key="mt5_demo_robot_forex_session_filter_enabled",
    )
    if controls[1].button("Armar robo demo", key="mt5_demo_robot_arm"):
        _mark_ui_critical_interaction()
        _record_runtime_event("DEMO_ROBOT_ARM_REQUESTED")
        _apply_forex_session_filter_preference(service, selected_session_filter)
        _sync_mt5_operational_model_with_service(service)
        _enable_mt5_demo_execution_for_session()
        armed_robot = service.arm_demo_robot(pair=selected_pair, timeframe=timeframe)
        online_allowed = _demo_robot_online_allowed(armed_robot)
        st.session_state[MT5_DEMO_ROBOT_ONLINE_KEY] = True
        st.session_state[MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY] = 0.0
        st.session_state[MT5_DEMO_ROBOT_LAST_VISIBLE_SNAPSHOT_KEY] = armed_robot
        _persist_demo_robot_online_state(
            online=True,
            pair=selected_pair,
            timeframe=timeframe,
            message=str(getattr(armed_robot, "message", "")),
        )
        if online_allowed:
            _record_runtime_event("DEMO_ROBOT_ARMED_ONLINE")
            st.session_state[MT5_DEMO_ROBOT_MESSAGE_KEY] = (
                "Robo demo armado e monitoramento online ligado."
            )
        else:
            _record_runtime_event("DEMO_ROBOT_ARM_BLOCKED")
            st.session_state[MT5_DEMO_ROBOT_MESSAGE_KEY] = (
                "Robo demo bloqueado pelo backend: "
                f"{getattr(armed_robot, 'message', 'motivo indisponivel')}"
            )
        data = _with_demo_robot_snapshot(service.get_dashboard_view_model(), armed_robot)
    if controls[3].button("Avaliar gatilho agora", key="mt5_demo_robot_evaluate"):
        _mark_ui_critical_interaction()
        _sync_current_mt5_entry_filter_mode_with_service(service)
        _sync_mt5_operational_model_with_service(service)
        if str(selected_pair or "").upper() in {"TODOS", "ALL"}:
            evaluated_robot = service.run_demo_robot_for_all(timeframe=timeframe)
        else:
            evaluated_robot = service.evaluate_armed_demo_robot_once(
                pair=selected_pair,
                timeframe=timeframe,
            )
        data = _with_demo_robot_snapshot(
            service.get_dashboard_view_model(),
            evaluated_robot,
        )
    if controls[4].button("Desarmar robo", key="mt5_demo_robot_disarm"):
        _mark_ui_critical_interaction()
        disarmed_robot = service.disarm_demo_robot(pair=selected_pair, timeframe=timeframe)
        st.session_state[MT5_DEMO_ROBOT_ONLINE_KEY] = False
        st.session_state[MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY] = 0.0
        st.session_state.pop(MT5_DEMO_ROBOT_LAST_VISIBLE_SNAPSHOT_KEY, None)
        _persist_demo_robot_online_state(
            online=False,
            pair=selected_pair,
            timeframe=timeframe,
            message=str(getattr(disarmed_robot, "message", "")),
        )
        data = _with_demo_robot_snapshot(
            service.get_dashboard_view_model(),
            disarmed_robot,
        )
    controls[5].caption(
        "Para operar em demo: conta MT5 DEMO, env habilitado, plano Research "
        "valido e sem posicao aberta no simbolo."
    )
    online_enabled = bool(st.session_state.get(MT5_DEMO_ROBOT_ONLINE_KEY, False))
    runtime_message = st.session_state.get(MT5_DEMO_ROBOT_MESSAGE_KEY)
    if runtime_message:
        st.caption(str(runtime_message))
    if online_enabled:
        if not _demo_robot_background_cycle_active():
            data, online_enabled = _run_demo_robot_online_cycle_if_due(
                service,
                data,
                selected_pair=selected_pair,
                timeframe=timeframe,
            )
        if online_enabled:
            st.success(
                "Monitoramento online ATIVO: o robo atualiza MT5 e entra "
                "automaticamente quando surgir gatilho valido."
            )
        else:
            st.warning(
                "Monitoramento online BLOQUEADO pelo backend. Verifique conta demo, "
                "TRADERIA_DEMO_EXECUTION_ENABLED e estado do robo antes de operar."
            )
    else:
        st.info("Monitoramento online INATIVO. Arme o robo para iniciar.")
    status_dot_slot.markdown(
        _demo_robot_status_dot_html(online_enabled),
        unsafe_allow_html=True,
    )
    if online_enabled:
        current_robot = service.get_demo_robot_status()
        if not _demo_robot_online_allowed(current_robot):
            current_robot = service.arm_demo_robot(
                pair=selected_pair,
                timeframe=timeframe,
            )
        if _demo_robot_online_allowed(current_robot):
            data = _with_demo_robot_snapshot(data, current_robot)
        else:
            online_enabled = True
            _keep_demo_robot_online_requested(
                pair=selected_pair,
                timeframe=timeframe,
                message=(
                    "Monitoramento online mantido pelo ultimo comando do usuario; "
                    "backend ainda nao confirmou robo armado e sera rearmado no "
                    "proximo ciclo."
                ),
            )
    robot = getattr(data, "demo_robot", None)
    if robot is None:
        st.info("Robo demo indisponivel no contrato do dashboard.")
        return data
    robot = _stable_demo_robot_snapshot(robot)
    robot_status = getattr(robot, "status", "DISARMED")
    robot_message = getattr(robot, "message", "Robo demo desarmado.")
    robot_result_status = getattr(robot, "result_status", "DISARMED")
    robot_result_message = getattr(
        robot,
        "result_message",
        "Nenhuma ordem foi enviada ao MT5.",
    )
    if robot_status == "READY" and not online_enabled:
        robot_status = "DISARMED"
        robot_message = (
            "Robo demo desarmado. Clique em Armar robo demo para aguardar entrada."
        )
        robot_result_status = "DISARMED"
        robot_result_message = "Nenhuma ordem foi enviada ao MT5."
    elif online_enabled and robot_status in {"READY", "ARMED"}:
        robot_status = "ARMED_WAITING"
        robot_message = (
            "Robo demo armado e monitorando entradas teoricas do Research Lab."
        )
        robot_result_status = "ARMED_WAITING"
        if robot_result_message == "Nenhuma ordem foi enviada ao MT5.":
            robot_result_message = "Aguardando gatilho valido para envio MT5 Demo."
    columns = st.columns(5)
    columns[0].metric("Status", robot_status)
    columns[1].metric("Par", getattr(robot, "selected_pair", "N/D"))
    columns[2].metric("Modelo", getattr(robot, "model", "N/D"))
    columns[3].metric("Decisao", getattr(robot, "decision", "WAIT"))
    columns[4].metric("Provider", getattr(robot, "provider", "N/D"))
    display_entry, display_stop, display_target = _demo_robot_trade_prices(robot)
    columns = st.columns(4)
    columns[0].metric("Entrada", _optional_price(display_entry))
    columns[1].metric("Stop", _optional_price(display_stop))
    columns[2].metric("Alvo", _optional_price(display_target))
    mt5_send_enabled = bool(getattr(robot, "mt5_" + "order" + "_send_enabled", False))
    columns[3].metric(
        "Envio MT5",
        "DESLIGADO" if not mt5_send_enabled else "LIGADO",
    )
    st.caption(robot_message)
    st.caption(robot_result_message)
    if online_enabled:
        st.caption(
            "Ultimo ciclo online: "
            f"{st.session_state.get(MT5_DEMO_ROBOT_LAST_CYCLE_KEY, 'N/D')} | "
            f"proxima checagem em {int(MT5_DEMO_ROBOT_INTERVAL_SECONDS)}s. "
            f"Timeframe do candle: {timeframe}."
        )
    st.caption(
        "O card acima mostra o ultimo par avaliado. A tabela abaixo mostra todos "
        "os pares monitorados e se cada um possui plano executavel."
    )
    rejection_tree = list(getattr(robot, "rejection_tree", []) or [])
    if rejection_tree:
        st.markdown("#### Arvore de rejeicao do ultimo candidato")
        _render_stable_readonly_table(
            [_demo_robot_rejection_step_row(step) for step in rejection_tree]
        )
    monitor_rows = [_demo_robot_monitor_row(row) for row in rows]
    if monitor_rows:
        st.markdown("#### Monitor do Robo - Modelo 1 atual")
        _render_stable_readonly_table(monitor_rows)
    model2_monitor_rows = [
        _demo_robot_monitor_row(_model2_inverse_entry_row(row))
        for row in rows
    ]
    if model2_monitor_rows:
        st.markdown("#### Monitor do Robo - Modelo 2 espelho BETA2 RR1")
        _render_stable_readonly_table(model2_monitor_rows)
    audit = list(getattr(robot, "audit_log", []) or [])
    if audit:
        _render_stable_readonly_table([_demo_robot_audit_row(row) for row in audit[-5:]])
    else:
        st.info("Nenhum ciclo demo executado nesta sessao.")
    return data


def _demo_robot_monitor_row(row: dict[str, object]) -> dict[str, object]:
    decision = str(row.get("Decisao", "WAIT") or "WAIT")
    entry_status = str(row.get("Entrada Teorica", "SEM_GATILHO") or "SEM_GATILHO")
    plan_status = str(row.get("Plano Research", "SEM_PLANO") or "SEM_PLANO")
    stop = str(row.get("Stop Research", "N/D") or "N/D")
    target = str(row.get("Alvo Research", "N/D") or "N/D")
    exit_plan = "N/D" if stop == "N/D" or target == "N/D" else f"{stop} / {target}"
    if decision == "WAIT":
        robot_status = "AGUARDANDO"
        block_reason = "SEM_SINAL"
    elif entry_status != "SINAL_TEORICO":
        robot_status = "AGUARDANDO"
        block_reason = str(row.get("Codigo Rejeicao", "") or "SEM_ENTRADA_NOVA")
    elif plan_status != "PLANO_VALIDO":
        robot_status = "BLOQUEADO"
        block_reason = str(row.get("Codigo Rejeicao", "") or "SEM_PLANO")
    else:
        robot_status = "PRONTO"
        block_reason = "NENHUM"
    return {
        "Par": row.get("Par", "N/D"),
        "TF ativo": row.get("Periodo de tempo", row.get("Timeframe", "N/D")),
        "Modelo": row.get("Modelo Ativo", "N/D"),
        "Gestor saida": _demo_robot_exit_manager_label(row),
        "Plano inicial": _demo_robot_initial_risk_plan_label(row),
        "Acao PM atual": _demo_robot_position_manager_action_label(row),
        "Decisao": decision,
        "Entrada": "SIM" if entry_status == "SINAL_TEORICO" else "NAO",
        "Plano": "VALIDO" if plan_status == "PLANO_VALIDO" else "NAO",
        "Stop/Alvo": exit_plan,
        "RR": row.get("RR Research", "N/D"),
        "RR min": row.get("RR Minimo", "N/D"),
        "Status robo": robot_status,
        "Bloqueio": block_reason,
        "Proximo": row.get("Gatilho Esperado", "N/D"),
    }


def _demo_robot_exit_manager_label(row: dict[str, object]) -> str:
    beta = str(row.get("Beta Lab", "BETA001") or "BETA001").upper()
    mode = str(row.get("Modo Beta", "") or "").upper()
    if beta == "BETA002":
        return f"BETA002 ({_demo_robot_beta2_current_action(row)})"
    if mode and mode != "N/D":
        return f"{beta} ({mode})"
    return beta


def _demo_robot_beta2_current_action(row: dict[str, object]) -> str:
    action = str(row.get("Recomendacao Saida", "") or "").upper()
    pm_action = str(row.get("Acao PM atual", "") or "").upper()
    status_text = " ".join((action, pm_action))
    if "FULL_EXIT" in status_text or "EARLY_EXIT" in status_text:
        return "FULL_EXIT"
    if "PROTECT" in status_text or "STOP_MOVED" in status_text:
        return "PROTECT"
    return "HOLD"


def _demo_robot_initial_risk_plan_label(row: dict[str, object]) -> str:
    exit_model = str(row.get("Modelo Saida", "NONE") or "NONE")
    if exit_model == "NONE":
        exit_model = str(
            row.get("Gestao Stop", "POSITION_MANAGER") or "POSITION_MANAGER"
        )
    return exit_model


def _demo_robot_position_manager_action_label(row: dict[str, object]) -> str:
    action = str(row.get("Recomendacao Saida", "") or "").upper()
    market_state = str(row.get("Estado Mercado Saida", "") or "").upper()
    if action and action not in {"N/D", "KEEP_ORIGINAL_PLAN"}:
        return action
    if market_state and market_state not in {"", "N/D", "NO_POSITION"}:
        return f"HOLD_POSITION ({market_state})"
    if str(row.get("Plano Research", "") or "").upper() == "PLANO_VALIDO":
        return "AGUARDANDO_POSICAO"
    return "SEM_PLANO_ATIVO"


def _demo_robot_rejection_step_row(step: object) -> dict[str, object]:
    return {
        "Ordem": int(getattr(step, "order", 0) or 0),
        "Par": getattr(step, "symbol", "N/D"),
        "TF": getattr(step, "timeframe", "N/D"),
        "Etapa": getattr(step, "stage", "N/D"),
        "Status": getattr(step, "status", "PENDENTE"),
        "Motivo": getattr(step, "reason", "N/D"),
        "Detalhe": getattr(step, "detail", ""),
    }


def _demo_robot_status_dot_html(online_enabled: bool) -> str:
    color = "#16A34A" if online_enabled else "#DC2626"
    title = "Robo demo ligado" if online_enabled else "Robo demo desligado"
    return (
        '<span '
        f'title="{title}" '
        'style="display:inline-block;width:12px;height:12px;'
        'border-radius:50%;'
        f'background-color:{color};'
        'box-shadow:0 0 0 2px rgba(17,24,39,0.08);"'
        "></span>"
    )


def _with_demo_robot_snapshot(data: object, robot: object) -> object:
    try:
        return replace(data, demo_robot=robot)
    except TypeError:
        return data


def _demo_robot_has_visible_plan(robot: object) -> bool:
    if robot is None:
        return False
    selected_pair = str(getattr(robot, "selected_pair", "") or "").upper()
    status = str(getattr(robot, "status", "") or "").upper()
    result_status = str(getattr(robot, "result_status", "") or "").upper()
    display_entry, display_stop, display_target = _demo_robot_trade_prices(robot)
    has_pair = selected_pair not in {"", "N/D", "NONE"}
    has_prices = all(value is not None for value in (display_entry, display_stop, display_target))
    visible_statuses = {
        "ACCEPTED",
        "EXECUTED",
        "REJECTED",
        "PLANO_VALIDO",
        "AGUARDANDO_PLANO",
        "ARMED_WAITING",
        "SEM_GATILHO_VALIDO",
        "NO_SIGNAL",
    }
    return (has_pair and has_prices) or status in visible_statuses or result_status in visible_statuses


def _stable_demo_robot_snapshot(robot: object) -> object:
    if _demo_robot_has_visible_plan(robot):
        st.session_state[MT5_DEMO_ROBOT_LAST_VISIBLE_SNAPSHOT_KEY] = robot
        return robot
    previous = st.session_state.get(MT5_DEMO_ROBOT_LAST_VISIBLE_SNAPSHOT_KEY)
    if previous is not None and _demo_robot_has_visible_plan(previous):
        return previous
    return robot


def _demo_robot_online_status(data: object) -> bool:
    """Mostra o estado online confirmado na sessao.

    A leitura do backend pode chegar atrasada no mesmo rerender do Streamlit apos
    armar o robo. O ultimo comando manual do usuario manda: somente o botao
    Desarmar deve persistir o monitoramento como desligado.
    """
    session_online = bool(st.session_state.get(MT5_DEMO_ROBOT_ONLINE_KEY, False))
    if not session_online:
        return False
    return True


def _arm_all_demo_robot_from_reports(service: DashboardService, data: object) -> object:
    _enable_mt5_demo_execution_for_session()
    forex = getattr(data, "mt5_forex_signals", None)
    timeframe = getattr(forex, "timeframe", "M1")
    _record_runtime_event("DEMO_ROBOT_ARM_REQUESTED")
    armed_robot = service.arm_demo_robot(pair="TODOS", timeframe=timeframe)
    online_allowed = _demo_robot_online_allowed(armed_robot)
    st.session_state[MT5_DEMO_ROBOT_ONLINE_KEY] = True
    st.session_state[MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY] = 0.0
    _persist_demo_robot_online_state(
        online=True,
        pair="TODOS",
        timeframe=str(timeframe or "M1"),
        message=str(getattr(armed_robot, "message", "")),
    )
    if online_allowed:
        _record_runtime_event("DEMO_ROBOT_ARMED_ONLINE")
    else:
        _record_runtime_event("DEMO_ROBOT_ARM_BLOCKED")
    return armed_robot


def _run_demo_robot_online_cycle_if_due(
    service: DashboardService,
    data: object,
    *,
    selected_pair: str,
    timeframe: str,
) -> tuple[object, bool]:
    now = time.monotonic()
    last_cycle = float(
        st.session_state.get(MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY, 0.0) or 0.0
    )
    if now - last_cycle < MT5_DEMO_ROBOT_INTERVAL_SECONDS:
        _record_runtime_event("DEMO_ROBOT_ONLINE_CYCLE_SKIPPED_INTERVAL")
        return data, True

    current_robot = service.get_demo_robot_status()
    if not _demo_robot_online_allowed(current_robot):
        current_robot = service.arm_demo_robot(pair=selected_pair, timeframe=timeframe)
    if not _demo_robot_online_allowed(current_robot):
        _keep_demo_robot_online_requested(
            pair=selected_pair,
            timeframe=timeframe,
            message=(
                "Monitoramento online permanece ligado pelo ultimo comando do "
                "usuario; backend ainda indisponivel para armar neste ciclo."
            ),
        )
        return data, True

    _record_runtime_event("DEMO_ROBOT_ONLINE_CYCLE_STARTED")
    st.session_state[MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY] = now
    _sync_current_mt5_entry_filter_mode_with_service(service)
    _sync_mt5_operational_model_with_service(service)
    cycle_robot = service.run_online_demo_robot_cycle(
        pair=selected_pair,
        timeframe=timeframe,
    )
    st.session_state[MT5_DEMO_ROBOT_LAST_CYCLE_KEY] = time.strftime("%H:%M:%S")
    _record_runtime_event("DEMO_ROBOT_ONLINE_CYCLE_COMPLETED")
    if not _demo_robot_online_allowed(cycle_robot):
        _keep_demo_robot_online_requested(
            pair=selected_pair,
            timeframe=timeframe,
            message=(
                "Monitoramento online mantido pelo ultimo comando do usuario; "
                "backend bloqueou este ciclo: "
                f"{getattr(cycle_robot, 'message', 'motivo indisponivel')}"
            ),
        )
        refreshed_data = service.get_dashboard_view_model()
        refreshed_robot = _stable_demo_robot_snapshot(
            getattr(refreshed_data, "demo_robot", cycle_robot)
        )
        try:
            refreshed_data = replace(refreshed_data, demo_robot=refreshed_robot)
        except TypeError:
            pass
        return refreshed_data, True
    return _with_demo_robot_snapshot(service.get_dashboard_view_model(), cycle_robot), True


def _demo_robot_online_allowed(robot: object) -> bool:
    """Confirma se o backend aceitou manter o robo demo em monitoramento online."""
    status = str(getattr(robot, "status", "") or "").upper()
    result_status = str(getattr(robot, "result_status", "") or "").upper()
    provider = str(getattr(robot, "provider", "") or "").upper()
    mt5_send_enabled = bool(
        getattr(robot, "mt5_" + "order" + "_send_enabled", False)
    )
    if status in {"DISABLED", "DISARMED", "NOT_ARMED"}:
        return False
    if provider == "MT5_DEMO_DISABLED":
        return False
    armed_statuses = {
        "ARMED",
        "READY",
        "ARMED_WAITING",
        "AGUARDANDO_PLANO",
        "NO_SIGNAL",
        "SEM_GATILHO_VALIDO",
        "BATCH_COMPLETED",
    }
    return mt5_send_enabled and (
        status in armed_statuses or result_status in armed_statuses
    )


def _demo_robot_trade_prices(
    robot: object,
) -> tuple[object | None, object | None, object | None]:
    """Exibe precos do robo apenas quando existe plano completo ou ordem avaliada."""
    status = str(getattr(robot, "status", "") or "").upper()
    result_status = str(getattr(robot, "result_status", "") or "").upper()
    executable_statuses = {
        "ACCEPTED",
        "EXECUTED",
        "REJECTED",
        "PLANO_VALIDO",
    }
    waiting_or_invalid = {
        "AGUARDANDO_PLANO",
        "ARMED_WAITING",
        "SEM_GATILHO_VALIDO",
        "SEM_DIRECAO_EXECUTAVEL",
        "ENTRADA_INVALIDA",
        "RR_INSUFICIENTE",
        "NOT_ARMED",
        "DISARMED",
        "DISABLED",
    }
    if status in waiting_or_invalid or result_status in waiting_or_invalid:
        return None, None, None
    if result_status not in executable_statuses and status not in executable_statuses:
        return None, None, None
    entry = getattr(robot, "entry_price", None)
    stop = getattr(robot, "stop", None)
    target = getattr(robot, "target", None)
    if entry is None or stop is None or target is None:
        return None, None, None
    return entry, stop, target


def _enable_mt5_demo_execution_for_session() -> None:
    """Habilita envio MT5 apenas para conta demo na sessao atual do Streamlit."""
    os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"


def _demo_robot_audit_row(row: object) -> dict[str, object]:
    return {
        "Horario": getattr(row, "timestamp", "N/D"),
        "Par": getattr(row, "symbol", "N/D"),
        "Lado": getattr(row, "side", "N/D"),
        "Quantidade": getattr(row, "quantity", 0),
        "Alpha": getattr(row, "alpha_id", "N/D"),
        "Versao Alpha": getattr(row, "alpha_version", "N/D"),
        "Beta": getattr(row, "beta_id", "BETA001"),
        "Versao Beta": getattr(row, "beta_version", "BETA v1"),
        "Modo Beta": getattr(row, "beta_mode", "PROTECT_ONLY"),
        "Versao politica sessao": getattr(row, "session_policy_version", "N/D"),
        "Versao pipeline execucao": getattr(row, "execution_pipeline_version", "N/D"),
        "Versao config Lab": getattr(row, "lab_configuration_version", "N/D"),
        "Versao Trade Plan": getattr(row, "trade_plan_version", "N/D"),
        "Versao motor execucao": getattr(row, "execution_engine_version", "N/D"),
        "Versao indicadores": getattr(row, "indicator_bundle_version", "N/D"),
        "Versao microestrutura": getattr(row, "microstructure_version", "N/D"),
        "Versao validacao": getattr(row, "validation_pipeline_version", "N/D"),
        "Versao estrategia": getattr(row, "strategy_definition_version", "N/D"),
        "Score Tecnico": _optional_percent(
            getattr(row, "technical_score", 0.0)
        ),
        "Confirmacao Historica": _optional_percent(
            getattr(row, "historical_confirmation", 0.0)
        ),
        "Entrada": _optional_price(getattr(row, "entry_price", None)),
        "Stop": _optional_price(getattr(row, "stop", None)),
        "Alvo": _optional_price(getattr(row, "target", None)),
        "RR": _optional_number(getattr(row, "risk_reward", None)),
        "Candle Gatilho": getattr(row, "candle_time", "N/D"),
        "Sessao Forex": getattr(row, "forex_session", "N/D"),
        "Mercado aberto": _forex_market_session_status(row),
        "Filtro sessao": "LIGADO"
        if bool(getattr(row, "session_filter_enabled", True))
        else "IGNORADO",
        "Resultado sessao": getattr(row, "session_filter_result", "N/D"),
        "Motivo sessao": getattr(row, "session_reason", "N/D"),
        "Horario UTC": getattr(row, "timestamp_utc", "N/D"),
        "Horario local": getattr(row, "timestamp_brt", "N/D"),
        "Dia semana": getattr(row, "weekday", "N/D"),
        "Rollover": bool(getattr(row, "is_rollover", False)),
        "Overlap Londres NY": bool(getattr(row, "is_london_ny_overlap", False)),
        "Abertura semanal": bool(getattr(row, "is_sunday_open", False)),
        "Fechamento semanal": bool(getattr(row, "is_friday_late", False)),
        "Aceito": bool(getattr(row, "accepted", False)),
        "Status": getattr(row, "status", "N/D"),
        "Mensagem": getattr(row, "message", "N/D"),
        "Ticket": getattr(row, "ticket", None),
        "Posicao MT5": getattr(row, "mt5_position", "N/D"),
    }


def _exibir_entradas_teoricas_mt5(
    rows: list[dict[str, object]],
    *,
    robot_online: bool = False,
    mt5_status: object = "N/D",
    operational_model: str = MT5_OPERATIONAL_MODEL_1,
) -> None:
    """Exibe radar read-only de entrada teorica fora da grade virtualizada."""
    st.markdown(
        (
            "<div class='traderia-status-legend'>"
            "<span class='traderia-legend-ok'>OK</span>"
            "<span class='traderia-legend-wait'>Aguardando encaixe</span>"
            "<span class='traderia-legend-blocked'>Bloqueado/Rejeitado</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    mt5_online = _mt5_connection_online(mt5_status)
    st.subheader("Entrada Teorica MT5 - Modelo 1 atual")
    st.caption(
        "Alpha segue o proprio sinal. Tabela sempre visivel para conferencia; "
        "envia ordem somente quando Modelo 1 ou Todos estiver selecionado."
    )
    _render_stable_readonly_table(
        [
            _forex_theoretical_entry_row(
                row,
                robot_online=robot_online,
                mt5_online=mt5_online,
                execution_enabled=_mt5_operational_model_enabled(
                    operational_model,
                    MT5_OPERATIONAL_MODEL_1,
                ),
                operational_model=MT5_OPERATIONAL_MODEL_1,
            )
            for row in rows
        ],
        model_column="Modelo ativo",
        decision_column="Direcao",
        color_status_cells=True,
    )
    st.subheader("Entrada Teorica MT5 - Modelo 2 espelho BETA2")
    st.caption(
        "Modelo experimental: inverte BUY/SELL da Alpha, usa o stop original "
        "como alvo e calcula stop simetrico com RR 1. Tabela sempre visivel "
        "para conferencia; envia ordem somente quando Modelo 2 ou Todos estiver "
        "selecionado."
    )
    _render_stable_readonly_table(
        [
            _forex_theoretical_entry_row(
                _model2_inverse_entry_row(row),
                robot_online=robot_online,
                mt5_online=mt5_online,
                execution_enabled=_mt5_operational_model_enabled(
                    operational_model,
                    MT5_OPERATIONAL_MODEL_2,
                ),
                model2_filter_trigger=True,
                operational_model=MT5_OPERATIONAL_MODEL_2,
            )
            for row in rows
        ],
        model_column="Modelo ativo",
        decision_column="Direcao",
        color_status_cells=True,
    )
    _exibir_entrada_teorica_mt5_rr3_experimental(
        rows,
        robot_online=robot_online,
        mt5_online=mt5_online,
        execution_enabled=_mt5_operational_model_enabled(
            operational_model,
            MT5_OPERATIONAL_MODEL_3,
        ),
    )
    st.subheader("Entrada Teorica MT5 - Modelo 4 espelho M1")
    st.caption(
        "Modelo espelho do M1: copia o plano vencedor do Lab sem recalcular, "
        "inverte BUY/SELL, usa o stop original como alvo e o alvo original "
        "como stop. Tabela sempre visivel para conferencia; envia ordem somente "
        "quando Modelo 4 ou Todos estiver selecionado."
    )
    _render_stable_readonly_table(
        [
            _forex_theoretical_entry_row(
                _model4_inverse_entry_row(row),
                robot_online=robot_online,
                mt5_online=mt5_online,
                execution_enabled=_mt5_operational_model_enabled(
                    operational_model,
                    MT5_OPERATIONAL_MODEL_4,
                ),
                operational_model=MT5_OPERATIONAL_MODEL_4,
            )
            for row in rows
        ],
        model_column="Modelo ativo",
        decision_column="Direcao",
        color_status_cells=True,
    )
    st.subheader("Entrada Teorica MT5 - Modelo 5 Price Action")
    st.caption(
        "Fluxo proprio M5: estrutura, expansao/retracao aproximada pela zona, "
        "confirmacao viva, stop estrutural e alvo estrutural/projecao."
    )
    _render_stable_readonly_table(
        [
            _forex_theoretical_entry_row(
                _model5_price_action_entry_row(row),
                robot_online=robot_online,
                mt5_online=mt5_online,
                execution_enabled=_mt5_operational_model_enabled(
                    operational_model,
                    MT5_OPERATIONAL_MODEL_5,
                ),
                operational_model=MT5_OPERATIONAL_MODEL_5,
            )
            for row in rows
        ],
        model_column="Modelo ativo",
        decision_column="Direcao",
        color_status_cells=True,
    )
    st.subheader("Entrada Teorica MT5 - Modelo 6 espelho M5")
    st.caption(
        "Modelo espelho do M5: calcula o Price Action do M5, inverte BUY/SELL, "
        "usa o stop original do M5 como alvo e o alvo original do M5 como stop."
    )
    _render_stable_readonly_table(
        [
            _forex_theoretical_entry_row(
                _model6_inverse_price_action_entry_row(row),
                robot_online=robot_online,
                mt5_online=mt5_online,
                execution_enabled=_mt5_operational_model_enabled(
                    operational_model,
                    MT5_OPERATIONAL_MODEL_6,
                ),
                operational_model=MT5_OPERATIONAL_MODEL_6,
            )
            for row in rows
        ],
        model_column="Modelo ativo",
        decision_column="Direcao",
        color_status_cells=True,
    )


def _exibir_entrada_teorica_mt5_rr3_experimental(
    rows: list[dict[str, object]],
    *,
    robot_online: bool = False,
    mt5_online: bool = False,
    execution_enabled: bool = False,
) -> None:
    """Mostra o fluxo M3 RR3 com os mesmos gates visuais de M1/M2."""
    st.subheader("Entrada Teorica MT5 - M3 RR3")
    st.caption(
        "Fluxo proprio M3: acompanha candidatos RR3 do snapshot separado com "
        "as mesmas etapas visuais de envio usadas em M1/M2."
    )
    payload = _load_rr3_experimental_snapshot_payload()
    if payload is None:
        st.info(
            "Snapshot RR3 experimental ainda nao encontrado. Gere pelo Lab em "
            "'Gerar snapshot RR3 experimental'."
        )
        return
    rows_by_pair = {
        str(row.get("Par", "") or "").upper(): row
        for row in rows
        if str(row.get("Par", "") or "").strip()
    }
    candidates = _rr3_experimental_mt5_rows(
        payload,
        rows_by_pair,
        robot_online=robot_online,
        mt5_online=mt5_online,
        execution_enabled=execution_enabled,
    )
    if not candidates:
        st.info(
            "Nenhum candidato RR3 passou nos criterios minimos de leitura "
            "experimental."
        )
        return
    _render_stable_readonly_table(
        candidates,
        model_column="Modelo ativo",
        decision_column="Direcao",
        color_status_cells=True,
    )


def _load_rr3_experimental_snapshot_payload() -> dict[str, object] | None:
    try:
        return json.loads(
            MT5_LAB_RR3_EXPERIMENTAL_SNAPSHOT_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None


def _rr3_experimental_mt5_rows(
    payload: dict[str, object],
    current_rows_by_pair: dict[str, dict[str, object]],
    *,
    robot_online: bool = False,
    mt5_online: bool = False,
    execution_enabled: bool = False,
) -> list[dict[str, object]]:
    scenarios = _rr3_experimental_best_scenarios_by_pair(payload)
    result: list[dict[str, object]] = []
    for scenario in scenarios:
        result.append(
            _rr3_experimental_theoretical_entry_row(
                scenario,
                current_rows_by_pair,
                robot_online=robot_online,
                mt5_online=mt5_online,
                execution_enabled=execution_enabled,
            )
        )
    return result


def _rr3_experimental_best_scenarios_by_pair(
    payload: dict[str, object],
) -> list[dict[str, object]]:
    source = [
        scenario
        for scenario in list(payload.get("scenario_ranking", []) or [])
        if isinstance(scenario, dict)
    ]
    if not source:
        source = [
            scenario
            for scenario in list(payload.get("best_scenarios_by_market", []) or [])
            if isinstance(scenario, dict)
        ]
    best_by_pair: dict[str, dict[str, object]] = {}
    for scenario in source:
        pair = str(scenario.get("pair", "") or "").upper()
        if not pair:
            continue
        parameters = dict(scenario.get("parameters", {}) or {})
        if _safe_float_or_none(parameters.get("rr")) != 3.0:
            continue
        current = best_by_pair.get(pair)
        if current is None or _rr3_experimental_runtime_rank(
            scenario,
        ) > _rr3_experimental_runtime_rank(current):
            best_by_pair[pair] = scenario
    return sorted(
        best_by_pair.values(),
        key=lambda scenario: str(scenario.get("pair", "")),
    )


def _rr3_experimental_runtime_rank(
    scenario: dict[str, object],
) -> tuple[bool, bool, bool, float, int, float, float]:
    status_ok = str(scenario.get("status", "") or "").upper() == "APROVADO"
    sample = int(_safe_float_or_none(scenario.get("lab_confidence_sample_size")) or 0)
    profit_factor = _safe_float_or_none(
        scenario.get("lab_confidence_profit_factor")
    ) or 0.0
    confidence = _safe_float_or_none(scenario.get("lab_confidence")) or 0.0
    score = _safe_float_or_none(scenario.get("score")) or 0.0
    return (
        status_ok,
        status_ok,
        sample > 0,
        confidence,
        sample,
        profit_factor,
        score,
    )


def _rr3_experimental_theoretical_entry_row(
    scenario: dict[str, object],
    current_rows_by_pair: dict[str, dict[str, object]],
    *,
    robot_online: bool = False,
    mt5_online: bool = False,
    execution_enabled: bool = False,
) -> dict[str, object]:
    pair = str(scenario.get("pair", "N/D") or "N/D").upper()
    current_row = dict(current_rows_by_pair.get(pair, {}))
    gate, reason = _rr3_experimental_gate(scenario)
    parameters = dict(scenario.get("parameters", {}) or {})
    direction = str(scenario.get("decision", "WAIT") or "WAIT").upper()
    live_direction = str(current_row.get("Direcao Teorica", "WAIT") or "WAIT").upper()
    live_trigger = str(current_row.get("Entrada Teorica", "") or "").upper()
    signal_gate = (
        "OK"
        if gate == "OK"
        and direction in {"BUY", "SELL"}
        and live_direction == direction
        and live_trigger == "SINAL_TEORICO"
        else "AGUARDA: sinal atual nao confirmou M3"
    )
    plan_gate = "OK" if gate == "OK" else gate
    zone_gate = _entry_zone_gate(current_row)
    robot_gate = _entry_robot_gate(robot_online)
    mt5_gate = _entry_mt5_gate(mt5_online)
    filter_gate = "OK: RR3" if gate == "OK" else gate
    regime_row = dict(current_row)
    regime_row["Direcao Teorica"] = direction
    regime_gate = _entry_regime_gate(regime_row)
    duplicate_gate = _entry_duplicate_gate(
        {
            **current_row,
            "Par": pair,
            "Periodo de tempo": scenario.get("timeframe", "N/D"),
            "Direcao Teorica": direction,
            "Preco Teorico": current_row.get("Preco Teorico", "N/D"),
            "Stop Research": current_row.get("Stop Research", "N/D"),
            "Alvo Research": current_row.get("Alvo Research", "N/D"),
            "Alpha Lab": scenario.get("alpha_id", "N/D"),
            "Modelo Saida": scenario.get("beta_id", "N/D"),
        },
        operational_model=MT5_OPERATIONAL_MODEL_3,
    )
    price_gate = (
        "OK"
        if signal_gate == "OK" and plan_gate == "OK"
        else "AGUARDA: M3 aguardando encaixe"
    )
    position_gate = _entry_position_gate(current_row)
    send_gate = _entry_send_gate(
        entry_gate=signal_gate,
        plan_gate=plan_gate,
        zone_gate=zone_gate,
        robot_gate=robot_gate,
        mt5_gate=mt5_gate,
        filter_gate=filter_gate,
        duplicate_gate=duplicate_gate,
        regime_gate=regime_gate,
        price_gate=price_gate,
        position_gate=position_gate,
    )
    if not execution_enabled:
        send_gate = "MONITOR: outro modelo"
    sample = int(_safe_float_or_none(scenario.get("lab_confidence_sample_size")) or 0)
    return {
        "Par": pair,
        "Timeframe": scenario.get("timeframe", "N/D"),
        "Envio resumo": send_gate,
        "Duplicidade": duplicate_gate,
        "Sinal": signal_gate,
        "Plano": plan_gate,
        "Zona gate": zone_gate,
        "Robo": robot_gate,
        "MT5": mt5_gate,
        "Filtro": filter_gate,
        "Regime": regime_gate,
        "Plano vigente": price_gate,
        "Posicao": position_gate,
        "Envio": send_gate,
        "Alpha": scenario.get("alpha_id", "N/D"),
        "Beta": scenario.get("beta_id", "N/D"),
        "Setup M3": scenario.get("model", "N/D"),
        "Config vencedora": _scenario_parameters_label(parameters),
        "Posicao aberta": "SIM"
        if _entry_open_position_side(current_row) != "N/D"
        else "NAO",
        "Direcao posicao": _entry_open_position_side(current_row),
        "Alpha posicao": _entry_open_position_alpha(current_row),
        "Sinal teorico atual": live_direction,
        "Confere posicao": _entry_position_theoretical_match(
            _entry_open_position_side(current_row),
            direction,
        ),
        "Modelo ativo": scenario.get("model", "N/D"),
        "Zona": current_row.get("Zona Operacional", "N/D"),
        "Suporte": current_row.get("Suporte", "N/D"),
        "Resistencia": current_row.get("Resistencia", "N/D"),
        "Pivot": current_row.get("Pivot", "N/D"),
        "Entrada Teorica": "SINAL_TEORICO" if signal_gate == "OK" else live_trigger or "SEM_GATILHO",
        "Candle do Sinal": current_row.get("Candle do Sinal", "N/D"),
        "Preco Teorico": current_row.get("Preco Teorico", "N/D"),
        "Direcao": direction,
        "Plano Research": "PLANO_VALIDO" if plan_gate == "OK" else "M3_AGUARDANDO",
        "Codigo Rejeicao": "N/D" if plan_gate == "OK" else reason,
        "Stop Research": current_row.get("Stop Research", "N/D"),
        "Alvo Research": current_row.get("Alvo Research", "N/D"),
        "RR Research": parameters.get("rr", "N/D"),
        "RR Minimo": 3.0,
        "Score": _optional_number(scenario.get("score")),
        "Confirmacao": _optional_percent(scenario.get("lab_confidence")),
        "Amostra": sample,
        "PF": _optional_number(scenario.get("lab_confidence_profit_factor")),
        "Modelo Saida": scenario.get("beta_id", "N/D"),
        "Motivo": reason,
    }


def _rr3_experimental_gate(scenario: dict[str, object]) -> tuple[str, str]:
    score = _safe_float_or_none(scenario.get("score")) or 0.0
    confidence = _safe_float_or_none(scenario.get("lab_confidence")) or 0.0
    sample = int(
        _safe_float_or_none(scenario.get("lab_confidence_sample_size")) or 0
    )
    profit_factor = (
        _safe_float_or_none(scenario.get("lab_confidence_profit_factor")) or 0.0
    )
    parameters = dict(scenario.get("parameters", {}) or {})
    rr = _safe_float_or_none(parameters.get("rr"))
    if rr != 3.0:
        return "BLOQ: RR diferente de 3", f"RR do cenario={rr or 'N/D'}."
    status = str(scenario.get("status", "") or "").upper()
    if status != "APROVADO":
        return "BLOQ: status RR3", f"Status RR3 {status or 'N/D'}."
    return (
        "OK",
        "Cenario vencedor RR3 aprovado; "
        f"amostra={sample}, PF={profit_factor:.2f}, "
        f"confirmacao={confidence:.2%}, score={score:.2f}.",
    )


def _exibir_saidas_teoricas_mt5(
    service: DashboardService,
    report: object | None,
    forex_rows: list[dict[str, object]],
) -> None:
    """Exibe leitura teorica do BETA002 somente para posicoes abertas."""
    st.subheader("Saida Teorica MT5")
    st.caption(
        "Somente leitura: acompanha posicoes abertas usando o modelo registrado "
        "na ordem. Modelo 1 mostra a saida do Lab; Modelo 2 mostra TP da BETA2 "
        "invertida e loss em RR1, conforme definido por voce."
    )
    st.markdown(
        (
            "<div class='traderia-status-legend'>"
            "<span class='traderia-legend-model1'>Modelo 1 / M1</span>"
            "<span class='traderia-legend-model2'>Modelo 2 / M2</span>"
            "<span class='traderia-legend-model3'>Modelo 3 / M3</span>"
            "<span class='traderia-legend-model4'>Modelo 4 / M4</span>"
            "<span class='traderia-legend-model5'>Modelo 5 / M5</span>"
            "<span class='traderia-legend-model6'>Modelo 6 / M6</span>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    if report is None:
        report = _load_mt5_trade_audit_report_locked(service)
        if report is not None:
            st.session_state[MT5_REPORT_AUDIT_CACHE_KEY] = report
    if report is None:
        st.info("Auditoria MT5 ainda nao carregada; aguardando proximo ciclo leve.")
        return
    open_rows = [
        row
        for row in list(getattr(report, "rows", []) or [])
        if _is_mt5_open_operation(row) and _is_valid_mt5_theoretical_exit_row(row)
    ]
    if not open_rows:
        refreshed_report = _load_mt5_trade_audit_report_locked(service)
        if refreshed_report is not None:
            st.session_state[MT5_REPORT_AUDIT_CACHE_KEY] = refreshed_report
            open_rows = [
                row
                for row in list(getattr(refreshed_report, "rows", []) or [])
                if _is_mt5_open_operation(row)
                and _is_valid_mt5_theoretical_exit_row(row)
            ]
    if not open_rows:
        st.info("Nenhuma posicao aberta no MT5 para acompanhar saida teorica.")
        return
    signal_by_pair = {
        str(row.get("Par", "") or "").upper(): row
        for row in forex_rows
        if str(row.get("Par", "") or "").strip()
    }
    fallback_operational_model = _sync_mt5_operational_model_with_service(service)
    rows = [
        _mt5_theoretical_exit_row(
            row,
            signal_by_pair,
            display_model=_mt5_theoretical_exit_effective_model(
                row,
                fallback_operational_model,
            ),
        )
        for row in _sorted_mt5_rows_like_mt5(open_rows)
    ]
    _render_mt5_theoretical_exit_table(rows)


def _is_valid_mt5_theoretical_exit_row(row: object) -> bool:
    """Evita saldo/linhas N/D na leitura teorica de saida."""
    symbol = str(getattr(row, "symbol", "") or "").upper()
    mt5_symbol = str(getattr(row, "mt5_symbol", "") or "").upper()
    if symbol in {"", "N/D", "NONE"} and mt5_symbol in {"", "N/D", "NONE"}:
        return False
    return bool(
        getattr(row, "mt5_ticket", None)
        or getattr(row, "local_ticket", None)
        or mt5_symbol not in {"", "N/D", "NONE"}
    )


def _mt5_theoretical_exit_row(
    row: object,
    signal_by_pair: dict[str, dict[str, object]],
    *,
    display_model: str | None = None,
) -> dict[str, object]:
    """Linha compacta da leitura de saida para posicao aberta."""
    pair = str(getattr(row, "symbol", "N/D") or "N/D").upper()
    signal = signal_by_pair.get(pair, {})
    scenario = _mt5_theoretical_exit_scenario(row)
    effective_model = _mt5_theoretical_exit_effective_model(
        row,
        str(display_model or MT5_OPERATIONAL_MODEL_1),
    )
    display_signal = _mt5_theoretical_exit_display_signal(signal, effective_model)
    entry_timeframe = _mt5_trade_row_timeframe(row) or _mt5_signal_timeframe(
        display_signal,
        signal,
    )
    model_label = _mt5_sender_model_label(row, effective_model)
    return {
        "Par": pair,
        "Lado": _mt5_theoretical_exit_side_label(row, display_signal, effective_model),
        "Modelo": model_label,
        "TF Entrada Lab": entry_timeframe,
        "TF Saida Beta": _mt5_beta_exit_timeframe(
            row,
            entry_timeframe,
        ),
        "Alpha": _mt5_trade_row_text(row, "alpha_id", "alpha_id", "alpha") or str(
            signal.get("Alpha Lab", "N/D")
        ),
        "Modelo entrada": _mt5_theoretical_exit_entry_model_label(row, display_signal),
        "Beta": _mt5_theoretical_exit_beta_label(row, signal, effective_model),
        "Modelo saida": _mt5_theoretical_exit_model_label(
            row,
            display_signal,
            effective_model,
        ),
        "Cenario BETA002": _mt5_theoretical_exit_scenario_label(scenario, effective_model),
        "Gestao stop": _mt5_theoretical_exit_stop_management_label(row, effective_model),
        "Movimento SL": _mt5_theoretical_exit_stop_movement_label(row, effective_model),
        "Modelo envio": model_label,
        "Stop inicial": _optional_price(
            _mt5_theoretical_exit_stop_value(row, display_signal, effective_model)
        ),
        "Stop atual": _optional_price(getattr(row, "mt5_stop", None)),
        "Stop candidato": _optional_price(
            _mt5_theoretical_exit_candidate_stop(row, effective_model)
        ),
        "Acao PM": str(getattr(row, "position_manager_action", "N/D")),
        "Status PM": str(getattr(row, "position_manager_status", "N/D")),
        "R atual": _optional_number(getattr(row, "dynamic_exit_r_multiple", None)),
        "Score forca": _optional_number(getattr(row, "beta_strength_score", None)),
        "Confirmacoes": int(getattr(row, "beta_confirmation_count", 0) or 0),
        "Duracao": int(getattr(row, "beta_state_duration", 0) or 0),
        "EMA14": _optional_price(getattr(row, "beta_ema14_value", None)),
        "Slope EMA14": _optional_number(getattr(row, "beta_ema14_slope", None)),
        "Momentum14": _optional_number(getattr(row, "beta_momentum_14", None)),
        "ATR14": _optional_number(getattr(row, "beta_atr_14", None)),
        "ATR relativo": _optional_percent(
            getattr(row, "beta_atr_relative_change", None)
        ),
        "Estrutura": str(getattr(row, "beta_structure_signal", "N/D")),
        "Preco atual": _optional_price(getattr(row, "mt5_price", None)),
        "Entrada": _optional_price(getattr(row, "entry_price", None)),
        "Alvo": _optional_price(
            _mt5_theoretical_exit_target_value(row, display_signal, effective_model)
        ),
        "Execucao": (
            "AUTORIZADA"
            if bool(getattr(row, "dynamic_exit_allowed_to_execute_demo", False))
            else "READ_ONLY"
        ),
        "Ultimo candle fechado": _friendly_candle_time(
            getattr(row, "beta_closed_candle_time", "N/D")
        ),
        "Horario leitura": _friendly_candle_time(
            getattr(row, "beta_evaluated_at", "N/D")
        ),
        "Leitura programada": _mt5_theoretical_exit_programming_label(row),
        "Motivo": _mt5_trade_audit_position_manager_message(row),
    }


def _mt5_signal_timeframe(
    primary: dict[str, object],
    fallback: dict[str, object] | None = None,
) -> str:
    """Retorna o timeframe ja transformado pelo modelo operacional."""
    for source in (primary, fallback or {}):
        for key in (
            "Periodo de tempo",
            "Período de tempo",
            "PerÃ­odo de tempo",
            "Timeframe",
            "TF",
        ):
            value = str(source.get(key, "") or "").strip().upper()
            if value and value not in {"N/D", "NONE"}:
                return value
    return "N/D"


def _mt5_trade_row_timeframe(row: object) -> str:
    """Prioriza o timeframe gravado na ordem/ticket aberto."""
    for value in (
        getattr(row, "timeframe", None),
        getattr(row, "lab_timeframe", None),
    ):
        text = str(value or "").strip().upper()
        if text and text not in {"N/D", "NONE"}:
            return text
    snapshot = getattr(row, "plan_snapshot", None)
    if isinstance(snapshot, dict):
        text = str(snapshot.get("timeframe", "") or "").strip().upper()
        if text and text not in {"N/D", "NONE"}:
            return text
    return ""


def _mt5_trade_plan_snapshot(row: object) -> dict[str, object]:
    snapshot = getattr(row, "plan_snapshot", None)
    if isinstance(snapshot, dict):
        return snapshot
    return {}


def _mt5_trade_row_text(
    row: object,
    attr: str,
    *snapshot_keys: str,
) -> str:
    """Prioriza texto salvo no plano da ordem aberta; sinal vivo e fallback."""
    text = str(getattr(row, attr, "") or "").strip()
    if text and text.upper() not in {"N/D", "NONE", "NULL"}:
        return text
    snapshot = _mt5_trade_plan_snapshot(row)
    for key in snapshot_keys:
        text = str(snapshot.get(key, "") or "").strip()
        if text and text.upper() not in {"N/D", "NONE", "NULL"}:
            return text
    return ""


def _mt5_trade_row_price(
    row: object,
    attr: str,
    *snapshot_keys: str,
) -> float | None:
    """Prioriza preco salvo no plano da ordem aberta; sinal vivo fica fallback."""
    value = _safe_float_or_none(getattr(row, attr, None))
    if value is not None:
        return value
    snapshot = _mt5_trade_plan_snapshot(row)
    for key in snapshot_keys:
        value = _safe_float_or_none(snapshot.get(key))
        if value is not None:
            return value
    return None


def _mt5_theoretical_exit_has_recorded_model(row: object) -> bool:
    return str(getattr(row, "operational_model", "") or "").upper() in {
        MT5_OPERATIONAL_MODEL_1,
        MT5_OPERATIONAL_MODEL_2,
        MT5_OPERATIONAL_MODEL_3,
        MT5_OPERATIONAL_MODEL_4,
        MT5_OPERATIONAL_MODEL_5,
    }


def _mt5_theoretical_exit_effective_model(
    row: object,
    fallback_model: str = MT5_OPERATIONAL_MODEL_1,
) -> str:
    """Usa o modelo gravado na ordem; fallback apenas para posicao legada."""
    row_model = str(getattr(row, "operational_model", "") or "").upper()
    if row_model in {
        MT5_OPERATIONAL_MODEL_1,
        MT5_OPERATIONAL_MODEL_2,
        MT5_OPERATIONAL_MODEL_3,
        MT5_OPERATIONAL_MODEL_4,
        MT5_OPERATIONAL_MODEL_5,
        MT5_OPERATIONAL_MODEL_6,
    }:
        return row_model
    fallback = str(fallback_model or MT5_OPERATIONAL_MODEL_1).upper()
    if fallback in {
        MT5_OPERATIONAL_MODEL_1,
        MT5_OPERATIONAL_MODEL_2,
        MT5_OPERATIONAL_MODEL_3,
        MT5_OPERATIONAL_MODEL_4,
        MT5_OPERATIONAL_MODEL_5,
        MT5_OPERATIONAL_MODEL_6,
    }:
        return fallback
    return MT5_OPERATIONAL_MODEL_1


def _mt5_theoretical_exit_display_signal(
    signal: dict[str, object],
    display_model: str,
) -> dict[str, object]:
    if display_model == MT5_OPERATIONAL_MODEL_2 and signal:
        return _model2_inverse_entry_row(signal, require_filter_trigger=False)
    if display_model == MT5_OPERATIONAL_MODEL_4 and signal:
        return _model4_inverse_entry_row(signal)
    if display_model == MT5_OPERATIONAL_MODEL_5 and signal:
        return _model5_price_action_entry_row(signal)
    if display_model == MT5_OPERATIONAL_MODEL_6 and signal:
        return _model6_inverse_price_action_entry_row(signal)
    return signal


def _mt5_theoretical_exit_side_label(
    row: object,
    display_signal: dict[str, object],
    display_model: str,
) -> str:
    del display_signal, display_model
    side = str(getattr(row, "mt5_side", None) or getattr(row, "side", "N/D")).upper()
    if side in {"BUY", "COMPRAR", "COMPRA"}:
        return "COMPRAR"
    if side in {"SELL", "VENDER", "VENDA"}:
        return "VENDER"
    return side if side not in {"", "NONE"} else "N/D"


def _mt5_theoretical_exit_stop_value(
    row: object,
    display_signal: dict[str, object],
    display_model: str,
) -> float | None:
    if _mt5_theoretical_exit_has_recorded_model(row):
        row_stop = _mt5_trade_row_price(row, "stop", "stop", "initial_stop", "stop_loss")
        if row_stop is not None:
            return row_stop
    if display_model == MT5_OPERATIONAL_MODEL_2 and display_signal:
        return _price_from_display(display_signal.get("Stop Research"))
    if display_model == MT5_OPERATIONAL_MODEL_4 and display_signal:
        return _price_from_display(display_signal.get("Stop Research"))
    if display_model == MT5_OPERATIONAL_MODEL_5 and display_signal:
        return _price_from_display(display_signal.get("Stop Research"))
    if display_model == MT5_OPERATIONAL_MODEL_6 and display_signal:
        return _price_from_display(display_signal.get("Stop Research"))
    return _mt5_trade_row_price(row, "stop", "stop", "initial_stop", "stop_loss")


def _mt5_theoretical_exit_target_value(
    row: object,
    display_signal: dict[str, object],
    display_model: str,
) -> float | None:
    if _mt5_theoretical_exit_has_recorded_model(row):
        row_target = _mt5_trade_row_price(
            row,
            "target",
            "target",
            "take_profit",
            "alvo",
        )
        if row_target is not None:
            return row_target
    if display_model == MT5_OPERATIONAL_MODEL_2 and display_signal:
        return _price_from_display(display_signal.get("Alvo Research"))
    if display_model == MT5_OPERATIONAL_MODEL_4 and display_signal:
        return _price_from_display(display_signal.get("Alvo Research"))
    if display_model == MT5_OPERATIONAL_MODEL_5 and display_signal:
        return _price_from_display(display_signal.get("Alvo Research"))
    if display_model == MT5_OPERATIONAL_MODEL_6 and display_signal:
        return _price_from_display(display_signal.get("Alvo Research"))
    return _mt5_trade_row_price(row, "target", "target", "take_profit", "alvo")


def _mt5_theoretical_exit_candidate_stop(
    row: object,
    display_model: str,
) -> float | None:
    if display_model == MT5_OPERATIONAL_MODEL_2:
        return None
    if display_model == MT5_OPERATIONAL_MODEL_4:
        return None
    if display_model == MT5_OPERATIONAL_MODEL_5:
        return _safe_float_or_none(getattr(row, "dynamic_exit_candidate_stop", None))
    if display_model == MT5_OPERATIONAL_MODEL_6:
        return None
    return _safe_float_or_none(getattr(row, "dynamic_exit_candidate_stop", None))


def _mt5_theoretical_exit_scenario_label(
    scenario: str,
    display_model: str,
) -> str:
    if display_model == MT5_OPERATIONAL_MODEL_2:
        return "TARGET_STOP_ORIGINAL_RR1"
    if display_model == MT5_OPERATIONAL_MODEL_4:
        return "ESPELHO_M1_STOP_ALVO_TROCADOS"
    if display_model == MT5_OPERATIONAL_MODEL_5:
        return "PRICE_ACTION_ESTRUTURAL"
    if display_model == MT5_OPERATIONAL_MODEL_6:
        return "ESPELHO_M5_STOP_ALVO_TROCADOS"
    return scenario


def _mt5_theoretical_exit_stop_management_label(
    row: object,
    display_model: str = MT5_OPERATIONAL_MODEL_1,
) -> str:
    """Classifica a gestao do stop com linguagem operacional curta."""
    if display_model == MT5_OPERATIONAL_MODEL_2:
        return "FIXO_STOP_ORIGINAL_RR1"
    if display_model == MT5_OPERATIONAL_MODEL_4:
        return "FIXO_ESPELHO_M1"
    if display_model == MT5_OPERATIONAL_MODEL_5:
        return "ESTRUTURAL_PRICE_ACTION"
    if display_model == MT5_OPERATIONAL_MODEL_6:
        return "FIXO_ESPELHO_M5"
    if _mt5_theoretical_exit_stop_moved(row):
        return "SL MOVIDO"
    if getattr(row, "dynamic_exit_candidate_stop", None) is not None:
        return "CANDIDATO"
    beta = str(getattr(row, "beta_id", "BETA001") or "BETA001").upper()
    policy = str(getattr(row, "dynamic_exit_policy", "") or "").upper()
    if beta == "BETA002" or policy not in {"", "N/D", "NONE", "FIXED_STOP"}:
        return "MONITORANDO"
    return "INICIAL"


def _mt5_theoretical_exit_stop_movement_label(
    row: object,
    display_model: str = MT5_OPERATIONAL_MODEL_1,
) -> str:
    if display_model == MT5_OPERATIONAL_MODEL_2:
        return "FIXO"
    if display_model == MT5_OPERATIONAL_MODEL_4:
        return "FIXO"
    if display_model == MT5_OPERATIONAL_MODEL_5:
        if _mt5_theoretical_exit_stop_moved(row):
            return "JA_MOVEU"
        return "AGUARDA_PIVO"
    if display_model == MT5_OPERATIONAL_MODEL_6:
        return "FIXO"
    if _mt5_theoretical_exit_stop_moved(row):
        return "JA_MOVEU"
    if getattr(row, "dynamic_exit_candidate_stop", None) is not None:
        return "PODE_MOVER"
    return "NAO_MOVEU"


def _mt5_theoretical_exit_beta_label(
    row: object,
    signal: dict[str, object],
    display_model: str = MT5_OPERATIONAL_MODEL_1,
) -> str:
    row_beta = _mt5_trade_row_text(row, "beta_id", "beta_id", "beta")
    if row_beta and _mt5_theoretical_exit_has_recorded_model(row):
        return row_beta.upper()
    if display_model == MT5_OPERATIONAL_MODEL_2:
        return "BETA002"
    if display_model == MT5_OPERATIONAL_MODEL_4:
        return "BETA004"
    if display_model == MT5_OPERATIONAL_MODEL_5:
        return "BETAPRICE5"
    if display_model == MT5_OPERATIONAL_MODEL_6:
        return "BETAPRICE6"
    signal_beta = str(signal.get("Beta Lab", "") or "").upper()
    return row_beta.upper() or signal_beta or "BETA001"


def _mt5_theoretical_exit_entry_model_label(
    row: object,
    signal: dict[str, object],
) -> str:
    for value in (
        getattr(row, "entry_setup", None),
        getattr(row, "active_model", None),
        _mt5_trade_row_text(row, "entry_setup", "entry_setup", "active_model", "setup"),
        signal.get("Modelo Ativo"),
        signal.get("Setup entrada"),
    ):
        text = str(value or "").strip()
        if text and text.upper() not in {"N/D", "NONE"}:
            return text
    return "N/D"


def _mt5_theoretical_exit_model_label(
    row: object,
    signal: dict[str, object],
    display_model: str = MT5_OPERATIONAL_MODEL_1,
) -> str:
    if display_model == MT5_OPERATIONAL_MODEL_2:
        return "BETA002_ESPELHO_STOP_RR1"
    if display_model == MT5_OPERATIONAL_MODEL_4:
        return "BETA004_ESPELHO_M1"
    if display_model == MT5_OPERATIONAL_MODEL_5:
        return "BETAPRICE5_PRICE_ACTION_STRUCTURE_EXIT"
    if display_model == MT5_OPERATIONAL_MODEL_6:
        return "BETAPRICE6_ESPELHO_M5"
    for value in (
        getattr(row, "exit_setup", None),
        getattr(row, "dynamic_exit_policy", None),
        getattr(row, "stop_management", None),
        _mt5_trade_row_text(
            row,
            "exit_setup",
            "exit_setup",
            "exit_model",
            "dynamic_exit_policy",
            "stop_management",
        ),
    ):
        text = str(value or "").strip()
        if text and text.upper() not in {"N/D", "NONE"}:
            return text
    for value in (
        signal.get("Modelo Saida"),
        signal.get("Plano inicial"),
    ):
        text = str(value or "").strip()
        if text and text.upper() not in {"N/D", "NONE"}:
            return text
    return "N/D"


def _mt5_sender_model_label(
    row: object,
    display_model: str | None = None,
) -> str:
    model = str(
        display_model
        or getattr(row, "operational_model", "N/D")
        or "N/D"
    ).upper()
    if model == MT5_OPERATIONAL_MODEL_1:
        return "MODELO 1"
    if model == MT5_OPERATIONAL_MODEL_2:
        return "MODELO 2"
    if model == MT5_OPERATIONAL_MODEL_3:
        return "MODELO 3"
    if model == MT5_OPERATIONAL_MODEL_4:
        return "MODELO 4"
    if model == MT5_OPERATIONAL_MODEL_5:
        return "MODELO 5"
    if model == MT5_OPERATIONAL_MODEL_6:
        return "MODELO 6"
    return model if model not in {"", "NONE"} else "N/D"


def _mt5_theoretical_exit_stop_moved(row: object) -> bool:
    """Detecta movimento real do SL priorizando o stop atual do MT5."""
    initial_stop = _safe_float_or_none(getattr(row, "stop", None))
    current_stop = _safe_float_or_none(getattr(row, "mt5_stop", None))
    if initial_stop is not None and current_stop is not None:
        return abs(initial_stop - current_stop) > 1e-5
    return bool(getattr(row, "stop_movel_acionado", False))


def _mt5_beta_exit_timeframe(row: object, lab_timeframe: object = "N/D") -> str:
    """Mostra o timeframe de leitura da saida, separado do TF de entrada."""
    beta = str(getattr(row, "beta_id", "BETA001") or "BETA001").upper()
    version = str(getattr(row, "beta_version", "") or "").upper()
    if beta == "BETA002" or version.startswith("M1_"):
        return "M1"
    fallback = str(lab_timeframe or "N/D").strip().upper()
    return fallback if fallback and fallback not in {"N/D", "NONE"} else "N/D"


def _mt5_theoretical_exit_scenario(row: object) -> str:
    """Resume a acao operacional do BETA002 em tres cenarios."""
    action = str(getattr(row, "position_manager_action", "") or "").upper()
    status = str(getattr(row, "position_manager_status", "") or "").upper()
    final_reason = str(getattr(row, "final_exit_reason", "") or "").upper()
    if "FULL_EXIT" in action or "EARLY_EXIT" in action or "FULL_EXIT" in final_reason:
        return "FULL_EXIT"
    if action in {"STOP_MOVED", "PROTECT_POSITION"} or status in {
        "STOP_MOVED",
        "EXECUTION_DISABLED",
        "STOP_MOVE_CANDIDATE",
    }:
        return "PROTECT"
    if getattr(row, "dynamic_exit_candidate_stop", None) is not None:
        return "PROTECT"
    return "HOLD"


def _mt5_theoretical_exit_programming_label(row: object) -> str:
    """Mostra a regra operacional atual de leitura do BETA002."""
    scenario = _mt5_theoretical_exit_scenario(row)
    if scenario == "FULL_EXIT":
        return "FULL_EXIT: score <= -0.50 + confirmacoes + evidencias suficientes."
    if scenario == "PROTECT":
        return "PROTECT: trade a favor e stop candidato mais protetivo."
    return "HOLD: manter enquanto nao houver protecao ou saida confirmada."


def _mt5_theoretical_exit_cell_class(row: dict[str, object], column: str) -> str:
    """Destaca apenas a celula do modelo; a linha ja comunica M1-M6."""
    if column == "Modelo envio":
        model = str(row.get(column, "") or "").upper()
        if model == "MODELO 4":
            return "traderia-cell-model4"
        if model == "MODELO 5":
            return "traderia-cell-model5"
        if model == "MODELO 6":
            return "traderia-cell-model6"
        if model == "MODELO 3":
            return "traderia-cell-model3"
        if model == "MODELO 2":
            return "traderia-cell-model2"
        if model == "MODELO 1":
            return "traderia-cell-model1"
    return ""


def _render_mt5_theoretical_exit_table(rows: list[dict[str, object]]) -> None:
    """Renderiza tabela da saida teorica colorida pelo modelo operacional."""
    if not rows:
        st.info("Nenhum registro disponivel.")
        return
    columns = list(rows[0].keys())
    header = "".join(f"<th>{_html_escape(column)}</th>" for column in columns)
    body = []
    for row in rows:
        row_class = _mt5_theoretical_exit_model_row_class(row)
        cells = []
        for column in columns:
            cell_class = _mt5_theoretical_exit_cell_class(row, column)
            cells.append(
                "<td"
                f"{f' class={cell_class!r}' if cell_class else ''}"
                ">"
                f"{_html_escape(row.get(column, ''))}"
                "</td>"
            )
        body.append(f"<tr class='{row_class}'>" + "".join(cells) + "</tr>")
    st.markdown(
        (
            "<div class='traderia-table-wrap'>"
            "<table class='traderia-stable-table'>"
            f"<thead><tr>{header}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody>"
            "</table>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _mt5_theoretical_exit_model_row_class(row: dict[str, object]) -> str:
    model_text = " ".join(
        str(row.get(column, "") or "").upper()
        for column in ("Modelo envio", "Modelo entrada", "Modelo saida")
    )
    if "MODELO 3" in model_text or "MODELO3" in model_text or "M3" in model_text:
        return "traderia-row-model3"
    if "MODELO 4" in model_text or "MODELO4" in model_text or "M4" in model_text:
        return "traderia-row-model4"
    if "MODELO 5" in model_text or "MODELO5" in model_text or "M5" in model_text:
        return "traderia-row-model5"
    if "MODELO 6" in model_text or "MODELO6" in model_text or "M6" in model_text:
        return "traderia-row-model6"
    if "MODELO 2" in model_text or "MODELO2" in model_text:
        return "traderia-row-model2"
    return "traderia-row-model1"


def _mt5_theoretical_exit_is_model3(row: dict[str, object]) -> bool:
    return any(
        "MODELO 3" in str(row.get(column, "") or "").upper()
        or "MODELO3" in str(row.get(column, "") or "").upper()
        or "M3" == str(row.get(column, "") or "").strip().upper()
        for column in ("Modelo envio", "Modelo entrada", "Modelo saida")
    )


def _parse_number_text(value: object) -> float:
    try:
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def _parse_optional_number_text(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text.upper() in {"N/D", "NA", "NONE", "NULL", "-"}:
        return None
    try:
        return float(text.replace("%", "").replace(",", "."))
    except (TypeError, ValueError):
        return None


def _safe_float_or_none(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _model2_adx_value(row: dict[str, object]) -> float | None:
    return _parse_optional_number_text(row.get("ADX"))


def _model2_adx_low_present(row: dict[str, object]) -> bool:
    adx = _model2_adx_value(row)
    return adx is not None and adx < MT5_ENTRY_FILTER_ADX_LOW_THRESHOLD


def _model2_adx_wait_reason(row: dict[str, object]) -> str:
    adx = _model2_adx_value(row)
    if adx is None:
        return "Modelo 2 aguardando leitura ADX para validar ADX < 20."
    return f"Modelo 2 aguardando ADX < 20. ADX atual: {adx:.2f}."


def _parse_percent_text(value: object) -> float:
    text = str(value or "").replace("%", "").replace(",", ".").strip()
    try:
        return float(text) / 100.0
    except ValueError:
        return 0.0


def _model2_inverse_entry_row(
    row: dict[str, object],
    *,
    require_filter_trigger: bool = True,
) -> dict[str, object]:
    """Cria leitura visual do Modelo 2 sem alterar a linha original do Lab."""
    direction = str(row.get("Direcao Teorica", "WAIT") or "WAIT").upper()
    if require_filter_trigger and not _model2_adx_low_present(row):
        cloned = dict(row)
        cloned["Modelo Ativo"] = f"MODELO2_AGUARDA_ADX_BAIXO | {row.get('Modelo Ativo', 'N/D')}"
        cloned["Direcao Teorica"] = "WAIT"
        cloned["Direcao"] = "WAIT"
        cloned["Plano Research"] = row.get("Plano Research", "SEM_PLANO")
        cloned["Codigo Rejeicao"] = row.get("Codigo Rejeicao", "N/D")
        cloned["Modelo Saida"] = "BETA002_ESPELHO_STOP_RR1"
        cloned["Motivo Entrada"] = _model2_adx_wait_reason(row)
        return cloned
    if direction not in {"BUY", "SELL"}:
        cloned = dict(row)
        cloned["Modelo Ativo"] = f"MODELO2_ESPELHO_BETA2 | {row.get('Modelo Ativo', 'N/D')}"
        cloned["Direcao Teorica"] = "WAIT"
        cloned["Direcao"] = "WAIT"
        cloned["Plano Research"] = row.get("Plano Research", "SEM_PLANO")
        cloned["Codigo Rejeicao"] = row.get("Codigo Rejeicao", "SEM_DIRECAO_ALPHA")
        cloned["Modelo Saida"] = "BETA002_ESPELHO_STOP_RR1"
        cloned["Motivo Entrada"] = "Modelo 2 aguardando BUY/SELL da Alpha."
        return cloned
    entry = _price_from_display(row.get("Preco Teorico"))
    original_stop = _price_from_display(row.get("Stop Research"))
    cloned = dict(row)
    inverse = "SELL" if direction == "BUY" else "BUY"
    cloned["Modelo Ativo"] = f"MODELO2_ESPELHO_BETA2 | {row.get('Modelo Ativo', 'N/D')}"
    cloned["Direcao Teorica"] = inverse
    cloned["Direcao"] = "VENDER" if inverse == "SELL" else "COMPRAR"
    cloned["Modelo Saida"] = "BETA002_ESPELHO_STOP_RR1"
    cloned["RR Research"] = "1.00"
    cloned["RR Minimo"] = "1.00"
    cloned["Motivo Entrada"] = (
        f"Modelo 2: Alpha {direction}; entrada espelhada {inverse}. "
        "Alvo no stop original da Alpha/Beta2 e stop em RR1."
    )
    if entry is None or original_stop is None:
        cloned["Plano Research"] = "SEM_PLANO"
        cloned["Codigo Rejeicao"] = "MODELO2_PRECO_OU_STOP_AUSENTE"
        return cloned
    distance = abs(entry - original_stop)
    if distance <= 0:
        cloned["Plano Research"] = "SEM_PLANO"
        cloned["Codigo Rejeicao"] = "MODELO2_DISTANCIA_ZERO"
        return cloned
    inverse_target = original_stop
    inverse_stop = entry + distance if inverse == "SELL" else entry - distance
    cloned["Stop Research"] = _format_model2_price(inverse_stop)
    cloned["Alvo Research"] = _format_model2_price(inverse_target)
    cloned["Plano Research"] = row.get("Plano Research", "PLANO_VALIDO")
    cloned["Codigo Rejeicao"] = row.get("Codigo Rejeicao", "N/D")
    return cloned


def _model4_inverse_entry_row(row: dict[str, object]) -> dict[str, object]:
    """Cria leitura visual do Modelo 4 espelhando o plano M1 sem alterar o Lab."""
    direction = str(row.get("Direcao Teorica", "WAIT") or "WAIT").upper()
    cloned = dict(row)
    cloned["Modelo Ativo"] = f"MODELO4_ESPELHO_M1 | {row.get('Modelo Ativo', 'N/D')}"
    cloned["Modelo Saida"] = "BETA004_ESPELHO_M1"
    if direction not in {"BUY", "SELL"}:
        cloned["Direcao Teorica"] = "WAIT"
        cloned["Direcao"] = "WAIT"
        cloned["Plano Research"] = row.get("Plano Research", "SEM_PLANO")
        cloned["Codigo Rejeicao"] = row.get("Codigo Rejeicao", "SEM_DIRECAO_M1")
        cloned["Motivo Entrada"] = "Modelo 4 aguardando BUY/SELL do Modelo 1."
        return cloned
    entry = _price_from_display(row.get("Preco Teorico"))
    original_stop = _price_from_display(row.get("Stop Research"))
    original_target = _price_from_display(row.get("Alvo Research"))
    inverse = "SELL" if direction == "BUY" else "BUY"
    cloned["Direcao Teorica"] = inverse
    cloned["Direcao"] = "VENDER" if inverse == "SELL" else "COMPRAR"
    cloned["Motivo Entrada"] = (
        f"Modelo 4: espelho do M1. M1 {direction}; entrada M4 {inverse}. "
        "Stop original vira alvo e alvo original vira stop."
    )
    if entry is None or original_stop is None or original_target is None:
        cloned["Plano Research"] = "SEM_PLANO"
        cloned["Codigo Rejeicao"] = "MODELO4_PRECO_STOP_OU_ALVO_AUSENTE"
        return cloned
    cloned["Stop Research"] = _format_model2_price(original_target)
    cloned["Alvo Research"] = _format_model2_price(original_stop)
    distance_stop = abs(float(original_target) - float(entry))
    distance_target = abs(float(entry) - float(original_stop))
    cloned["RR Research"] = (
        _format_model2_price(distance_target / distance_stop)
        if distance_stop > 0
        else "N/D"
    )
    cloned["RR Minimo"] = cloned["RR Research"]
    cloned["Plano Research"] = row.get("Plano Research", "PLANO_VALIDO")
    cloned["Codigo Rejeicao"] = row.get("Codigo Rejeicao", "N/D")
    return cloned


def _model5_price_action_entry_row(row: dict[str, object]) -> dict[str, object]:
    """Cria leitura visual do Modelo 5 Price Action sem alterar M1-M4."""
    decision = PriceActionSimpleModel().evaluate(
        PriceActionInput(
            symbol=str(row.get("Par", "N/D") or "N/D"),
            timeframe=MT5_OPERATIONAL_MODEL_5_ENTRY_TIMEFRAME,
            last_price=_price_from_display(row.get("Ultimo preco", row.get("Ultimo preço"))),
            pivot=_price_from_display(row.get("Pivot")),
            support=_price_from_display(row.get("Suporte")),
            resistance=_price_from_display(row.get("Resistencia")),
            swing_high=_price_from_display(row.get("Swing high", row.get("Topo"))),
            swing_low=_price_from_display(row.get("Swing low", row.get("Fundo"))),
            short_average=_price_from_display(row.get("Media curta", row.get("EMA curta"))),
            long_average=_price_from_display(row.get("Media longa", row.get("EMA longa"))),
            atr=_price_from_display(row.get("ATR")),
            spread=_price_from_display(row.get("Spread")),
            confirmation_status=str(row.get("Entrada Teorica", "") or ""),
            confirmation_direction=str(row.get("Direcao Teorica", row.get("Direcao", "WAIT")) or "WAIT"),
        )
    )
    cloned = dict(row)
    cloned["Periodo de tempo"] = MT5_OPERATIONAL_MODEL_5_ENTRY_TIMEFRAME
    cloned["Período de tempo"] = MT5_OPERATIONAL_MODEL_5_ENTRY_TIMEFRAME
    cloned["Timeframe"] = MT5_OPERATIONAL_MODEL_5_ENTRY_TIMEFRAME
    cloned["TF"] = MT5_OPERATIONAL_MODEL_5_ENTRY_TIMEFRAME
    cloned["Modelo Ativo"] = "MODELO5_PRICE_ACTION_SIMPLE"
    cloned["Modelo Saida"] = "BETAPRICE5_PRICE_ACTION_STRUCTURE_EXIT"
    cloned["Alpha Lab"] = "ALPHAPRICE5"
    cloned["Beta Lab"] = "BETAPRICE5"
    cloned["Estrutura M5"] = decision.market_structure
    cloned["Zona M5"] = decision.interest_zone
    cloned["Confirmacao M5"] = decision.confirmation_type
    cloned["Motivo Entrada"] = decision.reason
    if not decision.ready:
        cloned["Direcao Teorica"] = "WAIT"
        cloned["Direcao"] = "WAIT"
        cloned["Plano Research"] = "SEM_PLANO"
        cloned["Codigo Rejeicao"] = decision.status
        return cloned
    cloned["Direcao Teorica"] = decision.direction
    cloned["Direcao"] = "COMPRAR" if decision.direction == "BUY" else "VENDER"
    cloned["Entrada Teorica"] = "SINAL_TEORICO"
    cloned["Preco Teorico"] = _format_model2_price(float(decision.entry_price or 0.0))
    cloned["Stop Research"] = _format_model2_price(float(decision.stop or 0.0))
    cloned["Alvo Research"] = _format_model2_price(float(decision.target or 0.0))
    cloned["RR Research"] = _format_model2_price(decision.risk_reward)
    cloned["RR Minimo"] = _format_model2_price(PriceActionSimpleModel.minimum_risk_reward)
    cloned["Plano Research"] = "PLANO_VALIDO"
    cloned["Codigo Rejeicao"] = "N/D"
    return cloned


def _model6_inverse_price_action_entry_row(row: dict[str, object]) -> dict[str, object]:
    """Cria leitura visual do Modelo 6 espelhando o plano Price Action do M5."""
    m5_row = _model5_price_action_entry_row(row)
    cloned = dict(m5_row)
    cloned["Modelo Ativo"] = "MODELO6_ESPELHO_M5"
    cloned["Modelo Saida"] = "BETAPRICE6_ESPELHO_M5"
    cloned["Alpha Lab"] = "ALPHAPRICE6"
    cloned["Beta Lab"] = "BETAPRICE6"
    status = str(m5_row.get("Plano Research", "") or "").upper()
    direction = str(
        m5_row.get("Direcao Teorica", m5_row.get("Direcao", "WAIT")) or "WAIT"
    ).upper()
    if status != "PLANO_VALIDO" or direction not in {"BUY", "SELL", "COMPRAR", "VENDER"}:
        cloned["Direcao Teorica"] = "WAIT"
        cloned["Direcao"] = "WAIT"
        cloned["Plano Research"] = "SEM_PLANO"
        cloned["Codigo Rejeicao"] = str(
            m5_row.get("Codigo Rejeicao", "MODELO6_AGUARDA_M5_VALIDO")
            or "MODELO6_AGUARDA_M5_VALIDO"
        )
        cloned["Motivo Entrada"] = "M6 aguardando M5 pronto para espelhar."
        return cloned
    inverse_direction = "SELL" if direction in {"BUY", "COMPRAR"} else "BUY"
    original_stop = m5_row.get("Stop Research")
    original_target = m5_row.get("Alvo Research")
    cloned["Direcao Teorica"] = inverse_direction
    cloned["Direcao"] = "COMPRAR" if inverse_direction == "BUY" else "VENDER"
    cloned["Stop Research"] = original_target
    cloned["Alvo Research"] = original_stop
    cloned["RR Research"] = _model6_inverse_rr_from_prices(m5_row)
    cloned["RR Minimo"] = cloned["RR Research"]
    cloned["Plano Research"] = "PLANO_VALIDO"
    cloned["Codigo Rejeicao"] = "N/D"
    cloned["Motivo Entrada"] = (
        "M6 espelho do M5: inverte a direcao; stop do M5 vira alvo e "
        "alvo do M5 vira stop."
    )
    return cloned


def _model6_inverse_rr_from_prices(row: dict[str, object]) -> str:
    entry = _price_from_display(row.get("Preco Teorico"))
    stop = _price_from_display(row.get("Stop Research"))
    target = _price_from_display(row.get("Alvo Research"))
    if entry is None or stop is None or target is None:
        return str(row.get("RR Research", "0.00") or "0.00")
    risk = abs(float(target) - float(entry))
    reward = abs(float(entry) - float(stop))
    if risk <= 0:
        return "0.00"
    return _format_model2_price(reward / risk)


def _format_model2_price(value: float) -> str:
    return f"{float(value):.5f}".rstrip("0").rstrip(".")


def _forex_theoretical_entry_row(
    row: dict[str, object],
    *,
    robot_online: bool = False,
    mt5_online: bool = False,
    execution_enabled: bool = True,
    model2_filter_trigger: bool = False,
    operational_model: str = MT5_OPERATIONAL_MODEL_1,
) -> dict[str, object]:
    entry_gate = _entry_signal_gate(row)
    plan_gate = _entry_plan_gate(row)
    zone_gate = _entry_zone_gate(row)
    robot_gate = _entry_robot_gate(robot_online)
    mt5_gate = _entry_mt5_gate(mt5_online)
    filter_gate = (
        _entry_filter_gate_for_model2(row)
        if model2_filter_trigger
        else _entry_filter_gate(row)
    )
    regime_gate = _entry_regime_gate(row)
    price_gate = _entry_price_gate(row)
    position_gate = _entry_position_gate(row)
    duplicate_gate = _entry_duplicate_gate(
        row,
        operational_model=operational_model,
    )
    position_side = _entry_open_position_side(row)
    theoretical_direction = str(row.get("Direcao Teorica", "WAIT") or "WAIT").upper()
    position_alpha = _entry_open_position_alpha(row)
    position_match = _entry_position_theoretical_match(
        position_side,
        theoretical_direction,
    )
    send_gate = _entry_send_gate(
        entry_gate=entry_gate,
        plan_gate=plan_gate,
        zone_gate=zone_gate,
        robot_gate=robot_gate,
        mt5_gate=mt5_gate,
        filter_gate=filter_gate,
        duplicate_gate=duplicate_gate,
        regime_gate=regime_gate,
        price_gate=price_gate,
        position_gate=position_gate,
    )
    if not execution_enabled:
        send_gate = "MONITOR: outro modelo"
    return {
        "Par": row.get("Par", "N/D"),
        "Timeframe": row.get("Periodo de tempo", row.get("Timeframe", "N/D")),
        "Envio resumo": send_gate,
        "Duplicidade": duplicate_gate,
        "Sinal": entry_gate,
        "Plano": plan_gate,
        "Zona gate": zone_gate,
        "Robo": robot_gate,
        "MT5": mt5_gate,
        "Filtro": filter_gate,
        "Regime": regime_gate,
        "Plano vigente": price_gate,
        "Posicao": position_gate,
        "Envio": send_gate,
        "Posicao aberta": "SIM" if position_side != "N/D" else "NAO",
        "Direcao posicao": position_side,
        "Alpha posicao": position_alpha,
        "Sinal teorico atual": theoretical_direction,
        "Confere posicao": position_match,
        "Modelo ativo": row.get("Modelo Ativo", "N/D"),
        "Zona": row.get("Zona Operacional", "N/D"),
        "Suporte": row.get("Suporte", "N/D"),
        "Resistencia": row.get("Resistencia", "N/D"),
        "Pivot": row.get("Pivot", "N/D"),
        "Entrada Teorica": row.get("Entrada Teorica", "SEM_GATILHO"),
        "Candle do Sinal": row.get("Candle do Sinal", "N/D"),
        "Preco Teorico": row.get("Preco Teorico", "N/D"),
        "Direcao": row.get("Direcao Teorica", "WAIT"),
        "Plano Research": row.get("Plano Research", "SEM_PLANO"),
        "Codigo Rejeicao": row.get("Codigo Rejeicao", "N/D"),
        "Stop Research": row.get("Stop Research", "N/D"),
        "Alvo Research": row.get("Alvo Research", "N/D"),
        "RR Research": row.get("RR Research", "N/D"),
        "RR Minimo": row.get("RR Minimo", "N/D"),
        "Proxima Tentativa": row.get("Proxima Tentativa", "N/D"),
        "Gatilho Esperado": row.get("Gatilho Esperado", "N/D"),
        "Modelo Saida": row.get("Modelo Saida", "NONE"),
        "Score Saida": row.get("Score Saida", "N/D"),
        "Motivo": row.get("Motivo Entrada", "N/D"),
    }


def _entry_open_position_side(row: dict[str, object]) -> str:
    """Extrai o lado da posicao aberta quando a linha ja trouxe esse contexto."""
    for key in ("Direcao Posicao", "Posicao Direcao", "Lado MT5", "Posicao MT5"):
        value = str(row.get(key, "") or "").strip().upper()
        if value in {"BUY", "SELL", "COMPRAR", "VENDER"}:
            return "BUY" if value == "COMPRAR" else "SELL" if value == "VENDER" else value
    reason = str(row.get("Motivo Entrada", "") or "").upper()
    if "POSICAO ABERTA" not in reason and "POSI" not in reason:
        return "N/D"
    if "BUY" in reason or "COMPR" in reason:
        return "BUY"
    if "SELL" in reason or "VEND" in reason:
        return "SELL"
    return "N/D"


def _entry_open_position_alpha(row: dict[str, object]) -> str:
    """Mostra a Alpha da posicao quando conhecida; senao usa a Alpha vigente."""
    for key in ("Alpha Posicao", "Alpha MT5", "Alpha Ordem", "Alpha Lab"):
        value = str(row.get(key, "") or "").strip().upper()
        if value and value not in {"N/D", "NONE"}:
            return value
    if _entry_open_position_side(row) != "N/D":
        value = str(row.get("Alpha Lab", "") or "").strip().upper()
        return value if value else "N/D"
    return "N/D"


def _entry_position_theoretical_match(
    position_side: str,
    theoretical_direction: str,
) -> str:
    """Compara a posicao aberta com a leitura teorica atual."""
    position = str(position_side or "N/D").upper()
    theoretical = str(theoretical_direction or "WAIT").upper()
    if position not in {"BUY", "SELL"}:
        return "SEM_POSICAO"
    if theoretical not in {"BUY", "SELL"}:
        return "DIVERGIU: sinal atual WAIT"
    if position == theoretical:
        return "BATE"
    return f"DIVERGIU: posicao {position} x sinal {theoretical}"


def _mt5_connection_online(value: object) -> bool:
    status = str(value or "").strip().upper()
    return status in {"ONLINE", "CONECTADO", "CONNECTED", "OK"}


def _entry_signal_gate(row: dict[str, object]) -> str:
    status = str(row.get("Entrada Teorica", "") or "").upper()
    if status == "SINAL_TEORICO":
        return "OK"
    return f"AGUARDA: {status or 'SEM_GATILHO'}"


def _entry_plan_gate(row: dict[str, object]) -> str:
    status = str(row.get("Plano Research", "") or "").upper()
    if status == "PLANO_VALIDO":
        return "OK"
    reason = str(row.get("Codigo Rejeicao", "") or "").strip()
    if reason.upper() == "MODELO2_AGUARDA_ADX_BAIXO":
        return "AGUARDA: ADX <= 20"
    if reason and reason.upper() != "N/D":
        return f"BLOQ: {reason}"
    return f"BLOQ: {status or 'SEM_PLANO'}"


def _entry_zone_gate(row: dict[str, object]) -> str:
    zone = str(row.get("Zona Operacional", "") or "").upper()
    if zone in {"SUPORTE", "RESISTENCIA", "PIVO", "ZONA DE VALOR"}:
        return "OK"
    if zone in {"FORA_DA_ZONA_DE_INTERESSE", "FORA DA ZONA", "FORA_DA_ZONA"}:
        return "BLOQ: fora da zona"
    return f"AGUARDA: {zone or 'zona indefinida'}"


def _entry_robot_gate(robot_online: bool) -> str:
    return "OK" if robot_online else "AGUARDA: robo desarmado"


def _entry_mt5_gate(mt5_online: bool) -> str:
    return "OK" if mt5_online else "AGUARDA: MT5 offline"


def _entry_filter_gate(row: dict[str, object]) -> str:
    """Gate visual leve para filtros de entrada NV-V vindos do Lab."""
    status = str(row.get("Filtro entrada", "") or "").strip().upper()
    reason = str(row.get("Filtro motivo", "") or "").strip()
    if not status:
        return "OK"
    if status == "OK":
        return "OK"
    if status in {"BLOQUEADO", "REJEITADO"}:
        return f"BLOQ: {reason or 'filtro NV-V'}"
    if status in {"AGUARDA", "N/D", "INDISPONIVEL"}:
        return f"AGUARDA: {reason or 'filtro NV-V'}"
    return "OK"


def _entry_filter_gate_for_model2(row: dict[str, object]) -> str:
    """No Modelo 2, somente ADX < 20 vira gatilho de inversao."""
    adx = _model2_adx_value(row)
    if adx is None:
        return "AGUARDA: leitura ADX indisponivel"
    if adx < MT5_ENTRY_FILTER_ADX_LOW_THRESHOLD:
        return f"OK: gatilho inversao (ADX {adx:.2f} < 20)"
    return f"AGUARDA: ADX {adx:.2f} >= 20"


def _entry_regime_gate(row: dict[str, object]) -> str:
    """Mostra o mesmo gate de regime usado pelo robo antes do envio."""
    if str(row.get("Direcao Teorica", "WAIT") or "WAIT").upper() not in {
        "BUY",
        "SELL",
    }:
        return "AGUARDA: sem direcao"
    signal = SimpleNamespace(
        decision=str(row.get("Direcao Teorica", "WAIT") or "WAIT").upper(),
        trend=row.get("Tendencia"),
        last_price=_price_from_display(row.get("Ultimo preco")),
        entry_price=_price_from_display(row.get("Preco Teorico")),
        momentum=_parse_percent_text(row.get("Momentum")),
        rsi=_parse_number_text(row.get("RSI")),
        short_average=_price_from_display(row.get("Media curta")),
        long_average=_price_from_display(row.get("Media longa")),
        ema_fast=_price_from_display(row.get("EMA rapida")),
        ema_mid=_price_from_display(row.get("EMA principal")),
        atr=_parse_number_text(row.get("ATR")),
        support=_price_from_display(row.get("Suporte")),
        resistance=_price_from_display(row.get("Resistencia")),
    )
    result = MT5_ENTRY_REGIME_PIPELINE.evaluate(signal)
    if result.authorized:
        return "OK"
    return f"BLOQ: {result.block_reason or result.message or 'REGIME'}"


def _entry_price_gate(row: dict[str, object]) -> str:
    direction = str(row.get("Direcao Teorica", "") or "").upper()
    last_price = _price_from_display(row.get("Ultimo preco"))
    stop = _price_from_display(row.get("Stop Research"))
    target = _price_from_display(row.get("Alvo Research"))
    if direction not in {"BUY", "SELL"}:
        return "AGUARDA: sem direcao"
    if last_price is None or stop is None or target is None:
        return "AGUARDA: preco/SL/alvo ausente"
    if direction == "BUY" and stop < last_price < target:
        return "OK"
    if direction == "SELL" and target < last_price < stop:
        return "OK"
    if direction == "BUY":
        return "BLOQ: preco saiu do plano BUY"
    return "BLOQ: preco saiu do plano SELL"


def _entry_position_gate(row: dict[str, object]) -> str:
    reason = str(row.get("Motivo Entrada", "") or "").upper()
    if "POSICAO ABERTA" in reason or "POSIÇÃO ABERTA" in reason:
        return "BLOQUEADO"
    return "OK"


def _entry_duplicate_gate(
    row: dict[str, object],
    *,
    operational_model: str,
) -> str:
    """Mostra na entrada teorica o bloqueio de plano ja avaliado."""
    if _mt5_entry_plan_already_evaluated(row, operational_model):
        return "BLOQ: plano ja avaliado"
    return "OK"


def _mt5_entry_plan_already_evaluated(
    row: dict[str, object],
    operational_model: str,
) -> bool:
    current_key = _mt5_entry_execution_key(row)
    if current_key is None:
        return False
    current_identity_tokens = _mt5_entry_plan_identity_tokens(row, operational_model)
    for record in _read_mt5_demo_execution_records():
        if not _mt5_demo_record_counts_as_plan_evaluation(record):
            continue
        if str(record.get("operational_model") or "").upper() != operational_model:
            continue
        if _mt5_demo_record_execution_key(record) != current_key:
            continue
        plan_identity = str(record.get("plan_identity") or "").upper()
        if current_identity_tokens and not all(
            token in plan_identity for token in current_identity_tokens
        ):
            continue
        return True
    return False


def _mt5_entry_execution_key(
    row: dict[str, object],
) -> tuple[str, str, float, float, float] | None:
    symbol = str(row.get("Par", "") or "").upper()
    side = str(row.get("Direcao Teorica", "") or "").upper()
    entry = _price_from_display(row.get("Preco Teorico"))
    stop = _price_from_display(row.get("Stop Research"))
    target = _price_from_display(row.get("Alvo Research"))
    if (
        not symbol
        or side not in {"BUY", "SELL"}
        or entry is None
        or stop is None
        or target is None
    ):
        return None
    return (
        symbol,
        side,
        round(float(entry), 5),
        round(float(stop), 5),
        round(float(target), 5),
    )


def _mt5_demo_record_execution_key(
    record: dict[str, object],
) -> tuple[str, str, float, float, float] | None:
    symbol = str(record.get("symbol", "") or "").upper()
    side = str(record.get("side", "") or "").upper()
    entry = _safe_float_or_none(record.get("entry_price"))
    stop = _safe_float_or_none(record.get("stop"))
    target = _safe_float_or_none(record.get("target"))
    if (
        not symbol
        or side not in {"BUY", "SELL"}
        or entry is None
        or stop is None
        or target is None
    ):
        return None
    return (
        symbol,
        side,
        round(float(entry), 5),
        round(float(stop), 5),
        round(float(target), 5),
    )


def _mt5_entry_plan_identity_tokens(
    row: dict[str, object],
    operational_model: str,
) -> list[str]:
    parts = [
        row.get("Par"),
        row.get("Periodo de tempo", row.get("Timeframe")),
        row.get("Modelo Ativo"),
        row.get("Plano Research"),
        operational_model,
    ]
    return [
        str(part or "").upper()
        for part in parts
        if str(part or "").strip()
        and str(part or "").upper() not in {"N/D", "NONE", "SEM_PLANO"}
    ]


def _mt5_demo_record_counts_as_plan_evaluation(record: dict[str, object]) -> bool:
    return bool(record.get("accepted", False))


def _read_mt5_demo_execution_records() -> list[dict[str, object]]:
    try:
        lines = MT5_DEMO_EXECUTION_LOG_PATH.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines()
    except OSError:
        return []
    records: list[dict[str, object]] = []
    for line in lines[-2000:]:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _entry_send_gate(
    *,
    entry_gate: str,
    plan_gate: str,
    zone_gate: str,
    robot_online: bool,
    mt5_online: bool,
    price_gate: str,
    position_gate: str,
) -> str:
    gates = [entry_gate, plan_gate, zone_gate, price_gate, position_gate]
    if any(gate == "BLOQUEADO" for gate in gates):
        return "BLOQUEADO"
    if not robot_online or not mt5_online:
        return "AGUARDANDO"
    if all(gate == "OK" for gate in gates):
        return "PRONTO"
    return "AGUARDANDO"


def _entry_position_gate(row: dict[str, object]) -> str:
    reason = str(row.get("Motivo Entrada", "") or "").upper()
    if (
        "POSICAO ABERTA" in reason
        or "POSIÇÃO ABERTA" in reason
        or "POSIÃ‡ÃƒO ABERTA" in reason
    ):
        return "BLOQ: posicao aberta"
    return "OK"


def _entry_send_gate(
    *,
    entry_gate: str,
    plan_gate: str,
    zone_gate: str,
    robot_gate: str,
    mt5_gate: str,
    filter_gate: str,
    duplicate_gate: str,
    regime_gate: str,
    price_gate: str,
    position_gate: str,
) -> str:
    gates = [
        ("Sinal", entry_gate),
        ("Plano", plan_gate),
        ("Zona", zone_gate),
        ("Robo", robot_gate),
        ("MT5", mt5_gate),
        ("Filtro", filter_gate),
        ("Duplicidade", duplicate_gate),
        ("Plano vigente", price_gate),
        ("Regime", regime_gate),
        ("Posicao", position_gate),
    ]
    for name, gate in gates:
        if _gate_status(gate) == "blocked":
            return f"BLOQ: {name}"
    for name, gate in gates:
        if _gate_status(gate) == "wait":
            return f"AGUARDA: {name}"
    if all(_gate_status(gate) == "ok" for _, gate in gates):
        return "PRONTO"
    return "AGUARDA: validacao"


def _gate_status(value: object) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("OK") or text in {"PRONTO", "SIM", "APROVADO"}:
        return "ok"
    if text.startswith("BLOQ") or text in {"BLOQUEADO", "REJEITADO"}:
        return "blocked"
    return "wait"


def _price_from_display(value: object) -> float | None:
    text = str(value or "").strip()
    if not text or text.upper() == "N/D":
        return None
    text = text.replace(" ", "")
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _forex_zone_label(row: object) -> str:
    decision = str(getattr(row, "decision", "WAIT") or "WAIT").upper()
    price = _optional_float(getattr(row, "last_price", None))
    support = _optional_float(getattr(row, "support", None))
    resistance = _optional_float(getattr(row, "resistance", None))
    pivot = _optional_float(getattr(row, "pivot", None))
    atr = _optional_float(getattr(row, "atr", None)) or 0.0
    ema_mid = _optional_float(getattr(row, "ema_mid", None))
    mid_average = _optional_float(getattr(row, "mid_average", None))
    if price is None or price <= 0:
        return "SEM PRECO"
    tolerance = max(atr * 1.5, abs(price) * 0.003)
    near_support = support is not None and abs(price - support) <= tolerance
    near_resistance = resistance is not None and abs(price - resistance) <= tolerance
    if decision == "BUY" and near_support:
        return "SUPORTE"
    if decision == "SELL" and near_resistance:
        return "RESISTENCIA"
    if pivot is not None and abs(price - pivot) <= tolerance:
        return "PIVO"
    if near_support:
        return "SUPORTE"
    if near_resistance:
        return "RESISTENCIA"
    anchor = ema_mid if ema_mid is not None else mid_average
    value_tolerance = max(atr * 5.0, abs(price) * 0.02)
    if anchor is not None and abs(price - anchor) <= value_tolerance:
        return "ZONA DE VALOR"
    if support is not None and resistance is not None and support < price < resistance:
        return "MEIO DO RANGE"
    return "FORA DA ZONA"


def _optional_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _exibir_mt5_safe_mode_minimal_diagnostic(forex: object) -> None:
    with st.container(border=True):
        st.subheader("MT5 Safe Mode")
        _stable_metric_grid(
            [
                (
                    "Safe Mode",
                    "ATIVO"
                    if bool(getattr(forex, "mt5_safe_mode", True))
                    else "INATIVO",
                ),
                ("Fonte MT5", getattr(forex, "safe_mode_source", "MT5_SAFE_MODE")),
                ("Status", getattr(forex, "safe_mode_status", "OFFLINE")),
                ("Refresh ID", int(getattr(forex, "refresh_id", 0) or 0)),
                (
                    "Ultima atualizacao",
                    _friendly_candle_time(getattr(forex, "last_update", "") or "N/D"),
                ),
                (
                    "Ultima vela recebida",
                    _friendly_candle_time(
                        getattr(forex, "last_candle_time", "N/D")
                    ),
                ),
                (
                    "Candles recebidos",
                    int(getattr(forex, "safe_mode_received_candles", 0) or 0),
                ),
                (
                    "Ultimo preco",
                    _optional_price(getattr(forex, "safe_mode_last_price", None)),
                ),
            ]
        )
        safe_error = getattr(forex, "safe_mode_error", "") or getattr(
            forex,
            "health_message",
            "",
        )
        if safe_error:
            safe_status = str(getattr(forex, "safe_mode_status", "")).upper()
            connection_status = str(
                getattr(forex, "connection_status", "")
            ).upper()
            if safe_status in {"OFFLINE", "ERRO", "ERROR"} or connection_status in {
                "OFFLINE",
                "DISCONNECTED",
            }:
                st.caption(f"Erro MT5: {safe_error}")
            else:
                st.caption(f"Diagnostico MT5: {safe_error}")


def _exibir_mt5_connection_health(forex: object) -> None:
    with st.container(border=True):
        icon = getattr(forex, "connection_health_icon", "")
        status = getattr(forex, "connection_health", "OFFLINE")
        st.subheader(f"{icon} MT5 {status}".strip())
        _stable_metric_grid(
            [
                (
                    "Ultima atualizacao",
                    _friendly_candle_time(getattr(forex, "last_update", "")),
                ),
                (
                    "Ultima leitura MT5",
                    _friendly_candle_time(getattr(forex, "last_mt5_read", "")),
                ),
                ("Refresh ID", int(getattr(forex, "refresh_id", 0) or 0)),
                (
                    "Ultima vela",
                    _friendly_candle_time(
                        getattr(forex, "last_candle_time", "N/D")
                    ),
                ),
                (
                    "Tempo desde atualizacao",
                    f"{float(getattr(forex, 'seconds_since_update', 0.0) or 0.0):.1f}s",
                ),
                ("Dados", getattr(forex, "connection_health", "OFFLINE")),
                (
                    "Refresh leve",
                    f"{float(getattr(forex, 'fast_refresh_duration_ms', 0.0) or 0.0):.1f} ms",
                ),
                ("Fluxo", "Heuristica leve"),
            ]
        )
        st.caption("Fluxo: MT5 Forex online com heuristica leve.")
        st.caption(getattr(forex, "health_message", "N/D"))


def _exibir_mt5_manual_diagnostic_controls(
    service: DashboardService,
    data: object,
    forex: object,
) -> object:
    """Atualiza diagnostico MT5 somente quando solicitado."""
    pairs = list(getattr(forex, "pairs", []) or [])
    symbol = (
        str(getattr(pairs[0], "pair", "") or "").upper()
        if pairs
        else "EURUSD"
    )
    timeframe = str(getattr(forex, "timeframe", "M1") or "M1").upper()
    with st.container(border=True):
        colunas = st.columns([1, 3])
        if colunas[0].button(
            "Atualizar diagnostico MT5",
            key="mt5_forex_manual_diagnostic_refresh",
        ):
            try:
                with st.spinner("Atualizando diagnostico MT5..."):
                    diagnostic = service.test_mt5_connection(
                        symbol=symbol,
                        timeframe=timeframe,
                    )
                    st.session_state[MT5_FOREX_MANUAL_DIAGNOSTIC_KEY] = diagnostic
                    _record_runtime_event("MT5_DIAGNOSTIC_ONLY_COMPLETED")
                    _record_runtime_event("MT5_DIAGNOSTIC_DID_NOT_START_CYCLE")
                st.session_state[MT5_FOREX_MANUAL_DIAGNOSTIC_MESSAGE_KEY] = (
                    "Diagnostico MT5 atualizado. Nenhum ciclo automatico foi iniciado."
                )
            except Exception as exc:
                st.session_state[MT5_FOREX_MANUAL_DIAGNOSTIC_MESSAGE_KEY] = (
                    f"Falha ao atualizar diagnostico MT5: {exc}"
                )

        message = st.session_state.get(MT5_FOREX_MANUAL_DIAGNOSTIC_MESSAGE_KEY)
        if message:
            colunas[1].caption(str(message))
        if bool(st.session_state.get(MT5_FOREX_AUTO_CYCLE_UI_KEY, False)):
            colunas[1].caption(
                f"Ciclo automatico leve ativo a cada {MT5_FOREX_AUTO_REFRESH_SECONDS:.0f}s."
            )
        diagnostic = st.session_state.get(MT5_FOREX_MANUAL_DIAGNOSTIC_KEY)
        if diagnostic is not None:
            _exibir_mt5_connection_diagnostic(diagnostic)
    return data


def _stable_metric_grid(items: list[tuple[str, object]]) -> None:
    columns = st.columns(4)
    for index, (label, value) in enumerate(items):
        with columns[index % 4]:
            st.markdown(
                (
                    "<div class='traderia-stable-card'>"
                    f"<div class='traderia-stable-card-label'>{_html_escape(label)}</div>"
                    f"<div class='traderia-stable-card-value'>{_html_escape(value)}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )


def _render_stable_forex_table(rows: list[dict[str, object]]) -> None:
    """Renderiza a grade Forex sem componente virtualizado do Streamlit."""
    display_columns = _forex_main_table_columns()
    display_rows = [
        {column: row.get(column, "") for column in display_columns if column in row}
        for row in rows
    ]
    _render_stable_readonly_table(
        display_rows,
        model_column="Modelo Ativo",
        decision_column="Decisao",
        highlight_active_indicators=True,
    )


def _forex_main_table_columns() -> list[str]:
    return [
        "Par",
        "Status",
        "TF vencedor Lab",
        "Alpha Lab",
        "Beta Lab",
        "Modo Beta",
        "Modelo Ativo",
        "Fonte Config",
        "Timeframe MT5 lido",
        "Filtro entrada",
        "Filtro parametro",
        "Filtro leitura",
        "Filtro motivo",
        "Ultimo preco",
        "Horario",
        "Tendencia",
        "EMA curta Lab",
        "EMA longa Lab",
        "RSI sobrevenda Lab",
        "RSI sobrecompra Lab",
        "ATR stop Lab",
        "RR Lab",
        "Momentum min Lab",
        "Volatilidade min Lab",
        "ADX min Lab",
        "Regime ATR Lab",
        "Largura Bollinger Lab",
        "Z-Score min Lab",
        "Volume factor Lab",
        "Pullback tol Lab",
        "Donchian periodo Lab",
        "Breakout buffer Lab",
        "Indicadores do modelo",
        "Momentum",
        "Volatilidade",
        "RSI",
        "Media curta",
        "Media longa",
        "EMA rapida",
        "EMA principal",
        "EMA longa",
        "ADX",
        "MACD",
        "MACD signal",
        "ATR",
        "ATR media",
        "Bollinger superior",
        "Bollinger inferior",
        "Tick volume",
        "Tick volume media",
        "Maxima dia",
        "Minima dia",
        "Donchian max",
        "Donchian min",
        "Pivot",
        "VWAP",
        "Z-Score",
        "Suporte",
        "Resistencia",
        "Swing high",
        "Swing low",
        "Spread",
        "Spread media",
        "Slippage estimado",
        "Velocidade preco",
        "Decisao",
        "Entrada Teorica",
        "Candle do Sinal",
        "Preco Teorico",
        "Direcao Teorica",
        "Motivo Entrada",
        "Politica Saida Lab",
        "Estado Mercado Saida",
        "Recomendacao Saida",
        "Confianca Saida Dinamica",
        "R Atual Saida",
        "Stop Candidato",
        "Candles recebidos",
    ]


def _render_stable_readonly_table(
    rows: list[dict[str, object]],
    *,
    model_column: str = "Modelo",
    decision_column: str = "Decisao",
    highlight_active_indicators: bool = False,
    color_status_cells: bool = False,
    empty_columns: list[str] | None = None,
    empty_message: str = "Nenhum registro disponivel.",
) -> None:
    """Renderiza tabela HTML estavel para regioes com auto-refresh."""
    columns = list(rows[0].keys()) if rows else list(empty_columns or ["Status"])
    header = "".join(
        f"<th>{_html_escape(column)}</th>"
        for column in columns
    )
    body = []
    display_rows = rows or [{columns[0]: empty_message}]
    for row in display_rows:
        decision = _normalize_forex_decision(
            row.get(decision_column, row.get("Decisao", row.get("Direcao", "WAIT")))
        )
        row_class = {
            "BUY": "traderia-row-buy",
            "SELL": "traderia-row-sell",
            "WAIT": "traderia-row-wait",
        }.get(decision, "traderia-row-wait")
        active_columns = (
            _forex_active_indicator_columns(row.get(model_column, ""))
            if highlight_active_indicators
            else set()
        )
        cells = []
        for column in columns:
            cell_classes = []
            if column in active_columns:
                cell_classes.append("traderia-cell-active")
            if color_status_cells:
                status_class = _stable_table_status_cell_class(row.get(column, ""))
                if status_class:
                    cell_classes.append(status_class)
            cells.append(
                "<td class='"
                f"{' '.join(cell_classes)}"
                "'>"
                f"{_html_escape(row.get(column, ''))}"
                "</td>"
            )
        body.append(f"<tr class='{row_class}'>" + "".join(cells) + "</tr>")

    st.markdown(
        (
            "<div class='traderia-table-wrap'>"
            "<table class='traderia-stable-table'>"
            f"<thead><tr>{header}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody>"
            "</table>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def _mt5_trade_audit_model_row_class(row: dict[str, object]) -> str:
    model = str(row.get("Modelo", row.get("Modelo envio", "")) or "").upper()
    if "MODELO 5" in model or "MODELO5" in model or model == "M5":
        return "traderia-row-model5"
    if "MODELO 6" in model or "MODELO6" in model or model == "M6":
        return "traderia-row-model6"
    if "MODELO 4" in model or "MODELO4" in model or model == "M4":
        return "traderia-row-model4"
    if "MODELO 3" in model or "MODELO3" in model or model == "M3":
        return "traderia-row-model3"
    if "MODELO 2" in model or "MODELO2" in model or model == "M2":
        return "traderia-row-model2"
    if "MODELO 1" in model or "MODELO1" in model or model == "M1":
        return "traderia-row-model1"
    return "traderia-row-wait"


def _mt5_trade_audit_cell_class(row: dict[str, object], column: str) -> str:
    if column != "Resultado MT5":
        return ""
    result = _parse_number_text(row.get(column, 0.0))
    if result > 0:
        return "traderia-cell-result-positive"
    if result < 0:
        return "traderia-cell-result-negative"
    return "traderia-cell-result-neutral"


def _stable_table_status_cell_class(value: object) -> str:
    text = str(value or "").strip().upper()
    if text.startswith("BLOQ"):
        return "traderia-cell-blocked"
    if text.startswith("AGUARDA"):
        return "traderia-cell-wait"
    if text in {
        "OK",
        "SIM",
        "PRONTO",
        "APROVADO",
        "PLANO_VALIDO",
        "SINAL_TEORICO",
        "SEM_POSICAO",
    }:
        return "traderia-cell-ok"
    if text in {
        "AGUARDANDO",
        "N/D",
        "",
        "WAIT",
        "SEM_GATILHO",
        "REAVALIAR",
    }:
        return "traderia-cell-wait"
    if text in {
        "NAO",
        "NÃO",
        "REJEITADO",
        "BLOQUEADO",
        "INVALIDO",
        "PLANO_INVALIDO",
        "SEM_PLANO",
        "FORA_DA_ZONA_DE_INTERESSE",
        "POSICAO_ABERTA",
        "PRECO_INVALIDO",
    }:
        return "traderia-cell-blocked"
    return ""


def _html_escape(value: object) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def _inject_dashboard_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stSegmentedControl"] {
            display: flex;
            width: 100%;
            border-bottom: 1px solid rgba(49, 51, 63, 0.16);
            margin: 0.35rem 0 1rem 0;
            overflow-x: auto;
        }
        div[data-testid="stSegmentedControl"] button {
            min-height: 42px;
            padding: 0.55rem 1rem 0.65rem 1rem;
            border-radius: 0 !important;
            white-space: nowrap;
            font-size: 0.92rem;
            font-weight: 650;
            border-bottom: 3px solid transparent !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {
            border-bottom-color: #D71920 !important;
            color: #111827 !important;
            background: #FFFFFF !important;
        }
        .traderia-stable-card {
            border: 1px solid rgba(49, 51, 63, 0.18);
            border-radius: 8px;
            padding: 0.75rem 0.9rem;
            margin-bottom: 0.75rem;
            min-height: 84px;
            background: rgba(255, 255, 255, 0.02);
        }
        .traderia-stable-card-label {
            color: rgba(49, 51, 63, 0.72);
            font-size: 0.88rem;
            margin-bottom: 0.35rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .traderia-stable-card-value {
            color: rgb(49, 51, 63);
            font-size: 1.35rem;
            font-weight: 650;
            line-height: 1.25;
            overflow-wrap: anywhere;
        }
        .traderia-table-wrap {
            width: 100%;
            overflow-x: auto;
            border: 1px solid rgba(49, 51, 63, 0.14);
            border-radius: 8px;
            margin: 0.75rem 0 1rem 0;
            background: #FFFFFF;
        }
        .traderia-stable-table {
            width: max-content;
            min-width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }
        .traderia-stable-table th {
            position: sticky;
            top: 0;
            background: #F8FAFC !important;
            border-bottom: 1px solid rgba(49, 51, 63, 0.14);
            color: #334155 !important;
            font-weight: 750;
            padding: 0.65rem 0.75rem;
            text-align: left;
            white-space: nowrap;
            z-index: 1;
        }
        .traderia-stable-table td {
            border-bottom: 1px solid rgba(49, 51, 63, 0.10);
            border-right: 1px solid rgba(49, 51, 63, 0.08);
            color: #111827 !important;
            padding: 0.65rem 0.75rem;
            white-space: nowrap;
            font-weight: 600;
        }
        .traderia-row-buy td {
            background: #DDF7E3 !important;
            color: #0F3D24 !important;
            font-weight: 750;
        }
        .traderia-row-sell td {
            background: #FDE0E0 !important;
            color: #5C1A1A !important;
            font-weight: 750;
        }
        .traderia-row-wait td {
            background: #FFFFFF !important;
            color: #111827 !important;
        }
        .traderia-row-model1 td {
            background: #DDF7E3 !important;
            color: #0F3D24 !important;
            font-weight: 800;
        }
        .traderia-row-model2 td {
            background: #FEF3C7 !important;
            color: #78350F !important;
            font-weight: 800;
        }
        .traderia-row-model3 td {
            background: #FCE7F3 !important;
            color: #831843 !important;
            font-weight: 800;
        }
        .traderia-row-model4 td {
            background: #E0F2FE !important;
            color: #075985 !important;
            font-weight: 800;
        }
        .traderia-row-model5 td {
            background: #FFFFFF !important;
            color: #111827 !important;
            font-weight: 800;
        }
        .traderia-row-model6 td {
            background: #EDE9FE !important;
            color: #4C1D95 !important;
            font-weight: 800;
        }
        .traderia-stable-table td.traderia-cell-active {
            background: #DBEAFE !important;
            color: #0F172A !important;
            font-weight: 750;
        }
        .traderia-stable-table td.traderia-cell-ok {
            background: #DDF7E3 !important;
            color: #0F3D24 !important;
            font-weight: 800;
        }
        .traderia-stable-table td.traderia-cell-model1 {
            background: #DDF7E3 !important;
            color: #0F3D24 !important;
            font-weight: 850;
        }
        .traderia-stable-table td.traderia-cell-model2 {
            background: #FDE68A !important;
            color: #78350F !important;
            font-weight: 900;
        }
        .traderia-stable-table td.traderia-cell-model3 {
            background: #F9A8D4 !important;
            color: #831843 !important;
            font-weight: 900;
        }
        .traderia-stable-table td.traderia-cell-model4 {
            background: #7DD3FC !important;
            color: #075985 !important;
            font-weight: 900;
        }
        .traderia-stable-table td.traderia-cell-model5 {
            background: #FFFFFF !important;
            color: #111827 !important;
            font-weight: 900;
        }
        .traderia-stable-table td.traderia-cell-model6 {
            background: #DDD6FE !important;
            color: #4C1D95 !important;
            font-weight: 900;
        }
        .traderia-stable-table td.traderia-cell-result-positive {
            background: #DDF7E3 !important;
            color: #0F3D24 !important;
            font-weight: 900;
        }
        .traderia-stable-table td.traderia-cell-result-negative {
            background: #FDE0E0 !important;
            color: #5C1A1A !important;
            font-weight: 900;
        }
        .traderia-stable-table td.traderia-cell-result-neutral {
            background: #FFFFFF !important;
            color: #111827 !important;
            font-weight: 800;
        }
        .traderia-stable-table td.traderia-cell-wait {
            background: #FEF3C7 !important;
            color: #78350F !important;
            font-weight: 800;
        }
        .traderia-stable-table td.traderia-cell-blocked {
            background: #FDE0E0 !important;
            color: #5C1A1A !important;
            font-weight: 800;
        }
        .traderia-status-legend {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;
            margin: 0.25rem 0 0.75rem 0;
        }
        .traderia-status-legend span {
            border-radius: 6px;
            border: 1px solid rgba(49, 51, 63, 0.14);
            font-size: 0.82rem;
            font-weight: 800;
            padding: 0.28rem 0.55rem;
        }
        .traderia-legend-ok {
            background: #DDF7E3;
            color: #0F3D24;
        }
        .traderia-legend-model1 {
            background: #DDF7E3;
            color: #0F3D24;
        }
        .traderia-legend-model2 {
            background: #FEF3C7;
            color: #78350F;
        }
        .traderia-legend-model3 {
            background: #FCE7F3;
            color: #831843;
        }
        .traderia-legend-model4 {
            background: #E0F2FE;
            color: #075985;
        }
        .traderia-legend-model5 {
            background: #FFFFFF;
            color: #111827;
        }
        .traderia-legend-model6 {
            background: #EDE9FE;
            color: #4C1D95;
        }
        .traderia-legend-wait {
            background: #FEF3C7;
            color: #78350F;
        }
        .traderia-legend-active {
            background: #DBEAFE;
            color: #0F172A;
        }
        .traderia-legend-blocked {
            background: #FDE0E0;
            color: #5C1A1A;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _exibir_mt5_connection_diagnostic(forex: object) -> None:
    diagnostic = getattr(forex, "connection_diagnostic", None)
    if diagnostic is None and hasattr(forex, "connection_status"):
        diagnostic = forex
    if diagnostic is None:
        return
    with st.container(border=True):
        st.subheader("Diagnostico da conexao MT5")
        colunas = st.columns(4)
        colunas[0].metric(
            "Status da conexao",
            getattr(diagnostic, "connection_status", "OFFLINE"),
        )
        colunas[1].metric("last_error_code", _format_optional_int(
            getattr(diagnostic, "last_error_code", None)
        ))
        colunas[2].metric(
            "build",
            getattr(diagnostic, "build", "N/D"),
        )
        colunas[3].metric(
            "executado em",
            _friendly_candle_time(getattr(diagnostic, "executed_at", "") or "N/D"),
        )
        st.caption(
            f"last_error_message: {getattr(diagnostic, 'last_error_message', '') or 'N/D'}"
        )
        st.dataframe(
            [_mt5_connection_diagnostic_step_row(step) for step in getattr(diagnostic, "steps", [])],
            hide_index=True,
            width="stretch",
        )
        detalhes = st.columns(4)
        detalhes[0].metric("terminal_path", getattr(diagnostic, "terminal_path", "N/D"))
        detalhes[1].metric("server", getattr(diagnostic, "server", "N/D"))
        detalhes[2].metric("account", getattr(diagnostic, "account", "N/D"))
        detalhes[3].metric("failed_call", getattr(diagnostic, "failed_call", "") or "N/D")
        flags = st.columns(3)
        flags[0].metric("connected", str(bool(getattr(diagnostic, "connected", False))))
        flags[1].metric(
            "trade_allowed",
            str(bool(getattr(diagnostic, "trade_allowed", False))),
        )
        flags[2].metric(
            "community_connection",
            str(bool(getattr(diagnostic, "community_connection", False))),
        )
        st.info(getattr(diagnostic, "diagnostic_message", "N/D"))


def _mt5_connection_diagnostic_step_row(step: object) -> dict[str, object]:
    return {
        "Etapa": getattr(step, "name", "N/D"),
        "Status": getattr(step, "status", "FALHOU"),
        "Mensagem": getattr(step, "message", ""),
        "last_error_code": _format_optional_int(
            getattr(step, "last_error_code", None)
        ),
        "last_error_message": getattr(step, "last_error_message", ""),
    }


def _format_optional_int(value: object) -> str:
    if value in (None, ""):
        return "N/D"
    return str(value)


def _exibir_mt5_diagnostics(pares: list[object]) -> None:
    st.subheader("MT5 Diagnostics")
    st.dataframe(
        [_mt5_diagnostic_row(row) for row in pares],
        hide_index=True,
        width="stretch",
    )


def _mt5_diagnostic_row(row: object) -> dict[str, object]:
    return {
        "Simbolo": getattr(row, "pair", "N/D"),
        "Timeframe": getattr(row, "timeframe", "N/D"),
        "Candles configurados": int(getattr(row, "configured_candles", 0) or 0),
        "Candles solicitados": int(getattr(row, "requested_candles", 0) or 0),
        "Candles recebidos": int(getattr(row, "received_candles", 0) or 0),
        "Candles utilizados pelo Research Lab": int(
            getattr(row, "research_candles_used", 0) or 0
        ),
        "Horario do ultimo candle": _friendly_candle_time(
            getattr(row, "last_candle_time", "N/D")
        ),
        "Ultima atualizacao": _friendly_candle_time(getattr(row, "last_update", "")),
        "Status": getattr(row, "diagnostics_status", "ERRO"),
        "Log": getattr(row, "diagnostics_log", ""),
    }


def _exibir_timeframe_optimizer(service: DashboardService, data: object) -> None:
    st.subheader("Timeframe Optimizer")
    st.caption(
        "Recomendacao de pesquisa. Nenhum timeframe e aplicado automaticamente."
    )
    controles = st.columns([1, 3])
    if controles[0].button(
        "Atualizar Timeframe Optimizer",
        key="timeframe_optimizer_reload",
    ):
        service.load_timeframe_optimization_results()
        data = service.get_dashboard_view_model()

    results = list(getattr(data, "timeframe_optimizer", []) or [])
    if not results:
        st.info("Nenhuma otimizacao de timeframe executada nesta sessao.")
        return

    st.dataframe(
        [_timeframe_optimizer_row(result) for result in results],
        hide_index=True,
        width="stretch",
    )
    for result in results:
        symbol = getattr(result, "symbol", "N/D")
        best_timeframe = getattr(result, "best_timeframe", "NONE")
        with st.expander(f"{symbol}: candidatos ({best_timeframe})"):
            if best_timeframe == "NONE":
                st.warning(
                    "Nenhum timeframe aprovado pelos critérios mínimos de pesquisa."
                )
            st.write(getattr(result, "selected_reason", "N/D"))
            st.dataframe(
                [
                    _timeframe_candidate_row(candidate, result)
                    for candidate in list(getattr(result, "candidates", []) or [])
                ],
                hide_index=True,
                width="stretch",
            )


def _timeframe_optimizer_row(result: object) -> dict[str, object]:
    candidates = list(getattr(result, "candidates", []) or [])
    best_timeframe = getattr(result, "best_timeframe", "NONE")
    selected = next(
        (
            candidate
            for candidate in candidates
            if getattr(candidate, "timeframe", "") == best_timeframe
        ),
        None,
    )
    return {
        "Par": getattr(result, "symbol", "N/D"),
        "Melhor timeframe": best_timeframe,
        "Profit factor": _optional_factor(
            getattr(selected, "profit_factor", None)
            if selected is not None
            else 0.0
        ),
        "Win rate": _optional_percent(
            getattr(selected, "win_rate", None)
            if selected is not None
            else 0.0
        ),
        "Amostra": (
            int(getattr(selected, "sample_size", 0) or 0)
            if selected is not None
            else 0
        ),
        "Max drawdown": _optional_percent(
            getattr(selected, "max_drawdown", None)
            if selected is not None
            else 0.0
        ),
        "Confianca": _optional_percent(
            getattr(selected, "calibrated_confidence", None)
            if selected is not None
            else 0.0
        ),
        "Motivo": getattr(result, "selected_reason", "N/D"),
    }


def _timeframe_candidate_row(
    candidate: object,
    result: object,
) -> dict[str, object]:
    rejection_reason = str(getattr(candidate, "rejection_reason", "") or "")
    status = "REJEITADO" if rejection_reason else "APROVADO"
    return {
        "Par": getattr(candidate, "symbol", "N/D"),
        "Timeframe": getattr(candidate, "timeframe", "N/D"),
        "Status": status,
        "Rank score": _optional_number(getattr(candidate, "rank_score", 0.0)),
        "Amostra": int(getattr(candidate, "sample_size", 0) or 0),
        "Win rate": _optional_percent(getattr(candidate, "win_rate", 0.0)),
        "Profit factor": _optional_factor(getattr(candidate, "profit_factor", 0.0)),
        "Max drawdown": _optional_percent(getattr(candidate, "max_drawdown", 0.0)),
        "Confianca": _optional_percent(
            getattr(candidate, "calibrated_confidence", 0.0)
        ),
        "Rejection reason": rejection_reason or "APPROVED",
        "Selected reason": getattr(result, "selected_reason", "N/D"),
    }


def _timeframe_recommendations(data: object) -> dict[str, object]:
    return {
        str(getattr(result, "symbol", "")): result
        for result in list(getattr(data, "timeframe_optimizer", []) or [])
    }


def _timeframe_recommendation_values(result: object | None) -> dict[str, object]:
    if result is None:
        return {
            "best_timeframe": "NONE",
            "rank_score": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "sample_size": 0,
            "max_drawdown": 0.0,
            "selected_reason": "Nenhuma otimizacao de timeframe executada.",
            "rejection_reason": "NO_TIMEFRAME_OPTIMIZATION",
        }

    best_timeframe = str(getattr(result, "best_timeframe", "NONE") or "NONE")
    candidates = list(getattr(result, "candidates", []) or [])
    selected = next(
        (
            candidate
            for candidate in candidates
            if getattr(candidate, "timeframe", "") == best_timeframe
        ),
        None,
    )
    if selected is None:
        selected_reason = str(getattr(result, "selected_reason", "") or "")
        if best_timeframe == "NONE" and not selected_reason:
            selected_reason = (
                "Nenhum timeframe aprovado pelos criterios minimos de pesquisa."
            )
        rejection_reason = ", ".join(
            sorted(
                {
                    str(getattr(candidate, "rejection_reason", "") or "")
                    for candidate in candidates
                    if str(getattr(candidate, "rejection_reason", "") or "")
                }
            )
        )
        return {
            "best_timeframe": best_timeframe,
            "rank_score": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "sample_size": 0,
            "max_drawdown": 0.0,
            "selected_reason": selected_reason,
            "rejection_reason": rejection_reason or "NONE",
        }

    return {
        "best_timeframe": best_timeframe,
        "rank_score": float(getattr(selected, "rank_score", 0.0) or 0.0),
        "profit_factor": float(getattr(selected, "profit_factor", 0.0) or 0.0),
        "win_rate": float(getattr(selected, "win_rate", 0.0) or 0.0),
        "sample_size": int(getattr(selected, "sample_size", 0) or 0),
        "max_drawdown": float(getattr(selected, "max_drawdown", 0.0) or 0.0),
        "selected_reason": str(getattr(result, "selected_reason", "") or "N/D"),
        "rejection_reason": (
            str(getattr(selected, "rejection_reason", "") or "APPROVED")
        ),
    }


def _exibir_research_configuration(
    configuration: object | None,
    forex: object,
) -> None:
    if configuration is None:
        st.error("Contrato ConfigurationData indisponivel.")
        return
    with st.expander("Configuracao de Pesquisa", expanded=True):
        st.dataframe(
            [
                {
                    "Parametro": "Candles carregados",
                    "Valor": str(configuration.quantitative_score_candles_loaded),
                },
                {
                    "Parametro": "Lookback",
                    "Valor": str(configuration.quantitative_score_feature_lookback),
                },
                {
                    "Parametro": "Forward Return",
                    "Valor": (
                        f"{configuration.quantitative_score_forward_return_candles} "
                        "candles"
                    ),
                },
                {
                    "Parametro": "Fast MA",
                    "Valor": str(configuration.quantitative_score_fast_ma_period),
                },
                {
                    "Parametro": "Slow MA",
                    "Valor": str(configuration.quantitative_score_slow_ma_period),
                },
                {
                    "Parametro": "RSI",
                    "Valor": str(configuration.quantitative_score_rsi_period),
                },
                {
                    "Parametro": "ATR",
                    "Valor": str(configuration.quantitative_score_atr_period),
                },
                {
                    "Parametro": "Metodo Volatilidade",
                    "Valor": configuration.quantitative_score_volatility_bucket_method,
                },
                {
                    "Parametro": "Sample minimo",
                    "Valor": str(configuration.quantitative_score_min_sample_size),
                },
                {
                    "Parametro": "Profit Factor minimo",
                    "Valor": (
                        f"{configuration.quantitative_score_min_profit_factor:.2f}"
                    ),
                },
                {
                    "Parametro": "Win Rate minima",
                    "Valor": _optional_percent(
                        configuration.quantitative_score_min_win_rate
                    ),
                },
                {
                    "Parametro": "Drawdown maximo",
                    "Valor": _optional_percent(
                        configuration.quantitative_score_max_allowed_drawdown
                    ),
                },
                {
                    "Parametro": "Confidence Floor",
                    "Valor": _optional_percent(
                        configuration.quantitative_score_confidence_floor
                    ),
                },
                {
                    "Parametro": "Confidence Ceiling",
                    "Valor": _optional_percent(
                        configuration.quantitative_score_confidence_ceiling
                    ),
                },
                {
                    "Parametro": "Threshold Vol Low",
                    "Valor": str(configuration.quantitative_score_volatility_low_threshold),
                },
                {
                    "Parametro": "Threshold Vol High",
                    "Valor": str(configuration.quantitative_score_volatility_high_threshold),
                },
                {
                    "Parametro": "Threshold MA Flat",
                    "Valor": str(configuration.quantitative_score_ma_flat_threshold),
                },
                {
                    "Parametro": "Threshold MA Strong",
                    "Valor": str(configuration.quantitative_score_ma_strong_threshold),
                },
            ],
            hide_index=True,
            width="stretch",
        )
    _exibir_ultima_execucao_research(configuration, forex)


def _exibir_ultima_execucao_research(
    configuration: object,
    forex: object,
) -> None:
    row = _latest_research_execution_row(forex)
    with st.expander("Ultima Execucao do Research", expanded=True):
        st.dataframe(
            [
                {
                    "Parametro": "Candles carregados",
                    "Valor": str(configuration.quantitative_score_candles_loaded),
                },
                {
                    "Parametro": "Candles utilizados",
                    "Valor": str(row["candles_loaded"]),
                },
                {
                    "Parametro": "Forward Return",
                    "Valor": str(
                        configuration.quantitative_score_forward_return_candles
                    ),
                },
                {
                    "Parametro": "Sample encontrado",
                    "Valor": str(row["sample_size"]),
                },
                {
                    "Parametro": "Profit Factor encontrado",
                    "Valor": _optional_factor(row["profit_factor"]),
                },
                {
                    "Parametro": "Win Rate encontrada",
                    "Valor": _optional_percent(row["win_rate"]),
                },
                {
                    "Parametro": "Rejeicao",
                    "Valor": row["rejected_reason"],
                },
            ],
            hide_index=True,
            width="stretch",
        )


def _latest_research_execution_row(forex: object) -> dict[str, object]:
    pairs = list(getattr(forex, "pairs", []) or [])
    selected = next(
        (row for row in pairs if int(getattr(row, "candles_loaded", 0) or 0) > 0),
        None,
    )
    if selected is None:
        return {
            "candles_loaded": 0,
            "sample_size": 0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "confidence": 0.0,
            "rejected_reason": "NO_RESEARCH_EXECUTION",
        }
    rejection = str(getattr(selected, "rejected_reason", "") or "APPROVED")
    return {
        "candles_loaded": int(getattr(selected, "candles_loaded", 0) or 0),
        "sample_size": int(getattr(selected, "sample_size", 0) or 0),
        "profit_factor": float(getattr(selected, "profit_factor", 0.0) or 0.0),
        "win_rate": float(getattr(selected, "win_rate", 0.0) or 0.0),
        "confidence": float(getattr(selected, "confidence", 0.0) or 0.0),
        "rejected_reason": rejection,
    }


def _forex_signal_row(
    row: object,
    timeframe_result: object | None = None,
    filter_rules: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    lab_parameters = dict(getattr(row, "lab_parameters", {}) or {})
    if filter_rules is not None:
        filter_gate = _forex_entry_filter_summary(row, filter_rules)
    elif hasattr(row, "entry_filter_status"):
        filter_gate = {
            "status": str(getattr(row, "entry_filter_status", "OK") or "OK"),
            "parameter": str(
                getattr(row, "entry_filter_parameter", "SEM_FILTRO_ROBUSTO")
                or "SEM_FILTRO_ROBUSTO"
            ),
            "reading": str(getattr(row, "entry_filter_reading", "N/D") or "N/D"),
            "reason": str(
                getattr(row, "entry_filter_reason", "Sem filtro NV-V robusto aplicado.")
                or "Sem filtro NV-V robusto aplicado."
            ),
        }
    else:
        filter_gate = _forex_entry_filter_summary(row, [])
    return {
        "Par": getattr(row, "pair", "N/D"),
        "Status": getattr(row, "status", "N/D"),
        "TF vencedor Lab": getattr(
            row,
            "lab_timeframe",
            getattr(row, "timeframe", "N/D"),
        ),
        "Periodo de tempo": getattr(
            row,
            "lab_timeframe",
            getattr(row, "timeframe", "N/D"),
        ),
        "Timeframe MT5 lido": getattr(row, "timeframe", "N/D"),
        "Ultimo preco": _optional_price(getattr(row, "last_price", None)),
        "Horario": _friendly_candle_time(getattr(row, "last_candle_time", "N/D")),
        "Tendencia": getattr(row, "trend", "N/D"),
        "Zona Operacional": _forex_zone_label(row),
        "Alpha Lab": getattr(row, "lab_alpha_id", "ALPHA001"),
        "Beta Lab": getattr(row, "beta_id", "BETA001"),
        "Modo Beta": getattr(row, "beta_mode", "PROTECT_ONLY"),
        "Modelo Ativo": getattr(row, "active_model", "TREND_MOMENTUM"),
        "Fonte Config": getattr(row, "lab_configuration_source", "DEFAULT"),
        "Filtro entrada": filter_gate["status"],
        "Filtro parametro": filter_gate["parameter"],
        "Filtro leitura": filter_gate["reading"],
        "Filtro motivo": filter_gate["reason"],
        "ICT": f"{float(getattr(row, 'lab_ict_score', 0.0) or 0.0):.2f}",
        "Classe ICT": getattr(row, "lab_ict_grade", "E"),
        "Status ICT": getattr(row, "lab_ict_status", "REJEITADA"),
        "Uso ICT": getattr(row, "lab_ict_usage", "Rejeitada."),
        "Demo liberado ICT": _yes_no(getattr(row, "lab_ict_demo_allowed", False)),
        "Travas ICT": " | ".join(
            getattr(row, "lab_ict_rejection_reasons", ()) or ()
        )
        or "OK",
        "EMA curta Lab": _parameter_value(lab_parameters, "ema_curta"),
        "EMA longa Lab": _parameter_value(lab_parameters, "ema_longa"),
        "RSI sobrevenda Lab": _parameter_value(lab_parameters, "rsi_sobrevenda"),
        "RSI sobrecompra Lab": _parameter_value(lab_parameters, "rsi_sobrecompra"),
        "ATR stop Lab": _parameter_value(lab_parameters, "atr_stop_factor"),
        "RR Lab": _parameter_value(lab_parameters, "rr"),
        "Momentum min Lab": _parameter_value(lab_parameters, "momentum_threshold"),
        "Volatilidade min Lab": _parameter_value(lab_parameters, "volatility_threshold"),
        "ADX min Lab": _parameter_value(lab_parameters, "adx_min"),
        "Regime ATR Lab": _parameter_value(lab_parameters, "atr_regime"),
        "Largura Bollinger Lab": _parameter_value(lab_parameters, "bollinger_width_threshold"),
        "Z-Score min Lab": _parameter_value(lab_parameters, "z_threshold"),
        "Volume factor Lab": _parameter_value(lab_parameters, "volume_factor"),
        "Pullback tol Lab": _parameter_value(lab_parameters, "pullback_tolerance"),
        "Donchian periodo Lab": _parameter_value(lab_parameters, "donchian_period"),
        "Breakout buffer Lab": _parameter_value(lab_parameters, "breakout_buffer"),
        "Indicadores do modelo": " | ".join(
            list(getattr(row, "active_model_indicators", ()) or ())
        ),
        "Momentum": _optional_percent(getattr(row, "momentum", None)),
        "Volatilidade": _optional_percent(getattr(row, "volatility", None)),
        "RSI": _optional_number(getattr(row, "rsi", None)),
        "Media curta": _optional_price(getattr(row, "short_average", None)),
        "Media longa": _optional_price(getattr(row, "long_average", None)),
        "EMA rapida": _optional_price(getattr(row, "ema_fast", None)),
        "EMA principal": _optional_price(getattr(row, "ema_mid", None)),
        "EMA longa": _optional_price(getattr(row, "ema_slow", None)),
        "ADX": _optional_number(getattr(row, "adx", None)),
        "MACD": _optional_number(getattr(row, "macd", None)),
        "MACD signal": _optional_number(getattr(row, "macd_signal", None)),
        "ATR": _optional_number(getattr(row, "atr", None)),
        "ATR media": _optional_number(getattr(row, "atr_average", None)),
        "Bollinger superior": _optional_price(
            getattr(row, "bollinger_upper", None)
        ),
        "Bollinger inferior": _optional_price(
            getattr(row, "bollinger_lower", None)
        ),
        "Tick volume": _optional_int(getattr(row, "tick_volume", None)),
        "Tick volume media": _optional_number(
            getattr(row, "tick_volume_average", None)
        ),
        "Maxima dia": _optional_price(getattr(row, "day_high", None)),
        "Minima dia": _optional_price(getattr(row, "day_low", None)),
        "Donchian max": _optional_price(getattr(row, "donchian_high", None)),
        "Donchian min": _optional_price(getattr(row, "donchian_low", None)),
        "Pivot": _optional_price(getattr(row, "pivot", None)),
        "VWAP": _optional_price(getattr(row, "vwap", None)),
        "Z-Score": _optional_number(getattr(row, "z_score", None)),
        "Suporte": _optional_price(getattr(row, "support", None)),
        "Resistencia": _optional_price(getattr(row, "resistance", None)),
        "Swing high": _optional_price(getattr(row, "swing_high", None)),
        "Swing low": _optional_price(getattr(row, "swing_low", None)),
        "Spread": _optional_number(getattr(row, "spread", None)),
        "Spread media": _optional_number(getattr(row, "spread_average", None)),
        "Slippage estimado": _optional_number(
            getattr(row, "slippage_estimate", None)
        ),
        "Velocidade preco": _optional_number(getattr(row, "price_speed", None)),
        "Decisao": getattr(row, "decision", "WAIT"),
        "Entrada Teorica": getattr(row, "theoretical_entry_status", "SEM_GATILHO"),
        "Candle do Sinal": _friendly_candle_time(
            getattr(row, "theoretical_entry_candle", "N/D")
        ),
        "Preco Teorico": _optional_price(
            getattr(row, "theoretical_entry_price", None)
        ),
        "Direcao Teorica": getattr(row, "theoretical_entry_direction", "WAIT"),
        "Motivo Entrada": getattr(row, "theoretical_entry_reason", "N/D"),
        "Plano Research": getattr(row, "research_plan_status", "SEM_PLANO"),
        "Entrada Research": _optional_price(
            getattr(row, "research_plan_entry_price", None)
        ),
        "Stop Research": _optional_price(getattr(row, "research_plan_stop", None)),
        "Alvo Research": _optional_price(getattr(row, "research_plan_target", None)),
        "RR Research": _optional_number(
            getattr(row, "research_plan_risk_reward", None)
        ),
        "Risco pips": _optional_number(
            getattr(row, "research_plan_risk_pips", None)
        ),
        "Ganho pips": _optional_number(
            getattr(row, "research_plan_reward_pips", None)
        ),
        "Risco %": _optional_percent_value(
            getattr(row, "research_plan_risk_percent", None)
        ),
        "Ganho %": _optional_percent_value(
            getattr(row, "research_plan_reward_percent", None)
        ),
        "Modelo Saida": getattr(row, "research_plan_exit_model", "NONE"),
        "Gestao Stop": getattr(row, "research_plan_stop_management", "FIXED_STOP"),
        "Politica Saida Lab": getattr(row, "dynamic_exit_policy", "FIXED_STOP"),
        "Estado Mercado Saida": getattr(row, "dynamic_exit_market_state", "NO_POSITION"),
        "Recomendacao Saida": getattr(row, "dynamic_exit_action", "KEEP_ORIGINAL_PLAN"),
        "Motivo Saida Dinamica": getattr(row, "dynamic_exit_reason", "N/D"),
        "Confianca Saida Dinamica": _optional_percent(
            getattr(row, "dynamic_exit_confidence", None)
        ),
        "R Atual Saida": _optional_number(
            getattr(row, "dynamic_exit_r_multiple", None)
        ),
        "Stop Candidato": _optional_price(
            getattr(row, "dynamic_exit_candidate_stop", None)
        ),
        "Execucao Saida Permitida": _yes_no(
            getattr(row, "dynamic_exit_allowed_to_execute_demo", False)
        ),
        "Simulacao Saida": _yes_no(
            getattr(row, "dynamic_exit_simulation_enabled", False)
        ),
        "Gate Simulacao": (
            "APROVADO"
            if bool(getattr(row, "dynamic_exit_simulation_allowed", False))
            else "REJEITADO"
        ),
        "Stop Atual Simulado": _optional_price(
            getattr(row, "dynamic_exit_simulation_current_stop", None)
        ),
        "Stop Candidato Simulado": _optional_price(
            getattr(row, "dynamic_exit_simulation_candidate_stop", None)
        ),
        "Stop Aprovado Simulado": _optional_price(
            getattr(row, "dynamic_exit_simulation_approved_stop", None)
        ),
        "Motivos Gate Simulacao": " | ".join(
            getattr(row, "dynamic_exit_simulation_rejection_reasons", ()) or ()
        )
        or "N/D",
        "Modo SL Assistido": _yes_no(
            getattr(row, "dynamic_exit_demo_sl_assisted_enabled", False)
        ),
        "Gate SL Assistido": getattr(
            row,
            "dynamic_exit_demo_sl_assisted_gate",
            "REJEITADO",
        ),
        "Mensagem SL Assistido": getattr(
            row,
            "dynamic_exit_demo_sl_assisted_message",
            "Modo assistido desligado.",
        ),
        "Parametros Gestao": " | ".join(
            f"{key}={value}"
            for key, value in (
                getattr(row, "research_plan_stop_management_parameters", {}) or {}
            ).items()
        )
        or "N/D",
        "Motivo Gestao": (
            getattr(row, "research_plan_stop_management_reason", "") or "N/D"
        ),
        "Motivo Stop": getattr(row, "research_plan_stop_reason", "") or "N/D",
        "Motivo Alvo": getattr(row, "research_plan_target_reason", "") or "N/D",
        "Stop ATR": _optional_number(
            getattr(row, "research_plan_stop_multiplier", None)
        ),
        "Score Saida": _optional_number(getattr(row, "research_plan_exit_score", None)),
        "Combinacoes Saida": int(
            getattr(row, "research_plan_exit_candidates", 0) or 0
        ),
        "Motivo Plano": getattr(row, "research_plan_reason", "N/D"),
        "Codigo Rejeicao": getattr(row, "research_plan_invalid_reason", "") or "N/D",
        "Campos Invalidos": " | ".join(
            list(getattr(row, "research_plan_invalid_fields", ()) or ())
        )
        or "N/D",
        "Proxima Tentativa": getattr(row, "research_plan_next_retry", "") or "N/D",
        "Gatilho Esperado": (
            getattr(row, "research_plan_expected_trigger", "") or "N/D"
        ),
        "RR Atual": _optional_number(getattr(row, "research_plan_rr_current", None)),
        "RR Minimo": _optional_number(getattr(row, "research_plan_rr_minimum", None)),
        "Candles recebidos": int(getattr(row, "received_candles", 0) or 0),
        "Ultima atualizacao": getattr(row, "last_update", ""),
        "Motivo": getattr(row, "reason", "N/D"),
    }


def _forex_entry_filter_summary(
    row: object,
    filter_rules: list[dict[str, object]],
) -> dict[str, str]:
    """Resume filtros positivos NV-V sem recalcular historico."""
    if not filter_rules:
        return {
            "status": "OK_SEM_FILTRO",
            "parameter": "SEM_FILTRO_ROBUSTO",
            "reading": "N/D",
            "reason": (
                "Sem filtro NV-V robusto para o par "
                f"(min {MT5_ENTRY_FILTER_MIN_EDGE:.0%}, "
                f"amostra {MT5_ENTRY_FILTER_MIN_SAMPLE_SIZE})."
            ),
        }
    blocked: list[str] = []
    waiting: list[str] = []
    passed: list[str] = []
    for rule in filter_rules:
        indicator = str(rule.get("indicator", "N/D") or "N/D")
        present = _forex_entry_filter_indicator_present(row, indicator)
        required_present = bool(rule.get("required_present", True))
        label = _forex_entry_filter_rule_label(rule)
        if present is None:
            waiting.append(label)
        elif present == required_present:
            passed.append(label)
        else:
            blocked.append(label)
    if blocked:
        return {
            "status": "BLOQUEADO",
            "parameter": _forex_entry_filter_parameter_text(filter_rules),
            "reading": " | ".join(passed + waiting + blocked),
            "reason": "Filtro NV-V presente: " + " | ".join(blocked),
        }
    if waiting:
        return {
            "status": "AGUARDA",
            "parameter": _forex_entry_filter_parameter_text(filter_rules),
            "reading": " | ".join(passed + waiting),
            "reason": "Leitura indisponivel para: " + " | ".join(waiting),
        }
    return {
        "status": "OK",
        "parameter": _forex_entry_filter_parameter_text(filter_rules),
        "reading": " | ".join(passed),
        "reason": "Todos os filtros positivos NV-V estao ausentes.",
    }


def _forex_entry_filter_parameter_text(
    filter_rules: list[dict[str, object]],
) -> str:
    if not filter_rules:
        return "SEM_FILTRO_NV_V"
    return " | ".join(
        (
            f"{rule.get('indicator', 'N/D')} "
            f"{rule.get('source', 'NV-V')} "
            f"{_optional_signed_percent(rule.get('entry_edge', 0.0))} "
            f"{_entry_filter_action_text(rule)}"
        )
        for rule in filter_rules
    )


def _forex_entry_filter_rule_label(rule: dict[str, object]) -> str:
    return (
        f"{rule.get('indicator', 'N/D')} "
        f"V {_optional_percent(rule.get('winner_rate', 0.0))} x "
        f"NV {_optional_percent(rule.get('loser_rate', 0.0))} | "
        f"{rule.get('source', 'NV-V')} "
        f"{_optional_signed_percent(rule.get('entry_edge', 0.0))} | "
        f"{_entry_filter_action_text(rule)}"
    )


def _entry_filter_action_text(rule: dict[str, object]) -> str:
    if bool(rule.get("required_present", True)):
        return "liberar se presente"
    return "liberar se ausente"


def _forex_entry_filter_indicator_present(
    row: object,
    indicator: str,
) -> bool | None:
    """Avalia somente filtros que existem na leitura leve atual do Forex."""
    normalized = _normalize_filter_indicator_name(indicator)
    direction = str(
        getattr(row, "theoretical_entry_direction", getattr(row, "decision", "WAIT"))
        or "WAIT"
    ).upper()
    if normalized == "ADX BAIXO":
        adx = _optional_float(getattr(row, "adx", None))
        return None if adx is None else adx < MT5_ENTRY_FILTER_ADX_LOW_THRESHOLD
    if normalized == "ATR EM QUEDA":
        atr = _optional_float(getattr(row, "atr", None))
        atr_average = _optional_float(getattr(row, "atr_average", None))
        if atr is None or atr_average is None:
            return None
        return atr < atr_average
    if normalized == "ATR SUBINDO":
        atr = _optional_float(getattr(row, "atr", None))
        atr_average = _optional_float(getattr(row, "atr_average", None))
        if atr is None or atr_average is None:
            return None
        return atr > atr_average
    if normalized == "MOMENTUM CONTRA":
        momentum = _optional_float(getattr(row, "momentum", None))
        if momentum is None or direction not in {"BUY", "SELL"}:
            return None
        return momentum < 0.0 if direction == "BUY" else momentum > 0.0
    if normalized == "MACD HIST DIVERGENTE":
        macd = _optional_float(getattr(row, "macd", None))
        macd_signal = _optional_float(getattr(row, "macd_signal", None))
        if macd is None or macd_signal is None or direction not in {"BUY", "SELL"}:
            return None
        return macd < macd_signal if direction == "BUY" else macd > macd_signal
    return None


def _normalize_filter_indicator_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(ascii_text.upper().replace("_", " ").split())


def _optional_signed_percent(value: object) -> str:
    numeric = _optional_float(value)
    if numeric is None:
        return "N/D"
    return f"{numeric:+.2%}"


def _styled_forex_signal_rows(rows: list[object]) -> object:
    """Aplica cor institucional por decisao sem alterar os dados."""
    pd = __import__("pandas")
    dataframe = pd.DataFrame(rows)
    return dataframe.style.apply(_forex_decision_row_style, axis=1)


def _forex_decision_row_style(row: object) -> list[str]:
    decision = _normalize_forex_decision(row.get("Decisao", "WAIT"))
    if decision == "BUY":
        row_style = "background-color: #DDF7E3; color: #0F3D24; font-weight: 600;"
    elif decision == "SELL":
        row_style = "background-color: #FDE0E0; color: #5C1A1A; font-weight: 600;"
    else:
        row_style = "background-color: #FFFFFF; color: #111827;"

    active_columns = _forex_active_indicator_columns(row.get("Modelo Ativo", ""))
    styles = []
    columns = getattr(row, "index", None)
    if columns is None:
        columns = row.keys()
    for column in columns:
        if column in active_columns:
            styles.append(
                "background-color: #DBEAFE; color: #0F172A; font-weight: 700;"
            )
        elif column in {"Decisao", "Entrada Teorica", "Direcao Teorica"}:
            styles.append(row_style)
        else:
            styles.append(row_style)
    return styles


def _forex_active_indicator_columns(model: object) -> set[str]:
    normalized = str(model or "").upper()
    shared = {
        "Periodo de tempo",
        "Alpha Lab",
        "Beta Lab",
        "Modo Beta",
        "Modelo Ativo",
        "Fonte Config",
        "Filtro entrada",
        "Filtro parametro",
        "Filtro leitura",
        "Filtro motivo",
        "ICT",
        "Classe ICT",
        "Status ICT",
        "Demo liberado ICT",
        "ATR stop Lab",
        "RR Lab",
    }
    if normalized == "MA_RSI_FILTER":
        return shared | {
            "Media curta",
            "Media longa",
            "RSI",
            "EMA curta Lab",
            "EMA longa Lab",
            "RSI sobrevenda Lab",
            "RSI sobrecompra Lab",
        }
    if normalized == "RSI_REVERSAL":
        return shared | {
            "RSI",
            "RSI sobrevenda Lab",
            "RSI sobrecompra Lab",
        }
    if normalized == "TREND_MOMENTUM":
        return shared | {
            "Tendencia",
            "Momentum",
            "Volatilidade",
            "EMA curta Lab",
            "EMA longa Lab",
            "Momentum min Lab",
            "Volatilidade min Lab",
        }
    if normalized == "TREND_PULLBACK":
        return shared | {
            "Tendencia",
            "Media curta",
            "Media longa",
            "ADX",
            "EMA curta Lab",
            "EMA longa Lab",
            "ADX min Lab",
            "Pullback tol Lab",
        }
    if normalized == "BREAKOUT_CONSOLIDATION":
        return shared | {
            "Momentum",
            "Volatilidade",
            "ATR",
            "Momentum min Lab",
            "Volatilidade min Lab",
        }
    if normalized == "DONCHIAN_BREAKOUT":
        return shared | {
            "Maxima dia",
            "Minima dia",
            "Donchian max",
            "Donchian min",
            "Momentum",
            "Donchian periodo Lab",
            "Breakout buffer Lab",
            "Momentum min Lab",
        }
    if normalized == "ADX_TREND_STRENGTH":
        return shared | {"EMA rapida", "EMA longa", "ADX", "ATR", "Momentum", "ADX min Lab"}
    if normalized == "MACD_MOMENTUM_SHIFT":
        return shared | {"MACD", "MACD signal", "EMA rapida", "EMA longa", "ATR"}
    if normalized == "BOLLINGER_VOLATILITY_EXPANSION":
        return shared | {
            "Bollinger superior",
            "Bollinger inferior",
            "ATR",
            "Momentum",
            "Tick volume",
            "Tick volume media",
            "Largura Bollinger Lab",
        }
    if normalized == "ATR_VOLATILITY_REGIME":
        return shared | {"ATR", "ATR media", "Volatilidade", "EMA rapida", "EMA longa", "Regime ATR Lab"}
    if normalized == "DONCHIAN_STRUCTURE_BREAKOUT":
        return shared | {"Donchian max", "Donchian min", "Swing high", "Swing low", "ATR", "Momentum", "Donchian periodo Lab"}
    if normalized == "PIVOT_REJECTION":
        return shared | {"Pivot", "RSI", "ATR", "RSI sobrevenda Lab", "RSI sobrecompra Lab"}
    if normalized == "VWAP_MEAN_REVERSION":
        return shared | {"VWAP", "Z-Score", "RSI", "ATR", "Z-Score min Lab"}
    if normalized == "SUPPORT_RESISTANCE_REACTION":
        return shared | {"Suporte", "Resistencia", "Swing high", "Swing low", "RSI", "ATR"}
    if normalized == "MULTI_TIMEFRAME_ALIGNMENT":
        return shared | {"EMA rapida", "EMA longa", "Tendencia", "Momentum", "EMA curta Lab", "EMA longa Lab"}
    if normalized == "LIQUIDITY_SPREAD_FILTER":
        return shared | {"Spread", "Spread media", "Tick volume", "Tick volume media", "Volume factor Lab"}
    return set()


def _parameter_value(parameters: dict[str, object], key: str) -> str:
    value = parameters.get(key)
    if value is None or value == "":
        return "N/D"
    return str(value)


def _forex_decision_counts(rows: list[dict[str, object]]) -> dict[str, int]:
    counts = {"BUY": 0, "SELL": 0, "WAIT": 0}
    for row in rows:
        decision = _normalize_forex_decision(row.get("Decisao", "WAIT"))
        counts[decision] = counts.get(decision, 0) + 1
    return counts


def _normalize_forex_decision(value: object) -> str:
    decision = str(value or "WAIT").strip().upper()
    if decision in {"BUY", "SELL"}:
        return decision
    return "WAIT"


def _optional_price(value: object) -> str:
    if value is None:
        return "N/D"
    try:
        return f"{float(value):.5f}"
    except (TypeError, ValueError):
        return "N/D"


def _optional_percent(value: object) -> str:
    if value is None:
        return "N/D"
    try:
        return f"{float(value):.2%}"
    except (TypeError, ValueError):
        return "N/D"


def _optional_percent_value(value: object) -> str:
    if value is None:
        return "N/D"
    try:
        return f"{float(value):.4f}%"
    except (TypeError, ValueError):
        return "N/D"


def _optional_number(value: object) -> str:
    if value is None:
        return "N/D"
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "N/D"


def _optional_int(value: object) -> str:
    if value is None:
        return "N/D"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "N/D"


def _optional_factor(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/D"
    if number == float("inf"):
        return "inf"
    return f"{number:.2f}"


def _friendly_candle_time(value: object) -> str:
    return str(value or "N/D")


def _tuple_text(value: object) -> str:
    if not value:
        return "N/D"
    if isinstance(value, str):
        return value
    try:
        return ", ".join(str(item) for item in value)
    except TypeError:
        return str(value)


def exibir_home_overview(data: object) -> None:
    """Exibe atalhos visuais das principais areas do dashboard."""
    with st.container(border=True):
        st.subheader("Status Geral")
        exibir_status_bar(data)

    colunas = st.columns(2)
    with colunas[0]:
        with st.container(border=True):
            st.subheader("Replay")
            replay_data = getattr(data, "replay_data", None)
            replay_cols = st.columns(3)
            replay_cols[0].metric(
                "Candles",
                getattr(replay_data, "total_candles", 0),
            )
            replay_cols[1].metric(
                "Indice",
                getattr(replay_data, "current_index", 0),
            )
            replay_cols[2].metric("Status", _replay_status(replay_data))

    with colunas[1]:
        with st.container(border=True):
            st.subheader("Live")
            live_status = getattr(data, "live_research_status", None)
            safety_status = getattr(data, "safety_status", None)
            live_cols = st.columns(3)
            live_cols[0].metric("Simbolo", getattr(live_status, "symbol", "N/D"))
            live_cols[1].metric(
                "Timeframe",
                getattr(live_status, "timeframe", "N/D"),
            )
            live_cols[2].metric(
                "Seguranca",
                getattr(safety_status, "status", "READ ONLY"),
            )

    with st.container(border=True):
        st.subheader("Research")
        experiments = getattr(data, "research_lab_experiments", [])
        benchmarks = getattr(data, "research_benchmarks", [])
        research_cols = st.columns(3)
        research_cols[0].metric("Experimentos", len(experiments))
        research_cols[1].metric("Benchmarks", len(benchmarks))
        research_cols[2].metric(
            "Live signals",
            getattr(
                getattr(data, "live_experiment_summary", None),
                "total_signals",
                0,
            ),
        )


def exibir_status_geral_dashboard(data: object) -> None:
    """Exibe status geral organizado por containers e expanders."""
    with st.container(border=True):
        st.subheader("Status Geral")
        exibir_status_bar(data)
    with st.expander("Dataset ativo", expanded=True):
        exibir_dataset_ativo(data)
    with st.expander("Market DNA", expanded=False):
        exibir_market_dna(data)
    with st.expander("Pesquisa quantitativa", expanded=False):
        exibir_pesquisa_quantitativa(data)


def exibir_sistema_dashboard(data: object, service: DashboardService | None = None) -> None:
    """Exibe paineis de sistema sem alterar comportamento."""
    with st.container(border=True):
        exibir_sistema_forex(data, service)


def exibir_sistema_forex(
    data: object,
    service: DashboardService | None = None,
) -> None:
    """Exibe sistema simplificado para a experiencia Forex MT5."""
    status = data.system_status
    forex = getattr(data, "mt5_forex_signals", None)
    research = getattr(data, "mt5_heuristic_research", None)
    robot = getattr(data, "demo_robot", None)

    st.subheader("Sistema Forex MT5")
    colunas = st.columns(4)
    colunas[0].metric("App", "ONLINE" if status.status else "OFFLINE")
    colunas[1].metric("MT5", getattr(forex, "connection_status", "N/D"))
    colunas[2].metric("Conta", getattr(forex, "account", "N/D"))
    colunas[3].metric("Servidor", getattr(forex, "server", "N/D"))

    colunas = st.columns(4)
    colunas[0].metric("Timeframe", getattr(forex, "timeframe", "M1"))
    colunas[1].metric(
        "Pares monitorados",
        len(list(getattr(forex, "pairs", []) or [])),
    )
    colunas[2].metric(
        "Candles recebidos",
        int(getattr(forex, "safe_mode_received_candles", 0) or 0),
    )
    colunas[3].metric("Research", getattr(research, "status", "SEM_CALIBRACAO"))

    colunas = st.columns(4)
    colunas[0].metric("Robo demo", getattr(robot, "status", "N/D"))
    colunas[1].metric(
        "Envio MT5 Demo",
        getattr(robot, "mt5_order" + "_send_status", "N/D"),
    )
    colunas[2].metric("Operacao real", "BLOQUEADA")
    colunas[3].metric("Versao", status.version)

    st.warning(
        "Sistema em modo Forex-only. Esta tela usa somente MT5 Forex, "
        "calibracao sob demanda e execucao demo controlada."
    )
    if service is not None:
        _render_runtime_performance_controls(service, data)
    exibir_configuracoes_forex_readonly(data)


def _render_runtime_performance_controls(
    service: DashboardService,
    data: object,
) -> None:
    """Exibe diagnostico leve e reset seguro de runtime."""
    with st.expander("Diagnostico de performance / lentidao", expanded=False):
        snapshot = _runtime_performance_snapshot(service, data)
        message = st.session_state.get(RUNTIME_CLEANUP_MESSAGE_KEY)
        if message:
            st.success(str(message))
        legacy_message = st.session_state.get(LEGACY_PROCESS_GUARD_MESSAGE_KEY)
        if legacy_message:
            st.info(str(legacy_message))

        controls = st.columns([1, 1, 2])
        if controls[0].button(
            "Limpar filas e caches temporarios do runtime",
            key="runtime_clear_temporary_queues",
        ):
            removed = _clear_runtime_queues_and_temporary_caches()
            st.session_state[RUNTIME_CLEANUP_MESSAGE_KEY] = (
                "Filas e caches temporarios limpos. Reinicie o ciclo MT5 "
                "manualmente se necessario."
            )
            st.caption(f"Itens temporarios limpos: {len(removed)}")

        if bool(st.session_state.get(MT5_FOREX_AUTO_CYCLE_UI_KEY, False)):
            if controls[1].button(
                "Pausar ciclo automatico MT5 Forex",
                key="runtime_pause_mt5_forex_auto_cycle",
            ):
                st.session_state[MT5_FOREX_AUTO_CYCLE_UI_KEY] = False
                st.session_state[RUNTIME_CLEANUP_MESSAGE_KEY] = (
                    "Ciclo automatico MT5 Forex pausado nesta sessao."
                )
        else:
            controls[1].caption("Ciclo automatico MT5 Forex pausado.")

        _render_runtime_performance_snapshot(snapshot)


def _render_runtime_performance_snapshot(snapshot: dict[str, object]) -> None:
    rows = [
        {"Metrica": key, "Valor": _runtime_snapshot_value(value)}
        for key, value in snapshot.items()
    ]
    _render_stable_readonly_table(rows)


def _runtime_snapshot_value(value: object) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}={val}" for key, val in value.items()) or "{}"
    return str(value)


def exibir_configuracoes_forex_readonly(data: object) -> None:
    """Exibe configuracoes relevantes para a experiencia Forex."""
    configuration = getattr(data, "configuration_data", None)
    if configuration is None:
        st.info("Configuracoes Forex indisponiveis.")
        return

    st.subheader("Configuracao Forex")
    colunas = st.columns(4)
    colunas[0].metric("Candles online por par", configuration.mt5_safe_mode_candles_loaded)
    colunas[1].metric("Candles da pesquisa", configuration.quantitative_score_candles_loaded)
    colunas[2].metric("Media curta", configuration.mt5_safe_mode_fast_ma_period)
    colunas[3].metric("Media longa", configuration.mt5_safe_mode_slow_ma_period)
    colunas = st.columns(4)
    colunas[0].metric("RSI", configuration.mt5_safe_mode_rsi_period)
    colunas[1].metric("Momentum", configuration.mt5_safe_mode_momentum_period)
    colunas[2].metric("Volatilidade", configuration.mt5_safe_mode_volatility_period)
    colunas[3].metric("Modo", "READ ONLY / DEMO CONTROLADO")


def exibir_replay_dashboard(service: DashboardService, data: object) -> None:
    """Exibe repeticao Forex par-a-par dentro da navegacao principal."""
    with st.container(border=True):
        exibir_replay_forex_pair_dashboard(service, data)


def exibir_replay_forex_pair_dashboard(
    service: DashboardService,
    data: object,
) -> object:
    """Exibe analise de repeticao por par Forex sem datasets legados."""
    forex = getattr(data, "mt5_forex_signals", None)
    research = getattr(data, "mt5_heuristic_research", None)

    st.subheader("Replay Forex")
    st.caption(
        "Analise manual par-a-par usando somente pares Forex da fachada "
        "DashboardService. PETR/WDO e datasets historicos legados ficam fora "
        "desta aba."
    )

    pair_options = _forex_replay_pair_options(forex)
    timeframe_options = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]
    controles = st.columns([1, 1, 1, 1])
    selected_pair = controles[0].selectbox(
        "Par Forex do Replay",
        pair_options,
        index=_selected_index(pair_options, pair_options[0]),
        key="replay_forex_pair",
    )
    selected_timeframe = controles[1].selectbox(
        "Timeframe Forex do Replay",
        timeframe_options,
        index=_selected_index(
            timeframe_options,
            getattr(forex, "timeframe", "M1") if forex is not None else "M1",
        ),
        key="replay_forex_timeframe",
    )
    if controles[2].button("Carregar par Forex", key="replay_forex_load_pair"):
        _load_mt5_forex_signals_locked(service, timeframe=selected_timeframe)
        data = service.get_dashboard_view_model()
        forex = getattr(data, "mt5_forex_signals", forex)
        research = getattr(data, "mt5_heuristic_research", research)
    if controles[3].button("Executar Pesquisa do Par", key="replay_forex_run_pair"):
        research = service.run_mt5_research_calibration_for_pair(
            selected_pair,
            timeframe=selected_timeframe,
        )

    pair_row = _find_forex_replay_pair_row(forex, selected_pair)
    _exibir_replay_forex_pair_snapshot(pair_row)

    pair_scenarios = _filter_mt5_scenarios_by_pair(research, selected_pair)
    st.markdown("### Melhor cenario do par")
    best_rows = _mt5_best_directional_scenario_rows(pair_scenarios)
    if best_rows:
        _render_stable_readonly_table(best_rows)
    else:
        st.info(
            "Nenhum cenario calculado para este par. Clique em Executar "
            "Pesquisa do Par para analisar somente o par selecionado."
        )

    st.markdown("### Ranking do par")
    if pair_scenarios:
        _render_stable_readonly_table(
            [_mt5_scenario_row(scenario) for scenario in pair_scenarios[:30]]
        )
    else:
        st.info("Ranking do par ainda vazio.")
    return data


def _forex_replay_pair_options(forex: object) -> list[str]:
    pairs = [
        str(getattr(row, "pair", "") or "").upper()
        for row in list(getattr(forex, "pairs", []) or [])
        if str(getattr(row, "pair", "") or "").strip()
    ]
    unique_pairs = list(dict.fromkeys(pairs))
    return unique_pairs or [
        "EURUSD",
        "GBPUSD",
        "USDCHF",
        "USDJPY",
        "AUDUSD",
        "NZDUSD",
        "EURJPY",
        "USDCAD",
    ]


def _find_forex_replay_pair_row(forex: object, pair: str) -> object | None:
    pair_key = str(pair or "").upper()
    for row in list(getattr(forex, "pairs", []) or []):
        if str(getattr(row, "pair", "") or "").upper() == pair_key:
            return row
    return None


def _filter_mt5_scenarios_by_pair(research: object, pair: str) -> list[object]:
    pair_key = str(pair or "").upper()
    return [
        scenario
        for scenario in list(getattr(research, "scenario_ranking", []) or [])
        if str(getattr(scenario, "pair", "") or "").upper() == pair_key
    ]


def _exibir_replay_forex_pair_snapshot(row: object | None) -> None:
    st.markdown("### Leitura Forex do par")
    if row is None:
        st.info("Par Forex ainda nao carregado na leitura atual.")
        return
    display_row = _forex_signal_row(row)
    colunas = st.columns(5)
    colunas[0].metric("Par", display_row.get("Par", "N/D"))
    colunas[1].metric("Decisao", display_row.get("Decisao", "WAIT"))
    colunas[2].metric(
        "Timeframe",
        display_row.get("Periodo de tempo", display_row.get("Timeframe", "N/D")),
    )
    colunas[3].metric("Ultimo preco", display_row.get("Ultimo preco", "N/D"))
    colunas[4].metric("Horario", display_row.get("Horario", "N/D"))
    _render_stable_readonly_table([display_row])


def exibir_live_dashboard(service: DashboardService, data: object) -> None:
    """Exibe area Live Research dentro da nova navegacao."""
    data = exibir_mt5_market_data(service, data)
    exibir_live_research_read_only(data)


def exibir_mt5_market_data(
    service: DashboardService,
    data: object,
) -> object:
    """Exibe leitura MT5 read-only via DashboardService."""
    mt5_data = getattr(data, "mt5_market_data", None)
    if mt5_data is None:
        st.info("MT5 MARKET DATA indisponivel no contrato do dashboard.")
        return data

    with st.container(border=True):
        st.subheader("MT5 MARKET DATA")
        st.caption("SOMENTE MARKET DATA. OPERACAO REAL NAO AUTORIZADA.")

        symbol_options = _mt5_symbol_options(mt5_data)
        timeframe_options = _mt5_timeframe_options(mt5_data)
        controles = st.columns([1, 1, 1, 1])
        selected_symbol = controles[0].selectbox(
            "Simbolo MT5",
            symbol_options,
            index=_selected_index(symbol_options, getattr(mt5_data, "selected_symbol", "EURUSD")),
            key="mt5_market_data_symbol",
        )
        selected_timeframe = controles[1].selectbox(
            "Timeframe MT5",
            timeframe_options,
            index=_selected_index(
                timeframe_options,
                getattr(mt5_data, "selected_timeframe", "H1"),
            ),
            key="mt5_market_data_timeframe",
        )
        candle_count = controles[2].number_input(
            "Candles",
            min_value=1,
            max_value=1000,
            value=max(1, int(getattr(mt5_data, "candles_loaded", 100) or 100)),
            step=10,
            key="mt5_market_data_count",
        )
        if controles[3].button("Carregar MT5", key="mt5_market_data_load"):
            service.load_mt5_market_data(
                symbol=selected_symbol,
                timeframe=selected_timeframe,
                count=int(candle_count),
            )
            data = service.get_dashboard_view_model()
            mt5_data = getattr(data, "mt5_market_data", mt5_data)

        colunas = st.columns(4)
        colunas[0].metric("Status MT5", getattr(mt5_data, "connection_status", "N/D"))
        colunas[1].metric("Servidor", getattr(mt5_data, "server", "N/D"))
        colunas[2].metric("Conta", getattr(mt5_data, "account", "N/D"))
        colunas[3].metric("Tipo da conta", getattr(mt5_data, "account_type", "N/D"))

        colunas = st.columns(4)
        colunas[0].metric("Simbolo selecionado", getattr(mt5_data, "selected_symbol", "N/D"))
        colunas[1].metric("Timeframe selecionado", getattr(mt5_data, "selected_timeframe", "N/D"))
        colunas[2].metric("Candles carregados", getattr(mt5_data, "candles_loaded", 0))
        colunas[3].metric(
            "Modo MT5",
            getattr(mt5_data, "read_only_status", "SOMENTE MARKET DATA"),
        )

        st.caption("Simbolos disponiveis")
        st.write(", ".join(getattr(mt5_data, "available_symbols", []) or symbol_options))
        st.caption("Mensagem da conexao")
        st.write(getattr(mt5_data, "message", "N/D"))
        st.warning("OPERACAO REAL NAO AUTORIZADA")

        last_candle = getattr(mt5_data, "last_candle", None)
        exibir_mt5_last_candle(last_candle)
        exibir_mt5_price_chart(mt5_data)
    return data


def _mt5_symbol_options(mt5_data: object) -> list[str]:
    available = list(getattr(mt5_data, "available_symbols", []) or [])
    supported = list(getattr(mt5_data, "supported_symbols", []) or [])
    options = [symbol for symbol in supported if symbol in set(available)]
    if options:
        return options
    if supported:
        return supported
    if available:
        return available
    return ["EURUSD", "GBPUSD", "USDCHF", "USDJPY"]


def _mt5_timeframe_options(mt5_data: object) -> list[str]:
    options = list(getattr(mt5_data, "supported_timeframes", []) or [])
    return options or ["M1", "M5", "M15", "H1", "D1"]


def exibir_mt5_last_candle(last_candle: object | None) -> None:
    """Exibe ultimo candle MT5 carregado."""
    with st.container(border=True):
        st.subheader("Ultimo candle MT5")
        if last_candle is None:
            st.info("Nenhum candle MT5 carregado nesta sessao.")
            return
        colunas = st.columns(6)
        colunas[0].metric(
            "Horario",
            _friendly_candle_time(getattr(last_candle, "timestamp", "N/D")),
        )
        colunas[1].metric("Open", _price_label(getattr(last_candle, "open", 0.0)))
        colunas[2].metric("High", _price_label(getattr(last_candle, "high", 0.0)))
        colunas[3].metric("Low", _price_label(getattr(last_candle, "low", 0.0)))
        colunas[4].metric("Close", _price_label(getattr(last_candle, "close", 0.0)))
        colunas[5].metric("Volume", getattr(last_candle, "volume", 0))


def exibir_mt5_price_chart(mt5_data: object) -> None:
    """Exibe grafico simples dos candles MT5 carregados."""
    candles = list(getattr(mt5_data, "candles", []) or [])
    if not candles:
        return
    st.caption("Preco de fechamento")
    st.line_chart(
        {
            "close": {
                getattr(candle, "timestamp", str(index)): getattr(candle, "close", 0.0)
                for index, candle in enumerate(candles)
            }
        }
    )


def exibir_research_dashboard(service: DashboardService, data: object) -> None:
    """Exibe area Research Lab dentro da nova navegacao."""
    with st.container(border=True):
        st.subheader("Laboratorio de Pesquisa Forex")
        exibir_research_lab_actions(service)
        show_full_lab_audit = bool(
            st.session_state.get("research_show_full_lab_audit", False)
        )
        research_snapshot = _research_lab_snapshot_for_display(
            service,
            include_full_audit=show_full_lab_audit,
        )
        data = replace(
            service.get_light_dashboard_view_model(),
            mt5_heuristic_research=research_snapshot,
        )
        exibir_research_lab_data(
            service,
            data,
            include_full_audit=show_full_lab_audit,
        )


def exibir_dataset_ativo(data: object) -> None:
    """Exibe o dataset institucional ativo via DashboardService."""
    dataset = getattr(data, "active_dataset", None)
    datasets = getattr(data, "available_datasets", [])
    st.subheader("DATASET DE PESQUISA ATIVO")
    if dataset is None:
        st.info("Nenhum dataset ativo identificado pela camada de aplicacao.")
        return

    colunas = st.columns(4)
    colunas[0].metric("Dataset de pesquisa", dataset.asset)
    colunas[1].metric("Timeframe", dataset.timeframe.upper())
    colunas[2].metric("Candles Dataset", valor_ou_indisponivel(dataset.candles))
    colunas[3].metric("Status", dataset.status)

    colunas = st.columns(4)
    colunas[0].metric("Fonte", dataset.source)
    colunas[1].metric("Provider", dataset.provider)
    colunas[2].metric("Status Replay", dataset.replay_status)
    colunas[3].metric("Status Research Lab", dataset.research_status)

    st.caption("Dataset")
    st.write(dataset.dataset_id)
    st.caption("Periodo")
    st.write(dataset.period)
    st.caption("Ultima atualizacao")
    st.write(dataset.last_update)
    st.caption("Checksum")
    st.code(dataset.checksum)
    st.caption("Metadata Version")
    st.write(dataset.metadata_version)
    st.caption("Dataset Certification")
    st.write(dataset.dataset_certification)
    st.caption("Architecture")
    st.write(dataset.architecture_status)

    if len(datasets) > 1:
        st.subheader("DATASETS DISPONIVEIS")
        exibir_registros_readonly(_available_datasets_table(datasets))


def exibir_perfil_dataset(data: object) -> None:
    """Exibe perfil quantitativo do dataset historico ativo."""
    profile = getattr(data, "dataset_profile", None)
    if profile is None:
        return

    st.subheader("PERFIL DO DATASET")
    colunas = st.columns(4)
    colunas[0].metric("Ativo", profile.asset)
    colunas[1].metric("Timeframe", profile.timeframe.upper())
    colunas[2].metric("Candles", profile.candles)
    colunas[3].metric("Status de qualidade", profile.quality_status)

    colunas = st.columns(4)
    colunas[0].metric("Periodo", profile.period)
    colunas[1].metric("Preco inicial", _price_label(profile.initial_price))
    colunas[2].metric("Preco final", _price_label(profile.final_price))
    colunas[3].metric(
        "Retorno acumulado",
        _percent_metric(profile.accumulated_return),
    )

    colunas = st.columns(4)
    colunas[0].metric(
        "Retorno anualizado",
        _percent_metric(profile.annualized_return),
    )
    colunas[1].metric(
        "Volatilidade anualizada",
        _percent_metric(profile.annualized_volatility),
    )
    colunas[2].metric("Drawdown maximo", _percent_metric(profile.max_drawdown))
    colunas[3].metric("Volume medio", _integer_metric(profile.average_volume))

    colunas = st.columns(4)
    colunas[0].metric(
        "Melhor dia",
        _percent_metric(profile.best_day_return),
        profile.best_day,
    )
    colunas[1].metric(
        "Pior dia",
        _percent_metric(profile.worst_day_return),
        profile.worst_day,
    )
    colunas[2].metric("Dias positivos", profile.positive_days)
    colunas[3].metric("Dias negativos", profile.negative_days)

    colunas = st.columns(1)
    colunas[0].metric("Volume maximo", _integer_metric(profile.max_volume))

    graficos = st.columns(2)
    with graficos[0]:
        st.caption("Curva de preco")
        st.line_chart(_chart_series(profile.price_curve, "preco"))
    with graficos[1]:
        st.caption("Curva de retorno acumulado")
        st.line_chart(
            _chart_series(profile.accumulated_return_curve, "retorno")
        )

    graficos = st.columns(2)
    with graficos[0]:
        st.caption("Histograma de retornos diarios")
        st.bar_chart(_chart_series(profile.daily_return_histogram, "dias"))
    with graficos[1]:
        st.caption("Volume ao longo do tempo")
        st.line_chart(_chart_series(profile.volume_curve, "volume"))


def _chart_series(points: list[object], column: str) -> dict[str, list[float]]:
    """Converte pontos do profile para graficos Streamlit."""
    return {column: [float(point.value) for point in points]}


def _percent_metric(value: float) -> str:
    return f"{value * 100:.2f}%"


def _price_label(value: float) -> str:
    return f"{value:.2f}"


def _integer_metric(value: float | int) -> str:
    return f"{float(value):,.0f}".replace(",", ".")


def _available_datasets_table(datasets: list[object]) -> list[dict[str, object]]:
    """Monta tabela visual dos datasets disponiveis."""
    return [
        {
            "Dataset de pesquisa": dataset.asset,
            "Timeframe": dataset.timeframe.upper(),
            "Candles": valor_ou_indisponivel(dataset.candles),
            "Status": dataset.status,
            "Provider": dataset.provider,
            "Fonte": dataset.source,
            "Selecionado": "SIM" if dataset.selected else "NAO",
        }
        for dataset in datasets
    ]


def exibir_status_bar(data: object) -> None:
    """Exibe barra superior de status em todas as abas."""
    status = data.system_status
    system_state = "ONLINE" if status.status else "OFFLINE"
    colunas = st.columns(6)
    colunas[0].metric("Sistema", system_state)
    colunas[1].metric("Modo", status.status)
    colunas[2].metric("Ativo operacional", status.active_symbol)
    colunas[3].metric("Estratégias", status.loaded_strategies_count)
    colunas[4].metric("Eventos", status.event_count)
    colunas[5].metric("Versão", status.version)


def exibir_market_dna(data: object) -> None:
    """Exibe a aba de MARKET DNA."""
    replay_data = getattr(data, "replay_data", None)
    if replay_data is not None and getattr(replay_data, "current_candle", None):
        st.subheader("Painel de Mercado")
        st.info("Market DNA alinhado ao candle atual do Replay selecionado.")
        exibir_candle_replay(getattr(replay_data, "current_candle", None))
        exibir_features_replay(getattr(replay_data, "feature_snapshot", None))
        exibir_regime_replay(getattr(replay_data, "regime_analysis", None))
        exibir_pesquisa_replay(getattr(replay_data, "research_data", None))
        return

    snapshot = data.market_snapshot
    signal = data.strategy_signal

    st.subheader("Painel de Mercado")

    if snapshot is None:
        st.info(
            "Nenhum Replay real carregado. O Market DNA sera exibido somente "
            "a partir do dataset em uso no Replay."
        )
        return

    score = signal.score if signal else None
    confidence = signal.confidence if signal else None
    exibir_cards_mercado(snapshot, score, confidence)
    exibir_regime_mercado(data)
    exibir_pesquisa_quantitativa(data)


def exibir_regime_mercado(data: object) -> None:
    """Exibe a analise de regime de mercado."""
    regime_data = getattr(data, "regime_data", None)
    st.subheader("Regime de Mercado")
    if regime_data is None:
        st.info("Regime de mercado ainda não disponível.")
        return

    colunas = st.columns(3)
    colunas[0].metric("Regime", regime_data.regime)
    colunas[1].metric("Confiança", f"{regime_data.confidence:.0%}")
    colunas[2].write(regime_data.description)


def exibir_pesquisa_quantitativa(data: object) -> None:
    """Exibe pesquisa quantitativa baseada em memoria de mercado."""
    research_data = getattr(data, "research_data", None)
    st.subheader("Pesquisa Quantitativa")
    if research_data is None:
        st.info("Pesquisa quantitativa ainda nao disponivel.")
        return

    colunas = st.columns(6)
    colunas[0].metric("Cenarios parecidos", research_data.similar_scenarios)
    colunas[1].metric(
        "Confianca historica",
        f"{research_data.confidence:.2f}",
    )
    colunas[2].metric(
        "Score historico",
        f"{research_data.historical_score:.2f}",
    )
    colunas[3].metric(
        "Momentum medio",
        f"{research_data.average_momentum:.2f}",
    )
    colunas[4].metric(
        "Forca media de tendencia",
        f"{research_data.average_trend_strength:.2f}",
    )
    colunas[5].metric("Forca do historico", research_data.history_strength)
    st.info(research_data.summary)


def exibir_cards_mercado(snapshot: object, score: object, confidence: object) -> None:
    """Exibe cards do painel de mercado."""
    colunas = st.columns(5)
    with colunas[0]:
        exibir_card(
            "Regime do Mercado",
            snapshot.regime,
            descricao_regime(snapshot.regime),
        )
    with colunas[1]:
        exibir_card(
            "Score do Market DNA",
            score,
            "Forca da leitura contextual.",
            indicador_nivel(score, 40, 70),
        )
    with colunas[2]:
        exibir_card(
            "Confiança",
            confidence,
            "Confianca do sinal consolidado.",
            indicador_nivel(confidence, 0.4, 0.7),
        )
    with colunas[3]:
        exibir_card(
            "Volatilidade",
            f"{snapshot.volatility:.2f}",
            "Amplitude operacional recente.",
            indicador_nivel(snapshot.volatility, 25, 50),
        )
    with colunas[4]:
        exibir_card(
            "Liquidez",
            f"{snapshot.liquidity:.0f}",
            "Volume disponivel na leitura.",
            indicador_nivel(snapshot.liquidity, 1000, 1500),
        )


def descricao_regime(regime: str) -> str:
    """Retorna descricao curta do regime de mercado."""
    descricoes = {
        "ALTA": "O mercado apresenta predominância direcional de alta.",
        "BAIXA": "O mercado apresenta predominância direcional de baixa.",
        "NEUTRO": "O mercado ainda nao apresenta direcao clara.",
    }
    return descricoes.get(regime, "Estado atual do regime de mercado.")


def _titulos_painel_mercado() -> tuple[str, ...]:
    return (
        "Regime do Mercado",
        "Score do Market DNA",
        "Confiança",
        "Volatilidade",
        "Liquidez",
    )


def exibir_estrategias(data: object) -> None:
    """Exibe a aba de estrategias."""
    status = data.system_status
    replay_data = getattr(data, "replay_data", None)
    signal = getattr(replay_data, "strategy_signal", None)
    events = getattr(replay_data, "recent_events", []) if replay_data else []
    signal_count = len(
        [event for event in events if event.event_name == "STRATEGY_SIGNAL_CREATED"]
    )
    colunas = st.columns(4)
    colunas[0].metric(
        "Strategy carregada",
        getattr(replay_data, "active_strategy_name", "N/D"),
    )
    colunas[1].metric("Status", "PESQUISA/PAPER")
    colunas[2].metric("Versao", status.version)
    colunas[3].metric("Sinais na sessao", signal_count)
    dataset = getattr(data, "active_dataset", None)
    colunas = st.columns(4)
    colunas[0].metric("Market", getattr(dataset, "asset", "N/D"))
    colunas[1].metric("Timeframe", getattr(dataset, "timeframe", "N/D"))
    colunas[2].metric(
        "Ultima execucao",
        valor_ou_indisponivel(
            getattr(getattr(replay_data, "current_candle", None), "data", None)
        ),
    )
    colunas[3].metric(
        "Ultima decisao",
        valor_ou_indisponivel(getattr(signal, "decision", None)),
    )
    st.warning("Operacao real: NAO AUTORIZADA.")


def exibir_eventos(data: object) -> None:
    """Exibe a aba de eventos."""
    status = data.system_status
    replay_data = getattr(data, "replay_data", None)
    recent_events = getattr(replay_data, "recent_events", []) if replay_data else []
    event_count = getattr(replay_data, "event_count", status.event_count)
    st.metric("Eventos registrados", event_count)
    if not recent_events:
        st.info("Nenhum evento real registrado nesta sessao de Replay.")
        return
    exibir_registros_readonly(_events_table(recent_events))


def exibir_research_lab(service: DashboardService) -> None:
    """Exibe o laboratorio quantitativo."""
    st.subheader("Research Lab")
    exibir_research_lab_actions(service)
    show_full_lab_audit = st.checkbox(
        "Mostrar auditoria completa do Lab",
        value=False,
        key="research_show_full_lab_audit",
    )
    research_snapshot = _research_lab_snapshot_for_display(
        service,
        include_full_audit=show_full_lab_audit,
    )
    data = replace(
        service.get_light_dashboard_view_model(),
        mt5_heuristic_research=research_snapshot,
    )
    exibir_research_lab_data(service, data, include_full_audit=show_full_lab_audit)


def _research_lab_snapshot_for_display(
    service: DashboardService,
    *,
    include_full_audit: bool = False,
) -> object:
    """Prioriza o ultimo calculo valido da sessao para alimentar a planilha visual."""
    calculated = st.session_state.get(MT5_LAB_CALCULATION_SNAPSHOT_KEY)
    if calculated is not None:
        persisted = service.get_mt5_research_report_snapshot()
        if _research_snapshot_evidence_count(
            persisted
        ) > _research_snapshot_evidence_count(calculated):
            st.session_state[MT5_LAB_CALCULATION_SNAPSHOT_KEY] = persisted
            return persisted
        return calculated
    persisted = service.get_mt5_research_report_snapshot()
    constants = service.get_mt5_research_constants()
    if _research_snapshot_evidence_count(persisted) > _research_snapshot_evidence_count(
        constants
    ):
        return persisted
    if include_full_audit:
        return persisted
    return constants


def _research_snapshot_evidence_count(research: object | None) -> int:
    """Conta amostras historicas para detectar snapshot visual antigo."""
    if research is None:
        return 0
    scenarios = list(getattr(research, "scenario_ranking", []) or [])
    if scenarios:
        return sum(
            int(getattr(scenario, "lab_confidence_sample_size", 0) or 0)
            for scenario in scenarios
        )
    rows = list(getattr(research, "rows", []) or [])
    return sum(int(getattr(row, "sample_size", 0) or 0) for row in rows)


def exibir_research_lab_actions(service: DashboardService) -> None:
    """Exibe acoes do Research Lab."""
    st.info(
        "Fluxo correto: MT5 Forex atualiza online sozinho. Primeiro rode "
        "a pesquisa no Lab; depois use as constantes calculadas no MT5 Forex. "
        "O refresh online nao executa pesquisa pesada."
    )
    colunas = st.columns(4)
    colunas[0].metric(
        "Candles por busca",
        service.get_mt5_research_history_candle_count(),
    )
    colunas[1].metric("Cenarios por linha", MT5_ALPHA_LIBRARY_SEARCH_SPACE_SIZE)
    colunas[2].metric(
        "Alvo de confirmacao",
        _optional_percent(MT5_LAB_TARGET_CONFIDENCE),
    )
    colunas[3].metric("Operacao real", "BLOQUEADA")

    colunas = st.columns([1.15, 1.05, 1.6, 1.4])
    history_last_update = service.get_mt5_research_history_last_update()
    history_database_path = service.get_mt5_research_history_database_path()
    selected_session_filter = _render_forex_session_filter_checkbox(
        colunas[2],
        key="research_forex_session_filter_enabled",
    )
    _apply_forex_session_filter_preference(service, selected_session_filter)
    if colunas[0].button(
        "Atualizar histórico MT5",
        key="research_update_mt5_history",
    ):
        _apply_forex_session_filter_preference(service, selected_session_filter)
        progress = st.progress(0.0)
        status_box = st.status(
            "Preparando download multi-TF do histórico MT5...",
            expanded=True,
        )
        progress_floor = 0.12
        progress_span = 0.68

        def on_history_progress(event: dict[str, object]) -> None:
            phase = str(event.get("phase", ""))
            index = int(event.get("index", 0) or 0)
            total = max(1, int(event.get("total", 1) or 1))
            event_timeframe = str(event.get("timeframe", "N/D") or "N/D")
            ratio = min(1.0, max(0.0, index / total))
            if phase == "history_timeframe_started":
                progress.progress(progress_floor + progress_span * (index - 1) / total)
                status_box.write(
                    f"Baixando {event_timeframe} ({index}/{total})..."
                )
            elif phase == "history_timeframe_finished":
                received = int(event.get("received_candles", 0) or 0)
                event_status = str(event.get("status", "N/D") or "N/D")
                progress.progress(progress_floor + progress_span * ratio)
                status_box.write(
                    f"{event_timeframe} concluído: {received} candles | MT5 {event_status}."
                )
            elif phase == "history_snapshot_saving":
                progress.progress(0.86)
                status_box.write("Salvando histórico no banco local do Lab...")

        status_box.write("Verificando comunicação MT5 e parâmetros do Lab.")
        progress.progress(progress_floor)
        history = service._update_mt5_research_history(
            timeframe="MULTI",
            progress_callback=on_history_progress,
        )
        received_candles = int(getattr(history, "safe_mode_received_candles", 0) or 0)
        rows_count = len(list(getattr(history, "pairs", []) or []))
        communication_status = str(
            getattr(history, "safe_mode_status", "")
            or getattr(history, "connection_status", "N/D")
        )
        progress.progress(0.75)
        status_box.write(f"Comunicação MT5: {communication_status}.")
        status_box.write(
            f"Base recebida: {received_candles} candles em {rows_count} linhas multi-TF."
        )
        status_box.write(f"Banco local: {history_database_path}")
        progress.progress(1.0)
        if received_candles > 0:
            status_box.update(
                label="Histórico MT5 baixado e salvo.",
                state="complete",
                expanded=False,
            )
        else:
            status_box.update(
                label="Download terminou sem candles novos.",
                state="error",
                expanded=True,
            )
        history_last_update = getattr(history, "last_update", history_last_update)
        st.success(
            "Histórico MT5 atualizado: "
            f"{received_candles} candles em {rows_count} linhas multi-TF."
        )
    colunas[0].caption(
        "Ultima atualizacao: "
        f"{_friendly_candle_time(history_last_update)}"
    )
    colunas[0].caption(f"Banco local: {history_database_path}")
    if colunas[1].button(
        "Atualizar cálculos",
        key="research_update_mt5_calculations",
    ):
        _apply_forex_session_filter_preference(service, selected_session_filter)
        progress = st.progress(0.0)
        status_box = st.status(
            "Preparando cálculo multi-TF do Lab...",
            expanded=True,
        )
        progress_floor = 0.20
        progress_span = 0.60

        def on_calculation_progress(event: dict[str, object]) -> None:
            phase = str(event.get("phase", ""))
            index = int(event.get("index", 0) or 0)
            total = max(1, int(event.get("total", 1) or 1))
            pair = str(event.get("pair", "N/D") or "N/D")
            ratio = min(1.0, max(0.0, index / total))
            if phase == "calculation_pair_started":
                progress.progress(progress_floor + progress_span * (index - 1) / total)
                status_box.write(f"Calculando {pair} ({index}/{total})...")
            elif phase == "calculation_pair_finished":
                progress.progress(progress_floor + progress_span * ratio)
                status_box.write(f"{pair} calculado.")

        status_box.write("Carregando base local salva do MT5.")
        progress.progress(0.20)
        status_box.write(
            "Executando biblioteca pesada de Alphas, Betas e timeframes."
        )
        research = service._update_mt5_research_calculations(
            timeframe="MULTI",
            progress_callback=on_calculation_progress,
        )
        st.session_state[MT5_LAB_CALCULATION_SNAPSHOT_KEY] = research
        candles_loaded = int(getattr(research, "candles_loaded", 0) or 0)
        rows_count = len(list(getattr(research, "rows", []) or []))
        scenarios_count = len(list(getattr(research, "scenario_ranking", []) or []))
        progress.progress(0.85)
        status_box.write(f"Candles processados: {candles_loaded}.")
        status_box.write(f"Pares avaliados: {rows_count}.")
        status_box.write(f"Cenários Alpha+Beta gerados: {scenarios_count}.")
        progress.progress(1.0)
        if scenarios_count > 0:
            status_box.update(
                label="Cálculos do Lab concluídos.",
                state="complete",
                expanded=False,
            )
        else:
            status_box.update(
                label="Cálculo terminou sem cenários novos.",
                state="error",
                expanded=True,
            )
        st.success(
            "Cálculos atualizados: "
            f"{candles_loaded} candles em {rows_count} pares e "
            f"{scenarios_count} cenarios Alpha+Beta multi-TF."
        )
    if colunas[2].button(
        "Gerar snapshot RR3 experimental",
        key="research_generate_rr3_experimental_snapshot",
    ):
        _apply_forex_session_filter_preference(service, selected_session_filter)
        progress = st.progress(0.0)
        status_box = st.status(
            "Preparando snapshot experimental RR3...",
            expanded=True,
        )
        progress_floor = 0.20
        progress_span = 0.60

        def on_rr3_progress(event: dict[str, object]) -> None:
            phase = str(event.get("phase", ""))
            index = int(event.get("index", 0) or 0)
            total = max(1, int(event.get("total", 1) or 1))
            pair = str(event.get("pair", "N/D") or "N/D")
            ratio = min(1.0, max(0.0, index / total))
            if phase == "calculation_pair_started":
                progress.progress(progress_floor + progress_span * (index - 1) / total)
                status_box.write(f"Calculando RR3 {pair} ({index}/{total})...")
            elif phase == "calculation_pair_finished":
                progress.progress(progress_floor + progress_span * ratio)
                status_box.write(f"{pair} RR3 calculado.")

        status_box.write("Carregando base local salva do MT5.")
        progress.progress(0.20)
        status_box.write(
            "Executando calculo pesado em modo experimental RR3; "
            "snapshot operacional preservado."
        )
        research_rr3 = service.update_mt5_research_calculations_rr3_experimental(
            timeframe="MULTI",
            progress_callback=on_rr3_progress,
        )
        st.session_state[MT5_LAB_RR3_EXPERIMENTAL_SNAPSHOT_KEY] = research_rr3
        candles_loaded = int(getattr(research_rr3, "candles_loaded", 0) or 0)
        rows_count = len(list(getattr(research_rr3, "rows", []) or []))
        scenarios_count = len(
            list(getattr(research_rr3, "scenario_ranking", []) or [])
        )
        winners_count = len(
            list(getattr(research_rr3, "best_scenarios_by_market", []) or [])
        )
        progress.progress(0.90)
        status_box.write(f"Candles processados: {candles_loaded}.")
        status_box.write(f"Pares avaliados: {rows_count}.")
        status_box.write(f"Cenarios RR3 gerados: {scenarios_count}.")
        status_box.write(f"Vencedores RR3 por par: {winners_count}.")
        status_box.write(
            "Arquivo: .traderia/research/mt5_research_snapshot_rr3_experimental.json"
        )
        progress.progress(1.0)
        if scenarios_count > 0:
            status_box.update(
                label="Snapshot experimental RR3 concluido.",
                state="complete",
                expanded=False,
            )
        else:
            status_box.update(
                label="RR3 experimental terminou sem cenarios.",
                state="error",
                expanded=True,
            )
        st.success(
            "Snapshot RR3 experimental gerado sem alterar o operacional: "
            f"{scenarios_count} cenarios RR3 e {winners_count} vencedores por par."
        )
    if st.session_state.get(MT5_LAB_CALCULATION_SNAPSHOT_KEY) is not None:
        colunas[1].caption("Planilha de auditoria visual alimentada pelo ultimo calculo.")
    if st.session_state.get(MT5_LAB_RR3_EXPERIMENTAL_SNAPSHOT_KEY) is not None:
        colunas[2].caption(
            "RR3 salvo separado; alimenta o fluxo M3 quando esse modelo estiver ativo."
        )
    colunas[3].caption(
        "Use o primeiro botão para baixar/salvar candles do MT5. Use o segundo "
        "para recalcular Alphas, Betas e timeframes sobre o histórico salvo. "
        "O RR3 experimental grava outro snapshot. Nenhuma ação envia ordens "
        "ou participa do refresh leve do MT5 Forex."
    )
    _render_rr3_experimental_comparison(service)


def _render_rr3_experimental_comparison(service: DashboardService) -> None:
    """Compara o snapshot operacional atual com o RR3 experimental."""
    experimental_path = (
        Path(".traderia")
        / "research"
        / "mt5_research_snapshot_rr3_experimental.json"
    )
    if not experimental_path.exists():
        st.caption(
            "Comparacao RR3 indisponivel: gere primeiro o snapshot RR3 experimental."
        )
        return
    operational = service._load_mt5_research_snapshot()
    if operational is None:
        st.caption("Comparacao RR3 indisponivel: snapshot operacional nao encontrado.")
        return
    try:
        experimental_payload = json.loads(experimental_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        st.caption("Comparacao RR3 indisponivel: arquivo experimental invalido.")
        return
    st.markdown("### Comparacao operacional x RR3 experimental")
    st.caption(
        "Somente leitura: compara os vencedores atuais com os vencedores RR3 "
        "do snapshot experimental. Nao altera Forex, MT5, robo demo ou Position Manager."
    )
    _render_plain_markdown_table(
        _rr3_experimental_comparison_rows(operational, experimental_payload),
        empty_columns=[
            "Par",
            "Operacional",
            "RR3 experimental",
            "Leitura",
        ],
        empty_message="Sem dados comparaveis.",
    )
    _render_rr3_parameter_study(experimental_payload)


def _render_rr3_parameter_study(
    experimental_payload: dict[str, object],
) -> None:
    """Mostra quais variaveis diferenciam RR3 vencedor de nao vencedor."""
    scenarios = [
        row
        for row in list(experimental_payload.get("scenario_ranking", []) or [])
        if isinstance(row, dict)
    ]
    if not scenarios:
        return
    st.markdown("### Estudo experimental RR3: vencedores x nao vencedores")
    st.caption(
        "Criterio experimental: vencedor RR3 precisa estar APROVADO, ter amostra "
        "historica, confirmacao maior que zero e Profit Factor acima de 1. "
        "Esta tabela nao recomenda operar; ela mostra quais variaveis apareceram "
        "mais quando o RR3 funcionou."
    )
    summary = _rr3_parameter_study_summary(scenarios)
    columns = st.columns(4)
    columns[0].metric("Cenarios RR3", summary["total"])
    columns[1].metric("RR3 vencedores", summary["wins"])
    columns[2].metric("RR3 nao vencedores", summary["non_wins"])
    columns[3].metric("Taxa vencedora", _optional_percent(summary["win_rate"]))
    _render_plain_markdown_table(
        _rr3_parameter_edge_rows(scenarios),
        empty_columns=[
            "Variavel",
            "Valor",
            "Vencedores",
            "Total",
            "% vencedor",
            "Score medio",
            "Conf. media",
            "PF medio",
            "Leitura",
        ],
        empty_message="Sem variaveis suficientes para comparar.",
    )
    st.caption(
        "Leitura dos indicadores internos: se um indicador aparece mais nos nao "
        "vencedores, ele vira candidato a filtro de bloqueio; se aparece mais nos "
        "vencedores, ele vira candidato a requisito de liberacao."
    )
    _render_plain_markdown_table(
        _rr3_indicator_edge_rows(scenarios),
        empty_columns=[
            "Indicador",
            "Presenca vencedores",
            "Presenca nao vencedores",
            "Diferenca",
            "Interpretacao",
        ],
        empty_message="Sem indicadores internos suficientes.",
    )


def _rr3_experimental_comparison_rows(
    operational: object,
    experimental_payload: dict[str, object],
) -> list[dict[str, object]]:
    current_by_pair = {
        str(getattr(scenario, "pair", "") or "").upper(): scenario
        for scenario in list(getattr(operational, "best_scenarios_by_market", []) or [])
        if str(getattr(scenario, "pair", "") or "").strip()
    }
    rr3_by_pair = {
        str(row.get("pair", "") or "").upper(): row
        for row in list(experimental_payload.get("best_scenarios_by_market", []) or [])
        if isinstance(row, dict) and str(row.get("pair", "") or "").strip()
    }
    rows: list[dict[str, object]] = []
    for pair in sorted(set(current_by_pair) | set(rr3_by_pair)):
        current = current_by_pair.get(pair)
        rr3 = rr3_by_pair.get(pair)
        current_summary = _scenario_comparison_summary(current)
        rr3_summary = _scenario_payload_comparison_summary(rr3)
        current_score = _safe_float_or_none(getattr(current, "score", None))
        rr3_score = _safe_float_or_none((rr3 or {}).get("score") if rr3 else None)
        current_confidence = _safe_float_or_none(
            getattr(current, "lab_confidence", None)
        )
        rr3_confidence = _safe_float_or_none(
            (rr3 or {}).get("lab_confidence") if rr3 else None
        )
        rr3_sample = int(_safe_float_or_none((rr3 or {}).get("lab_confidence_sample_size")) or 0)
        rr3_pf = _safe_float_or_none(
            (rr3 or {}).get("lab_confidence_profit_factor") if rr3 else None
        )
        rows.append(
            {
                "Par": pair,
                "Operacional atual": current_summary,
                "RR3 experimental": rr3_summary,
                "Delta score": _delta_label(rr3_score, current_score),
                "Delta conf.": _delta_percent_label(rr3_confidence, current_confidence),
                "Historico RR3": _rr3_history_label(rr3_sample, rr3_pf),
                "Leitura": _rr3_comparison_reading(
                    rr3_score=rr3_score,
                    current_score=current_score,
                    rr3_confidence=rr3_confidence,
                    current_confidence=current_confidence,
                    rr3_sample=rr3_sample,
                    rr3_pf=rr3_pf,
                ),
            }
        )
    return rows


def _scenario_comparison_summary(scenario: object | None) -> str:
    if scenario is None:
        return "N/D"
    parameters = dict(getattr(scenario, "parameters", {}) or {})
    return (
        f"{getattr(scenario, 'alpha_id', 'N/D')} | "
        f"{getattr(scenario, 'model', 'N/D')} | "
        f"{getattr(scenario, 'timeframe', 'N/D')} | "
        f"{getattr(scenario, 'decision', 'WAIT')} | "
        f"RR {parameters.get('rr', 'N/D')} | "
        f"{getattr(scenario, 'beta_id', 'N/D')} | "
        f"{parameters.get('stop_management', 'N/D')} | "
        f"Score {_optional_number(getattr(scenario, 'score', None))} | "
        f"Conf {_optional_percent(getattr(scenario, 'lab_confidence', None))}"
    )


def _scenario_payload_comparison_summary(payload: dict[str, object] | None) -> str:
    if not payload:
        return "N/D"
    parameters = dict(payload.get("parameters", {}) or {})
    return (
        f"{payload.get('alpha_id', 'N/D')} | "
        f"{payload.get('model', 'N/D')} | "
        f"{payload.get('timeframe', 'N/D')} | "
        f"{payload.get('decision', 'WAIT')} | "
        f"RR {parameters.get('rr', 'N/D')} | "
        f"{payload.get('beta_id', 'N/D')} | "
        f"{parameters.get('stop_management', 'N/D')} | "
        f"Score {_optional_number(payload.get('score'))} | "
        f"Conf {_optional_percent(payload.get('lab_confidence'))}"
    )


def _delta_label(new_value: float | None, base_value: float | None) -> str:
    if new_value is None or base_value is None:
        return "N/D"
    return f"{new_value - base_value:+.4f}"


def _delta_percent_label(new_value: float | None, base_value: float | None) -> str:
    if new_value is None or base_value is None:
        return "N/D"
    return f"{new_value - base_value:+.2%}"


def _rr3_history_label(sample: int, profit_factor: float | None) -> str:
    pf = "N/D" if profit_factor is None else f"{profit_factor:.2f}"
    return f"Amostra {sample} | PF {pf}"


def _rr3_comparison_reading(
    *,
    rr3_score: float | None,
    current_score: float | None,
    rr3_confidence: float | None,
    current_confidence: float | None,
    rr3_sample: int,
    rr3_pf: float | None,
) -> str:
    if rr3_score is None:
        return "SEM_RR3"
    if rr3_sample <= 0 or rr3_pf is None or rr3_pf <= 0:
        return "NAO_USAR: sem historico valido"
    if rr3_pf < 1.20:
        return "FRACO: PF baixo"
    if current_score is not None and rr3_score < current_score:
        return "PIOR_SCORE"
    if current_confidence is not None and rr3_confidence is not None:
        if rr3_confidence < current_confidence:
            return "PIOR_CONFIRMACAO"
    return "CANDIDATO_A_ESTUDO"


def _rr3_parameter_study_summary(
    scenarios: list[dict[str, object]],
) -> dict[str, object]:
    wins = sum(1 for scenario in scenarios if _rr3_scenario_is_experimental_winner(scenario))
    total = len(scenarios)
    return {
        "total": total,
        "wins": wins,
        "non_wins": max(0, total - wins),
        "win_rate": wins / total if total else 0.0,
    }


def _rr3_scenario_is_experimental_winner(scenario: dict[str, object]) -> bool:
    return (
        str(scenario.get("status", "") or "").upper() == "APROVADO"
        and (_safe_float_or_none(scenario.get("lab_confidence")) or 0.0) > 0.0
        and (_safe_float_or_none(scenario.get("lab_confidence_sample_size")) or 0.0)
        > 0.0
        and (_safe_float_or_none(scenario.get("lab_confidence_profit_factor")) or 0.0)
        > 1.0
    )


def _rr3_parameter_edge_rows(
    scenarios: list[dict[str, object]],
) -> list[dict[str, object]]:
    fields = [
        "Par",
        "TF",
        "Direcao",
        "Alpha",
        "Setup",
        "Beta",
        "Stop",
        "EMA curta",
        "EMA longa",
        "RSI sobrevenda",
        "RSI sobrecompra",
        "ATR fator",
        "Sessao",
    ]
    buckets: dict[tuple[str, str], dict[str, float]] = {}
    for scenario in scenarios:
        values = _rr3_scenario_parameter_values(scenario)
        is_winner = _rr3_scenario_is_experimental_winner(scenario)
        for field in fields:
            value = str(values.get(field, "N/D") or "N/D")
            key = (field, value)
            bucket = buckets.setdefault(
                key,
                {
                    "total": 0.0,
                    "wins": 0.0,
                    "score": 0.0,
                    "confidence": 0.0,
                    "profit_factor": 0.0,
                    "profit_factor_count": 0.0,
                },
            )
            bucket["total"] += 1.0
            bucket["wins"] += 1.0 if is_winner else 0.0
            bucket["score"] += _safe_float_or_none(scenario.get("score")) or 0.0
            bucket["confidence"] += (
                _safe_float_or_none(scenario.get("lab_confidence")) or 0.0
            )
            profit_factor = _safe_float_or_none(
                scenario.get("lab_confidence_profit_factor")
            )
            if profit_factor is not None and profit_factor > 0.0:
                bucket["profit_factor"] += profit_factor
                bucket["profit_factor_count"] += 1.0
    rows: list[dict[str, object]] = []
    for (field, value), bucket in buckets.items():
        total = int(bucket["total"])
        wins = int(bucket["wins"])
        if total < 5:
            continue
        win_rate = wins / total if total else 0.0
        avg_score = bucket["score"] / total if total else 0.0
        avg_confidence = bucket["confidence"] / total if total else 0.0
        avg_profit_factor = (
            bucket["profit_factor"] / bucket["profit_factor_count"]
            if bucket["profit_factor_count"]
            else 0.0
        )
        rows.append(
            {
                "Variavel": field,
                "Valor": value,
                "Vencedores": wins,
                "Total": total,
                "% vencedor": _optional_percent(win_rate),
                "Score medio": _optional_number(avg_score),
                "Conf. media": _optional_percent(avg_confidence),
                "PF medio": _optional_number(avg_profit_factor),
                "Leitura": _rr3_parameter_reading(
                    win_rate,
                    wins,
                    avg_profit_factor,
                ),
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            _safe_float_or_none(str(row["% vencedor"]).replace("%", "")) or 0.0,
            int(row["Vencedores"]),
            _safe_float_or_none(row["PF medio"]) or 0.0,
        ),
        reverse=True,
    )[:18]


def _rr3_scenario_parameter_values(
    scenario: dict[str, object],
) -> dict[str, object]:
    parameters = dict(scenario.get("parameters", {}) or {})
    return {
        "Par": scenario.get("pair", "N/D"),
        "TF": scenario.get("timeframe", "N/D"),
        "Direcao": scenario.get("decision", "WAIT"),
        "Alpha": scenario.get("alpha_id", "N/D"),
        "Setup": scenario.get("model", "N/D"),
        "Beta": scenario.get("beta_id", "N/D"),
        "Stop": parameters.get("stop_management", "N/D"),
        "EMA curta": parameters.get("ema_curta", "N/D"),
        "EMA longa": parameters.get("ema_longa", "N/D"),
        "RSI sobrevenda": parameters.get("rsi_sobrevenda", "N/D"),
        "RSI sobrecompra": parameters.get("rsi_sobrecompra", "N/D"),
        "ATR fator": parameters.get("atr_stop_factor", "N/D"),
        "Sessao": scenario.get("temporal_session", "N/D"),
    }


def _rr3_parameter_reading(
    win_rate: float,
    wins: int,
    avg_profit_factor: float,
) -> str:
    if wins <= 0:
        return "EVITAR"
    if win_rate >= 0.20 and avg_profit_factor >= 1.20:
        return "FORTE_CANDIDATO"
    if win_rate >= 0.10 and avg_profit_factor >= 1.0:
        return "CANDIDATO"
    if avg_profit_factor < 1.0:
        return "PF_FRACO"
    return "OBSERVAR"


def _rr3_indicator_edge_rows(
    scenarios: list[dict[str, object]],
) -> list[dict[str, object]]:
    totals: dict[str, dict[str, float]] = {}
    for scenario in scenarios:
        if not _rr3_scenario_is_experimental_winner(scenario):
            continue
        metrics = dict(scenario.get("lab_discrimination_metrics", {}) or {})
        for name, metric in metrics.items():
            if str(name).startswith("_") or not isinstance(metric, dict):
                continue
            winner_rate = _safe_float_or_none(metric.get("winner_rate"))
            loser_rate = _safe_float_or_none(metric.get("loser_rate"))
            difference = _safe_float_or_none(metric.get("difference"))
            if difference is None:
                continue
            bucket = totals.setdefault(
                str(name),
                {
                    "count": 0.0,
                    "winner_rate": 0.0,
                    "loser_rate": 0.0,
                    "difference": 0.0,
                },
            )
            bucket["count"] += 1.0
            bucket["winner_rate"] += winner_rate or 0.0
            bucket["loser_rate"] += loser_rate or 0.0
            bucket["difference"] += difference
    rows: list[dict[str, object]] = []
    for name, bucket in totals.items():
        count = bucket["count"] or 1.0
        winner_rate = bucket["winner_rate"] / count
        loser_rate = bucket["loser_rate"] / count
        difference = bucket["difference"] / count
        rows.append(
            {
                "Indicador": name,
                "Presenca vencedores": _optional_percent(winner_rate),
                "Presenca nao vencedores": _optional_percent(loser_rate),
                "Diferenca": _optional_percent(difference),
                "Interpretacao": _rr3_indicator_reading(difference),
            }
        )
    return sorted(
        rows,
        key=lambda row: abs(
            _safe_float_or_none(str(row["Diferenca"]).replace("%", "")) or 0.0
        ),
        reverse=True,
    )[:10]


def _rr3_indicator_reading(difference: float) -> str:
    if difference >= 0.05:
        return "BLOQUEIO_CANDIDATO: aparece mais nos nao vencedores"
    if difference <= -0.05:
        return "LIBERACAO_CANDIDATA: aparece mais nos vencedores"
    return "NEUTRO"


def exibir_research_lab_data(
    service: DashboardService,
    data: object,
    *,
    include_full_audit: bool = False,
) -> None:
    """Exibe os dados consolidados do Research Lab."""
    exibir_research_lab_layers(service)
    exibir_mt5_setup_suggestions(
        service,
        getattr(data, "mt5_heuristic_research", None),
    )
    if include_full_audit:
        exibir_mt5_alpha_research_report(service)
    else:
        st.caption(
            "Auditoria completa do Lab ocultada para manter a tela leve. "
            "Marque a opcao acima para carregar ranking detalhado e evidencias."
        )
    exibir_mt5_heuristic_research_lab(data, include_full_audit=include_full_audit)


def exibir_research_lab_layers(service: DashboardService) -> None:
    """Exibe a ordem conceitual das camadas do Research Lab."""
    layers = service.get_research_layer_definitions()
    st.subheader("Camadas de decisão do Research Lab")
    st.caption(
        "A pesquisa responde uma pergunta por camada. A validação só acontece "
        "depois que dados, indicadores, contexto, estrutura, tempo, "
        "microestrutura, Alpha e plano de trade foram caracterizados."
    )
    _render_stable_readonly_table([_research_layer_row(layer) for layer in layers])


def _research_layer_row(layer: dict[str, object]) -> dict[str, object]:
    return {
        "Camada": f"{layer.get('index', 'N/D')} - {layer.get('title', 'N/D')}",
        "Pergunta respondida": layer.get("question", "N/D"),
        "O que explica na tabela": layer.get("responsibility", "N/D"),
    }


def exibir_mt5_setup_suggestions(
    service: DashboardService,
    research: object | None = None,
) -> None:
    """Exibe sugestoes de setup geradas pelo snapshot persistido do Lab."""
    suggestions = _stable_mt5_lab_setup_suggestions(
        service.suggest_mt5_lab_setups()
    )
    st.subheader("Sugestoes de Setup do Lab")
    st.caption(
        "Use esta area como painel de decisao. Clique em Executar Pesquisa "
        "para recalcular a biblioteca de Alphas; abaixo aparece a melhor "
        "sugestao encontrada por par, sem autorizar operacao real."
    )
    if not suggestions:
        suggestions = []
        summary = {
            "total": 0,
            "approved": 0,
            "best_confidence": 0.0,
            "best_pair": "N/D",
        }
    else:
        summary = _mt5_setup_suggestions_summary(suggestions)
    _render_lab_setup_summary_metrics(summary)

    st.caption(_mt5_setup_suggestions_status_message(suggestions, summary))
    st.markdown("#### Setups sugeridos")
    _render_plain_markdown_table(
        [_mt5_setup_suggestion_compact_row(item) for item in suggestions],
        empty_columns=list(_mt5_setup_suggestion_empty_row().keys()),
        empty_message="Nenhuma sugestao carregada.",
    )

    if st.checkbox(
        "Mostrar detalhes completos dos parametros",
        value=False,
        key="mt5_lab_show_full_setup_details",
    ):
        _render_plain_markdown_table(
            [_mt5_setup_suggestion_row(item) for item in suggestions],
            empty_columns=list(_mt5_setup_suggestion_detail_empty_row().keys()),
            empty_message="Nenhum detalhe carregado.",
        )


def _render_lab_historical_confirmation_audit(
    service: DashboardService,
    research: object | None = None,
) -> None:
    """Mostra confirmacao historica por par/Alpha, do maior para o menor."""
    if research is None:
        research = service.get_mt5_research_constants()
    st.subheader("Auditoria visual da Confirmação Histórica")
    st.caption(
        "Para cada par, esta tabela ordena as Alphas pela maior Confirmacao "
        "Historica encontrada no Lab. A coluna Trades observados e a amostra "
        "historica usada para calcular esse percentual."
    )
    rows = _lab_historical_confirmation_audit_rows_from_research(research)
    if not rows:
        rows = _lab_historical_confirmation_audit_rows_from_suggestions(
            service.suggest_mt5_lab_setups()
        )
    _render_plain_markdown_table(
        rows,
        empty_columns=_lab_historical_confirmation_audit_columns(),
        empty_message="Nenhum ranking historico carregado. Execute Pesquisa no Lab.",
    )


def _render_scenario_runner_confirmation_audit(research: object) -> None:
    """Exibe auditoria no bloco do corredor mesmo sem ranking completo."""
    st.markdown("### Auditoria visual da Confirmação Histórica")
    st.caption(
        "Visao de conferencia: para cada par, lista as 16 Alphas da maior "
        "confirmacao historica para a menor. Mostra confirmados, nao "
        "confirmados e compara cada setup contra o melhor setup do mesmo par."
    )
    _render_plain_markdown_table(
        _lab_historical_confirmation_audit_rows_from_research(research),
        empty_columns=_lab_historical_confirmation_audit_columns(),
        empty_message=(
            "Snapshot atual nao trouxe ranking nem amostra historica. "
            "Execute Pesquisa para gerar a auditoria."
        ),
    )


def _render_lab_historical_confirmation_preview() -> None:
    """Mostra a estrutura da planilha antes de rodar calculo pesado."""
    st.markdown("### Previa da planilha de auditoria")
    st.caption(
        "Modelo visual sem calculo: esta e a planilha que sera preenchida "
        "quando voce clicar em Atualizar calculos."
    )
    _render_plain_markdown_table(
        [_lab_historical_confirmation_preview_row()],
        empty_columns=_lab_historical_confirmation_audit_columns(),
        empty_message="Previa indisponivel.",
    )


def _lab_historical_confirmation_audit_columns() -> list[str]:
    return [
        "Par",
        "Alpha de entrada",
        "Confirmacao Historica",
        "% Nao confirmado",
        "Trades observados",
        "Confirmados",
        "Nao confirmados",
        "TF",
        "Direcao",
        "Setup de entrada",
        "Parametros da entrada",
        "Beta Stop",
        "Stop inicial em R",
        "Plano Position Manager",
        "Iguais ao melhor do par",
        "Diferentes do melhor do par",
        "Padrao observado",
        "Filtro de liberacao",
        "Regra de liberacao",
        "RSI divergente",
        "MACD hist divergente",
        "ADX baixo",
        "ADX caindo",
        "ADX indisponivel",
        "ATR em queda",
        "ATR subindo",
        "Momentum contra",
        "Momentum enfraquecendo",
        "Indicadores que diferenciam",
        "Status",
    ]


def _lab_historical_confirmation_preview_row() -> dict[str, object]:
    return {
        column: "A preencher apos Atualizar calculos"
        for column in _lab_historical_confirmation_audit_columns()
    } | {
        "Par": "EXEMPLO",
        "Alpha de entrada": "ALPHA001",
        "Confirmacao Historica": "0.00%",
        "% Nao confirmado": "0.00%",
        "Trades observados": 0,
        "Confirmados": 0,
        "Nao confirmados": 0,
        "TF": "M1/M5/M15/H1",
        "Direcao": "BUY/SELL/WAIT",
        "Setup de entrada": "MODELO_DA_ALPHA",
        "Parametros da entrada": "ema_curta=... | ema_longa=... | rr=...",
        "Beta Stop": "BETA...",
        "Stop inicial em R": "1R = stop inicial ... | alvo planejado ...",
        "Filtro de liberacao": "Indicador NV-V positivo",
        "Regra de liberacao": "Regra aplicada ao filtro de entrada",
        "Status": "PREVIA",
    }


def _lab_historical_confirmation_audit_rows_from_research(
    research: object,
) -> list[dict[str, object]]:
    scenarios = list(getattr(research, "scenario_ranking", []) or [])
    if scenarios:
        return _lab_historical_confirmation_audit_rows(scenarios)
    return _lab_historical_confirmation_audit_rows_from_rows(
        list(getattr(research, "rows", []) or [])
    )


def _lab_historical_confirmation_audit_rows_from_suggestions(
    suggestions: list[object],
) -> list[dict[str, object]]:
    return _lab_historical_confirmation_audit_rows(list(suggestions or []))


def _lab_historical_confirmation_audit_rows_from_rows(
    rows: list[object],
) -> list[dict[str, object]]:
    scenario_like_rows = []
    for row in rows:
        final_configuration = dict(getattr(row, "final_configuration", {}) or {})
        scenario_like_rows.append(
            SimpleNamespace(
                pair=getattr(row, "pair", "N/D"),
                alpha_id=final_configuration.get("alpha", "ALPHA001"),
                lab_confidence=getattr(row, "confidence", 0.0),
                lab_confidence_sample_size=getattr(row, "sample_size", 0),
                score=getattr(row, "score", 0.0),
                timeframe=getattr(
                    row,
                    "ideal_timeframe",
                    getattr(row, "timeframe", "M1"),
                ),
                decision=getattr(row, "decision", "WAIT"),
                model=final_configuration.get(
                    "modelo",
                    getattr(row, "recommended_heuristic", "N/D"),
                ),
                parameters=final_configuration,
                status=getattr(row, "status", "N/D"),
            )
        )
    return _lab_historical_confirmation_audit_rows(scenario_like_rows)


def _lab_historical_confirmation_audit_rows(
    scenarios: list[object],
) -> list[dict[str, object]]:
    """Seleciona a melhor evidencia e completa as 16 Alphas por par."""
    best_by_pair_alpha: dict[tuple[str, str], object] = {}
    pairs: set[str] = set()
    for scenario in scenarios:
        pair = str(getattr(scenario, "pair", "") or "").upper().strip()
        alpha = str(getattr(scenario, "alpha_id", "ALPHA001") or "ALPHA001").upper()
        if not pair:
            continue
        pairs.add(pair)
        key = (pair, alpha)
        current = best_by_pair_alpha.get(key)
        if current is None or _historical_confirmation_rank(scenario) > (
            _historical_confirmation_rank(current)
        ):
            best_by_pair_alpha[key] = scenario

    completed: list[object] = []
    for pair in sorted(pairs):
        for alpha_id in MT5_LAB_ALPHA_IDS:
            completed.append(
                best_by_pair_alpha.get(
                    (pair, alpha_id),
                    _empty_lab_alpha_audit_scenario(pair, alpha_id),
                )
            )

    ordered = sorted(
        completed,
        key=lambda scenario: (
            str(getattr(scenario, "pair", "") or "").upper(),
            -float(getattr(scenario, "lab_confidence", 0.0) or 0.0),
            -int(getattr(scenario, "lab_confidence_sample_size", 0) or 0),
            str(getattr(scenario, "alpha_id", "ALPHA001") or "ALPHA001").upper(),
        ),
    )
    reference_by_pair: dict[str, object] = {}
    for item in ordered:
        pair = str(getattr(item, "pair", "") or "").upper()
        if pair and pair not in reference_by_pair:
            reference_by_pair[pair] = item
    winning_filter_by_pair = {
        pair: _lab_pair_winning_filter(pair, ordered)
        for pair in reference_by_pair
    }
    return [
        _lab_historical_confirmation_audit_row(
            item,
            reference_by_pair.get(str(getattr(item, "pair", "") or "").upper()),
            winning_filter_by_pair.get(
                str(getattr(item, "pair", "") or "").upper(),
                ("N/D", "Sem filtro vencedor do par com diferenca suficiente."),
            ),
        )
        for item in ordered
    ]


def _empty_lab_alpha_audit_scenario(pair: str, alpha_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        pair=pair,
        alpha_id=alpha_id,
        lab_confidence=0.0,
        lab_confidence_sample_size=0,
        score=0.0,
        timeframe="N/D",
        decision="WAIT",
        model="SEM_EVIDENCIA",
        parameters={},
        lab_discrimination_summary="Sem evidencia historica para diferenciar.",
        status="SEM_DADOS",
    )


def _historical_confirmation_rank(scenario: object) -> tuple[float, int, float]:
    return (
        float(getattr(scenario, "lab_confidence", 0.0) or 0.0),
        int(getattr(scenario, "lab_confidence_sample_size", 0) or 0),
        float(getattr(scenario, "score", 0.0) or 0.0),
    )


def _lab_historical_confirmation_audit_row(
    scenario: object,
    reference: object | None = None,
    pair_winning_filter: tuple[str, str] | None = None,
) -> dict[str, object]:
    confidence = float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
    sample_size = int(getattr(scenario, "lab_confidence_sample_size", 0) or 0)
    confirmed = int(round(sample_size * confidence))
    not_confirmed = max(sample_size - confirmed, 0)
    not_confirmed_percent = (1.0 - confidence) if sample_size > 0 else 0.0
    equal_parameters, different_parameters = _lab_setup_parameter_comparison(
        scenario,
        reference,
    )
    row = {
        "Par": str(getattr(scenario, "pair", "N/D") or "N/D").upper(),
        "Alpha de entrada": str(getattr(scenario, "alpha_id", "ALPHA001") or "ALPHA001").upper(),
        "Confirmacao Historica": _optional_percent(confidence),
        "% Nao confirmado": _optional_percent(not_confirmed_percent),
        "Trades observados": sample_size,
        "Confirmados": confirmed,
        "Nao confirmados": not_confirmed,
        "TF": getattr(scenario, "timeframe", "N/D"),
        "Direcao": getattr(scenario, "decision", "WAIT"),
        "Setup de entrada": getattr(scenario, "model", "N/D"),
        "Parametros da entrada": _lab_setup_parameter_summary(scenario),
        "Beta Stop": _lab_beta_stop_label(scenario),
        "Stop inicial em R": _lab_initial_stop_r_summary(scenario),
        "Plano Position Manager": _lab_position_manager_plan_summary(scenario),
        "Iguais ao melhor do par": equal_parameters,
        "Diferentes do melhor do par": different_parameters,
        "Padrao observado": _lab_setup_pattern_summary(
            scenario,
            reference,
            sample_size,
            confidence,
            different_parameters,
        ),
        "Filtro de liberacao": (
            pair_winning_filter[0] if pair_winning_filter else "N/D"
        ),
        "Regra de liberacao": (
            pair_winning_filter[1]
            if pair_winning_filter
            else "Entrada liberada sem filtro adicional validado para o par."
        ),
    }
    row.update(_lab_discrimination_indicator_columns(scenario))
    row.update(
        {
            "Indicadores que diferenciam": getattr(
                scenario,
                "lab_discrimination_summary",
                "N/D",
            ),
            "Status": getattr(scenario, "status", "N/D"),
        }
    )
    return row


def _lab_discrimination_indicator_columns(scenario: object) -> dict[str, str]:
    metrics = dict(getattr(scenario, "lab_discrimination_metrics", {}) or {})
    return {
        indicator: _lab_discrimination_metric_text(metrics.get(indicator))
        for indicator in (
            "RSI divergente",
            "MACD hist divergente",
            "ADX baixo",
            "ADX caindo",
            "ADX indisponivel",
            "ATR em queda",
            "ATR subindo",
            "Momentum contra",
            "Momentum enfraquecendo",
        )
    }


def _lab_beta_stop_label(scenario: object) -> str:
    beta_id, beta_mode, beta_version = _lab_beta_stop_descriptor(scenario)
    return f"{beta_id} | {beta_mode} | {beta_version}"


def _lab_initial_stop_r_summary(scenario: object) -> str:
    parameters = _lab_setup_parameters(scenario)
    atr_factor = _safe_float_or_none(parameters.get("atr_stop_factor"))
    rr = _safe_float_or_none(parameters.get("rr"))
    if atr_factor is None and rr is None:
        return "N/D"
    atr_text = f"{atr_factor:g} ATR" if atr_factor is not None else "N/D"
    rr_text = f"{rr:g}R" if rr is not None else "N/D"
    return f"1R = stop inicial {atr_text} | alvo planejado {rr_text}"


def _lab_position_manager_plan_summary(scenario: object) -> str:
    parameters = _lab_setup_parameters(scenario)
    policy = str(parameters.get("stop_management", "FIXED_STOP") or "FIXED_STOP").upper()
    beta_id, _, _ = _lab_beta_stop_descriptor(scenario)
    beta_id = beta_id.upper()
    beta_number = _lab_beta_number(beta_id)
    if beta_number is not None and beta_number >= 3:
        prefix = f"{beta_id} sem FULL_EXIT"
    else:
        prefix = f"{beta_id}"
    if policy == "FIXED_STOP":
        return f"{prefix}: manter stop inicial; Position Manager apenas monitora."
    if policy == "BREAK_EVEN":
        trigger = parameters.get("break_even_trigger_rr", "1.0")
        offset = parameters.get("break_even_offset_pips", "0.0")
        return (
            f"{prefix}: mover para break-even ao atingir {trigger}R; "
            f"offset {offset} pip(s)."
        )
    if policy == "ATR_TRAILING_STOP":
        factor = parameters.get("atr_trailing_factor", parameters.get("atr_stop_factor", "N/D"))
        activation = parameters.get("atr_trailing_activation_rr", "1.0")
        return (
            f"{prefix}: trailing por ATR x{factor}; ativa a partir de "
            f"{activation}R."
        )
    if policy == "CHANDELIER_EXIT":
        period = parameters.get("chandelier_period", "22")
        factor = parameters.get("chandelier_atr_factor", parameters.get("atr_stop_factor", "N/D"))
        return f"{prefix}: Chandelier {period} candles com ATR x{factor}."
    if policy == "DONCHIAN_CHANNEL_STOP":
        period = parameters.get("donchian_stop_period", "20")
        return f"{prefix}: stop pelo canal Donchian de {period} candles."
    if policy == "MOVING_AVERAGE_EXIT":
        period = parameters.get("exit_ma_period", "N/D")
        ma_type = parameters.get("exit_ma_type", "EMA")
        return f"{prefix}: stop/saida acompanhado por {ma_type}{period}."
    if policy == "TIME_STOP":
        bars = parameters.get("max_bars_in_trade", "N/D")
        minutes = parameters.get("max_minutes_in_trade", "N/D")
        return f"{prefix}: time stop em {bars} barras ou {minutes} minutos."
    if policy == "VOLATILITY_STOP":
        factor = parameters.get("volatility_multiplier", parameters.get("atr_stop_factor", "N/D"))
        return f"{prefix}: stop adaptado por volatilidade x{factor}."
    return f"{prefix}: politica {policy}; parametros auditaveis no cenario."


def _lab_beta_stop_descriptor(scenario: object) -> tuple[str, str, str]:
    """Deriva a Beta de saida pela politica de stop avaliada no cenario."""
    parameters = _lab_setup_parameters(scenario)
    beta_id = str(
        parameters.get("beta_id", getattr(scenario, "beta_id", "BETA001"))
        or "BETA001"
    ).upper()
    beta_version = str(
        parameters.get("beta_version", getattr(scenario, "beta_version", "N/D"))
        or "N/D"
    )
    beta_mode = str(
        parameters.get("beta_mode", getattr(scenario, "beta_mode", "N/D"))
        or "N/D"
    )
    beta_number = _lab_beta_number(beta_id)
    if beta_number is not None and beta_number >= 3:
        return beta_id, beta_mode, beta_version
    policy = str(
        parameters.get(
            "stop_management",
            getattr(scenario, "stop_management", ""),
        )
        or ""
    ).upper()
    by_policy = {
        "FIXED_STOP": ("BETA003", "FIXED_STOP_ONLY", "FIXED_STOP_MANAGER"),
        "BREAK_EVEN": ("BETA004", "BREAK_EVEN_ONLY", "BREAK_EVEN_MANAGER"),
        "ATR_TRAILING_STOP": (
            "BETA005",
            "ATR_TRAILING_ONLY",
            "ATR_TRAILING_STOP_MANAGER",
        ),
        "CHANDELIER_EXIT": ("BETA006", "CHANDELIER_ONLY", "CHANDELIER_STOP_MANAGER"),
        "PARABOLIC_SAR": ("BETA007", "PARABOLIC_SAR_ONLY", "PARABOLIC_SAR_MANAGER"),
        "DONCHIAN_CHANNEL_STOP": (
            "BETA008",
            "DONCHIAN_STOP_ONLY",
            "DONCHIAN_STOP_MANAGER",
        ),
        "MOVING_AVERAGE_EXIT": (
            "BETA009",
            "MA_STOP_ONLY",
            "MOVING_AVERAGE_STOP_MANAGER",
        ),
        "TIME_STOP": ("BETA010", "TIME_STOP_ONLY", "TIME_STOP_MANAGER"),
        "VOLATILITY_STOP": (
            "BETA011",
            "VOLATILITY_STOP_ONLY",
            "VOLATILITY_STOP_MANAGER",
        ),
    }
    return by_policy.get(policy, (beta_id, beta_mode, beta_version))


def _lab_beta_number(beta_id: str) -> int | None:
    raw = str(beta_id or "").upper().replace("BETA", "", 1)
    try:
        return int(raw)
    except ValueError:
        return None


def _lab_discrimination_metric_text(metric: object) -> str:
    if not isinstance(metric, dict):
        return "N/D"
    try:
        winner_rate = float(metric.get("winner_rate", 0.0) or 0.0)
        loser_rate = float(metric.get("loser_rate", 0.0) or 0.0)
        difference = float(metric.get("difference", 0.0) or 0.0)
    except (TypeError, ValueError):
        return "N/D"
    return (
        f"V {_optional_percent(winner_rate)} | "
        f"NV {_optional_percent(loser_rate)} | "
        f"Dif {difference:+.0%}"
    )


def _lab_pair_winning_filter(
    pair: str,
    scenarios: list[object],
) -> tuple[str, str]:
    """Escolhe o melhor filtro candidato para reduzir entradas ruins no par."""
    best: tuple[float, int, float, str, dict[str, float]] | None = None
    normalized_pair = str(pair or "").upper()
    for scenario in scenarios:
        if str(getattr(scenario, "pair", "") or "").upper() != normalized_pair:
            continue
        sample_size = int(getattr(scenario, "lab_confidence_sample_size", 0) or 0)
        confidence = float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
        metrics = dict(getattr(scenario, "lab_discrimination_metrics", {}) or {})
        for indicator, metric in metrics.items():
            if indicator in {"_sample", "ADX indisponivel"}:
                continue
            if not isinstance(metric, dict):
                continue
            try:
                difference = float(metric.get("difference", 0.0) or 0.0)
                winner_rate = float(metric.get("winner_rate", 0.0) or 0.0)
                loser_rate = float(metric.get("loser_rate", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            if difference < 0.10:
                continue
            candidate = (
                difference,
                sample_size,
                confidence,
                str(indicator),
                {
                    "winner_rate": winner_rate,
                    "loser_rate": loser_rate,
                    "difference": difference,
                },
            )
            if best is None or candidate[:3] > best[:3]:
                best = candidate
    if best is None:
        return ("N/D", "Entrada liberada sem filtro adicional validado para o par.")
    _, sample_size, _, indicator, metric = best
    filter_label = (
        f"{indicator} | NV {_optional_percent(metric['loser_rate'])} "
        f"x V {_optional_percent(metric['winner_rate'])} | "
        f"Dif {metric['difference']:+.0%}"
    )
    usage = (
        f"Entrada da Alpha so deve ser liberada no {normalized_pair} quando "
        f"{indicator} nao estiver presente; base={sample_size} trades observados. "
        "Ainda nao altera execucao."
    )
    return (filter_label, usage)


def _lab_setup_parameters(scenario: object) -> dict[str, object]:
    parameters = dict(getattr(scenario, "parameters", {}) or {})
    if not parameters:
        parameters = dict(getattr(scenario, "final_configuration", {}) or {})
    if not parameters:
        parameters = dict(getattr(scenario, "lab_parameters", {}) or {})
    return {str(key): value for key, value in parameters.items()}


def _lab_setup_comparable_parameters(scenario: object) -> dict[str, str]:
    parameters = _lab_setup_parameters(scenario)
    comparable: dict[str, str] = {
        "TF": str(getattr(scenario, "timeframe", "N/D") or "N/D"),
        "Direcao": str(getattr(scenario, "decision", "WAIT") or "WAIT"),
        "Modelo": str(getattr(scenario, "model", "N/D") or "N/D"),
    }
    for key in (
        "ema_curta",
        "ema_longa",
        "rsi_sobrevenda",
        "rsi_sobrecompra",
        "atr_stop_factor",
        "rr",
        "momentum_threshold",
        "volatility_threshold",
        "donchian_period",
        "stop_management",
        "beta_id",
        "reversal_strength",
    ):
        if key in parameters:
            comparable[key] = str(parameters[key])
    return comparable


def _lab_setup_parameter_summary(scenario: object) -> str:
    comparable = _lab_setup_comparable_parameters(scenario)
    if str(getattr(scenario, "model", "") or "") == "SEM_EVIDENCIA":
        return "Sem evidencia historica para esta Alpha no par."
    ordered = [
        key
        for key in (
            "TF",
            "Direcao",
            "Modelo",
            "ema_curta",
            "ema_longa",
            "rsi_sobrevenda",
            "rsi_sobrecompra",
            "atr_stop_factor",
            "rr",
            "momentum_threshold",
            "volatility_threshold",
            "donchian_period",
            "stop_management",
            "beta_id",
            "reversal_strength",
        )
        if key in comparable
    ]
    return " | ".join(f"{key}={comparable[key]}" for key in ordered) or "N/D"


def _lab_setup_parameter_comparison(
    scenario: object,
    reference: object | None,
) -> tuple[str, str]:
    if reference is None:
        return "N/D", "N/D"
    current = _lab_setup_comparable_parameters(scenario)
    baseline = _lab_setup_comparable_parameters(reference)
    if not current or not baseline:
        return "N/D", "N/D"
    equal = [
        f"{key}={current[key]}"
        for key in current
        if key in baseline and current[key] == baseline[key]
    ]
    different = [
        f"{key}: {current[key]} != {baseline[key]}"
        for key in current
        if key in baseline and current[key] != baseline[key]
    ]
    return (
        " | ".join(equal) if equal else "Nenhum parametro igual",
        " | ".join(different) if different else "Nenhuma diferenca",
    )


def _lab_setup_pattern_summary(
    scenario: object,
    reference: object | None,
    sample_size: int,
    confidence: float,
    different_parameters: str,
) -> str:
    if sample_size <= 0:
        return "Sem amostra: Alpha nao gerou trades observados neste par."
    if reference is not None and scenario is reference:
        return "Melhor padrao do par: usado como referencia de comparacao."
    if confidence >= 0.70:
        base = "Confirmados predominam historicamente."
    elif confidence >= 0.50:
        base = "Confirmacao equilibrada; vantagem historica moderada."
    else:
        base = "Nao confirmados predominam; setup inferior ao padrao do par."
    if different_parameters and different_parameters != "Nenhuma diferenca":
        return f"{base} Diferenca-chave: {different_parameters}"
    return base


def _render_lab_setup_summary_metrics(summary: dict[str, object]) -> None:
    """Usa componentes nativos para evitar instabilidade de DOM no Lab."""
    columns = st.columns(4)
    columns[0].metric("Pares sugeridos", summary["total"])
    columns[1].metric("Confirmaram 70%", summary["approved"])
    columns[2].metric(
        "Melhor confirmacao",
        _optional_percent(summary["best_confidence"]),
    )
    columns[3].metric("Melhor par", summary["best_pair"])


def _render_plain_markdown_table(
    rows: list[dict[str, object]],
    *,
    empty_columns: list[str] | None = None,
    empty_message: str = "Nenhum registro disponivel.",
) -> None:
    """Renderiza tabela Markdown simples para evitar falhas do front-end."""
    columns = list(rows[0].keys()) if rows else list(empty_columns or ["Status"])
    display_rows = rows or [{columns[0]: empty_message}]
    header = "| " + " | ".join(_markdown_cell(column) for column in columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in display_rows:
        body.append(
            "| "
            + " | ".join(_markdown_cell(row.get(column, "")) for column in columns)
            + " |"
        )
    st.markdown("\n".join([header, separator] + body))


def _markdown_cell(value: object) -> str:
    text = str(value)
    return (
        text.replace("\n", " ")
        .replace("\r", " ")
        .replace("|", "\\|")
        .strip()
    )


def _stable_mt5_lab_setup_suggestions(suggestions: list[object]) -> list[object]:
    if suggestions:
        st.session_state[MT5_LAB_LAST_VALID_SUGGESTIONS_KEY] = list(suggestions)
        get_runtime_guard_service().preserve_snapshot(
            MT5_LAB_LAST_VALID_SUGGESTIONS_KEY,
            list(suggestions),
            validator=lambda value: bool(value),
        )
        return list(suggestions)
    previous = get_runtime_guard_service().preserve_snapshot(
        MT5_LAB_LAST_VALID_SUGGESTIONS_KEY,
        list(suggestions),
        validator=lambda value: bool(value),
    )
    if previous is suggestions or previous == list(suggestions):
        previous = st.session_state.get(MT5_LAB_LAST_VALID_SUGGESTIONS_KEY)
    if previous:
        st.session_state[MT5_LAB_LAST_VALID_SUGGESTIONS_KEY] = list(previous)
        return list(previous)
    return []


def _mt5_setup_suggestions_summary(
    suggestions: list[object],
) -> dict[str, object]:
    best = max(
        suggestions,
        key=lambda item: float(getattr(item, "lab_confidence", 0.0) or 0.0),
    )
    return {
        "total": len(suggestions),
        "approved": sum(
            1
            for item in suggestions
            if float(getattr(item, "lab_confidence", 0.0) or 0.0)
            >= MT5_LAB_TARGET_CONFIDENCE
        ),
        "best_confidence": float(getattr(best, "lab_confidence", 0.0) or 0.0),
        "best_pair": getattr(best, "pair", "N/D"),
    }


def _mt5_setup_suggestions_status_message(
    suggestions: list[object],
    summary: dict[str, object],
) -> str:
    if not suggestions:
        return (
            "Status Lab: aguardando snapshot de sugestoes. Execute Pesquisa para "
            "carregar o historico antes de escolher setup."
        )
    approved = int(summary.get("approved", 0) or 0)
    if approved > 0:
        return "Status Lab: sugestoes ativas carregadas pelo snapshot do Research Lab."
    return "Status Lab: sugestoes carregadas, ainda sem confirmacao historica de 70%."


def _mt5_setup_suggestion_empty_row() -> dict[str, object]:
    return {
        "Alpha": "N/D",
        "Beta": "BETA001",
        "Par": "N/D",
        "TF": "N/D",
        "Direcao": "WAIT",
        "Setup": "N/D",
        "Gestao runtime": "N/D",
        "Plano de risco": "N/D",
        "Resumo parametros": "N/D",
        "Encaixe Tecnico": "N/D",
        "Confirmacao Historica": "N/D",
        "Janela que confirmou": "N/D",
        "Status": "AGUARDANDO_SNAPSHOT",
    }


def _mt5_setup_suggestion_compact_row(suggestion: object) -> dict[str, object]:
    parameters = getattr(suggestion, "parameters", {}) or {}
    beta_id, _, _ = _lab_beta_stop_descriptor(suggestion)
    return {
        "Alpha": getattr(suggestion, "alpha_id", "ALPHA001"),
        "Beta": beta_id,
        "Par": getattr(suggestion, "pair", "N/D"),
        "TF": getattr(suggestion, "timeframe", "M1"),
        "Direcao": getattr(suggestion, "decision", "WAIT"),
        "Setup": getattr(suggestion, "model", "WAIT_NO_EDGE"),
        "Gestao runtime": "POSITION_MANAGER_DINAMICO",
        "Plano de risco": _runtime_risk_plan_label(
            getattr(suggestion, "exit_model", "INITIAL_RISK_PLAN")
        ),
        "Resumo parametros": _setup_parameters_summary(
            parameters
        ),
        "Encaixe Tecnico": _optional_percent(getattr(suggestion, "score", 0.0)),
        "Confirmacao Historica": _optional_percent(
            getattr(suggestion, "lab_confidence", 0.0)
        ),
        "Janela que confirmou": _historical_confirmation_context(suggestion),
        "Status": _setup_status_label(getattr(suggestion, "status", "SEM_SUGESTAO")),
    }


def _setup_parameters_summary(parameters: object) -> str:
    if not isinstance(parameters, dict):
        return "N/D"
    ema = (
        f"EMA {parameters.get('ema_curta', 'N/D')}"
        f"x{parameters.get('ema_longa', 'N/D')}"
    )
    rsi = (
        f"RSI {parameters.get('rsi_sobrevenda', 'N/D')}/"
        f"{parameters.get('rsi_sobrecompra', 'N/D')}"
    )
    atr = f"ATR {parameters.get('atr_stop_factor', 'N/D')}"
    rr = f"RR {parameters.get('rr', 'N/D')}"
    return " | ".join((ema, rsi, atr, rr))


def _historical_confirmation_context(suggestion: object) -> str:
    parameters = getattr(suggestion, "parameters", {}) or {}
    if not isinstance(parameters, dict):
        parameters = {}
    sample = int(getattr(suggestion, "lab_confidence_sample_size", 0) or 0)
    profit_factor = float(
        getattr(suggestion, "lab_confidence_profit_factor", 0.0) or 0.0
    )
    expectancy = float(
        getattr(suggestion, "lab_confidence_expectancy", 0.0) or 0.0
    )
    drawdown = float(
        getattr(suggestion, "lab_confidence_max_drawdown", 0.0) or 0.0
    )
    source = str(getattr(suggestion, "lab_confidence_source", "N/D") or "N/D")
    context_parts = [
        f"{getattr(suggestion, 'pair', 'N/D')} {getattr(suggestion, 'timeframe', 'N/D')}",
        str(getattr(suggestion, "model", "N/D")),
        f"RR {parameters.get('rr', 'N/D')}",
        f"ATR {parameters.get('atr_stop_factor', 'N/D')}",
        f"EMA {parameters.get('ema_curta', 'N/D')}x{parameters.get('ema_longa', 'N/D')}",
    ]
    metric_parts = []
    if sample > 0:
        metric_parts.append(f"amostra {sample}")
    if profit_factor > 0.0:
        metric_parts.append(f"PF {profit_factor:.2f}")
    if expectancy != 0.0:
        metric_parts.append(f"Exp {expectancy:.4f}")
    if drawdown > 0.0:
        metric_parts.append(f"DD {drawdown:.4f}")
    if source and source != "N/D":
        metric_parts.append(source)
    if metric_parts:
        return " | ".join(context_parts + metric_parts)
    return " | ".join(context_parts + ["sem amostra detalhada"])


def _setup_status_label(status: object) -> str:
    normalized = str(status or "SEM_SUGESTAO").upper()
    if normalized == "SUGERIDO_70":
        return "ATINGIU_70"
    if normalized == "MAIS_PROXIMO_DE_70":
        return "MAIS_PROXIMO"
    return normalized


def _mt5_setup_suggestion_detail_empty_row() -> dict[str, object]:
    return {
        "Alpha": "N/D",
        "Beta": "BETA001",
        "Par": "N/D",
        "Timeframe": "N/D",
        "Setup sugerido": "N/D",
        "Direcao": "WAIT",
        "Gestao runtime": "N/D",
        "Plano de risco": "N/D",
        "Hint legado": "N/D",
        "Parametros": "N/D",
        "Encaixe Tecnico": "N/D",
        "Confirmacao Historica": "N/D",
        "Janela que confirmou": "N/D",
        "Alvo de confirmacao": _optional_percent(MT5_LAB_TARGET_CONFIDENCE),
        "Status": "AGUARDANDO_SNAPSHOT",
        "Fonte": "N/D",
        "Motivo": "N/D",
    }


def _mt5_setup_suggestion_row(suggestion: object) -> dict[str, object]:
    parameters = getattr(suggestion, "parameters", {}) or {}
    beta_id, _, _ = _lab_beta_stop_descriptor(suggestion)
    return {
        "Alpha": getattr(suggestion, "alpha_id", "ALPHA001"),
        "Beta": beta_id,
        "Par": getattr(suggestion, "pair", "N/D"),
        "Timeframe": getattr(suggestion, "timeframe", "M1"),
        "Setup sugerido": getattr(suggestion, "model", "WAIT_NO_EDGE"),
        "Direcao": getattr(suggestion, "decision", "WAIT"),
        "Gestao runtime": "POSITION_MANAGER_DINAMICO",
        "Plano de risco": _runtime_risk_plan_label(
            getattr(suggestion, "exit_model", "INITIAL_RISK_PLAN")
        ),
        "Hint legado": getattr(suggestion, "stop_management", "N/D"),
        "Parametros": _scenario_parameters_label(
            parameters
        ),
        "Encaixe Tecnico": _optional_percent(getattr(suggestion, "score", 0.0)),
        "Confirmacao Historica": _optional_percent(
            getattr(suggestion, "lab_confidence", 0.0)
        ),
        "Janela que confirmou": _historical_confirmation_context(suggestion),
        "Alvo de confirmacao": _optional_percent(
            getattr(suggestion, "target_confidence", MT5_LAB_TARGET_CONFIDENCE)
        ),
        "Status": getattr(suggestion, "status", "SEM_SUGESTAO"),
        "Fonte": getattr(suggestion, "source", "MT5_RESEARCH_SNAPSHOT"),
        "Motivo gestao": getattr(
            suggestion,
            "stop_management_reason",
            "Gestao runtime decidida pelo Position Manager.",
        ),
        "Motivo": getattr(suggestion, "reason", "N/D"),
    }


def _runtime_risk_plan_label(value: object) -> str:
    normalized = str(value or "INITIAL_RISK_PLAN").strip().upper()
    if normalized in {
        "SCENARIO_EXIT_RESEARCH_SELECTION",
        "ATR_RR_RESEARCH_SELECTION",
        "NONE",
        "N/D",
        "",
    }:
        return "INITIAL_RISK_PLAN"
    return normalized


def exibir_mt5_alpha_research_report(service: DashboardService) -> None:
    """Exibe ranking e relatorio tecnico de aprovacao/reprovacao das Alphas."""
    ranking = service.get_mt5_alpha_research_ranking()
    report = ranking[0] if ranking else service.get_mt5_alpha_research_report()
    st.subheader("Ranking Final de Alphas")
    if ranking:
        _render_stable_readonly_table(
            [_mt5_alpha_research_report_row(item) for item in ranking]
        )
    else:
        st.info("Ranking de Alphas indisponivel. Execute Pesquisa no Lab.")

    st.subheader("Research Report da Alpha vencedora")
    colunas = st.columns(4)
    colunas[0].metric("Status Alpha", getattr(report, "status", "SEM_DADOS"))
    colunas[1].metric(
        "Cenarios testados",
        int(getattr(report, "tested_scenarios", 0) or 0),
    )
    colunas[2].metric(
        "Confirmacao vencedora",
        _optional_percent(getattr(report, "best_confidence", 0.0)),
    )
    colunas[3].metric(
        "Alvo minimo",
        _optional_percent(
            getattr(report, "target_confidence", MT5_LAB_TARGET_CONFIDENCE)
        ),
    )
    _render_stable_readonly_table([_mt5_alpha_research_report_row(report)])
    with st.expander("Motivos, recomendacoes e evidencias ausentes", expanded=False):
        st.markdown("#### Motivos")
        _render_stable_readonly_table(
            [
                {"Motivo": item}
                for item in list(getattr(report, "failure_reasons", []) or [])
            ]
        )
        st.markdown("#### Recomendacoes")
        _render_stable_readonly_table(
            [
                {"Recomendacao": item}
                for item in list(getattr(report, "recommendations", []) or [])
            ]
        )
        st.markdown("#### Evidencias ainda nao calculadas")
        _render_stable_readonly_table(
            [
                {"Evidencia": item}
                for item in list(getattr(report, "unavailable_evidence", []) or [])
            ]
        )


def _mt5_alpha_research_report_row(report: object) -> dict[str, object]:
    return {
        "Alpha": getattr(report, "alpha_id", "ALPHA001"),
        "Nome": getattr(report, "alpha_name", "N/D"),
        "Status": getattr(report, "status", "SEM_DADOS"),
        "Melhor par": getattr(report, "best_pair", "NONE"),
        "TF": getattr(report, "best_timeframe", "NONE"),
        "Modelo": getattr(report, "best_model", "NONE"),
        "Direcao": getattr(report, "best_decision", "WAIT"),
        "Indicadores usados": " | ".join(
            list(getattr(report, "used_indicators", ()) or ())
        )
        or "N/D",
        "Encaixe Tecnico": _optional_percent(getattr(report, "best_score", 0.0)),
        "Confirmacao Historica": _optional_percent(
            getattr(report, "best_confidence", 0.0)
        ),
        "Pares avaliados": int(getattr(report, "evaluated_pairs", 0) or 0),
        "Fonte": getattr(report, "source", "MT5_RESEARCH_SNAPSHOT"),
    }


def exibir_mt5_heuristic_research_lab(
    data: object,
    *,
    include_full_audit: bool = False,
) -> None:
    """Exibe calibracao MT5 independente do refresh online."""
    research = getattr(data, "mt5_heuristic_research", None)
    forex = getattr(data, "mt5_forex_signals", None)
    st.subheader("Calibracao Forex MT5")
    st.warning(
        "Resultado somente para pesquisa. Nenhuma ordem real sera enviada. "
        "O MT5 Forex online nao executa esta pesquisa automaticamente."
    )
    if research is None:
        st.info("Calibracao MT5 indisponivel.")
        return

    colunas = st.columns(4)
    colunas[0].metric("Fonte historica", getattr(research, "source", "MT5_RESEARCH_SNAPSHOT"))
    colunas[1].metric("Timeframe pesquisa", getattr(research, "timeframe", "M1"))
    colunas[2].metric(
        "Candles historicos",
        int(getattr(research, "candles_loaded", 0) or 0),
    )
    colunas[3].metric(
        "Ultima atualizacao",
        _friendly_candle_time(getattr(research, "last_update", "N/D")),
    )

    colunas = st.columns(3)
    colunas[0].metric("Status pesquisa", getattr(research, "status", "SEM_DADOS"))
    colunas[1].metric("Pares avaliados", len(list(getattr(research, "rows", []) or [])))
    colunas[2].metric("MT5 online", getattr(forex, "connection_status", "N/D"))

    colunas = st.columns(3)
    colunas[0].metric("Melhor par", getattr(research, "best_pair", "NONE"))
    colunas[1].metric(
        "Melhor constante/modelo",
        getattr(research, "best_heuristic", "NONE"),
    )
    colunas[2].metric(
        "Encaixe Tecnico",
        _optional_percent(getattr(research, "best_score", 0.0)),
    )
    colunas = st.columns(2)
    colunas[0].metric("Decisao", getattr(research, "best_decision", "WAIT"))
    colunas[1].metric(
        "Confianca",
        _confidence_label(float(getattr(research, "best_confidence", 0.0) or 0.0)),
    )
    st.caption(getattr(research, "message", "N/D"))
    exibir_modelo_vencedor_mt5_research(research)
    exibir_mt5_scenario_runner_research(
        research,
        include_full_audit=include_full_audit,
    )

    rows = list(getattr(research, "rows", []) or [])
    if not rows:
        st.info(
            "Clique em Executar Pesquisa para atualizar o snapshot historico. "
            "Fluxo equivalente a Atualizar historico de pesquisa (5000 candles). "
            "carregar o snapshot historico de calibracao. O MT5 Forex online "
            "continua atualizando sozinho e nao executa pesquisa pesada."
        )
        return


def exibir_modelo_vencedor_mt5_research(research: object) -> None:
    """Exibe auditoria read-only do modelo vencedor MT5."""
    if getattr(research, "best_heuristic", "NONE") == "NONE":
        st.info("Nenhum modelo vencedor disponivel para auditoria.")
        return

    st.markdown("### Modelo vencedor geral")
    st.caption(
        "Mostra o melhor modelo encontrado na pesquisa inteira. "
        "Serve como resumo global; a tabela operacional para conferencia "
        "por moeda continua sendo Melhor cenario por par."
    )
    _render_stable_readonly_table(
        _dict_to_rows(getattr(research, "winner_configuration", {}))
    )

    st.markdown("### Composicao do Encaixe Tecnico")
    st.caption(
        "Quebra do Encaixe Tecnico: mostra quais componentes ajudaram "
        "a pontuacao tecnica do modelo vencedor. Nao e probabilidade de ganho."
    )
    _render_stable_readonly_table(
        _dict_to_rows(getattr(research, "winner_score_breakdown", {}))
    )

    st.markdown("### Diagnostico")
    st.caption(
        "Leitura textual do resultado. Ajuda a entender por que o Lab aprovou "
        "ou rejeitou a configuracao encontrada."
    )
    diagnostics = list(getattr(research, "winner_diagnostics", []) or [])
    if diagnostics:
        _render_stable_readonly_table([{"Diagnostico": item} for item in diagnostics])
    else:
        st.info("Diagnostico indisponivel para o modelo vencedor.")

    st.markdown("### Configuracao da pesquisa")
    st.caption(
        "Parametros do experimento: tamanho do snapshot, alvos e limites usados "
        "para pesquisar os cenarios. Nao e a configuracao final de operacao."
    )
    _render_stable_readonly_table(
        _dict_to_rows(getattr(research, "winner_research_configuration", {}))
    )


def exibir_mt5_scenario_runner_research(
    research: object,
    *,
    include_full_audit: bool = False,
) -> None:
    """Exibe ranking e vencedores do Scenario Runner MT5."""
    scenarios = list(getattr(research, "scenario_ranking", []) or [])
    best_by_market = _mt5_best_directional_scenario_rows(scenarios)
    best_scenario = getattr(research, "best_scenario", None)

    st.markdown("### Corredor de cenarios")
    st.caption(
        "Esta e a auditoria do Scenario Runner: o Lab cria muitos cenarios, "
        "compara cada combinacao e guarda o ranking. O corredor nao e a "
        "configuracao final; ele explica de onde sairam os vencedores."
        "Definicao oficial: Encaixe Tecnico = setup parece bom agora; "
        "Confirmacao Historica = setups parecidos funcionaram no historico."
    )
    _render_stable_readonly_table(
        [
            {
                "Modo Lab": getattr(research, "priority_event_mode", "NORMAL_LAB_FLOW"),
                "Evento": getattr(research, "priority_event_type", "NONE"),
                "Contexto": getattr(research, "priority_event_context", "NO_TRADE"),
                "Motivo": getattr(
                    research,
                    "priority_event_reason",
                    "Nenhum evento prioritario ativo.",
                ),
            }
        ]
    )
    if best_scenario is None:
        st.info("Nenhum melhor cenario geral disponivel.")
    else:
        st.markdown("#### Melhor cenario geral da pesquisa")
        st.caption(
            "O melhor cenario geral e o primeiro colocado do ranking completo. "
            "Ele pode ser diferente do melhor cenario de uma moeda especifica."
        )
        _render_stable_readonly_table([_mt5_scenario_row(best_scenario)])

    st.markdown("### Melhor cenario por par")
    st.caption(
        "Tabela principal para conferencia visual: uma linha por par, com o "
        "melhor cenario de compra, venda e lateralidade. As colunas de "
        "configuracao mostram Alpha, modelo, timeframe, decisao e parametros "
        "dos indicadores escolhidos."
    )
    if best_by_market:
        _display_temporal_table(best_by_market)
    else:
        st.info("Nenhum cenario vencedor por par disponivel.")
        _render_lab_historical_confirmation_preview()

    show_confirmation_audit = st.checkbox(
        "Mostrar planilha de auditoria da Confirmacao Historica",
        value=True,
        key="mt5_lab_show_confirmation_audit_table",
    )
    if show_confirmation_audit:
        _render_scenario_runner_confirmation_audit(research)
    else:
        st.caption(
            "Planilha de auditoria da Confirmacao Historica ocultada apenas "
            "para aliviar a tela. O ultimo calculo do Lab permanece preservado."
        )

    if include_full_audit:
        st.markdown("### Ranking de cenarios testados")
        st.caption(
            "Auditoria completa dos cenarios avaliados. Serve para investigar por "
            "que uma configuracao ganhou de outra, nao para operar diretamente."
        )
        if scenarios:
            _render_mt5_scenario_ranking_table(scenarios)
        else:
            st.info("Nenhum ranking de cenarios disponivel.")
    else:
        st.caption(
            "Ranking completo dos cenarios ocultado para manter a aba Lab leve. "
            "A auditoria visual da Confirmacao Historica permanece visivel; "
            "marque 'Mostrar auditoria completa do Lab' para carregar o ranking pesado."
        )


def _render_mt5_scenario_ranking_table(scenarios: list[object]) -> None:
    """Renderiza ranking pesado em paginas curtas para nao travar a rolagem."""
    pairs = sorted(
        {
            str(getattr(scenario, "pair", "") or "").upper()
            for scenario in scenarios
            if str(getattr(scenario, "pair", "") or "").strip()
        }
    )
    statuses = sorted(
        {
            str(getattr(scenario, "status", "") or "").upper()
            for scenario in scenarios
            if str(getattr(scenario, "status", "") or "").strip()
        }
    )
    filters = st.columns([1, 1, 1, 1])
    selected_pair = filters[0].selectbox(
        "Par",
        ["TODOS", *pairs],
        index=0,
        key="mt5_scenario_ranking_pair_filter",
    )
    selected_status = filters[1].selectbox(
        "Status",
        ["TODOS", *statuses],
        index=0,
        key="mt5_scenario_ranking_status_filter",
    )
    page_size = int(
        filters[2].selectbox(
            "Linhas por pagina",
            [25, 50, 100, 200],
            index=1,
            key="mt5_scenario_ranking_page_size",
            help="Limite visual para manter a aba Lab leve durante a rolagem.",
        )
    )
    filtered = [
        scenario
        for scenario in scenarios
        if (
            selected_pair == "TODOS"
            or str(getattr(scenario, "pair", "") or "").upper() == selected_pair
        )
        and (
            selected_status == "TODOS"
            or str(getattr(scenario, "status", "") or "").upper() == selected_status
        )
    ]
    total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
    page = int(
        filters[3].number_input(
            "Pagina",
            min_value=1,
            max_value=total_pages,
            value=1,
            step=1,
            key="mt5_scenario_ranking_page",
        )
    )
    start = (page - 1) * page_size
    end = start + page_size
    st.caption(
        f"Exibindo {start + 1 if filtered else 0}-{min(end, len(filtered))} "
        f"de {len(filtered)} filtrados; total bruto: {len(scenarios)} cenarios. "
        "A tabela e paginada para preservar a leveza da aba Lab."
    )
    _render_stable_readonly_table(
        [_mt5_scenario_row(scenario) for scenario in filtered[start:end]],
        decision_column="Status",
        color_status_cells=True,
        empty_columns=["Status", "Alpha", "Beta", "Par", "Timeframe"],
        empty_message="Nenhum cenario encontrado para o filtro.",
    )


def _mt5_scenario_row(scenario: object) -> dict[str, object]:
    parameters = getattr(scenario, "parameters", {}) or {}
    beta_id, beta_mode, _ = _lab_beta_stop_descriptor(scenario)
    return {
        "Status": getattr(scenario, "status", "REJEITADO"),
        "Score": _optional_percent(getattr(scenario, "score", 0.0)),
        "Alpha": getattr(scenario, "alpha_id", "ALPHA001"),
        "Beta": beta_id,
        "Modo Beta": beta_mode,
        "Par": getattr(scenario, "pair", "N/D"),
        "Timeframe": getattr(scenario, "timeframe", "M1"),
        "Modelo": getattr(scenario, "model", "N/D"),
        "Decisao": getattr(scenario, "decision", "WAIT"),
        "Plano inicial": parameters.get(
            "stop_management",
            parameters.get("exit_model", "N/D"),
        ),
        "Sessao": getattr(scenario, "temporal_session_label", "N/D"),
        "Janela BRT": getattr(scenario, "temporal_window_brt", "N/D"),
        "Dia": getattr(scenario, "temporal_weekday", "N/D"),
        "Overlap LDN/NY": _yes_no(getattr(scenario, "temporal_is_overlap", False)),
        "Rollover": _yes_no(getattr(scenario, "temporal_is_rollover", False)),
        "Bloqueio Temporal": getattr(scenario, "temporal_status", "N/D"),
        "Motivo Tempo": getattr(scenario, "temporal_reason", "N/D"),
        "Centros": " | ".join(
            getattr(scenario, "temporal_financial_centers", ()) or ()
        )
        or "N/D",
        "Evento": parameters.get("event_type", "N/D"),
        "Modo Evento": parameters.get("event_mode", "N/D"),
        "Contexto Evento": parameters.get("context", "N/D"),
        "Parametros": " | ".join(
            f"{key}={value}" for key, value in dict(parameters).items()
        )
        or "N/D",
        "Confirmacao Historica": _optional_percent(
            getattr(scenario, "lab_confidence", 0.0)
        ),
        "Amostra Historica": int(
            getattr(scenario, "lab_confidence_sample_size", 0) or 0
        ),
        "PF Historico": _optional_number(
            getattr(scenario, "lab_confidence_profit_factor", 0.0)
        ),
        "Expectancy Hist.": _optional_percent(
            getattr(scenario, "lab_confidence_expectancy", 0.0)
        ),
        "DD Hist.": _optional_percent(
            getattr(scenario, "lab_confidence_max_drawdown", 0.0)
        ),
        "Fonte Confirmacao": getattr(
            scenario,
            "lab_confidence_source",
            "SCENARIO_HISTORICAL_EVIDENCE",
        ),
        "ICT": f"{float(getattr(scenario, 'ict_score', 0.0) or 0.0):.2f}",
        "Classe ICT": getattr(scenario, "ict_grade", "E"),
        "Uso ICT": getattr(scenario, "ict_usage", "Rejeitada."),
        "Demo liberado": _yes_no(getattr(scenario, "ict_demo_allowed", False)),
        "Travas ICT": " | ".join(
            getattr(scenario, "ict_rejection_reasons", ()) or ()
        )
        or "OK",
        "Alvo de confirmacao": _optional_percent(MT5_LAB_TARGET_CONFIDENCE),
        "Distancia alvo": _optional_percent(
            abs(
                float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
                - MT5_LAB_TARGET_CONFIDENCE
            )
        ),
        "Motivo": getattr(scenario, "reason", "N/D"),
    }


def _mt5_best_directional_scenario_rows(scenarios: list[object]) -> list[dict[str, object]]:
    pairs = sorted(
        {
            str(getattr(scenario, "pair", "") or "").upper()
            for scenario in scenarios
            if str(getattr(scenario, "pair", "") or "").strip()
        }
    )
    rows: list[dict[str, object]] = []
    for pair in pairs:
        buy_scenario = _best_scenario_for_pair_and_decision(scenarios, pair, "BUY")
        sell_scenario = _best_scenario_for_pair_and_decision(scenarios, pair, "SELL")
        wait_scenario = _best_scenario_for_pair_and_decision(scenarios, pair, "WAIT")
        rows.append(
            {
                "Par": pair,
                "Compra": _directional_scenario_summary(buy_scenario),
                "Venda": _directional_scenario_summary(sell_scenario),
                "Lateralidade": _directional_scenario_summary(wait_scenario),
                "Config Compra": _scenario_configuration_summary(buy_scenario),
                "Config Venda": _scenario_configuration_summary(sell_scenario),
                "Config Lateral": _scenario_configuration_summary(wait_scenario),
                "Sessao Compra": _scenario_temporal_summary(buy_scenario),
                "Sessao Venda": _scenario_temporal_summary(sell_scenario),
                "Sessao Lateral": _scenario_temporal_summary(wait_scenario),
                "Bloqueio Compra": _scenario_temporal_status(buy_scenario),
                "Bloqueio Venda": _scenario_temporal_status(sell_scenario),
                "Bloqueio Lateral": _scenario_temporal_status(wait_scenario),
                "Encaixe Alpha001": _alpha_score_text(scenarios, pair, "ALPHA001"),
                "Encaixe Alpha002": _alpha_score_text(scenarios, pair, "ALPHA002"),
                "Encaixe Alpha003": _alpha_score_text(scenarios, pair, "ALPHA003"),
                "Encaixe Alpha004": _alpha_score_text(scenarios, pair, "ALPHA004"),
                "Encaixe Alpha005": _alpha_score_text(scenarios, pair, "ALPHA005"),
                "Encaixe Alpha006": _alpha_score_text(scenarios, pair, "ALPHA006"),
                "Encaixe Alpha007": _alpha_score_text(scenarios, pair, "ALPHA007"),
                "Encaixe Alpha008": _alpha_score_text(scenarios, pair, "ALPHA008"),
                "Encaixe Alpha009": _alpha_score_text(scenarios, pair, "ALPHA009"),
                "Encaixe Alpha010": _alpha_score_text(scenarios, pair, "ALPHA010"),
                "Encaixe Alpha011": _alpha_score_text(scenarios, pair, "ALPHA011"),
                "Encaixe Alpha012": _alpha_score_text(scenarios, pair, "ALPHA012"),
                "Encaixe Alpha013": _alpha_score_text(scenarios, pair, "ALPHA013"),
                "Encaixe Alpha014": _alpha_score_text(scenarios, pair, "ALPHA014"),
                "Encaixe Alpha015": _alpha_score_text(scenarios, pair, "ALPHA015"),
                "TF Compra": _scenario_timeframe(buy_scenario),
                "TF Venda": _scenario_timeframe(sell_scenario),
                "TF Lateral": _scenario_timeframe(wait_scenario),
                "Encaixe Compra": _scenario_score_text(buy_scenario),
                "Encaixe Venda": _scenario_score_text(sell_scenario),
                "Encaixe Lateral": _scenario_score_text(wait_scenario),
                "Confirmacao Compra": _scenario_lab_confidence_text(buy_scenario),
                "Confirmacao Venda": _scenario_lab_confidence_text(sell_scenario),
                "Confirmacao Lateral": _scenario_lab_confidence_text(wait_scenario),
                "Amostra Compra": _scenario_sample_text(buy_scenario),
                "Amostra Venda": _scenario_sample_text(sell_scenario),
                "Amostra Lateral": _scenario_sample_text(wait_scenario),
                "ICT Compra": _scenario_ict_text(buy_scenario),
                "ICT Venda": _scenario_ict_text(sell_scenario),
                "ICT Lateral": _scenario_ict_text(wait_scenario),
                "Alvo de confirmacao": _optional_percent(MT5_LAB_TARGET_CONFIDENCE),
            }
        )
    return rows


def _alpha_score_text(
    scenarios: list[object],
    pair: str,
    alpha_id: str,
) -> str:
    candidates = [
        scenario
        for scenario in scenarios
        if str(getattr(scenario, "pair", "") or "").upper() == pair
        and str(getattr(scenario, "alpha_id", "ALPHA001") or "").upper()
        == alpha_id
    ]
    if not candidates:
        return "0.00%"
    best = max(
        candidates,
        key=lambda scenario: float(getattr(scenario, "score", 0.0) or 0.0),
    )
    return _optional_percent(getattr(best, "score", 0.0))


def _scenario_ict_text(scenario: object | None) -> str:
    if scenario is None:
        return "N/D"
    return (
        f"{float(getattr(scenario, 'ict_score', 0.0) or 0.0):.2f} | "
        f"{getattr(scenario, 'ict_grade', 'E')} | "
        f"{getattr(scenario, 'ict_status', 'REJEITADA')}"
    )


def _scenario_sample_text(scenario: object | None) -> str:
    if scenario is None:
        return "0"
    return str(int(getattr(scenario, "lab_confidence_sample_size", 0) or 0))


def _best_scenario_for_pair_and_decision(
    scenarios: list[object],
    pair: str,
    decision: str,
) -> object | None:
    candidates = [
        scenario
        for scenario in scenarios
        if str(getattr(scenario, "pair", "") or "").upper() == pair
        and str(getattr(scenario, "decision", "") or "").upper() == decision
    ]
    if not candidates:
        return None
    return max(candidates, key=_mt5_lab_target_scenario_rank)


def _mt5_lab_target_scenario_rank(scenario: object) -> tuple[bool, float, float, float]:
    lab_confidence = float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
    score = float(getattr(scenario, "score", 0.0) or 0.0)
    return (
        lab_confidence >= MT5_LAB_TARGET_CONFIDENCE,
        -abs(lab_confidence - MT5_LAB_TARGET_CONFIDENCE),
        score,
        lab_confidence,
    )


def _mt5_directional_scenario_row(
    pair: str,
    label: str,
    scenario: object | None,
) -> dict[str, object]:
    if scenario is None:
        return {
            "Par": pair,
            "Tipo": label,
            "Timeframe": "N/D",
            "Modelo": "N/D",
            "Parametros": "N/D",
            "Encaixe Tecnico": "0.00%",
            "Confirmacao Historica": "0.00%",
            "Alvo de confirmacao": _optional_percent(MT5_LAB_TARGET_CONFIDENCE),
            "Distancia alvo": "N/D",
            "Confiabilidade": "BAIXA",
            "Status": "SEM_CENARIO",
            "Motivo": "Nenhum cenario encontrado para esta direcao.",
        }
    parameters = getattr(scenario, "parameters", {}) or {}
    score = float(getattr(scenario, "score", 0.0) or 0.0)
    lab_confidence = float(getattr(scenario, "lab_confidence", 0.0) or 0.0)
    return {
        "Par": pair,
        "Tipo": label,
        "Timeframe": getattr(scenario, "timeframe", "M1"),
        "Modelo": getattr(scenario, "model", "N/D"),
        "Parametros": _scenario_parameters_label(parameters),
        "Encaixe Tecnico": _optional_percent(score),
        "Confirmacao Historica": _optional_percent(lab_confidence),
        "Alvo de confirmacao": _optional_percent(MT5_LAB_TARGET_CONFIDENCE),
        "Distancia alvo": _optional_percent(
            abs(lab_confidence - MT5_LAB_TARGET_CONFIDENCE)
        ),
        "Confiabilidade": _confidence_label(lab_confidence),
        "Status": getattr(scenario, "status", "REJEITADO"),
        "Motivo": getattr(scenario, "reason", "N/D"),
    }


def _directional_scenario_summary(scenario: object | None) -> str:
    if scenario is None:
        return "SEM_CENARIO"
    model = getattr(scenario, "model", "N/D")
    timeframe = getattr(scenario, "timeframe", "M1")
    status = getattr(scenario, "status", "REJEITADO")
    score = _scenario_score_text(scenario)
    lab_confidence = _scenario_lab_confidence_text(scenario)
    return (
        f"{model} | {timeframe} | encaixe {score} | "
        f"confirmacao {lab_confidence} | {status}"
    )


def _scenario_configuration_summary(scenario: object | None) -> str:
    if scenario is None:
        return "N/D"
    alpha = getattr(scenario, "alpha_id", "ALPHA001")
    model = getattr(scenario, "model", "N/D")
    timeframe = getattr(scenario, "timeframe", "M1")
    decision = getattr(scenario, "decision", "WAIT")
    parameters = _scenario_parameters_label(getattr(scenario, "parameters", {}) or {})
    return (
        f"{alpha} | {model} | {timeframe} | decisao={decision} | "
        f"{parameters}"
    )


def _scenario_timeframe(scenario: object | None) -> str:
    if scenario is None:
        return "N/D"
    return str(getattr(scenario, "timeframe", "M1"))


def _scenario_temporal_summary(scenario: object | None) -> str:
    if scenario is None:
        return "N/D"
    session = getattr(scenario, "temporal_session_label", "N/D")
    window_brt = getattr(scenario, "temporal_window_brt", "N/D")
    note = getattr(scenario, "temporal_quality_note", "N/D")
    return f"{session} | BRT {window_brt} | {note}"


def _scenario_temporal_status(scenario: object | None) -> str:
    if scenario is None:
        return "N/D"
    return str(getattr(scenario, "temporal_status", "N/D") or "N/D")


def _display_temporal_table(rows: list[dict[str, object]]) -> None:
    if not rows:
        _render_stable_readonly_table(rows)
        return
    _render_stable_readonly_table(rows)


def _optional_int(value: object) -> str:
    if value is None:
        return "N/D"
    try:
        return str(int(value))
    except (TypeError, ValueError):
        return "N/D"


def _yes_no(value: object) -> str:
    return "SIM" if bool(value) else "NAO"


def _scenario_score_text(scenario: object | None) -> str:
    if scenario is None:
        return "0.00%"
    return _optional_percent(getattr(scenario, "score", 0.0))


def _scenario_lab_confidence_text(scenario: object | None) -> str:
    if scenario is None:
        return "0.00%"
    return _optional_percent(getattr(scenario, "lab_confidence", 0.0))


def _dict_to_rows(values: object) -> list[dict[str, object]]:
    if not isinstance(values, dict):
        return []
    return [
        {"Campo": str(key), "Valor": str(value)}
        for key, value in values.items()
    ]


def _confidence_label(confidence: float) -> str:
    if confidence >= 0.75:
        return "ALTA"
    if confidence >= 0.50:
        return "MEDIA"
    return "BAIXA"


def _mt5_heuristic_research_row(row: object) -> dict[str, object]:
    return {
        "Par": getattr(row, "pair", "N/D"),
        "Timeframe ideal": getattr(
            row,
            "ideal_timeframe",
            getattr(row, "timeframe", "M1"),
        ),
        "Heuristica recomendada": getattr(
            row,
            "recommended_heuristic",
            "WAIT_NO_EDGE",
        ),
        "Configuracao usada": _scenario_parameters_label(
            getattr(row, "final_configuration", {}) or {}
        ),
        "Cenario compra": _scenario_parameters_label(
            getattr(row, "buy_scenario", {}) or {}
        ),
        "Encaixe compra": _optional_percent(getattr(row, "buy_score", 0.0)),
        "Cenario venda": _scenario_parameters_label(
            getattr(row, "sell_scenario", {}) or {}
        ),
        "Encaixe venda": _optional_percent(getattr(row, "sell_score", 0.0)),
        "Decisao": getattr(row, "decision", "WAIT"),
        "Encaixe Tecnico": _optional_percent(getattr(row, "score", 0.0)),
        "Confirmacao Historica": _optional_percent(
            getattr(row, "confidence", 0.0)
        ),
        "Status": getattr(row, "status", "SEM_DADOS"),
        "Motivo": getattr(row, "reason", "N/D"),
    }


def _scenario_parameters_label(parameters: object) -> str:
    if not isinstance(parameters, dict) or not parameters:
        return "N/D"
    return " | ".join(f"{key}={value}" for key, value in parameters.items())


def exibir_dataset_research_lab(data: object) -> None:
    """Exibe o dataset real usado pelo Research Lab."""
    dataset = getattr(data, "active_dataset", None)
    st.subheader("Dataset de Research")
    if dataset is None:
        st.info("Nenhum dataset de pesquisa disponivel.")
        return
    colunas = st.columns(4)
    colunas[0].metric("Ativo", dataset.asset)
    colunas[1].metric("Timeframe", dataset.timeframe.upper())
    colunas[2].metric("Candles", valor_ou_indisponivel(dataset.candles))
    colunas[3].metric("Status", dataset.status)
    st.caption(dataset.dataset_id)


def exibir_status_alpha001_research_lab(alpha_status: object) -> None:
    """Exibe resumo visual da Alpha 001 no Research Lab."""
    st.subheader("Alpha 001 - IORB")
    if alpha_status is None:
        st.info("Status da Alpha 001 indisponível.")
        return

    colunas = st.columns(4)
    colunas[0].metric("Status", alpha_status.status)
    colunas[1].metric(
        "Operacao real",
        _autorizado(alpha_status.real_trading_authorized),
    )
    colunas[2].metric(
        "Corretora/MT5",
        _integrado(alpha_status.broker_mt5_integrated),
    )
    colunas[3].metric("IA", _autorizado(alpha_status.ai_authorized))
    st.caption(alpha_status.statistical_validation_status)


def exibir_alpha001_paper_status(paper_status: object) -> None:
    """Exibe estado paper da Alpha001 via DashboardService."""
    st.subheader("Paper Trading Alpha001")
    if paper_status is None:
        st.info("Estado paper Alpha001 indisponivel.")
        return
    colunas = st.columns(4)
    colunas[0].metric("Status", paper_status.status)
    colunas[1].metric("Operacoes", paper_status.total_trades)
    colunas[2].metric(
        "Resultado acumulado",
        f"{paper_status.accumulated_result_points:.2f}",
    )
    colunas[3].metric(
        "Operacao real",
        _autorizado(paper_status.real_trading_authorized),
    )
    exibir_alpha001_paper_position(paper_status.position)
    exibir_alpha001_paper_history(paper_status.trades_history)
    exibir_alpha001_paper_equity(paper_status.equity_curve)


def exibir_alpha001_paper_position(position: object) -> None:
    """Exibe a posicao paper atual da Alpha001."""
    st.caption("Posicao paper atual")
    if position is None:
        st.info("Nenhuma posicao paper aberta.")
        return
    colunas = st.columns(5)
    colunas[0].metric("Side", position.side)
    colunas[1].metric("Quantity", position.quantity)
    colunas[2].metric("Status", position.status)
    colunas[3].metric("Entrada", f"{position.entry_price:.2f}")
    colunas[4].metric("Resultado", f"{position.result_points:.2f}")


def exibir_alpha001_paper_history(history: list[object]) -> None:
    """Exibe historico paper Alpha001."""
    st.caption("Historico paper")
    if not history:
        st.info("Nenhuma operacao paper fechada.")
        return
    exibir_registros_readonly(_alpha001_paper_trades_table(history))


def exibir_alpha001_paper_equity(equity_curve: list[float]) -> None:
    """Exibe curva de patrimonio paper Alpha001."""
    st.caption("Equity curve paper")
    if not equity_curve:
        st.line_chart([0.0])
        return
    st.line_chart(equity_curve)


def exibir_alpha001_paper_report(report: object) -> None:
    """Exibe relatorio operacional paper Alpha001."""
    st.subheader("Relatorio Operacional Paper Alpha001")
    if report is None:
        st.info("Relatorio paper Alpha001 indisponivel.")
        return
    colunas = st.columns(6)
    colunas[0].metric("Status", report.status)
    colunas[1].metric("Operacoes", report.total_operations)
    colunas[2].metric("Win rate paper", f"{report.paper_win_rate:.0%}")
    colunas[3].metric(
        "Resultado acumulado",
        f"{report.accumulated_result_points:.2f}",
    )
    colunas[4].metric("Max drawdown", f"{report.max_drawdown_points:.2f}")
    colunas[5].metric("Max perdas seguidas", report.max_loss_sequence)
    exibir_alpha001_paper_report_position(report.current_position)


def exibir_alpha001_paper_report_position(position: object) -> None:
    """Exibe posicao atual do relatorio paper."""
    st.caption("Posicao atual no relatorio")
    if position is None:
        st.info("Nenhuma posicao paper aberta no relatorio.")
        return
    colunas = st.columns(4)
    colunas[0].metric("Side", position.side)
    colunas[1].metric("Quantity", position.quantity)
    colunas[2].metric("Status", position.status)
    colunas[3].metric("Entrada", f"{position.entry_price:.2f}")


def exibir_relatorio_alpha001_research_lab(report: object) -> None:
    """Exibe relatorio consolidado da Alpha 001 no Research Lab."""
    st.subheader("Relatório de Validação Alpha 001")
    if report is None:
        st.info("Relatório da Alpha 001 indisponível.")
        return

    colunas = st.columns(5)
    colunas[0].metric("Trades", report.total_trades)
    colunas[1].metric("Win rate", f"{report.win_rate:.0%}")
    colunas[2].metric("Profit factor", _format_profit_factor(report.profit_factor))
    colunas[3].metric("Max drawdown", f"{report.max_drawdown_points:.2f}")
    colunas[4].metric("Net points", f"{report.net_profit_points:.2f}")
    st.metric("Status de validacao", report.validation_status)
    st.warning("Operacao real: NAO AUTORIZADA. Envio de ordens reais proibido.")
    st.caption(report.summary)


def exibir_dashboard_research_alpha001(metrics: object) -> None:
    """Exibe metricas consolidadas do Research Lab via DashboardService."""
    st.subheader("Dashboard Research Alpha001")
    if metrics is None:
        st.info("Metricas de research Alpha001 indisponiveis.")
        return

    colunas = st.columns(4)
    colunas[0].metric("Total trades", metrics.total_trades)
    colunas[1].metric("Total BUY", metrics.total_buy)
    colunas[2].metric("Total SELL", metrics.total_sell)
    colunas[3].metric("Total WAIT", metrics.total_wait)

    colunas = st.columns(4)
    colunas[0].metric("Net profit", f"{metrics.net_profit:.2f}")
    colunas[1].metric("Gross profit", f"{metrics.gross_profit:.2f}")
    colunas[2].metric("Gross loss", f"{metrics.gross_loss:.2f}")
    colunas[3].metric("Max drawdown", f"{metrics.max_drawdown:.2f}")

    colunas = st.columns(4)
    colunas[0].metric("Win rate", f"{metrics.win_rate:.0%}")
    colunas[1].metric(
        "Profit factor",
        _format_profit_factor(metrics.profit_factor),
    )
    colunas[2].metric("Expectancy", f"{metrics.expectancy:.2f}")
    colunas[3].metric("Recommendation", metrics.recommendation)

    st.caption("Equity curve")
    st.line_chart(metrics.equity_curve or [0.0])
    exibir_benchmark_dashboard_research_alpha001(metrics.benchmark)


def exibir_benchmark_dashboard_research_alpha001(benchmark: object) -> None:
    """Exibe benchmark entre experimentos Alpha001 via DashboardService."""
    st.caption("Benchmark entre experimentos")
    if benchmark is None or benchmark.total_results == 0:
        st.info("Nenhum benchmark Alpha001 disponivel.")
        return

    colunas = st.columns(4)
    colunas[0].metric("Experimentos", benchmark.total_results)
    colunas[1].metric("Melhor geral", valor_ou_indisponivel(benchmark.best_overall))
    colunas[2].metric(
        "Mais trades",
        valor_ou_indisponivel(benchmark.best_total_trades),
    )
    colunas[3].metric(
        "Melhor net",
        valor_ou_indisponivel(benchmark.best_net_profit),
    )

    exibir_registros_readonly(_alpha001_dashboard_benchmark_table(benchmark))


def exibir_research_report(report: object) -> None:
    """Exibe ResearchReport consolidado via camada Application."""
    st.subheader("Research Report")
    if report is None:
        st.info("Research Report indisponivel.")
        return
    st.metric("Conclusao", report.conclusion)
    st.caption(report.statistical_summary)
    if report.metrics:
        exibir_registros_readonly(_dict_table(report.metrics))
    if report.parameters:
        st.caption("Parametros utilizados")
        exibir_registros_readonly(_dict_table(report.parameters))
    if report.conclusion_reasons:
        st.caption(", ".join(report.conclusion_reasons))


def exibir_ranking_alpha001_research_lab(
    service: DashboardService,
    ranking: list[object],
) -> None:
    """Exibe ranking de parametros da Alpha 001."""
    st.subheader("Ranking de Parametros Alpha001")
    if not ranking:
        st.info("Nenhum ranking Alpha001 executado.")
        return
    selected_status = st.selectbox(
        "Filtro Alpha001",
        ["ALL", "APPROVED", "REJECTED", "INSUFFICIENT_SAMPLE"],
    )
    filtered_ranking = service.filter_alpha001_parameter_ranking(
        selected_status,
    )
    if not filtered_ranking:
        st.info("Nenhum resultado Alpha001 para o filtro selecionado.")
        return
    exibir_melhor_configuracao_alpha001(filtered_ranking[0])
    exibir_registros_readonly(_alpha001_ranking_table(filtered_ranking))


def exibir_exportacao_alpha001_research_lab(
    service: DashboardService,
) -> None:
    """Exibe acao explicita de exportacao CSV Alpha001."""
    st.subheader("Exportacao Alpha001")
    output_path = st.text_input(
        "Caminho do CSV Alpha001",
        value="resultados/alpha001_ranking.csv",
    )
    if st.button("Exportar CSV Alpha001"):
        try:
            exported_path = service.export_alpha001_results_to_csv(output_path)
            st.success(f"CSV Alpha001 exportado em: {exported_path}")
        except Exception as exc:
            st.error(f"Nao foi possivel exportar CSV Alpha001: {exc}")


def exibir_resumo_alpha001_research_lab(summary: object) -> None:
    """Exibe resumo estatistico consolidado da Alpha001."""
    st.subheader("Resumo Estatistico Alpha001")
    if summary is None:
        st.info("Resumo Alpha001 indisponivel.")
        return
    colunas = st.columns(4)
    colunas[0].metric("Experimentos", summary.total_experiments)
    colunas[1].metric("Aprovados", summary.total_approved)
    colunas[2].metric("Rejeitados", summary.total_rejected)
    colunas[3].metric("Taxa aprovacao", f"{summary.approval_rate:.0%}")
    colunas = st.columns(3)
    colunas[0].metric(
        "Melhor profit factor",
        _format_profit_factor(summary.best_profit_factor),
    )
    colunas[1].metric(
        "Menor drawdown",
        f"{summary.lowest_max_drawdown_points:.2f}",
    )
    colunas[2].metric(
        "Melhor net points",
        f"{summary.best_net_profit_points:.2f}",
    )


def exibir_robustez_alpha001_research_lab(robustness: object) -> None:
    """Exibe analise de robustez da Alpha001."""
    st.subheader("Robustez Alpha001")
    if robustness is None:
        st.info("Robustez Alpha001 indisponivel.")
        return
    colunas = st.columns(2)
    colunas[0].metric("Robustness score", f"{robustness.robustness_score:.0f}")
    colunas[1].metric("Status", robustness.status)
    st.write(", ".join(robustness.reasons))


def exibir_melhor_configuracao_alpha001(best: object) -> None:
    """Exibe a melhor configuracao ranqueada da Alpha001."""
    st.caption("Melhor configuracao")
    colunas = st.columns(5)
    colunas[0].metric("Opening Range", best.opening_range_minutes)
    colunas[1].metric(
        "Profit factor",
        _format_profit_factor(best.profit_factor),
    )
    colunas[2].metric("Drawdown", f"{best.max_drawdown_points:.2f}")
    colunas[3].metric("Net points", f"{best.net_profit_points:.2f}")
    colunas[4].metric("Status", best.validation_status)


def exibir_estrategias_disponiveis_research_lab(strategies: list[str]) -> None:
    """Exibe estrategias disponiveis para experimentos do Research Lab."""
    st.subheader("Estratégias Disponíveis")
    if not strategies:
        st.info("Nenhuma estratégia disponível.")
        return
    st.selectbox("Estratégia para pesquisa", strategies)


def exibir_ultimo_experimento_research_lab(experiment: object) -> None:
    """Exibe metricas do ultimo experimento."""
    st.subheader("Ultimo Experimento")
    if experiment is None:
        st.info("Nenhum experimento executado.")
        return
    exibir_metricas_experimento(experiment)


def exibir_lista_experimentos_research_lab(experiments: list[object]) -> None:
    """Exibe lista de experimentos executados."""
    st.subheader("Experimentos")
    if not experiments:
        st.info("Nenhum experimento na memoria.")
        return
    exibir_registros_readonly(_research_experiments_table(experiments))


def exibir_benchmarks_research_lab(benchmarks: list[object]) -> None:
    """Exibe benchmarks executados no laboratorio."""
    st.subheader("Benchmarks")
    if not benchmarks:
        st.info("Nenhum benchmark executado.")
        return
    exibir_registros_readonly(_research_benchmarks_table(benchmarks))


def exibir_comparacao_benchmarks_research_lab(comparison: object) -> None:
    """Exibe ranking e melhor benchmark."""
    st.subheader("Comparacao de Benchmarks")
    if comparison is None:
        st.info("Nenhuma comparacao executada.")
        return
    exibir_melhor_benchmark(comparison)
    st.caption("Ranking")
    exibir_registros_readonly(_research_benchmarks_table(comparison.ranking))


def exibir_melhor_benchmark(comparison: object) -> None:
    """Exibe metricas da melhor estrategia."""
    colunas = st.columns(5)
    colunas[0].metric("Melhor estrategia", comparison.best_strategy or "N/D")
    colunas[1].metric("Melhor lucro", f"{comparison.best_profit:.2f}")
    colunas[2].metric(
        "Melhor profit factor",
        _format_profit_factor(comparison.best_profit_factor),
    )
    colunas[3].metric("Melhor win rate", f"{comparison.best_win_rate:.0%}")
    colunas[4].metric("Melhor drawdown", f"{comparison.best_drawdown:.2f}")


def exibir_parameter_grid_research_lab(
    grid_results: list[object],
    best_grid: object,
) -> None:
    """Exibe resultados da grade de parametros."""
    st.subheader("Grid de Parametros")
    if not grid_results:
        st.info("Nenhum grid de parametros executado.")
        return
    if best_grid is not None:
        exibir_melhor_grid(best_grid)
    exibir_registros_readonly(_parameter_grid_table(grid_results, best_grid))


def exibir_melhor_grid(best_grid: object) -> None:
    """Destaca a melhor combinacao por lucro liquido."""
    st.caption("Melhor combinacao por net_profit_points")
    colunas = st.columns(4)
    colunas[0].metric("Stop", best_grid.stop_points)
    colunas[1].metric("Target", best_grid.target_points)
    colunas[2].metric("Estrategia", best_grid.strategy_name)
    colunas[3].metric("Net points", f"{best_grid.net_profit_points:.2f}")


def exibir_validacoes_benchmarks_research_lab(validations: list[object]) -> None:
    """Exibe validacoes estatisticas dos benchmarks."""
    st.subheader("Validacao Estatistica")
    if not validations:
        st.info("Nenhuma validacao estatistica executada.")
        return
    exibir_registros_readonly(_benchmark_validations_table(validations))
    st.info(validations[-1].summary)


def exibir_metricas_experimento(experiment: object) -> None:
    """Exibe metricas basicas de um experimento."""
    st.caption(experiment.experiment_name)
    colunas = st.columns(4)
    colunas[0].metric("Estrategia", experiment.strategy_name)
    colunas[1].metric("Stop", experiment.stop_points)
    colunas[2].metric("Target", experiment.target_points)
    colunas[3].metric("Trades", experiment.total_trades)
    colunas = st.columns(4)
    colunas[0].metric("Vitorias", experiment.wins)
    colunas[1].metric("Derrotas", experiment.losses)
    colunas[2].metric("Win rate", f"{experiment.win_rate:.0%}")
    colunas[3].metric("Net points", f"{experiment.net_profit_points:.2f}")
    colunas = st.columns(2)
    colunas[0].metric(
        "Profit factor",
        _format_profit_factor(experiment.profit_factor),
    )
    colunas[1].metric(
        "Max drawdown",
        f"{experiment.max_drawdown_points:.2f}",
    )


def exibir_replay(service: DashboardService) -> None:
    """Exibe controles e estado do replay."""
    st.subheader("Replay")
    pending_replay_data = apply_pending_replay_action(service)
    data = service.get_dashboard_data()
    replay_data = getattr(data, "replay_data", None)
    if pending_replay_data is not None:
        replay_data = pending_replay_data
    show_pending_replay_message()
    replay_data = exibir_controles_replay(service, replay_data)
    if replay_data is None:
        st.info("Replay ainda nao disponivel.")
        return
    exibir_estado_replay(replay_data)
    exibir_candle_replay(getattr(replay_data, "current_candle", None))
    exibir_features_replay(getattr(replay_data, "feature_snapshot", None))
    exibir_regime_replay(getattr(replay_data, "regime_analysis", None))
    exibir_pesquisa_replay(getattr(replay_data, "research_data", None))
    exibir_sinal_estrategia_replay(
        getattr(replay_data, "strategy_signal", None)
    )
    exibir_decision_context_replay(
        getattr(replay_data, "decision_context", None)
    )
    exibir_order_preview_replay(getattr(replay_data, "order_preview", None))
    exibir_paper_position_replay(
        getattr(replay_data, "paper_position", None)
    )
    exibir_paper_trades_history_replay(replay_data)
    exibir_paper_equity_curve_replay(replay_data)
    exibir_paper_metrics_replay(getattr(replay_data, "paper_metrics", None))
    exibir_eventos_replay(replay_data)
    exibir_mini_chart_replay(replay_data)
    executar_auto_run(service, replay_data)


def exibir_controles_replay(
    service: DashboardService,
    replay_data: object,
) -> object:
    """Exibe botoes de controle do replay."""
    colunas = st.columns(5)
    if colunas[0].button(
        "Carregar Dataset Selecionado",
        key="replay_load_selected_dataset",
    ):
        request_replay_action("load_dataset")

    exibir_datasets_historicos_replay(service)

    disabled = replay_control_disabled(replay_data)
    if colunas[1].button("Iniciar", disabled=disabled["start"], key="replay_start"):
        replay_data = service.start_replay()

    disabled = replay_control_disabled(replay_data)
    if colunas[2].button(
        "Proximo Candle",
        disabled=disabled["next"],
        key="replay_next_candle",
    ):
        replay_data = service.next_replay_candle()

    disabled = replay_control_disabled(replay_data)
    if colunas[3].button("Parar", disabled=disabled["stop"], key="replay_stop"):
        replay_data = service.stop_replay()

    disabled = replay_control_disabled(replay_data)
    if colunas[4].button("Resetar", disabled=disabled["reset"], key="replay_reset"):
        replay_data = service.reset_replay()

    replay_data = exibir_controles_auto_replay(service, replay_data)
    return replay_data


def exibir_datasets_historicos_replay(service: DashboardService) -> None:
    """Exibe selecao de dataset historico via DashboardService."""
    st.caption("Datasets historicos de pesquisa")
    datasets = service.list_historical_datasets()
    selected = service.get_selected_historical_dataset()
    exibir_saude_datasets_historicos(service)
    exibir_metricas_providers_historicos(service)
    exibir_dataset_historico_ativo(selected)
    exibir_readiness_dataset_historico(service)
    exibir_metricas_readiness_gate(service)
    exibir_auditoria_readiness_gate(service)
    if not datasets:
        st.info("Nenhum dataset historico cadastrado.")
        return
    exibir_registros_readonly(_historical_datasets_table(datasets))
    dataset_id = st.selectbox(
        "Dataset historico de pesquisa",
        options=[dataset.dataset_id for dataset in datasets],
        key="historical_dataset_id",
    )
    if st.button("Selecionar Dataset Historico", key="select_historical_dataset"):
        request_replay_action("select_dataset", dataset_id)
    exibir_acoes_dataset_historico(service)
    exibir_historico_qualidade_dataset_historico(service)


def exibir_acoes_dataset_historico(service: DashboardService) -> None:
    """Exibe acoes manuais para dataset historico selecionado."""
    colunas = st.columns(3)
    if colunas[0].button(
        "Carregar Replay do Dataset",
        key="load_selected_historical_dataset_replay",
    ):
        request_replay_action("load_dataset")
    if colunas[1].button(
        "Executar Research do Dataset",
        key="run_selected_historical_dataset_research",
    ):
        try:
            experiment = service.run_selected_historical_dataset_research_experiment()
            st.success(
                f"Research executado: {experiment.experiment_name}"
            )
        except ValueError as exc:
            st.error(str(exc))
    if colunas[2].button(
        "Analisar Qualidade do Dataset",
        key="analyze_selected_historical_dataset_quality",
    ):
        try:
            report = service.analyze_selected_historical_dataset_quality()
            exibir_qualidade_dataset_historico(report)
        except ValueError as exc:
            st.error(str(exc))


def exibir_saude_datasets_historicos(service: DashboardService) -> None:
    """Exibe resumo consolidado de saude dos datasets."""
    summary = service.get_historical_dataset_health_summary()
    st.caption("Saude geral dos datasets historicos")
    colunas = st.columns(6)
    colunas[0].metric("Catalogados", summary.total_datasets)
    colunas[1].metric("Validados", summary.total_validated)
    colunas[2].metric("Aprovados", summary.total_approved)
    colunas[3].metric("Reprovados", summary.total_rejected)
    colunas[4].metric("Sem validacao", summary.total_unvalidated)
    colunas[5].metric(
        "Ultima validacao",
        valor_ou_indisponivel(summary.last_validation_at),
    )


def exibir_metricas_providers_historicos(service: DashboardService) -> None:
    """Exibe comparacao consolidada por provider historico."""
    metrics = service.get_historical_provider_metrics()
    st.caption("Comparacao de providers historicos registrados")
    if not metrics:
        st.info("Nenhuma metrica de provider historico registrada.")
        return
    exibir_registros_readonly(_historical_provider_metrics_table(metrics))


def exibir_readiness_dataset_historico(service: DashboardService) -> None:
    """Exibe Data Readiness Gate do dataset selecionado."""
    st.caption("Data Readiness Gate")
    try:
        readiness = service.get_selected_historical_dataset_readiness()
    except ValueError:
        st.info("Selecione um dataset historico para ver a prontidao.")
        return
    colunas = st.columns(2)
    colunas[0].metric("Readiness", readiness.readiness)
    colunas[1].metric("Dataset", readiness.dataset_id)
    if readiness.reasons:
        exibir_registros_readonly(
            _historical_dataset_readiness_reasons_table(readiness.reasons)
        )
        return
    st.info("Nenhum motivo restritivo registrado.")


def exibir_auditoria_readiness_gate(service: DashboardService) -> None:
    """Exibe historico de decisoes do Data Readiness Gate."""
    st.caption("Auditoria do Data Readiness Gate")
    dataset = service.get_selected_historical_dataset()
    if dataset is None:
        st.info("Selecione um dataset historico para ver a auditoria do gate.")
        return
    logs = [
        log
        for log in service.list_data_readiness_gate_logs()
        if log.dataset_id == dataset.dataset_id
    ]
    if not logs:
        st.info("Nenhuma decisao do Data Readiness Gate registrada.")
        return
    exibir_registros_readonly(_data_readiness_gate_logs_table(logs))


def exibir_metricas_readiness_gate(service: DashboardService) -> None:
    """Exibe metricas agregadas do Data Readiness Gate."""
    metrics = service.get_data_readiness_gate_metrics()
    st.caption("Metricas do Data Readiness Gate")
    colunas = st.columns(6)
    colunas[0].metric("Avaliacoes", metrics.total_evaluations)
    colunas[1].metric("Allowed", metrics.total_allowed)
    colunas[2].metric("Blocked", metrics.total_blocked)
    colunas[3].metric("Replay", metrics.total_replay_evaluations)
    colunas[4].metric("Research", metrics.total_research_evaluations)
    colunas[5].metric(
        "Ultima avaliacao",
        valor_ou_indisponivel(metrics.last_evaluation_at),
    )
    colunas = st.columns(2)
    colunas[0].metric(
        "Ultimo dataset bloqueado",
        valor_ou_indisponivel(metrics.last_blocked_dataset_id),
    )
    colunas[1].metric(
        "Ultimo motivo de bloqueio",
        valor_ou_indisponivel(metrics.last_block_reason),
    )


def exibir_qualidade_dataset_historico(report: object) -> None:
    """Exibe relatorio pronto de qualidade do dataset historico."""
    st.caption("Qualidade do dataset historico")
    colunas = st.columns(4)
    colunas[0].metric("Total de candles", report.total_candles)
    colunas[1].metric("Inicio", valor_ou_indisponivel(report.start_datetime))
    colunas[2].metric("Fim", valor_ou_indisponivel(report.end_datetime))
    colunas[3].metric("Dataset", report.dataset_id)
    colunas = st.columns(4)
    colunas[0].metric("OHLC invalido", report.invalid_ohlc_candles)
    colunas[1].metric("Volume invalido", report.invalid_volume_candles)
    colunas[2].metric("Gaps temporais", report.temporal_gaps)
    colunas[3].metric("Duplicidades", report.duplicate_timestamps)


def exibir_historico_qualidade_dataset_historico(
    service: DashboardService,
) -> None:
    """Exibe historico de validacoes do dataset selecionado."""
    st.caption("Historico de qualidade do dataset")
    dataset = service.get_selected_historical_dataset()
    if dataset is None:
        st.info("Selecione um dataset historico para ver o historico.")
        return
    history = service.list_historical_dataset_quality_validations(
        dataset.dataset_id
    )
    if not history:
        st.info("Nenhuma validacao de qualidade registrada para este dataset.")
        return
    exibir_registros_readonly(_historical_dataset_quality_history_table(history))


def exibir_dataset_historico_ativo(dataset: object | None) -> None:
    """Exibe o dataset historico selecionado."""
    if dataset is None:
        st.info("Nenhum dataset historico ativo.")
        return
    colunas = st.columns(4)
    colunas[0].metric("Dataset ativo", dataset.dataset_id)
    colunas[1].metric("Ativo", dataset.ativo)
    colunas[2].metric("Timeframe", dataset.timeframe)
    colunas[3].metric("Provider", dataset.provider)
    st.caption(
        f"{dataset.start_date} a {dataset.end_date} | "
        f"{dataset.estimated_candles} candles estimados"
    )


def exibir_controles_auto_replay(
    service: DashboardService,
    replay_data: object,
) -> object:
    """Exibe controles do replay automatico."""
    disabled = replay_control_disabled(replay_data)
    current_speed = getattr(replay_data, "replay_speed_seconds", 1.0)
    speed = st.number_input(
        "Velocidade do Auto Replay (segundos)",
        min_value=0.0,
        value=float(current_speed),
        step=0.5,
        key="replay_auto_speed_seconds",
    )
    colunas = st.columns(2)
    if colunas[0].button(
        "Ativar Auto Replay",
        disabled=disabled["auto"],
        key="enable_replay_auto_run",
    ):
        replay_data = service.enable_replay_auto_run(speed)
    if colunas[1].button("Desativar Auto Replay", key="disable_replay_auto_run"):
        replay_data = service.disable_replay_auto_run()
    return replay_data


def exibir_estado_replay(replay_data: object) -> None:
    """Exibe os indicadores do replay."""
    total = replay_data.total_candles
    processed = max(replay_data.current_index + 1, 0)
    progress = 0.0 if total == 0 else processed / total
    colunas = st.columns(6)
    colunas[0].metric("Indice atual", replay_data.current_index)
    colunas[1].metric("Total de candles", replay_data.total_candles)
    colunas[2].metric("Posicao", processed)
    colunas[3].metric("Progresso", f"{progress:.0%}")
    colunas[4].metric("Rodando", _sim_nao(replay_data.is_running))
    colunas[5].metric("Replay Status", _replay_status(replay_data))
    st.progress(progress)


def exibir_candle_replay(candle: object) -> None:
    """Exibe o candle atual do replay."""
    st.subheader("Candle atual")
    if candle is None:
        st.info("Nenhum candle carregado.")
        return
    colunas = st.columns(6)
    colunas[0].metric("Data", candle.data)
    colunas[1].metric("Abertura", f"{candle.abertura:.2f}")
    colunas[2].metric("Maxima", f"{candle.maxima:.2f}")
    colunas[3].metric("Minima", f"{candle.minima:.2f}")
    colunas[4].metric("Fechamento", f"{candle.fechamento:.2f}")
    colunas[5].metric("Volume", candle.volume)


def exibir_features_replay(feature_snapshot: object) -> None:
    """Exibe indicadores temporais calculados no replay."""
    st.subheader("Indicadores Temporais")
    if feature_snapshot is None:
        st.info("Avance um candle para calcular os indicadores temporais.")
        return
    colunas = st.columns(6)
    colunas[0].metric("Direction", feature_snapshot.direction)
    colunas[1].metric("Momentum", f"{feature_snapshot.momentum:.2f}")
    colunas[2].metric(
        "Average range",
        f"{feature_snapshot.average_range:.2f}",
    )
    colunas[3].metric(
        "Trend strength",
        f"{feature_snapshot.trend_strength:.2f}",
    )
    colunas[4].metric("Volatility", feature_snapshot.volatility_level)
    colunas[5].metric("Candles", feature_snapshot.candles_count)


def exibir_regime_replay(regime_analysis: object) -> None:
    """Exibe a analise de regime calculada no replay."""
    st.subheader("Regime do Replay")
    if regime_analysis is None:
        st.info("Avance um candle para calcular o regime do mercado.")
        return
    colunas = st.columns(3)
    colunas[0].metric("Regime", regime_analysis.regime.value)
    colunas[1].metric("Confidence", f"{regime_analysis.confidence:.0%}")
    colunas[2].write(regime_analysis.description)


def exibir_pesquisa_replay(research_data: object) -> None:
    """Exibe a pesquisa quantitativa calculada no replay."""
    st.subheader("Pesquisa Quantitativa do Replay")
    if research_data is None:
        st.info("Avance um candle para calcular a pesquisa quantitativa.")
        return
    colunas = st.columns(4)
    colunas[0].metric("Cenarios parecidos", research_data.similar_scenarios)
    colunas[1].metric("Confidence", f"{research_data.confidence:.2f}")
    colunas[2].metric(
        "Historical score",
        f"{research_data.historical_score:.2f}",
    )
    colunas[3].metric("History strength", research_data.history_strength)
    st.info(research_data.summary)


def exibir_sinal_estrategia_replay(strategy_signal: object) -> None:
    """Exibe o sinal de estrategia calculado no replay."""
    st.subheader("Sinal de Estrategia")
    if strategy_signal is None:
        st.info("Avance um candle para gerar o sinal de estrategia.")
        return
    colunas = st.columns(3)
    colunas[0].metric("Decision", strategy_signal.decision)
    colunas[1].metric("Score", strategy_signal.score)
    colunas[2].metric("Confidence", f"{strategy_signal.confidence:.0%}")
    st.write(", ".join(strategy_signal.reasons))


def exibir_decision_context_replay(decision_context: object) -> None:
    """Exibe o preview do DecisionPipeline no replay."""
    st.subheader("Decision Pipeline Preview")
    if decision_context is None:
        st.info("Avance um candle para gerar o preview de decisao.")
        return
    colunas = st.columns(4)
    colunas[0].metric("Final decision", decision_context.final_decision)
    colunas[1].metric(
        "Final confidence",
        f"{decision_context.final_confidence:.0%}",
    )
    colunas[2].metric("Approved", _sim_nao(decision_context.approved))
    colunas[3].write(decision_context.risk_decision.reason)


def exibir_order_preview_replay(order_preview: object) -> None:
    """Exibe a previa simulada de ordem do replay."""
    st.subheader("Previa de Ordem Simulada")
    if order_preview is None:
        st.info("Nenhuma previa de ordem simulada gerada.")
        return
    st.warning("Prévia simulada. Nenhuma ordem real foi enviada.")
    colunas = st.columns(5)
    colunas[0].metric("Side", order_preview.side)
    colunas[1].metric("Quantity", order_preview.quantity)
    colunas[2].metric("Entry", f"{order_preview.entry_price:.2f}")
    colunas[3].metric("Stop", f"{order_preview.stop:.2f}")
    colunas[4].metric("Target", f"{order_preview.target:.2f}")


def exibir_paper_position_replay(paper_position: object) -> None:
    """Exibe a posicao paper simulada do replay."""
    st.subheader("Posicao Paper Simulada")
    if paper_position is None:
        st.info("Nenhuma posicao paper simulada aberta.")
        return
    st.warning("Simulacao em memoria. Nenhuma ordem real foi enviada.")
    colunas = st.columns(4)
    colunas[0].metric("Side", paper_position.side)
    colunas[1].metric("Quantity", paper_position.quantity)
    colunas[2].metric("Status", paper_position.status)
    colunas[3].metric(
        "Resultado",
        f"{paper_position.result_points:.2f}",
    )
    colunas = st.columns(5)
    colunas[0].metric("Entrada", f"{paper_position.entry_price:.2f}")
    colunas[1].metric("Stop", f"{paper_position.stop:.2f}")
    colunas[2].metric("Target", f"{paper_position.target:.2f}")
    colunas[3].metric("Saida", _format_optional_price(paper_position))
    colunas[4].metric("Fechamento", paper_position.close_reason or "-")


def exibir_paper_trades_history_replay(replay_data: object) -> None:
    """Exibe historico de operacoes paper fechadas."""
    st.subheader("Historico de Operacoes Paper")
    colunas = st.columns(4)
    colunas[0].metric(
        "Operacoes",
        getattr(replay_data, "total_paper_trades", 0),
    )
    colunas[1].metric("Vitorias", getattr(replay_data, "wins", 0))
    colunas[2].metric("Derrotas", getattr(replay_data, "losses", 0))
    colunas[3].metric(
        "Resultado total",
        f"{getattr(replay_data, 'total_paper_result_points', 0.0):.2f}",
    )
    history = getattr(replay_data, "paper_trades_history", [])
    if not history:
        st.info("Nenhuma operacao paper fechada.")
        return
    exibir_registros_readonly(_paper_trades_table(history))


def exibir_paper_equity_curve_replay(replay_data: object) -> None:
    """Exibe a curva de patrimonio paper em pontos."""
    st.subheader("Curva de Patrimonio Paper")
    curve = getattr(replay_data, "paper_equity_curve", [0.0])
    colunas = st.columns(3)
    colunas[0].metric(
        "Resultado atual",
        f"{getattr(replay_data, 'current_equity_points', 0.0):.2f}",
    )
    colunas[1].metric(
        "Maior valor",
        f"{getattr(replay_data, 'max_equity_points', 0.0):.2f}",
    )
    colunas[2].metric(
        "Menor valor",
        f"{getattr(replay_data, 'min_equity_points', 0.0):.2f}",
    )
    st.line_chart({"equity_points": curve})


def exibir_paper_metrics_replay(paper_metrics: object) -> None:
    """Exibe metricas basicas das operacoes paper."""
    st.subheader("Metricas Paper")
    if paper_metrics is None:
        st.info("Nenhuma metrica paper disponivel.")
        return
    colunas = st.columns(4)
    colunas[0].metric("Taxa de acerto", f"{paper_metrics.win_rate:.0%}")
    colunas[1].metric(
        "Lucro bruto",
        f"{paper_metrics.gross_profit_points:.2f}",
    )
    colunas[2].metric(
        "Prejuizo bruto",
        f"{paper_metrics.gross_loss_points:.2f}",
    )
    colunas[3].metric(
        "Lucro liquido",
        f"{paper_metrics.net_profit_points:.2f}",
    )
    colunas = st.columns(3)
    colunas[0].metric(
        "Ganho medio",
        f"{paper_metrics.average_win_points:.2f}",
    )
    colunas[1].metric(
        "Perda media",
        f"{paper_metrics.average_loss_points:.2f}",
    )
    colunas[2].metric(
        "Profit factor",
        _format_profit_factor(paper_metrics.profit_factor),
    )
    colunas = st.columns(3)
    colunas[0].metric(
        "Drawdown atual",
        f"{paper_metrics.current_drawdown_points:.2f}",
    )
    colunas[1].metric(
        "Drawdown maximo",
        f"{paper_metrics.max_drawdown_points:.2f}",
    )
    colunas[2].metric(
        "Pico da curva",
        f"{paper_metrics.peak_equity_points:.2f}",
    )


def exibir_eventos_replay(replay_data: object) -> None:
    """Exibe eventos registrados durante o replay."""
    st.subheader("Eventos do Replay")
    event_count = getattr(replay_data, "event_count", 0)
    recent_events = getattr(replay_data, "recent_events", [])
    st.metric("Eventos registrados", event_count)
    if not recent_events:
        st.info("Nenhum evento de replay registrado.")
        return
    exibir_registros_readonly(_events_table(recent_events))


def _format_optional_price(paper_position: object) -> str:
    exit_price = getattr(paper_position, "exit_price", None)
    if exit_price is None:
        return "-"
    return f"{exit_price:.2f}"


def _format_profit_factor(value: float) -> str:
    if value == float("inf"):
        return "Infinito"
    return f"{value:.2f}"


def _dict_table(values: dict[str, object]) -> list[dict[str, object]]:
    return [
        {"campo": key, "valor": value}
        for key, value in values.items()
    ]


def _alpha001_dashboard_benchmark_table(benchmark: object) -> list[dict[str, object]]:
    return [
        {"metrica": "best_overall", "experimento": benchmark.best_overall},
        {
            "metrica": "best_total_trades",
            "experimento": benchmark.best_total_trades,
        },
        {"metrica": "best_net_profit", "experimento": benchmark.best_net_profit},
        {
            "metrica": "best_max_drawdown",
            "experimento": benchmark.best_max_drawdown,
        },
        {
            "metrica": "best_profit_factor",
            "experimento": benchmark.best_profit_factor,
        },
        {"metrica": "best_win_rate", "experimento": benchmark.best_win_rate},
        {"metrica": "best_expectancy", "experimento": benchmark.best_expectancy},
        {"metrica": "ranking", "experimento": ", ".join(benchmark.ranking)},
    ]


def _research_experiments_table(experiments: list[object]) -> list[dict]:
    rows = []
    for experiment in experiments:
        rows.append(
            {
                "nome": experiment.experiment_name,
                "estrategia": experiment.strategy_name,
                "stop": experiment.stop_points,
                "target": experiment.target_points,
                "trades": experiment.total_trades,
                "wins": experiment.wins,
                "losses": experiment.losses,
                "net_points": experiment.net_profit_points,
                "win_rate": experiment.win_rate,
                "profit_factor": _format_profit_factor(
                    experiment.profit_factor
                ),
                "max_drawdown": experiment.max_drawdown_points,
            }
        )
    return rows


def _research_benchmarks_table(benchmarks: list[object]) -> list[dict]:
    rows = []
    for benchmark in benchmarks:
        rows.append(
            {
                "estrategia": benchmark.strategy_name,
                "trades": benchmark.total_trades,
                "wins": benchmark.wins,
                "losses": benchmark.losses,
                "net_points": benchmark.net_profit_points,
                "win_rate": benchmark.win_rate,
                "profit_factor": _format_profit_factor(
                    benchmark.profit_factor
                ),
                "max_drawdown": benchmark.max_drawdown_points,
            }
        )
    return rows


def _parameter_grid_table(
    grid_results: list[object],
    best_grid: object,
) -> list[dict]:
    rows = []
    for result in grid_results:
        rows.append(
            {
                "melhor": _is_best_grid(result, best_grid),
                "stop": result.stop_points,
                "target": result.target_points,
                "estrategia": result.strategy_name,
                "trades": result.total_trades,
                "wins": result.wins,
                "losses": result.losses,
                "net_points": result.net_profit_points,
                "win_rate": result.win_rate,
                "profit_factor": _format_profit_factor(result.profit_factor),
                "max_drawdown": result.max_drawdown_points,
            }
        )
    return rows


def _alpha001_ranking_table(ranking: list[object]) -> list[dict]:
    rows = []
    for index, result in enumerate(ranking, start=1):
        rows.append(
            {
                "rank": index,
                "opening_range": result.opening_range_minutes,
                "minimum_range": result.minimum_range_size,
                "minimum_volume": result.minimum_volume,
                "trades": result.total_trades,
                "profit_factor": _format_profit_factor(result.profit_factor),
                "max_drawdown": result.max_drawdown_points,
                "net_points": result.net_profit_points,
                "validation_status": result.validation_status,
            }
        )
    return rows


def _is_best_grid(result: object, best_grid: object) -> str:
    if best_grid is None:
        return ""
    if (
        result.stop_points == best_grid.stop_points
        and result.target_points == best_grid.target_points
        and result.strategy_name == best_grid.strategy_name
    ):
        return "SIM"
    return ""


def _benchmark_validations_table(validations: list[object]) -> list[dict]:
    rows = []
    for validation in validations:
        rows.append(
            {
                "sample_size": validation.sample_size,
                "relevante": _sim_nao(validation.is_statistically_relevant),
                "confidence_level": validation.confidence_level,
                "warnings": ", ".join(validation.warnings),
                "summary": validation.summary,
            }
        )
    return rows


def _historical_datasets_table(datasets: list[object]) -> list[dict]:
    """Monta tabela visual de metadados historicos."""
    rows = []
    for dataset in datasets:
        rows.append(
            {
                "dataset_id": dataset.dataset_id,
                "ativo": dataset.ativo,
                "timeframe": dataset.timeframe,
                "inicio": dataset.start_date,
                "fim": dataset.end_date,
                "candles_estimados": dataset.estimated_candles,
                "provider": dataset.provider,
            }
        )
    return rows


def _events_table(events: list[object]) -> list[dict[str, object]]:
    """Monta tabela visual dos eventos reais registrados."""
    return [
        {
            "timestamp": valor_ou_indisponivel(
                getattr(event, "timestamp", None)
            ),
            "evento": getattr(event, "event_name", "N/D"),
            "payload": _event_payload_summary(getattr(event, "payload", None)),
        }
        for event in events
    ]


def _event_payload_summary(payload: object) -> str:
    if isinstance(payload, dict):
        return ", ".join(
            f"{key}={_payload_value(value)}"
            for key, value in payload.items()
        )
    return _payload_value(payload)


def _payload_value(value: object) -> str:
    if value is None:
        return "N/D"
    text = str(value)
    if len(text) > 80:
        return f"{text[:77]}..."
    return text


def _historical_dataset_quality_history_table(
    history: list[object],
) -> list[dict]:
    """Monta tabela visual do historico de qualidade."""
    rows = []
    for record in history:
        rows.append(
            {
                "validacao": record.validated_at,
                "status": record.quality_status,
                "total_candles": record.total_candles,
                "ohlc_invalidos": record.invalid_ohlc_candles,
                "volumes_invalidos": record.invalid_volume_candles,
                "gaps": record.temporal_gaps,
                "timestamps_duplicados": record.duplicate_timestamps,
                "mensagens": "; ".join(record.messages),
            }
        )
    return rows


def _historical_dataset_readiness_reasons_table(
    reasons: list[str],
) -> list[dict]:
    """Monta tabela visual dos motivos de prontidao."""
    return [{"motivo": reason} for reason in reasons]


def _data_readiness_gate_logs_table(logs: list[object]) -> list[dict]:
    """Monta tabela visual da auditoria do Data Readiness Gate."""
    rows = []
    for log in logs:
        rows.append(
            {
                "dataset_id": log.dataset_id,
                "avaliacao": log.evaluated_at,
                "acao": log.requested_action,
                "readiness": log.readiness_status,
                "decisao": log.decision,
                "motivos": "; ".join(log.reasons),
            }
        )
    return rows


def _historical_provider_metrics_table(metrics: object) -> list[dict]:
    """Monta tabela visual das metricas agregadas por provider."""
    rows = []
    for provider, metric in _historical_provider_metric_items(metrics):
        rows.append(
            {
                "provider": provider,
                "datasets_catalogados": _metric_value(
                    metric,
                    "total_datasets",
                ),
                "datasets_validados": _metric_value(
                    metric,
                    "validated_datasets",
                    "total_validated",
                ),
                "datasets_aprovados": _metric_value(
                    metric,
                    "approved_datasets",
                    "total_approved",
                ),
                "datasets_reprovados": _metric_value(
                    metric,
                    "rejected_datasets",
                    "total_rejected",
                ),
                "datasets_sem_validacao": _metric_value(
                    metric,
                    "not_validated_datasets",
                    "total_unvalidated",
                ),
                "avaliacoes_gate": _metric_value(
                    metric,
                    "gate_evaluations",
                    "total_gate_evaluations",
                ),
                "allowed": _metric_value(metric, "allowed", "total_allowed"),
                "blocked": _metric_value(metric, "blocked", "total_blocked"),
                "ultima_validacao": valor_ou_indisponivel(
                    _metric_value(metric, "last_validation_at")
                ),
                "ultima_avaliacao_gate": valor_ou_indisponivel(
                    _metric_value(metric, "last_gate_evaluation_at")
                ),
            }
        )
    return rows


def _historical_provider_metric_items(metrics: object) -> list[tuple[str, object]]:
    if isinstance(metrics, dict):
        return [(str(provider), metric) for provider, metric in metrics.items()]
    return [
        (str(getattr(metric, "provider", "")), metric)
        for metric in list(metrics or [])
    ]


def _metric_value(metric: object, *names: str) -> object:
    for name in names:
        if isinstance(metric, dict) and name in metric:
            return metric[name]
        if hasattr(metric, name):
            return getattr(metric, name)
    return 0


def _paper_trades_table(history: list[object]) -> list[dict]:
    rows = []
    for index, trade in enumerate(history, 1):
        rows.append(
            {
                "operacao": index,
                "side": trade.side,
                "quantity": trade.quantity,
                "entrada": trade.entry_price,
                "stop": trade.stop,
                "target": trade.target,
                "saida": trade.exit_price,
                "resultado": trade.result_points,
                "motivo": trade.close_reason,
            }
        )
    return rows


def _alpha001_paper_trades_table(history: list[object]) -> list[dict]:
    rows = []
    for index, trade in enumerate(history, 1):
        rows.append(
            {
                "operacao": index,
                "side": trade.side,
                "quantity": trade.quantity,
                "entrada": trade.entry_price,
                "saida": trade.exit_price,
                "resultado": trade.result_points,
                "motivo": trade.close_reason,
            }
        )
    return rows


def exibir_mini_chart_replay(replay_data: object) -> None:
    """Exibe tabela e grafico simples de candles do replay."""
    st.subheader("Mini Chart")
    candles_loaded = getattr(replay_data, "candles_loaded", [])
    candles_processed = getattr(replay_data, "candles_processed", [])
    if not candles_loaded:
        st.info("Carregue o dataset selecionado para visualizar o mini chart.")
        return

    st.caption("Candles carregados")
    exibir_registros_readonly(
        _candles_table(candles_loaded, len(candles_processed)),
        max_items=8,
    )
    st.caption("Fechamentos processados")
    if candles_processed:
        st.line_chart(_close_values(candles_processed))
    else:
        st.info("Avance um candle para iniciar o grafico de fechamento.")


def _candles_table(candles: list[object], processed_count: int) -> list[dict]:
    rows = []
    for index, candle in enumerate(candles):
        rows.append(
            {
                "status": _candle_status(index, processed_count),
                "data": candle.data,
                "abertura": candle.abertura,
                "maxima": candle.maxima,
                "minima": candle.minima,
                "fechamento": candle.fechamento,
                "volume": candle.volume,
            }
        )
    return rows


def _candle_status(index: int, processed_count: int) -> str:
    if index < processed_count:
        return "processado"
    return "pendente"


def _close_values(candles: list[object]) -> dict[str, list[float]]:
    return {"fechamento": [candle.fechamento for candle in candles]}


def executar_auto_run(service: DashboardService, replay_data: object) -> None:
    """Avanca automaticamente um candle por ciclo de renderizacao."""
    if not getattr(replay_data, "auto_run_enabled", False):
        return
    if getattr(replay_data, "is_finished", False):
        service.disable_replay_auto_run()
        return
    time.sleep(float(getattr(replay_data, "replay_speed_seconds", 1.0)))
    service.next_replay_candle()
    st.rerun()


def _replay_status(replay_data: object) -> str:
    status = getattr(replay_data, "status", None)
    if status is None:
        return "EMPTY"
    return getattr(status, "value", str(status))


def _sim_nao(valor: bool) -> str:
    return "Sim" if valor else "Nao"


def _autorizado(valor: bool) -> str:
    return "AUTORIZADA" if valor else "NAO AUTORIZADA - PROIBIDA"


def _integrado(valor: bool) -> str:
    return "INTEGRADO" if valor else "NÃO INTEGRADO"


def exibir_sistema(data: object) -> None:
    """Exibe a aba de sistema."""
    status = data.system_status
    colunas = st.columns(4)
    colunas[0].metric("Status", status.status)
    colunas[1].metric("Versão", status.version)
    colunas[2].metric("Ativo operacional", status.active_symbol)
    colunas[3].metric("Modo atual", "Simulação")
    exibir_dataset_ativo(data)
    exibir_session_runtime(data)
    exibir_sessao_operacional(data)
    exibir_configuracoes(data)


def exibir_session_runtime(data: object) -> None:
    """Exibe runtime institucional da sessao visual."""
    st.subheader("Runtime da Sessao")
    dataset = getattr(data, "active_dataset", None)
    replay_data = getattr(data, "replay_data", None)
    experiments = getattr(data, "research_lab_experiments", [])
    colunas = st.columns(4)
    colunas[0].metric("Dataset", getattr(dataset, "dataset_id", "N/D"))
    colunas[1].metric("Replay", _replay_status(replay_data))
    colunas[2].metric("Research", f"{len(experiments)} experimento(s)")
    colunas[3].metric(
        "Eventos",
        getattr(replay_data, "event_count", 0) if replay_data else 0,
    )
    colunas = st.columns(4)
    colunas[0].metric(
        "Candles Replay",
        getattr(replay_data, "total_candles", 0) if replay_data else 0,
    )
    colunas[1].metric(
        "Posicao Replay",
        getattr(replay_data, "current_index", -1) if replay_data else -1,
    )
    colunas[2].metric("Tempo de execucao", "Sessao Streamlit")
    colunas[3].metric("Memoria", "N/D")
    st.warning("Operacao real: NAO AUTORIZADA.")


def exibir_configuracoes(data: object) -> None:
    """Exibe configuracoes atuais do sistema."""
    configuration = getattr(data, "configuration_data", None)
    st.subheader("Configurações")
    if configuration is None:
        st.info("Configurações ainda não disponíveis.")
        return

    exibir_configuracoes_readonly(configuration)
    exibir_formulario_configuracoes(configuration)
    exibir_presets_configuracao()


def exibir_configuracoes_readonly(configuration: object) -> None:
    """Exibe campos informativos da configuracao."""
    colunas = st.columns(2)
    colunas[0].metric("Ativo operacional", configuration.symbol)
    colunas[1].metric("Versão", configuration.version)


def exibir_formulario_configuracoes(configuration: object) -> None:
    """Exibe formulario de edicao de configuracoes basicas."""
    with st.form("configuration_form"):
        values = campos_configuracao(configuration)
        submitted = st.form_submit_button("Salvar Configurações")

    if not submitted:
        return

    try:
        get_dashboard_service().update_configuration(**values)
        st.success("Configurações salvas com sucesso.")
    except ValueError as error:
        st.error(f"Erro ao salvar configurações: {error}")


def exibir_presets_configuracao() -> None:
    """Exibe controles de presets de configuracao."""
    st.caption("Presets de configuração")
    service = get_dashboard_service()
    preset_name = st.text_input("Nome do preset", key="preset_name")
    colunas = st.columns(3)

    if colunas[0].button("Salvar Preset"):
        salvar_preset(service, preset_name)

    selected = selecionar_preset(service)
    if colunas[1].button("Carregar Preset"):
        carregar_preset(service, selected)
    if colunas[2].button("Excluir Preset"):
        excluir_preset(service, selected)


def selecionar_preset(service: DashboardService) -> str:
    """Renderiza seletor de presets."""
    presets = service.list_configuration_presets()
    if not presets:
        st.info("Nenhum preset salvo nesta sessão.")
        return ""
    return st.selectbox("Presets existentes", presets)


def salvar_preset(service: DashboardService, preset_name: str) -> None:
    """Salva preset pela fachada do dashboard."""
    try:
        service.save_configuration_preset(preset_name)
        st.success("Preset salvo com sucesso.")
    except ValueError as error:
        st.error(f"Erro ao salvar preset: {error}")


def carregar_preset(service: DashboardService, preset_name: str) -> None:
    """Carrega preset pela fachada do dashboard."""
    try:
        service.load_configuration_preset(preset_name)
        st.success("Preset carregado com sucesso.")
    except ValueError as error:
        st.error(f"Erro ao carregar preset: {error}")


def excluir_preset(service: DashboardService, preset_name: str) -> None:
    """Exclui preset pela fachada do dashboard."""
    try:
        service.delete_configuration_preset(preset_name)
        st.success("Preset excluído com sucesso.")
    except ValueError as error:
        st.error(f"Erro ao excluir preset: {error}")


def campos_configuracao(configuration: object) -> dict[str, object]:
    """Renderiza inputs e retorna valores informados."""
    colunas = st.columns(3)
    values = {
        "initial_capital": colunas[0].number_input(
            "Capital inicial",
            value=float(configuration.initial_capital),
        ),
        "contracts": colunas[1].number_input(
            "Contratos",
            value=int(configuration.contracts),
            step=1,
        ),
        "stop_points": colunas[2].number_input(
            "Stop em pontos",
            value=float(configuration.stop_points),
        ),
    }
    values.update(campos_configuracao_risco(configuration))
    return values


def campos_configuracao_risco(configuration: object) -> dict[str, object]:
    """Renderiza inputs de risco e alvo."""
    colunas = st.columns(3)
    values = {
        "target_points": colunas[0].number_input(
            "Alvo em pontos",
            value=float(configuration.target_points),
        ),
        "max_daily_loss": colunas[1].number_input(
            "Perda máxima diária",
            value=float(configuration.max_daily_loss),
        ),
        "max_daily_gain": colunas[2].number_input(
            "Ganho máximo diário",
            value=float(configuration.max_daily_gain),
        ),
    }
    values.update(campos_configuracao_sinal(configuration))
    return values


def campos_configuracao_sinal(configuration: object) -> dict[str, object]:
    """Renderiza inputs de sinal e modo."""
    colunas = st.columns(3)
    values = {
        "minimum_score": colunas[0].number_input(
            "Score mínimo",
            value=int(configuration.minimum_score),
            step=1,
        ),
        "minimum_confidence": colunas[1].number_input(
            "Confiança mínima",
            value=float(configuration.minimum_confidence),
        ),
        "simulation_mode": colunas[2].checkbox(
            "Modo simulação",
            value=bool(configuration.simulation_mode),
        ),
    }
    st.markdown("#### REGRAS DE EXECUCAO")
    values["forex_session_filter_enabled"] = st.checkbox(
        "Operar somente durante as sessoes oficiais do Forex",
        value=bool(getattr(configuration, "forex_session_filter_enabled", False)),
    )
    return values


def exibir_sessao_operacional(data: object) -> None:
    """Exibe o resumo da sessao operacional."""
    session = getattr(data, "session_snapshot", None)
    st.subheader("Sessão Operacional")
    if session is None:
        st.info("Sessão operacional ainda não disponível.")
        return

    colunas = st.columns(4)
    colunas[0].metric("Data da sessão", session.session_date)
    colunas[1].metric("Status do sistema", session.system_status)
    colunas[2].metric("Operações hoje", session.operations_today)
    colunas[3].metric("Vitórias hoje", session.wins_today)

    colunas = st.columns(4)
    colunas[0].metric("Derrotas hoje", session.losses_today)
    colunas[1].metric("Lucro bruto", f"{session.gross_profit:.2f}")
    colunas[2].metric("Prejuízo bruto", f"{session.gross_loss:.2f}")
    colunas[3].metric("Resultado líquido", f"{session.net_profit:.2f}")

    colunas = st.columns(3)
    colunas[0].metric("Posição atual", valor_ou_indisponivel(session.current_position))
    colunas[1].metric("Último sinal", valor_ou_indisponivel(session.last_signal))
    colunas[2].metric("Último evento", valor_ou_indisponivel(session.last_event))


def exibir_research_workbench(service: DashboardService, data: object) -> None:
    """Exibe a tela unica do MVP de pesquisa quantitativa."""
    data = exibir_menu_lateral_workbench(service, data)
    replay_data = getattr(data, "replay_data", None)

    st.subheader("Research Workbench MVP")
    st.caption("Pesquisa quantitativa em modo paper. Operacao real: NAO AUTORIZADA.")
    exibir_status_bar(data)

    grafico, replay = st.columns([2, 1])
    with grafico:
        exibir_regiao_grafico_workbench(replay_data)
    with replay:
        replay_data = exibir_regiao_replay_workbench(service, replay_data)

    data = service.get_dashboard_data()
    replay_data = getattr(data, "replay_data", replay_data)
    exibir_market_reading_pipeline(replay_data, data)

    alpha, estatisticas = st.columns([1, 1])
    with alpha:
        exibir_regiao_alpha_workbench(replay_data, data)
    with estatisticas:
        exibir_regiao_estatisticas_workbench(replay_data, data)

    executar_auto_run(service, replay_data)


def exibir_live_research_read_only(data: object) -> None:
    """Exibe Live Research profissional e somente leitura."""
    live_status = getattr(data, "live_research_status", None)
    session_summary = getattr(data, "live_session_summary", None)
    signal_quality = list(getattr(data, "live_signal_quality", []) or [])
    live_history = list(getattr(data, "live_history", []) or [])
    safety_status = getattr(data, "safety_status", None)
    st.subheader("Live Research READ ONLY")
    st.caption("Pipeline live observacional. Ordens reais: NAO AUTORIZADAS.")
    exibir_live_status_section(live_status, live_history, safety_status)
    exibir_live_session_summary_section(session_summary)
    exibir_live_signal_quality_section(signal_quality)
    exibir_live_history_section(live_history)
    exibir_live_system_health_section(live_status, signal_quality, safety_status)
    if not getattr(live_status, "has_data", False):
        st.info("Sem dados live read-only nesta sessao.")


def exibir_live_status_section(
    live_status: object,
    live_history: list[object],
    safety_status: object,
) -> None:
    """Exibe status live read-only."""
    with st.container(border=True):
        st.subheader("LIVE STATUS")
        st.caption(_live_badge("READ ONLY"))
        colunas = st.columns(5)
        colunas[0].metric(
            "Conectado",
            "SIM" if getattr(live_status, "has_data", False) else "SEM DADOS",
        )
        colunas[1].metric("Simbolo", getattr(live_status, "symbol", "N/D"))
        colunas[2].metric("Timeframe", getattr(live_status, "timeframe", "N/D"))
        colunas[3].metric(
            "Ultimo candle",
            getattr(
                live_history[-1]
                if live_history
                else None,
                "timestamp",
                "N/D",
            ),
        )
        colunas[4].metric(
            "Status",
            getattr(safety_status, "status", "READ ONLY"),
        )


def exibir_live_session_summary_section(summary: object) -> None:
    """Exibe resumo estatistico live."""
    with st.container(border=True):
        st.subheader("SESSION SUMMARY")
        colunas = st.columns(5)
        colunas[0].metric("BUY", getattr(summary, "buy_count", 0))
        colunas[1].metric("SELL", getattr(summary, "sell_count", 0))
        colunas[2].metric("WAIT", getattr(summary, "wait_count", 0))
        colunas[3].metric(
            "Confidence",
            _format_percent(getattr(summary, "average_confidence", 0.0)),
        )
        colunas[4].metric("Snapshots", getattr(summary, "total_snapshots", 0))

        colunas = st.columns(5)
        colunas[0].metric(
            "Maior confidence",
            _format_percent(getattr(summary, "highest_confidence", 0.0)),
        )
        colunas[1].metric(
            "Menor confidence",
            _format_percent(getattr(summary, "lowest_confidence", 0.0)),
        )
        colunas[2].metric(
            "Ultima decisao",
            _decision_badge(getattr(summary, "last_decision", "N/D")),
        )
        colunas[3].metric("Ultimo snapshot", getattr(summary, "last_timestamp", "N/D"))
        colunas[4].metric("Modo", "READ ONLY")


def exibir_live_signal_quality_section(signal_quality: list[object]) -> None:
    """Exibe qualidade dos sinais por estrategia."""
    with st.container(border=True):
        st.subheader("SIGNAL QUALITY")
        if not signal_quality:
            st.info("Nenhum sinal live registrado para avaliar qualidade.")
            return
        st.dataframe(
            [
                {
                    "strategy": row.strategy_name,
                    "signals": row.signal_count,
                    "BUY": row.buy_count,
                    "SELL": row.sell_count,
                    "WAIT": row.wait_count,
                    "confidence_mean": _format_percent(row.average_confidence),
                    "last_decision": _decision_badge(row.last_decision),
                }
                for row in signal_quality
            ],
            hide_index=True,
            width="stretch",
        )


def exibir_live_history_section(history: list[object]) -> None:
    """Exibe historico live da sessao."""
    with st.container(border=True):
        st.subheader("LIVE HISTORY")
        if history:
            st.caption("Ultimos snapshots")
            st.dataframe(
                [
                    {
                        "timestamp": _format_timestamp(row.timestamp),
                        "symbol": row.symbol,
                        "timeframe": row.timeframe,
                        "decision": _decision_badge(row.decision),
                        "confidence": _format_percent(row.confidence),
                        "signals": row.strategy_signals,
                        "contexts": row.decision_contexts,
                    }
                    for row in reversed(history)
                ],
                hide_index=True,
                width="stretch",
            )
        if not history:
            st.info("Sem historico live nesta sessao.")


def exibir_live_system_health_section(
    live_status: object,
    signal_quality: list[object],
    safety_status: object,
) -> None:
    """Exibe saude dos componentes do pipeline live."""
    with st.container(border=True):
        st.subheader("SYSTEM HEALTH")
        colunas = st.columns(4)
        colunas[0].metric(
            "Pipeline",
            "ACTIVE" if getattr(live_status, "has_data", False) else "IDLE",
        )
        colunas[1].metric(
            "Feature Engine",
            "READY" if getattr(live_status, "candles_ingested", 0) else "WAITING",
        )
        colunas[2].metric(
            "Research",
            "READY" if signal_quality else "WAITING",
        )
        colunas[3].metric(
            "Decision Pipeline",
            "READ ONLY"
            if getattr(safety_status, "read_only", True)
            else "CHECK REQUIRED",
        )


def _format_percent(value: object) -> str:
    try:
        return f"{float(value):.0%}"
    except (TypeError, ValueError):
        return "N/D"


def _format_timestamp(value: object) -> str:
    text = str(value or "N/D")
    return text.replace("+00:00", "Z")


def _decision_badge(decision: object) -> str:
    value = str(decision or "N/D").upper()
    if value in {"BUY", "SELL", "WAIT"}:
        return f"[{value}]"
    return value


def _live_badge(status: object) -> str:
    return f"[{str(status or 'READ ONLY').upper()}]"


def exibir_market_reading_pipeline(replay_data: object, data: object) -> None:
    """Exibe o fluxo Dados -> Leitura -> Contexto -> Setup -> Decisao -> Resultado."""
    st.subheader("Market Reading Pipeline")
    primeira_linha = st.columns(3)
    segunda_linha = st.columns(3)
    with primeira_linha[0]:
        exibir_bloco_dados_pipeline(replay_data, data)
    with primeira_linha[1]:
        exibir_bloco_leitura_pipeline(replay_data, data)
    with primeira_linha[2]:
        exibir_bloco_contexto_pipeline(replay_data)
    with segunda_linha[0]:
        exibir_bloco_setup_pipeline(replay_data, data)
    with segunda_linha[1]:
        exibir_bloco_decisao_pipeline(replay_data)
    with segunda_linha[2]:
        exibir_bloco_resultado_pipeline(replay_data)


def exibir_bloco_dados_pipeline(replay_data: object, data: object) -> None:
    """Exibe dados do candle atual."""
    dataset = getattr(data, "active_dataset", None)
    candle = getattr(replay_data, "current_candle", None)
    with st.container(border=True):
        st.subheader("Dados")
        colunas = st.columns(2)
        colunas[0].metric("Ativo", getattr(dataset, "asset", "N/D"))
        colunas[1].metric("Timeframe", getattr(dataset, "timeframe", "N/D"))
        colunas = st.columns(2)
        colunas[0].metric("Candle atual", _current_candle_position(replay_data))
        colunas[1].metric("Data", valor_ou_indisponivel(getattr(candle, "data", None)))
        colunas = st.columns(2)
        colunas[0].metric("OHLC", _ohlc_label(candle))
        colunas[1].metric("Volume", valor_ou_indisponivel(getattr(candle, "volume", None)))


def exibir_bloco_leitura_pipeline(replay_data: object, data: object) -> None:
    """Exibe leitura numerica do mercado."""
    profile = getattr(data, "dataset_profile", None)
    with st.container(border=True):
        st.subheader("Leitura do Mercado")
        colunas = st.columns(2)
        colunas[0].metric("Retorno candle", _percent_metric(_candle_return(replay_data)))
        colunas[1].metric(
            "Retorno acumulado",
            _percent_metric(_retorno_acumulado_replay(replay_data, profile)),
        )
        colunas = st.columns(2)
        colunas[0].metric("Volatilidade simples", _price_label(_simple_volatility(replay_data)))
        colunas[1].metric("Drawdown", _percent_metric(_market_drawdown(replay_data)))
        st.metric("Volume relativo", _relative_volume_label(replay_data))


def exibir_bloco_contexto_pipeline(replay_data: object) -> None:
    """Exibe contexto de mercado derivado das features do Replay."""
    feature_snapshot = getattr(replay_data, "feature_snapshot", None)
    with st.container(border=True):
        st.subheader("Contexto")
        colunas = st.columns(2)
        colunas[0].metric("Tendencia", _trend_label(feature_snapshot))
        colunas[1].metric("Lateralidade", _sideways_label(feature_snapshot))
        colunas = st.columns(2)
        colunas[0].metric("Volatilidade", _volatility_context_label(feature_snapshot))
        colunas[1].metric("Momentum", _momentum_label(feature_snapshot))


def exibir_bloco_setup_pipeline(replay_data: object, data: object) -> None:
    """Exibe leitura de setup da Alpha atual."""
    signal = getattr(replay_data, "strategy_signal", None)
    reasons = list(getattr(signal, "reasons", []) or [])
    with st.container(border=True):
        st.subheader("Setup")
        colunas = st.columns(2)
        colunas[0].metric(
            "Alpha avaliada",
            getattr(replay_data, "active_strategy_label", "N/D"),
        )
        colunas[1].metric("Setup encontrado", _setup_found_label(signal))
        st.metric("Motivo principal", reasons[0] if reasons else "Aguardando candle")
        warning = getattr(replay_data, "strategy_compatibility_warning", "")
        if warning:
            st.warning(warning)


def exibir_bloco_decisao_pipeline(replay_data: object) -> None:
    """Exibe decisao quantitativa candle a candle."""
    signal = getattr(replay_data, "strategy_signal", None)
    with st.container(border=True):
        st.subheader("Decisao")
        colunas = st.columns(3)
        colunas[0].metric("BUY", _decision_flag(signal, "BUY"))
        colunas[1].metric("SELL", _decision_flag(signal, "SELL"))
        colunas[2].metric("WAIT", _decision_flag(signal, "WAIT"))
        colunas = st.columns(2)
        colunas[0].metric("Confidence", f"{getattr(signal, 'confidence', 0.0):.0%}")
        colunas[1].metric("Score", getattr(signal, "score", 0))


def exibir_bloco_resultado_pipeline(replay_data: object) -> None:
    """Exibe resultado paper do Replay."""
    metrics = getattr(replay_data, "paper_metrics", None)
    equity_curve = list(getattr(replay_data, "paper_equity_curve", [0.0]))
    with st.container(border=True):
        st.subheader("Resultado")
        colunas = st.columns(2)
        colunas[0].metric("Trades", getattr(metrics, "total_trades", 0))
        colunas[1].metric("PnL", f"{getattr(metrics, 'net_profit_points', 0.0):.2f}")
        colunas = st.columns(2)
        colunas[0].metric("Drawdown", f"{getattr(metrics, 'max_drawdown_points', 0.0):.2f}")
        colunas[1].metric("Win rate", f"{getattr(metrics, 'win_rate', 0.0):.0%}")
        st.metric("Equity", f"{equity_curve[-1] if equity_curve else 0.0:.2f}")


def exibir_menu_lateral_workbench(
    service: DashboardService,
    data: object,
) -> object:
    """Exibe menu lateral do workbench e aplica escolhas antes do desenho."""
    st.sidebar.title("TraderIA")
    st.sidebar.caption("Research Workbench")

    datasets = service.list_historical_datasets()
    selected_id = service.get_selected_historical_dataset_id()
    dataset_options = [dataset.dataset_id for dataset in datasets]
    if dataset_options:
        selected_index = _selected_index(dataset_options, selected_id)
        dataset_id = st.sidebar.selectbox(
            "Dataset",
            dataset_options,
            index=selected_index,
            key="workbench_dataset",
        )
        data = aplicar_dataset_workbench(service, data, dataset_id)
    else:
        st.sidebar.info("Nenhum dataset disponivel.")

    strategies = service.list_available_replay_strategies()
    if strategies:
        active_strategy = service.get_active_replay_strategy_name()
        selected_strategy = st.sidebar.selectbox(
            "Alpha",
            strategies,
            index=_selected_index(strategies, active_strategy),
            key="workbench_alpha",
        )
        if selected_strategy != active_strategy:
            try:
                service.select_replay_strategy(selected_strategy)
                data = service.get_dashboard_data()
                st.sidebar.success(f"Alpha ativa: {selected_strategy}")
            except ValueError as exc:
                st.sidebar.error(str(exc))
    else:
        st.sidebar.info("Nenhuma Alpha disponivel.")

    replay_data = getattr(data, "replay_data", None)
    warning = getattr(replay_data, "strategy_compatibility_warning", "")
    if warning:
        st.sidebar.warning(warning)

    current_speed = getattr(replay_data, "replay_speed_seconds", 1.0)
    speed = st.sidebar.number_input(
        "Velocidade",
        min_value=0.0,
        value=float(current_speed),
        step=0.5,
        key="workbench_replay_speed",
    )

    if st.sidebar.button("Play", key="workbench_play"):
        data = carregar_dataset_se_necessario(service, data)
        service.enable_replay_auto_run(speed)
        data = service.get_dashboard_data()
    if st.sidebar.button("Pause", key="workbench_pause"):
        service.disable_replay_auto_run()
        data = service.get_dashboard_data()
    if st.sidebar.button("Reset", key="workbench_reset"):
        service.reset_replay()
        data = service.get_dashboard_data()

    return carregar_dataset_se_necessario(service, data)


def aplicar_dataset_workbench(
    service: DashboardService,
    data: object,
    dataset_id: str,
) -> object:
    """Seleciona e carrega o dataset escolhido pela sidebar."""
    current_id = service.get_selected_historical_dataset_id()
    replay_data = getattr(data, "replay_data", None)
    current_total = getattr(replay_data, "total_candles", 0)
    if dataset_id == current_id and current_total > 0:
        return data
    try:
        service.select_historical_dataset(dataset_id)
        service.load_selected_historical_dataset_to_replay()
        st.sidebar.success("Dataset carregado.")
    except ValueError as exc:
        st.sidebar.error(str(exc))
    return service.get_dashboard_data()


def carregar_dataset_se_necessario(
    service: DashboardService,
    data: object,
) -> object:
    """Garante que a tela principal sempre tenha dataset real carregado."""
    replay_data = getattr(data, "replay_data", None)
    if getattr(replay_data, "total_candles", 0) > 0:
        return data
    if service.get_selected_historical_dataset() is None:
        return data
    try:
        service.load_selected_historical_dataset_to_replay()
    except ValueError as exc:
        st.sidebar.error(str(exc))
    return service.get_dashboard_data()


def exibir_regiao_grafico_workbench(replay_data: object) -> None:
    """Exibe grafico candlestick e volume do dataset carregado."""
    st.subheader("Grafico")
    candles = list(getattr(replay_data, "candles_loaded", []))
    processed_count = len(getattr(replay_data, "candles_processed", []))
    if not candles:
        st.info("Selecione um dataset para carregar o grafico.")
        return

    chart_data = _candlestick_chart_data(candles, processed_count)
    st.vega_lite_chart(
        chart_data,
        _candlestick_spec(),
        width="stretch",
    )
    st.caption("Volume")
    st.vega_lite_chart(
        chart_data,
        _volume_spec(),
        width="stretch",
    )


def exibir_regiao_replay_workbench(
    service: DashboardService,
    replay_data: object,
) -> object:
    """Exibe controles de replay orientados a pesquisa."""
    st.subheader("Replay")
    disabled = replay_control_disabled(replay_data)
    colunas = st.columns(4)
    if colunas[0].button(
        "Candle anterior",
        disabled=getattr(replay_data, "current_index", -1) <= 0,
        key="workbench_previous_candle",
    ):
        replay_data = voltar_candle_replay(service, replay_data)
    if colunas[1].button(
        "Proximo candle",
        disabled=disabled["next"],
        key="workbench_next_candle",
    ):
        replay_data = service.next_replay_candle()
    if colunas[2].button("Play", disabled=disabled["auto"], key="workbench_region_play"):
        replay_data = service.enable_replay_auto_run(
            float(getattr(replay_data, "replay_speed_seconds", 1.0))
        )
    if colunas[3].button("Pause", key="workbench_region_pause"):
        replay_data = service.disable_replay_auto_run()

    target_date = st.text_input("Ir para data", value="", key="workbench_go_to_date")
    if st.button("Ir", key="workbench_go_to_date_button") and target_date.strip():
        replay_data = ir_para_data_replay(service, replay_data, target_date.strip())

    exibir_estado_replay(replay_data)
    exibir_candle_replay(getattr(replay_data, "current_candle", None))
    return replay_data


def voltar_candle_replay(
    service: DashboardService,
    replay_data: object,
) -> object:
    """Retorna um candle usando apenas operacoes existentes da fachada."""
    current_index = int(getattr(replay_data, "current_index", -1))
    if current_index <= 0:
        return service.reset_replay()
    target_index = current_index - 1
    replay_data = service.reset_replay()
    for _ in range(target_index + 1):
        replay_data = service.next_replay_candle()
    return replay_data


def ir_para_data_replay(
    service: DashboardService,
    replay_data: object,
    target_date: str,
) -> object:
    """Avanca ate a primeira data igual ou posterior ao alvo informado."""
    candles = list(getattr(replay_data, "candles_loaded", []))
    replay_data = service.reset_replay()
    for candle in candles:
        replay_data = service.next_replay_candle()
        if str(getattr(candle, "data", "")) >= target_date:
            break
    return replay_data


def exibir_regiao_alpha_workbench(replay_data: object, data: object) -> None:
    """Exibe decisao quantitativa da Alpha carregada."""
    st.subheader("Alpha")
    signal = getattr(replay_data, "strategy_signal", None)
    decision = getattr(signal, "decision", "WAIT")
    confidence = getattr(signal, "confidence", 0.0)
    score = getattr(signal, "score", 0)
    reasons = list(getattr(signal, "reasons", []) or [])

    colunas = st.columns(3)
    colunas[0].metric(
        "Alpha carregada",
        getattr(replay_data, "active_strategy_label", "N/D"),
    )
    colunas[1].metric("Status", "PESQUISA/PAPER")
    colunas[2].metric("Decisao", decision)

    colunas = st.columns(2)
    colunas[0].metric("Confidence", f"{confidence:.0%}")
    colunas[1].metric("Score", score)

    st.caption("Explicacao")
    if reasons:
        for reason in reasons:
            st.write(f"- {reason}")
    else:
        st.write("- Aguardando candle processado para gerar decisao quantitativa.")
    warning = getattr(replay_data, "strategy_compatibility_warning", "")
    if warning:
        st.warning(warning)
    st.warning("Nenhuma ordem real sera executada nesta tela.")


def exibir_regiao_estatisticas_workbench(
    replay_data: object,
    data: object,
) -> None:
    """Exibe estatisticas quantitativas atualizadas pelo Replay."""
    st.subheader("Estatisticas")
    metrics = getattr(replay_data, "paper_metrics", None)
    profile = getattr(data, "dataset_profile", None)
    equity_curve = list(getattr(replay_data, "paper_equity_curve", [0.0]))

    total_trades = getattr(metrics, "total_trades", 0)
    win_rate = getattr(metrics, "win_rate", 0.0)
    pf_value = getattr(metrics, "profit_factor", 0.0)
    drawdown = getattr(metrics, "max_drawdown_points", 0.0)
    net_profit = getattr(metrics, "net_profit_points", 0.0)
    expectancy = _expectancy_from_metrics(metrics)
    sharpe = _sharpe_from_equity_curve(equity_curve)
    accumulated_return = _retorno_acumulado_replay(replay_data, profile)

    colunas = st.columns(4)
    colunas[0].metric("Trades", total_trades)
    colunas[1].metric("PnL", f"{net_profit:.2f}")
    colunas[2].metric("Win Rate", f"{win_rate:.0%}")
    colunas[3].metric("Profit Factor", _format_profit_factor(pf_value))

    colunas = st.columns(4)
    colunas[0].metric("Drawdown", f"{drawdown:.2f}")
    colunas[1].metric("Expectancy", f"{expectancy:.2f}")
    colunas[2].metric("Quantidade de operacoes", total_trades)
    colunas[3].metric("Sharpe", sharpe)

    st.metric("Retorno acumulado", _percent_metric(accumulated_return))
    st.caption("Equity Curve")
    st.line_chart({"equity": equity_curve})


def _selected_index(options: list[str], selected: str | None) -> int:
    if selected in options:
        return options.index(selected)
    return 0


def _current_candle_position(replay_data: object) -> str:
    total = getattr(replay_data, "total_candles", 0)
    current_index = getattr(replay_data, "current_index", -1)
    if total <= 0:
        return "N/D"
    position = max(current_index + 1, 0)
    return f"{position}/{total}"


def _ohlc_label(candle: object) -> str:
    if candle is None:
        return "N/D"
    return (
        f"{getattr(candle, 'abertura', 0.0):.2f} | "
        f"{getattr(candle, 'maxima', 0.0):.2f} | "
        f"{getattr(candle, 'minima', 0.0):.2f} | "
        f"{getattr(candle, 'fechamento', 0.0):.2f}"
    )


def _candle_return(replay_data: object) -> float:
    candle = getattr(replay_data, "current_candle", None)
    if candle is None:
        return 0.0
    open_price = float(getattr(candle, "abertura", 0.0))
    close_price = float(getattr(candle, "fechamento", 0.0))
    if open_price == 0:
        return 0.0
    return (close_price / open_price) - 1.0


def _simple_volatility(replay_data: object) -> float:
    candle = getattr(replay_data, "current_candle", None)
    if candle is None:
        feature_snapshot = getattr(replay_data, "feature_snapshot", None)
        return float(getattr(feature_snapshot, "average_range", 0.0) or 0.0)
    return float(getattr(candle, "maxima", 0.0)) - float(getattr(candle, "minima", 0.0))


def _market_drawdown(replay_data: object) -> float:
    candles = list(getattr(replay_data, "candles_processed", []))
    if not candles:
        current = getattr(replay_data, "current_candle", None)
        candles = [] if current is None else [current]
    closes = [float(getattr(candle, "fechamento", 0.0)) for candle in candles]
    if not closes:
        return 0.0
    peak = max(closes)
    current_close = closes[-1]
    if peak == 0:
        return 0.0
    return (current_close / peak) - 1.0


def _relative_volume_label(replay_data: object) -> str:
    candle = getattr(replay_data, "current_candle", None)
    if candle is None:
        return "N/D"
    candles = list(getattr(replay_data, "candles_processed", []))
    volumes = [float(getattr(item, "volume", 0.0)) for item in candles if item is not candle]
    if not volumes:
        return "1.00x"
    average_volume = sum(volumes) / len(volumes)
    if average_volume == 0:
        return "N/D"
    return f"{float(getattr(candle, 'volume', 0.0)) / average_volume:.2f}x"


def _trend_label(feature_snapshot: object) -> str:
    direction = getattr(feature_snapshot, "direction", None)
    if direction is None:
        return "N/D"
    return str(direction).upper()


def _sideways_label(feature_snapshot: object) -> str:
    trend_strength = float(getattr(feature_snapshot, "trend_strength", 0.0) or 0.0)
    if trend_strength == 0.0:
        return "N/D"
    return "SIM" if trend_strength < 0.25 else "NAO"


def _volatility_context_label(feature_snapshot: object) -> str:
    volatility = getattr(feature_snapshot, "volatility_level", None)
    if volatility is None:
        return "N/D"
    return str(volatility).upper()


def _momentum_label(feature_snapshot: object) -> str:
    momentum = getattr(feature_snapshot, "momentum", None)
    if momentum is None:
        return "N/D"
    return f"{float(momentum):.2f}"


def _setup_found_label(signal: object) -> str:
    decision = getattr(signal, "decision", "WAIT")
    return "SIM" if decision in {"BUY", "SELL"} else "NAO"


def _decision_flag(signal: object, expected: str) -> str:
    decision = getattr(signal, "decision", "WAIT")
    return "SIM" if decision == expected else "NAO"


def _candlestick_chart_data(
    candles: list[object],
    processed_count: int,
) -> list[dict[str, object]]:
    rows = []
    for index, candle in enumerate(candles):
        rows.append(
            {
                "data": str(getattr(candle, "data", "")),
                "open": float(getattr(candle, "abertura", 0.0)),
                "high": float(getattr(candle, "maxima", 0.0)),
                "low": float(getattr(candle, "minima", 0.0)),
                "close": float(getattr(candle, "fechamento", 0.0)),
                "volume": float(getattr(candle, "volume", 0.0)),
                "direction": (
                    "alta"
                    if getattr(candle, "fechamento", 0.0)
                    >= getattr(candle, "abertura", 0.0)
                    else "baixa"
                ),
                "status": _candle_status(index, processed_count),
            }
        )
    return rows


def _candlestick_spec() -> dict[str, object]:
    return {
        "height": 430,
        "params": [{"name": "zoom", "select": "interval", "bind": "scales"}],
        "encoding": {
            "x": {
                "field": "data",
                "type": "temporal",
                "axis": {"title": "Data"},
            },
            "tooltip": [
                {"field": "data", "type": "temporal", "title": "Data"},
                {"field": "open", "type": "quantitative", "title": "Open"},
                {"field": "high", "type": "quantitative", "title": "High"},
                {"field": "low", "type": "quantitative", "title": "Low"},
                {"field": "close", "type": "quantitative", "title": "Close"},
                {"field": "volume", "type": "quantitative", "title": "Volume"},
            ],
        },
        "layer": [
            {
                "mark": "rule",
                "encoding": {
                    "y": {"field": "low", "type": "quantitative"},
                    "y2": {"field": "high"},
                    "color": {
                        "field": "direction",
                        "scale": {"range": ["#1B8A5A", "#C43D3D"]},
                    },
                },
            },
            {
                "mark": {"type": "bar", "size": 5},
                "encoding": {
                    "y": {"field": "open", "type": "quantitative"},
                    "y2": {"field": "close"},
                    "color": {
                        "field": "direction",
                        "scale": {"range": ["#1B8A5A", "#C43D3D"]},
                        "legend": None,
                    },
                },
            },
        ],
    }


def _volume_spec() -> dict[str, object]:
    return {
        "height": 120,
        "params": [{"name": "zoom", "select": "interval", "bind": "scales"}],
        "mark": {"type": "bar", "color": "#557A95"},
        "encoding": {
            "x": {"field": "data", "type": "temporal", "axis": {"title": "Data"}},
            "y": {
                "field": "volume",
                "type": "quantitative",
                "axis": {"title": "Volume"},
            },
            "tooltip": [
                {"field": "data", "type": "temporal", "title": "Data"},
                {"field": "volume", "type": "quantitative", "title": "Volume"},
            ],
        },
    }


def _expectancy_from_metrics(metrics: object) -> float:
    if metrics is None:
        return 0.0
    wins = getattr(metrics, "wins", 0)
    losses = getattr(metrics, "losses", 0)
    total = wins + losses
    if total == 0:
        return 0.0
    average_win = getattr(metrics, "average_win_points", 0.0)
    average_loss = getattr(metrics, "average_loss_points", 0.0)
    win_rate = getattr(metrics, "win_rate", 0.0)
    loss_rate = 1.0 - win_rate
    return (win_rate * average_win) - (loss_rate * average_loss)


def _sharpe_from_equity_curve(equity_curve: list[float]) -> str:
    if len(equity_curve) < 3:
        return "N/D"
    returns = [
        equity_curve[index] - equity_curve[index - 1]
        for index in range(1, len(equity_curve))
    ]
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / len(returns)
    if variance == 0:
        return "N/D"
    sharpe = mean / (variance ** 0.5)
    return f"{sharpe:.2f}"


def _retorno_acumulado_replay(replay_data: object, profile: object) -> float:
    current = getattr(replay_data, "current_candle", None)
    candles = list(getattr(replay_data, "candles_loaded", []))
    if current is not None and candles:
        first_close = float(getattr(candles[0], "fechamento", 0.0))
        current_close = float(getattr(current, "fechamento", 0.0))
        if first_close:
            return (current_close / first_close) - 1.0
    return float(getattr(profile, "accumulated_return", 0.0) or 0.0)


def main() -> None:
    """Renderiza a plataforma de pesquisa quantitativa."""
    app_title = os.getenv("TRADERIA_APP_TITLE", "TraderIA Local").strip()
    st.set_page_config(page_title=app_title or "TraderIA Local", layout="wide")
    _inject_dashboard_css()
    fast_boot_enabled = os.getenv("TRADERIA_FAST_BOOT_ENABLED", "0").strip() == "1"
    fast_boot_unlocked = os.getenv("TRADERIA_ALLOW_FAST_BOOT", "0").strip() == "1"
    if fast_boot_enabled and fast_boot_unlocked:
        _render_fast_boot_dashboard(app_title or "TraderIA Nuvem")
        return
    service = get_dashboard_service()
    ensure_mt5_forex_initial_load(service)
    # Fallback completo preservado para auditoria: get_dashboard_view_model_or_stop(service)
    data = get_light_dashboard_view_model_or_stop(service)
    data = _apply_fast_mt5_snapshot_if_available(service, data)

    st.title("TraderIA Novo")
    _render_top_runtime_reset()
    initial_mt5_error = st.session_state.get(MT5_FOREX_INITIAL_LOAD_ERROR_KEY)
    if initial_mt5_error:
        st.caption(f"Erro MT5 na carga inicial: {initial_mt5_error}")
    render_contract_diagnostics(service)
    exibir_dashboard_layout(service, data)


def _render_fast_boot_dashboard(app_title: str) -> None:
    """Abre a copia GitHub rapido, com Forex/Lab/Relatorio operacionais."""
    st.title(app_title)
    st.caption(
        "Modo rapido da copia GitHub. MT5 em leitura direta; Workbench completo "
        "preservado no codigo e habilitavel com TRADERIA_FAST_BOOT_ENABLED=0."
    )
    snapshot = _build_fast_mt5_forex_snapshot(DashboardService())
    if snapshot is None:
        st.warning("MT5 nao conectado nesta leitura rapida.")
        snapshot = DashboardMT5ForexSignalViewModel(
            connection_status="OFFLINE",
            message="MT5 nao conectado.",
        )

    forex_tab, lab_tab, report_tab = st.tabs(["Forex MT5", "Lab", "Relatorio"])
    positioned_rows = [
        row
        for row in list(getattr(snapshot, "pairs", []) or [])
        if getattr(row, "decision", "WAIT") in {"BUY", "SELL"}
    ]

    with forex_tab:
        st.subheader("MT5 Forex")
        cols = st.columns(5)
        cols[0].metric("Status MT5", snapshot.connection_status)
        cols[1].metric("Servidor", snapshot.server)
        cols[2].metric("Conta", snapshot.account)
        cols[3].metric("Pares", len(snapshot.pairs))
        cols[4].metric("Posicoes", len(positioned_rows))
        if snapshot.connection_status == "ONLINE":
            st.success(snapshot.message)
        else:
            st.warning(snapshot.message)
        st.dataframe(
            [_fast_forex_display_row(row) for row in snapshot.pairs],
            hide_index=True,
            width="stretch",
        )

    with lab_tab:
        st.subheader("Lab")
        st.caption("Parametros operacionais usados pelo ciclo rapido.")
        cols = st.columns(5)
        cols[0].metric("Setup", "TREND_MOMENTUM")
        cols[1].metric("Timeframe", snapshot.timeframe)
        cols[2].metric("Entrada", "Zona + posicao")
        cols[3].metric("Velas", "500")
        cols[4].metric("Saida", "Lab/MT5")
        st.dataframe(
            [
                {
                    "Par": row.pair,
                    "TF decisor": row.timeframe,
                    "Setup": row.active_model,
                    "Entrada": row.decision,
                    "Saida": row.research_plan_stop_management,
                    "Motivo": row.reason,
                }
                for row in snapshot.pairs
            ],
            hide_index=True,
            width="stretch",
        )

    with report_tab:
        st.subheader("Relatorio")
        open_profit = sum(
            float(getattr(row, "confidence", 0.0) or 0.0)
            for row in positioned_rows
        )
        cols = st.columns(4)
        cols[0].metric("Auditoria", "READ_ONLY")
        cols[1].metric("Pares", len(snapshot.pairs))
        cols[2].metric("Posicoes abertas", len(positioned_rows))
        cols[3].metric("Status", snapshot.connection_status)
        st.info("Relatorio rapido da copia GitHub: acompanha posicoes abertas sem enviar ordens.")
        st.dataframe(
            [_fast_report_display_row(row) for row in snapshot.pairs],
            hide_index=True,
            width="stretch",
        )


def _fast_forex_display_row(row: DashboardMT5ForexSignalRowViewModel) -> dict[str, object]:
    return {
        "Par": row.pair,
        "Status": row.status,
        "Decisao": row.decision,
        "TF": row.timeframe,
        "Preco": _price_label(float(row.last_price or 0.0)),
        "Stop": _price_label(float(row.research_plan_stop or 0.0)),
        "Alvo": _price_label(float(row.research_plan_target or 0.0)),
        "Motivo": row.reason,
    }


def _fast_report_display_row(row: DashboardMT5ForexSignalRowViewModel) -> dict[str, object]:
    return {
        "Par": row.pair,
        "Operacao": "ABERTA" if row.decision in {"BUY", "SELL"} else "SEM POSICAO",
        "Lado": row.decision,
        "Preco": _price_label(float(row.last_price or 0.0)),
        "Stop": _price_label(float(row.research_plan_stop or 0.0)),
        "Alvo": _price_label(float(row.research_plan_target or 0.0)),
        "Fonte": "MT5_FAST_SNAPSHOT",
    }


if __name__ == "__main__":
    main()
