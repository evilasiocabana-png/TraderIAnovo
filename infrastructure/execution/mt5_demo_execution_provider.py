"""Adaptador exclusivo para envio de ordens em conta demo do MetaTrader 5."""

from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from application.model15_xau_m5_breakout import MODEL_15_ID
from application.model16_xau_m5_price_ema_breakout import MODEL_16_ID
from application.model23_basket_accumulator import (
    is_model23,
    model23_order_comment,
)
from application.model24_xau_basket import is_model24, model24_order_comment
from application.model3_xau_m5_rsi50_flip import MODEL_3_ID
from application.model8_xau_m5_sma_rsi_reentry import MODEL_8_ID
from application.xau_m5_sma_rsi_model_family import (
    XAU_IMPROVED_REENTRY_MODEL_IDS,
    XAU_ALL_TREND_FILTER_MODEL_IDS as XAU_TREND_FILTER_MODEL_IDS,
    xau_model_requires_target,
)
from application.forex_m5_sma_rsi_model_family import FOREX_SMA_RSI_MODEL_IDS
from domain.operational_model_policy import (
    is_dynamic_exit_operational_model,
    is_retired_operational_model,
)
from domain.contracts.dynamic_exit_demo_sl import DynamicExitDemoSLExecutionResult
from core.jsonl_tail import read_last_text_lines
from core.mt5_external_process_gate import (
    get_mt5_external_cache,
    mt5_external_process_slot,
    set_mt5_external_cache,
)
from core.mt5_process_probe import resolve_mt5_terminal_path, terminate_process_tree


_MT5_ORDER_SEND_LOCK = threading.Lock()
MAX_OPERATIONAL_MODELS_PER_SYMBOL = 22
MAX_MODEL23_POSITIONS_PER_SYMBOL = 64
KNOWN_MODEL_COMMENTS = frozenset(f"M{index}" for index in range(1, 25))
INDEPENDENT_SMA_RSI_MODEL_IDS = frozenset(
    {
        MODEL_8_ID,
        *XAU_TREND_FILTER_MODEL_IDS,
        *FOREX_SMA_RSI_MODEL_IDS,
    }
)


def _is_basket_model(value: object) -> bool:
    return is_model23(value) or is_model24(value)


@dataclass(frozen=True)
class _ExecutionSendException:
    error: Exception


@dataclass
class MT5DemoExecutionProvider:
    """Provider MT5 restrito a conta demo e ordens normalizadas."""

    mt5: Any | None = None
    magic: int = 260629
    deviation: int = 20
    log_path: Path = field(
        default_factory=lambda: Path(".traderia") / "mt5_demo_execution.jsonl"
    )
    management_log_path: Path = field(
        default_factory=lambda: Path(".traderia") / "mt5_stop_management.jsonl"
    )
    external_read_cache: dict[str, tuple[float, dict[str, Any]]] = field(
        default_factory=dict,
        repr=False,
    )
    execution_log_cache: list[dict[str, Any]] | None = field(
        default=None,
        init=False,
        repr=False,
    )
    execution_log_cache_signature: tuple[int, int] | None = field(
        default=None,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if self.mt5 is None:
            self.mt5 = importlib.import_module("MetaTrader5")


    def has_open_position(self, symbol: str) -> bool:
        """Consulta posicoes abertas para impedir duplicidade por simbolo."""
        if self._external_reads_enabled():
            payload = self._external_mt5_read("positions", symbol=symbol)
            return True if not bool(payload.get("ok")) else bool(payload.get("rows"))
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return True
        positions = self.mt5.positions_get(symbol=symbol)
        return bool(positions)

    def has_open_position_for_model(
        self,
        symbol: str,
        operational_model: str,
    ) -> bool:
        """Consulta posicao aberta do mesmo simbolo e modelo operacional."""
        if self._external_reads_enabled():
            payload = self._external_mt5_read("positions", symbol=symbol)
            if not bool(payload.get("ok")):
                return True
            positions = [
                SimpleNamespace(**dict(row)) for row in payload.get("rows", [])
            ]
        else:
            initialize_check = self._initialize_check()
            if initialize_check is not None:
                return True
            positions = list(self.mt5.positions_get(symbol=symbol) or [])
        if _is_basket_model(operational_model):
            if len(positions) >= MAX_MODEL23_POSITIONS_PER_SYMBOL:
                return True
            for position in positions:
                comment = str(getattr(position, "comment", "") or "").upper()
                if not (KNOWN_MODEL_COMMENTS & set(comment.split())):
                    return True
            return False
        if len(positions) >= MAX_OPERATIONAL_MODELS_PER_SYMBOL:
            return True
        expected = self._model_comment(operational_model)
        for position in positions:
            comment = str(getattr(position, "comment", "") or "").upper()
            model_tokens = KNOWN_MODEL_COMMENTS & set(comment.split())
            if expected in model_tokens:
                return True
            # Posicao manual (ou de origem nao identificada) no mesmo simbolo
            # nao pode receber uma segunda ordem automatica. Somente uma
            # posicao TraderIA claramente marcada como outro modelo pode
            # coexistir no ativo.
            if not model_tokens:
                return True
        return False

    def get_open_position(self, symbol: str) -> object | None:
        """Retorna a primeira posicao aberta do simbolo em conta demo."""
        if self._external_reads_enabled():
            positions = self._external_positions(symbol)
            return positions[0] if positions else None
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return None
        positions = self.mt5.positions_get(symbol=symbol) or []
        return positions[0] if positions else None

    def get_open_position_by_ticket(self, symbol: str, ticket: int) -> object | None:
        """Retorna a posicao aberta exata pelo ticket."""
        if self._external_reads_enabled():
            return next(
                (
                    position
                    for position in self._external_positions(symbol)
                    if int(getattr(position, "ticket", 0) or 0) == int(ticket or 0)
                ),
                None,
            )
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return None
        return self._find_position(str(symbol or "").upper(), int(ticket or 0))

    def list_open_positions(self) -> list[object]:
        """Lista posicoes abertas para gestao por ticket/modelo."""
        if self._external_reads_enabled():
            return self._external_positions("")
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            raise RuntimeError(
                "MT5 indisponivel para leitura das posicoes abertas: "
                f"{initialize_check.message}"
            )
        return list(self.mt5.positions_get() or [])

    def get_current_price(self, symbol: str) -> float | None:
        """Retorna preco atual read-only para validacao de SL."""
        if self._external_reads_enabled():
            payload = self._external_mt5_read("tick", symbol=symbol)
            bid = self._positive_float(payload.get("bid"))
            ask = self._positive_float(payload.get("ask"))
            if bid is not None and ask is not None:
                return (bid + ask) / 2.0
            return bid if bid is not None else ask
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return None
        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        bid = self._positive_float(getattr(tick, "bid", None))
        ask = self._positive_float(getattr(tick, "ask", None))
        if bid is not None and ask is not None:
            return (bid + ask) / 2.0
        return bid if bid is not None else ask

    def get_recent_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[object]:
        """Retorna candles MT5 recentes em modo read-only."""
        if self._external_reads_enabled():
            payload = self._external_mt5_read(
                "candles",
                symbol=symbol,
                timeframe=timeframe,
                limit=max(int(limit), 1),
            )
            return [SimpleNamespace(**dict(row)) for row in payload.get("rows", [])]
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return []
        copy_rates = getattr(self.mt5, "copy_rates_from_pos", None)
        if not callable(copy_rates):
            return []
        timeframe_value = getattr(self.mt5, f"TIMEFRAME_{str(timeframe).upper()}", None)
        if timeframe_value is None:
            return []
        try:
            rates = copy_rates(symbol, timeframe_value, 0, max(int(limit), 1))
        except Exception:  # noqa: BLE001 - provider externo MT5
            return []
        if rates is None:
            return []
        return list(rates)

    def _external_reads_enabled(self) -> bool:
        return (
            os.getenv("TRADERIA_MT5_EXECUTION_READ_EXTERNAL_PROCESS_ENABLED", "0")
            .strip()
            == "1"
        )

    def _external_positions(self, symbol: str) -> list[object]:
        payload = self._external_mt5_read("positions", symbol=symbol)
        if not bool(payload.get("ok")):
            raise RuntimeError(
                "Sonda MT5 nao confirmou a leitura das posicoes abertas."
            )
        return [SimpleNamespace(**dict(row)) for row in payload.get("rows", [])]

    def _external_mt5_read(self, action: str, **kwargs: Any) -> dict[str, Any]:
        request = {
            "action": str(action),
            "terminal_path": resolve_mt5_terminal_path(),
            **kwargs,
        }
        cache_key = json.dumps(request, sort_keys=True, default=str)
        shared_cache_key = f"execution_read:{cache_key}"
        cached = self.external_read_cache.get(cache_key)
        ttl = max(
            float(os.getenv("TRADERIA_MT5_EXECUTION_READ_CACHE_SECONDS", "2")),
            0.0,
        )
        if cached and time.monotonic() - cached[0] <= ttl:
            return dict(cached[1])
        shared = get_mt5_external_cache(shared_cache_key, ttl_seconds=ttl)
        if isinstance(shared, dict):
            self.external_read_cache[cache_key] = (time.monotonic(), shared)
            return dict(shared)
        code = r'''
import json
import sys

request = json.loads(sys.argv[1])
import MetaTrader5 as mt5

path = request.get("terminal_path")
ok = bool(mt5.initialize(path=path) if path else mt5.initialize())
if not ok:
    print(json.dumps({"ok": False, "rows": [], "message": str(mt5.last_error())}))
    raise SystemExit(0)

action = request.get("action")
if action == "positions":
    symbol = str(request.get("symbol") or "")
    values = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
    rows = [item._asdict() for item in (values or [])]
    payload = {"ok": True, "rows": rows}
elif action == "tick":
    tick = mt5.symbol_info_tick(str(request.get("symbol") or ""))
    payload = {"ok": tick is not None, **(tick._asdict() if tick else {})}
elif action == "candles":
    timeframe = getattr(mt5, "TIMEFRAME_" + str(request.get("timeframe") or "M1").upper(), None)
    rates = None if timeframe is None else mt5.copy_rates_from_pos(
        str(request.get("symbol") or ""),
        timeframe,
        0,
        max(int(request.get("limit") or 1), 1),
    )
    rows = []
    for rate in (list(rates) if rates is not None else []):
        rows.append({
            "time": int(rate["time"]),
            "open": float(rate["open"]),
            "high": float(rate["high"]),
            "low": float(rate["low"]),
            "close": float(rate["close"]),
            "tick_volume": int(rate["tick_volume"]),
        })
    payload = {"ok": True, "rows": rows}
else:
    payload = {"ok": False, "rows": [], "message": "unknown action"}
print(json.dumps(payload, default=str))
mt5.shutdown()
'''
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0)
            if sys.platform.startswith("win")
            else 0
        )
        process: subprocess.Popen[str] | None = None
        timeout_seconds = max(
            float(os.getenv("TRADERIA_MT5_EXECUTION_READ_TIMEOUT_SECONDS", "5")),
            1.0,
        )
        with mt5_external_process_slot(timeout=min(timeout_seconds, 1.0)) as acquired:
            if not acquired:
                return dict(cached[1]) if cached else {"ok": False, "rows": []}
            try:
                process = subprocess.Popen(
                    [sys.executable, "-c", code, json.dumps(request)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=creationflags,
                )
                stdout, _stderr = process.communicate(timeout=timeout_seconds)
            except (OSError, subprocess.TimeoutExpired):
                if process is not None:
                    terminate_process_tree(process)
                return dict(cached[1]) if cached else {"ok": False, "rows": []}
        output = (stdout or "").strip().splitlines()
        if not output:
            return {"ok": False, "rows": []}
        try:
            payload = dict(json.loads(output[-1]))
        except (json.JSONDecodeError, TypeError, ValueError):
            return {"ok": False, "rows": []}
        self.external_read_cache[cache_key] = (time.monotonic(), payload)
        set_mt5_external_cache(shared_cache_key, payload)
        return payload

    def get_atr(
        self,
        symbol: str,
        timeframe: str,
        period: int,
    ) -> float | None:
        """Calcula ATR simples a partir de candles recentes quando possivel."""
        candles = self.get_recent_candles(symbol, timeframe, max(int(period) + 1, 2))
        if len(candles) < 2:
            return None
        true_ranges: list[float] = []
        for previous, current in zip(candles, candles[1:]):
            high = self._candle_value(current, "high")
            low = self._candle_value(current, "low")
            previous_close = self._candle_value(previous, "close")
            if high is None or low is None or previous_close is None:
                return None
            true_ranges.append(
                max(
                    high - low,
                    abs(high - previous_close),
                    abs(low - previous_close),
                )
            )
        if not true_ranges:
            return None
        return sum(true_ranges[-int(period):]) / min(len(true_ranges), int(period))

    def modify_position_sl(
        self,
        symbol: str,
        ticket: int,
        new_stop: float,
    ) -> DynamicExitDemoSLExecutionResult:
        """Porta generica para alterar somente SL de posicao MT5 Demo."""
        position = self._find_position(str(symbol or "").upper(), int(ticket or 0))
        if position is None:
            created_at = datetime.now().astimezone().isoformat()
            return self._assisted_sl_result(
                symbol=str(symbol or "").upper(),
                ticket=ticket,
                side="N/D",
                requested_stop=new_stop,
                created_at=created_at,
                message="Posicao demo nao encontrada para modificar SL.",
                rejection_reasons=("Posicao demo nao encontrada.",),
            )
        side = self._position_side(position, {})
        return self.modify_demo_position_stop_loss(
            symbol=str(symbol or "").upper(),
            ticket=int(ticket or 0),
            side=side,
            requested_stop=float(new_stop),
            decision_key="POSITION_MANAGER",
        )

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> ExecutionResult:
        """Fecha posicao existente em conta demo usando ordem oposta."""
        normalized_symbol = str(symbol or "").upper()
        normalized_side = str(side or "").upper()
        created_at = datetime.now().astimezone().isoformat()
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    volume,
                    reason,
                    initialize_check,
                    submitted=False,
                )
            )
            return initialize_check
        demo_check = self._demo_account_check()
        if demo_check is not None:
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    volume,
                    reason,
                    demo_check,
                    submitted=False,
                )
            )
            return demo_check
        symbol_check = self._ensure_symbol(normalized_symbol)
        if symbol_check is not None:
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    volume,
                    reason,
                    symbol_check,
                    submitted=False,
                )
            )
            return symbol_check
        position = self._find_position(normalized_symbol, int(ticket or 0))
        if position is None:
            result = ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Posicao demo nao encontrada para fechamento.",
            )
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    volume,
                    reason,
                    result,
                    submitted=False,
                )
            )
            return result
        position_side = self._position_side(position, {"decision": normalized_side})
        if normalized_side not in {"BUY", "SELL"} or position_side != normalized_side:
            result = ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Lado informado nao confere com posicao MT5.",
            )
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    volume,
                    reason,
                    result,
                    submitted=False,
                )
            )
            return result
        close_volume = float(volume or getattr(position, "volume", 0.0) or 0.0)
        if close_volume <= 0.0:
            result = ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Volume invalido para fechamento demo.",
            )
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    volume,
                    reason,
                    result,
                    submitted=False,
                )
            )
            return result
        tick = self.mt5.symbol_info_tick(normalized_symbol)
        if tick is None:
            result = ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Tick indisponivel para fechamento demo.",
            )
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    close_volume,
                    reason,
                    result,
                    submitted=False,
                )
            )
            return result
        close_type = (
            self.mt5.ORDER_TYPE_SELL
            if normalized_side == "BUY"
            else self.mt5.ORDER_TYPE_BUY
        )
        price = (
            self._positive_float(getattr(tick, "bid", None))
            if normalized_side == "BUY"
            else self._positive_float(getattr(tick, "ask", None))
        )
        if price is None:
            result = ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Preco indisponivel para fechamento demo.",
            )
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    close_volume,
                    reason,
                    result,
                    submitted=False,
                )
            )
            return result
        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "position": int(ticket),
            "symbol": normalized_symbol,
            "volume": close_volume,
            "type": close_type,
            "price": float(price),
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": "TraderIA PM EXIT",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        order_check = self._order_check(request)
        if order_check is not None and not self._order_check_passed(order_check):
            result = ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=self._order_check_message(order_check),
                error_code=self._order_check_retcode(order_check),
            )
            self._write_management_log(
                self._close_log_payload(
                    created_at,
                    normalized_symbol,
                    ticket,
                    normalized_side,
                    close_volume,
                    reason,
                    result,
                    submitted=False,
                    price=float(price),
                    order_check=order_check,
                )
            )
            return result
        response = self._order_send(request)
        result = self._result_from_response(response, order_check=order_check)
        self._write_management_log(
            self._close_log_payload(
                created_at,
                normalized_symbol,
                ticket,
                normalized_side,
                close_volume,
                reason,
                result,
                submitted=True,
                price=float(price),
                order_check=order_check,
            )
        )
        return result

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        """Converte ExecutionOrder em request MT5 e envia para conta demo."""
        retirement_check = self._retired_model_preflight(order)
        if retirement_check is not None:
            self._write_log(order, retirement_check)
            return retirement_check

        native_indicator_check = self._native_indicator_source_preflight(order)
        if native_indicator_check is not None:
            self._write_log(order, native_indicator_check)
            return native_indicator_check

        initialize_check = self._initialize_check()
        if initialize_check is not None:
            self._write_log(order, initialize_check)
            return initialize_check

        demo_check = self._demo_account_check()
        if demo_check is not None:
            self._write_log(order, demo_check)
            return demo_check

        symbol_check = self._ensure_symbol(order.symbol)
        if symbol_check is not None:
            self._write_log(order, symbol_check)
            return symbol_check

        duplicate_rejection = self._duplicate_plan_preflight(order)
        if duplicate_rejection is not None:
            self._write_log(order, duplicate_rejection)
            return duplicate_rejection
        position_rejection = self._open_position_model_limit_preflight(order)
        if position_rejection is not None:
            self._write_log(order, position_rejection)
            return position_rejection

        tick = self.mt5.symbol_info_tick(order.symbol)
        if tick is None:
            result = ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=f"Tick indisponivel para {order.symbol}.",
            )
            self._write_log(order, result)
            return result

        stop_target_rejection = self._stop_target_preflight(order, tick)
        if stop_target_rejection is not None:
            self._write_log(order, stop_target_rejection)
            return stop_target_rejection
        with _MT5_ORDER_SEND_LOCK:
            duplicate_rejection = self._duplicate_plan_preflight(order)
            if duplicate_rejection is not None:
                self._write_log(order, duplicate_rejection)
                return duplicate_rejection
            position_rejection = self._open_position_model_limit_preflight(order)
            if position_rejection is not None:
                self._write_log(order, position_rejection)
                return position_rejection
            tick = self.mt5.symbol_info_tick(order.symbol)
            if tick is None:
                result = ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=f"Tick indisponivel para {order.symbol}.",
                )
                self._write_log(order, result)
                return result
            stop_target_rejection = self._stop_target_preflight(order, tick)
            if stop_target_rejection is not None:
                self._write_log(order, stop_target_rejection)
                return stop_target_rejection
            request = self._request(order, tick)
            order_check = self._order_check(request)
            if order_check is not None and not self._order_check_passed(order_check):
                result = ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=self._order_check_message(order_check),
                    error_code=self._order_check_retcode(order_check),
                )
                self._write_log(order, result)
                return result
            pending_replacement = self._replace_pending_stop_order_locked(order)
            if pending_replacement is not None:
                self._write_log(order, pending_replacement)
                return pending_replacement
            try:
                response = self.mt5.order_send(request)
            except Exception as exc:  # noqa: BLE001 - ponte externa MT5
                response = _ExecutionSendException(exc)
            result = self._result_from_response(response, order_check=order_check)
            self._write_log(order, result)
            return result

    def apply_stop_management_from_signals(
        self,
        signals: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Aplica gestao de stop em posicoes demo abertas a partir do plano do Lab."""
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return [
                {
                    "status": "REJECTED",
                    "message": initialize_check.message,
                }
            ]
        demo_check = self._demo_account_check()
        if demo_check is not None:
            return [
                {
                    "status": "REJECTED",
                    "message": demo_check.message,
                }
            ]

        signal_by_symbol = {
            str(signal.get("symbol", "")).upper(): signal
            for signal in signals
            if signal.get("symbol")
        }
        results: list[dict[str, Any]] = []
        positions = self.mt5.positions_get() or []
        for position in positions:
            symbol = str(getattr(position, "symbol", "") or "").upper()
            signal = signal_by_symbol.get(symbol)
            if signal is None:
                continue
            update = self._managed_stop_update(position, signal)
            if update is None:
                continue
            response = self.mt5.order_send(update["request"])
            result = self._result_from_response(response)
            payload = {
                "timestamp": datetime.now().astimezone().isoformat(),
                "symbol": symbol,
                "ticket": update["ticket"],
                "policy": update["policy"],
                "old_stop": update["old_stop"],
                "new_stop": update["new_stop"],
                "target": update["target"],
                "accepted": result.accepted,
                "status": result.status,
                "message": result.message,
                "error_code": result.error_code,
            }
            self._write_management_log(payload)
            results.append(payload)
        return results

    def modify_demo_position_stop_loss(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        requested_stop: float,
        decision_key: str = "N/D",
    ) -> DynamicExitDemoSLExecutionResult:
        """Modifica somente SL de posicao existente em conta MT5 Demo."""
        created_at = datetime.now().astimezone().isoformat()
        normalized_symbol = str(symbol or "").upper()
        normalized_side = str(side or "").upper()
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                created_at=created_at,
                message=initialize_check.message,
                rejection_reasons=(initialize_check.message,),
            )
        demo_check = self._demo_account_check()
        if demo_check is not None:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                created_at=created_at,
                message=demo_check.message,
                rejection_reasons=(demo_check.message,),
            )
        symbol_check = self._ensure_symbol(normalized_symbol)
        if symbol_check is not None:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                created_at=created_at,
                message=symbol_check.message,
                rejection_reasons=(symbol_check.message,),
            )
        position = self._find_position(normalized_symbol, int(ticket or 0))
        if position is None:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                created_at=created_at,
                message="Posicao demo nao encontrada para ticket informado.",
                rejection_reasons=("Posicao demo nao encontrada.",),
            )
        position_side = self._position_side(position, {"decision": normalized_side})
        if normalized_side not in {"BUY", "SELL"} or position_side != normalized_side:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                created_at=created_at,
                message="Lado informado nao confere com posicao MT5.",
                rejection_reasons=("Lado da posicao nao confere.",),
            )
        current_stop = self._positive_float(getattr(position, "sl", None))
        if current_stop is None:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                created_at=created_at,
                message="Stop atual ausente na posicao MT5.",
                rejection_reasons=("Stop atual ausente.",),
            )
        target = self._positive_float(getattr(position, "tp", None)) or 0.0
        tick = self.mt5.symbol_info_tick(normalized_symbol)
        if tick is None:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                previous_stop=current_stop,
                created_at=created_at,
                message="Tick indisponivel para revalidar SL assistido.",
                rejection_reasons=("Tick indisponivel.",),
            )
        current_price = (
            self._positive_float(getattr(tick, "bid", None))
            if normalized_side == "BUY"
            else self._positive_float(getattr(tick, "ask", None))
        )
        if current_price is None:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                previous_stop=current_stop,
                created_at=created_at,
                message="Preco atual indisponivel para revalidar SL assistido.",
                rejection_reasons=("Preco atual ausente.",),
            )
        requested = self._positive_float(requested_stop)
        if requested is None:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested_stop,
                previous_stop=current_stop,
                created_at=created_at,
                message="SL solicitado invalido.",
                rejection_reasons=("SL solicitado invalido.",),
            )
        rejection_reasons = self._assisted_sl_rejections(
            normalized_side,
            requested,
            current_stop,
            current_price,
        )
        if rejection_reasons:
            return self._assisted_sl_result(
                symbol=normalized_symbol,
                ticket=ticket,
                side=normalized_side,
                requested_stop=requested,
                previous_stop=current_stop,
                created_at=created_at,
                message="Gate final MT5 rejeitou SL assistido.",
                rejection_reasons=tuple(rejection_reasons),
            )
        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "position": int(ticket),
            "symbol": normalized_symbol,
            "sl": float(requested),
            "tp": float(target),
            "magic": self.magic,
            "comment": "TraderIA PM SL",
        }
        response = self._order_send(request)
        result = self._result_from_response(response)
        payload = {
            "timestamp": created_at,
            "type": "ASSISTED_DYNAMIC_EXIT_SL",
            "symbol": normalized_symbol,
            "ticket": int(ticket),
            "side": normalized_side,
            "decision_key": decision_key,
            "old_stop": current_stop,
            "new_stop": requested,
            "target_preserved": target,
            "submitted": True,
            "success": result.accepted,
            "retcode": result.error_code,
            "message": result.message,
        }
        self._write_management_log(payload)
        return DynamicExitDemoSLExecutionResult(
            symbol=normalized_symbol,
            ticket=int(ticket),
            side=normalized_side,
            requested_stop=requested,
            previous_stop=current_stop,
            new_stop=requested if result.accepted else None,
            allowed=True,
            submitted=True,
            success=result.accepted,
            retcode=str(result.error_code or "DONE"),
            message=result.message,
            rejection_reasons=(),
            created_at=created_at,
        )

    def _managed_stop_update(
        self,
        position: object,
        signal: dict[str, Any],
    ) -> dict[str, Any] | None:
        policy = str(signal.get("stop_management") or "FIXED_STOP").upper()
        if policy not in {"BREAK_EVEN", "ATR_TRAILING_STOP"}:
            return None

        side = self._position_side(position, signal)
        entry = self._positive_float(getattr(position, "price_open", None))
        if entry is None:
            entry = self._positive_float(signal.get("entry"))
        current_stop = self._positive_float(getattr(position, "sl", None))
        if entry is None or current_stop is None:
            return None

        tick = self.mt5.symbol_info_tick(str(getattr(position, "symbol", "")))
        if tick is None:
            return None
        current_price = (
            self._positive_float(getattr(tick, "bid", None))
            if side == "BUY"
            else self._positive_float(getattr(tick, "ask", None))
        )
        if current_price is None:
            return None

        candidate_stop = (
            self._break_even_stop(side, entry, current_stop, current_price, signal)
            if policy == "BREAK_EVEN"
            else self._atr_trailing_stop(side, current_stop, current_price, signal)
        )
        if candidate_stop is None:
            return None
        if not self._is_better_stop(side, candidate_stop, current_stop):
            return None
        if not self._is_stop_before_market(side, candidate_stop, current_price):
            return None

        target = self._positive_float(getattr(position, "tp", None))
        if target is None:
            target = self._positive_float(signal.get("target")) or 0.0
        ticket = int(getattr(position, "ticket", 0) or 0)
        return {
            "ticket": ticket,
            "policy": policy,
            "old_stop": current_stop,
            "new_stop": candidate_stop,
            "target": target,
            "request": {
                "action": self.mt5.TRADE_ACTION_SLTP,
                "position": ticket,
                "symbol": str(getattr(position, "symbol", "")),
                "sl": float(candidate_stop),
                "tp": float(target),
                "magic": self.magic,
                "comment": f"TraderIA {policy}",
            },
        }

    def _break_even_stop(
        self,
        side: str,
        entry: float,
        current_stop: float,
        current_price: float,
        signal: dict[str, Any],
    ) -> float | None:
        parameters = signal.get("stop_management_parameters") or {}
        trigger_rr = self._positive_float(parameters.get("break_even_trigger_rr")) or 1.0
        offset_pips = self._non_negative_float(
            parameters.get("break_even_offset_pips")
        )
        pip = self._pip_size(str(signal.get("symbol") or ""))
        initial_risk = abs(entry - current_stop)
        if initial_risk <= 0.0:
            return None
        favorable_move = current_price - entry if side == "BUY" else entry - current_price
        if favorable_move < initial_risk * trigger_rr:
            return None
        offset = offset_pips * pip
        return entry + offset if side == "BUY" else entry - offset

    def _atr_trailing_stop(
        self,
        side: str,
        current_stop: float,
        current_price: float,
        signal: dict[str, Any],
    ) -> float | None:
        indicators = signal.get("market_indicators") or {}
        atr = self._positive_float(indicators.get("atr"))
        if atr is None:
            return None
        parameters = signal.get("stop_management_parameters") or {}
        factor = self._positive_float(parameters.get("atr_trailing_factor")) or 2.0
        if side == "BUY":
            return current_price - atr * factor
        return current_price + atr * factor

    def _position_side(self, position: object, signal: dict[str, Any]) -> str:
        buy_type = getattr(self.mt5, "POSITION_TYPE_BUY", 0)
        sell_type = getattr(self.mt5, "POSITION_TYPE_SELL", 1)
        position_type = getattr(position, "type", None)
        if position_type == buy_type:
            return "BUY"
        if position_type == sell_type:
            return "SELL"
        decision = str(signal.get("decision") or "BUY").upper()
        return "SELL" if decision == "SELL" else "BUY"

    def _is_better_stop(self, side: str, candidate: float, current: float) -> bool:
        epsilon = 1e-10
        if side == "BUY":
            return candidate > current + epsilon
        return candidate < current - epsilon

    def _is_stop_before_market(
        self,
        side: str,
        candidate: float,
        current_price: float,
    ) -> bool:
        if side == "BUY":
            return candidate < current_price
        return candidate > current_price

    def _find_position(self, symbol: str, ticket: int) -> object | None:
        if ticket <= 0:
            return None
        positions = self.mt5.positions_get(symbol=symbol) or []
        for position in positions:
            if int(getattr(position, "ticket", 0) or 0) == int(ticket):
                return position
        return None

    def _assisted_sl_rejections(
        self,
        side: str,
        requested_stop: float,
        current_stop: float,
        current_price: float,
    ) -> list[str]:
        reasons: list[str] = []
        if not self._is_better_stop(side, requested_stop, current_stop):
            reasons.append("SL solicitado nao melhora o risco.")
        if not self._is_stop_before_market(side, requested_stop, current_price):
            reasons.append("SL solicitado cruza ou encosta no preco atual.")
        if abs(float(requested_stop) - float(current_stop)) < 0.00001:
            reasons.append("Diferenca de SL irrelevante.")
        return reasons

    def _assisted_sl_result(
        self,
        *,
        symbol: str,
        ticket: int | None,
        side: str,
        requested_stop: float | None,
        created_at: str,
        message: str,
        rejection_reasons: tuple[str, ...],
        previous_stop: float | None = None,
    ) -> DynamicExitDemoSLExecutionResult:
        result = DynamicExitDemoSLExecutionResult(
            symbol=symbol,
            ticket=ticket,
            side=side,
            requested_stop=requested_stop,
            previous_stop=previous_stop,
            allowed=False,
            submitted=False,
            success=False,
            retcode="REJECTED",
            message=message,
            rejection_reasons=rejection_reasons,
            created_at=created_at,
        )
        self._write_management_log(
            {
                "timestamp": created_at,
                "type": "ASSISTED_DYNAMIC_EXIT_SL",
                "symbol": symbol,
                "ticket": ticket,
                "side": side,
                "requested_stop": requested_stop,
                "submitted": False,
                "success": False,
                "message": message,
                "rejection_reasons": list(rejection_reasons),
            }
        )
        return result

    def _close_log_payload(
        self,
        timestamp: str,
        symbol: str,
        ticket: int | None,
        side: str,
        volume: float,
        reason: str,
        result: ExecutionResult,
        *,
        submitted: bool,
        price: float | None = None,
        order_check: object | None = None,
    ) -> dict[str, Any]:
        return {
            "timestamp": timestamp,
            "type": "POSITION_MANAGER_CLOSE",
            "symbol": symbol,
            "ticket": ticket,
            "side": side,
            "volume": volume,
            "reason": reason,
            "submitted": submitted,
            "success": result.accepted,
            "status": result.status,
            "message": result.message,
            "price": price,
            "error_code": result.error_code,
            "order_check_retcode": self._order_check_retcode(order_check),
            "order_check_comment": self._order_check_comment(order_check),
            "mt5_last_error": self._last_error_payload(),
        }

    def _positive_float(self, value: object) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if parsed <= 0.0:
            return None
        return parsed

    def _candle_value(self, candle: object, key: str) -> float | None:
        if isinstance(candle, dict):
            return self._positive_float(candle.get(key))
        try:
            value = candle[key]  # type: ignore[index]
        except (KeyError, IndexError, TypeError):
            value = getattr(candle, key, None)
        return self._positive_float(value)

    def _non_negative_float(self, value: object) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(parsed, 0.0)

    def _pip_size(self, symbol: str) -> float:
        return 0.01 if str(symbol).upper().endswith("JPY") else 0.0001

    def _initialize_check(self) -> ExecutionResult | None:
        terminal_info = getattr(self.mt5, "terminal_info", None)
        account_info = getattr(self.mt5, "account_info", None)
        if callable(terminal_info) and callable(account_info):
            try:
                terminal = terminal_info()
                account = account_info()
            except (OSError, RuntimeError, ValueError, TypeError):
                terminal = None
                account = None
            if (
                terminal is not None
                and account is not None
                and getattr(terminal, "connected", None) is True
            ):
                return None
        initialize = getattr(self.mt5, "initialize", None)
        terminal_path = resolve_mt5_terminal_path(os.getenv("MT5_PATH"))
        arguments = {"path": terminal_path} if terminal_path else {}
        initialized = True
        if callable(initialize):
            try:
                initialized = bool(initialize(**arguments))
            except TypeError:
                initialized = bool(initialize())
        if not initialized:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="MT5 initialize() falhou para execucao demo.",
            )
        return None

    def _demo_account_check(self) -> ExecutionResult | None:
        account = self.mt5.account_info()
        if account is None:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Conta MT5 indisponivel.",
            )
        demo_mode = getattr(self.mt5, "ACCOUNT_TRADE_MODE_DEMO", None)
        trade_mode = getattr(account, "trade_mode", None)
        if demo_mode is not None and trade_mode != demo_mode:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Execucao bloqueada: conta MT5 nao e demo.",
            )
        return None

    def _ensure_symbol(self, symbol: str) -> ExecutionResult | None:
        info = self.mt5.symbol_info(symbol)
        if info is None:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=f"Simbolo {symbol} indisponivel no MT5.",
            )
        if not bool(getattr(info, "visible", True)):
            if not bool(self.mt5.symbol_select(symbol, True)):
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=f"Simbolo {symbol} nao pode ser selecionado.",
                )
        return None

    def _request(self, order: ExecutionOrder, tick: object) -> dict[str, object]:
        side = order.side.upper()
        if self._is_pending_stop_order(order):
            order_type = (
                self.mt5.ORDER_TYPE_BUY_STOP
                if side == "BUY"
                else self.mt5.ORDER_TYPE_SELL_STOP
            )
            request: dict[str, object] = {
                "action": self.mt5.TRADE_ACTION_PENDING,
                "symbol": order.symbol,
                "volume": float(order.quantity),
                "type": order_type,
                "price": float(order.entry_price),
                "sl": float(order.stop),
                "tp": 0.0 if self._is_no_target_model(order) else float(order.target),
                "deviation": self.deviation,
                "magic": self.magic,
                "comment": self._order_comment(order),
                "type_time": self.mt5.ORDER_TIME_GTC,
                "type_filling": getattr(
                    self.mt5,
                    "ORDER_FILLING_RETURN",
                    self.mt5.ORDER_FILLING_IOC,
                ),
            }
            expiration = self._pending_stop_expiration(order)
            specified = getattr(self.mt5, "ORDER_TIME_SPECIFIED", None)
            if expiration is not None and specified is not None:
                request["type_time"] = specified
                request["expiration"] = expiration
            return request
        order_type = (
            self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL
        )
        price = float(getattr(tick, "ask") if side == "BUY" else getattr(tick, "bid"))
        return {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": order.symbol,
            "volume": float(order.quantity),
            "type": order_type,
            "price": price,
            "sl": float(order.stop),
            "tp": 0.0 if self._is_no_target_model(order) else float(order.target),
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": self._order_comment(order),
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

    def _stop_target_preflight(
        self,
        order: ExecutionOrder,
        tick: object,
    ) -> ExecutionResult | None:
        """Rejeita plano stale antes do MT5 retornar Invalid stops."""
        side = str(order.side or "").upper()
        bid = self._positive_float(getattr(tick, "bid", None))
        ask = self._positive_float(getattr(tick, "ask", None))
        price = ask if side == "BUY" else bid
        stop = self._positive_float(getattr(order, "stop", None))
        target = self._positive_float(getattr(order, "target", None))
        if price is None:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=f"Preco executavel indisponivel para {order.symbol}.",
            )
        no_target = self._is_no_target_model(order)
        if stop is None or (target is None and not no_target):
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Stop Loss e Take Profit invalidos para envio MT5 Demo.",
            )
        if self._is_pending_stop_order(order):
            model_label = self._order_comment(order)
            entry = self._positive_float(getattr(order, "entry_price", None))
            expiration = self._pending_stop_expiration(order)
            server_now = self._positive_float(getattr(tick, "time", None))
            comparison_time = int(server_now if server_now is not None else time.time())
            if expiration is not None and expiration <= comparison_time + 1:
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=f"{model_label}: candle M5 expirou antes do envio da ordem pendente.",
                )
            if entry is None or bid is None or ask is None:
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=f"{model_label}: preco de gatilho indisponivel para ordem pendente.",
                )
            minimum_distance = self._minimum_stop_distance(order.symbol)
            if side == "BUY" and not (
                entry > ask and stop < entry and (entry - ask) >= minimum_distance
            ):
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=(
                        f"{model_label} BUY STOP invalida ou ja rompida: gatilho deve estar "
                        "acima do ask e o SL abaixo da entrada."
                    ),
                    executed_price=ask,
                )
            if side == "SELL" and not (
                entry < bid and entry < stop and (bid - entry) >= minimum_distance
            ):
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=(
                        f"{model_label} SELL STOP invalida ou ja rompida: gatilho deve estar "
                        "abaixo do bid e o SL acima da entrada."
                    ),
                    executed_price=bid,
                )
            if side not in {"BUY", "SELL"}:
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=f"Direcao invalida para ordem pendente {model_label}.",
                )
            return None
        if side == "BUY" and (
            bid is None
            or ask is None
            or not (stop < bid)
            or (not no_target and not (ask < float(target)))
        ):
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=(
                    "Plano MT5 Demo stale: preco atual tornou SL/TP invalidos "
                    f"para BUY (SL {stop:.6f} < bid {bid or 0.0:.6f}; "
                    f"ask {ask or 0.0:.6f} < TP {float(target or 0.0):.6f})."
                ),
                executed_price=price,
            )
        if side == "SELL" and (
            bid is None
            or ask is None
            or not (ask < stop)
            or (not no_target and not (float(target) < bid))
        ):
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=(
                    "Plano MT5 Demo stale: preco atual tornou SL/TP invalidos "
                    f"para SELL (TP {float(target or 0.0):.6f} < bid {bid or 0.0:.6f}; "
                    f"ask {ask or 0.0:.6f} < SL {stop:.6f})."
                ),
                executed_price=price,
            )
        if side not in {"BUY", "SELL"}:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Direcao invalida para envio MT5 Demo.",
            )
        minimum_distance = self._minimum_stop_distance(order.symbol)
        if minimum_distance > 0.0:
            stop_distance = abs(float(price) - float(stop))
            target_distance = (
                abs(float(target) - float(price))
                if target is not None and not no_target
                else minimum_distance
            )
            if stop_distance < minimum_distance or (
                not no_target and target_distance < minimum_distance
            ):
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=(
                        "Plano MT5 Demo rejeitado antes do envio: SL/TP abaixo da "
                        f"distancia minima do broker para {order.symbol} "
                        f"(min {minimum_distance:.6f}; "
                        f"dist SL {stop_distance:.6f}; dist TP {target_distance:.6f})."
                    ),
                    executed_price=price,
                )
        return None

    def _is_no_target_model(self, order: ExecutionOrder) -> bool:
        snapshot = dict(getattr(order, "plan_snapshot", None) or {})
        parameters = dict(snapshot.get("stop_management_parameters") or {})
        if is_model24(getattr(order, "operational_model", "")):
            return True
        if (
            is_model23(getattr(order, "operational_model", ""))
            and bool(parameters.get("m23_structural_target_enabled"))
            and self._positive_float(getattr(order, "target", None)) is not None
        ):
            return False
        model = self._effective_operational_model(order)
        return self._model_uses_no_target(model, self._entry_order_type(order))

    @staticmethod
    def _model_uses_no_target(model: str, entry_order_type: object) -> bool:
        if model in XAU_IMPROVED_REENTRY_MODEL_IDS:
            return not xau_model_requires_target(model, entry_order_type)
        return model in {
            MODEL_3_ID,
            MODEL_8_ID,
            MODEL_15_ID,
            MODEL_16_ID,
            *XAU_TREND_FILTER_MODEL_IDS,
            *FOREX_SMA_RSI_MODEL_IDS,
        }

    @staticmethod
    def _entry_order_type(order: ExecutionOrder) -> str:
        snapshot = dict(getattr(order, "plan_snapshot", None) or {})
        parameters = dict(snapshot.get("stop_management_parameters") or {})
        return str(parameters.get("active_entry_order_type") or "").upper()

    @staticmethod
    def _source_operational_model(order: ExecutionOrder) -> str:
        snapshot = dict(getattr(order, "plan_snapshot", None) or {})
        parameters = dict(snapshot.get("stop_management_parameters") or {})
        return str(parameters.get("source_operational_model") or "").upper()

    def _effective_operational_model(self, order: ExecutionOrder) -> str:
        model = str(getattr(order, "operational_model", "") or "").upper()
        if not _is_basket_model(model):
            return model
        return self._source_operational_model(order) or model

    def _is_pending_stop_order(self, order: ExecutionOrder) -> bool:
        model = self._effective_operational_model(order)
        if model in {MODEL_15_ID, MODEL_16_ID}:
            return True
        if model not in {
            MODEL_8_ID,
            *XAU_TREND_FILTER_MODEL_IDS,
            *FOREX_SMA_RSI_MODEL_IDS,
        }:
            return False
        return self._entry_order_type(order) in {
            "BUY_STOP",
            "SELL_STOP",
        }

    def _pending_stop_expiration(self, order: ExecutionOrder) -> int | None:
        # O terminal valida a expiracao no relogio do servidor da corretora.
        # O candle MT5 ja carrega esse relogio; usar o UTC da maquina produz
        # "Invalid expiration" quando o servidor opera com outro deslocamento.
        snapshot = dict(getattr(order, "plan_snapshot", None) or {})
        raw = str(snapshot.get("candle_time") or "").strip()
        if not raw or raw.upper() == "N/D":
            return None
        try:
            candle_time = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
        # ``candle_time`` e a abertura do ultimo candle fechado. Quando o plano
        # nasce, o candle seguinte ja esta em formacao; portanto, a pendencia
        # deve permanecer valida ate o fechamento desse candle corrente. Somar
        # apenas cinco minutos fazia a ordem nascer expirada no primeiro ciclo.
        # Se nao executar, o proximo plano remove a pendencia e publica o novo
        # extremo fechado com SL/TP recalculados.
        return int((candle_time + timedelta(minutes=10)).timestamp())

    def _replace_pending_stop_order_locked(
        self,
        order: ExecutionOrder,
    ) -> ExecutionResult | None:
        """Substitui apenas a pendencia anterior do mesmo modelo operacional."""
        if not self._is_pending_stop_order(order):
            return None
        orders_get = getattr(self.mt5, "orders_get", None)
        if not callable(orders_get):
            return None
        try:
            pending_orders = list(orders_get(symbol=order.symbol) or [])
        except Exception as exc:  # noqa: BLE001 - ponte externa MT5
            return ExecutionResult(
                accepted=False,
                status="ERROR",
                message=f"{self._order_comment(order)} nao conseguiu auditar ordens pendentes: {exc}",
            )
        expected_comment = self._order_comment(order).upper()
        pending_types = {
            value
            for value in (
                getattr(self.mt5, "ORDER_TYPE_BUY_STOP", None),
                getattr(self.mt5, "ORDER_TYPE_SELL_STOP", None),
            )
            if value is not None
        }
        for pending in pending_orders:
            if str(getattr(pending, "comment", "") or "").upper() != expected_comment:
                continue
            if getattr(pending, "type", None) not in pending_types:
                continue
            ticket = int(getattr(pending, "ticket", 0) or 0)
            if ticket <= 0:
                continue
            response = self.mt5.order_send(
                {
                    "action": self.mt5.TRADE_ACTION_REMOVE,
                    "order": ticket,
                    "symbol": order.symbol,
                    "comment": f"{self._order_comment(order)} replace",
                }
            )
            result = self._result_from_response(response)
            if not result.accepted:
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=(
                        f"{self._order_comment(order)} nao substituiu a ordem pendente anterior: "
                        f"{result.message}"
                    ),
                    error_code=result.error_code,
                )
        return None

    def _minimum_stop_distance(self, symbol: str) -> float:
        """Distancia minima exigida pelo broker para SL/TP no preco atual."""
        try:
            info = self.mt5.symbol_info(symbol)
        except Exception:  # noqa: BLE001 - ponte externa MT5
            return 0.0
        if info is None:
            return 0.0
        point = self._positive_float(getattr(info, "point", None))
        if point is None:
            digits = getattr(info, "digits", None)
            try:
                point = 10 ** (-int(digits))
            except (TypeError, ValueError):
                point = self._pip_size(symbol)
        stops_level = self._non_negative_float(getattr(info, "trade_stops_level", 0))
        freeze_level = self._non_negative_float(getattr(info, "trade_freeze_level", 0))
        return float(max(stops_level, freeze_level) * point)

    def _duplicate_plan_preflight(
        self,
        order: ExecutionOrder,
    ) -> ExecutionResult | None:
        """Bloqueia reenvio do mesmo plano no mesmo candle/identidade do Lab."""
        current_identity = str(getattr(order, "plan_identity", "") or "").strip()
        if not current_identity or current_identity.upper() == "N/D":
            return None
        current_key = self._execution_plan_key(order)
        if current_key is None:
            return None
        current_snapshot = dict(getattr(order, "plan_snapshot", None) or {})
        current_candle = str(current_snapshot.get("candle_time") or "").strip()
        current_model = str(
            getattr(order, "operational_model", "")
            or current_snapshot.get("operational_model", "")
        ).upper()
        for record in self._read_execution_log_records():
            if not self._record_counts_as_plan_evaluation(record):
                continue
            record_identity = str(record.get("plan_identity") or "").strip()
            if self._record_plan_key(record) != current_key:
                continue
            record_snapshot = dict(record.get("plan_snapshot") or {})
            record_model = str(
                record.get("operational_model")
                or record_snapshot.get("operational_model", "")
            ).upper()
            if current_model != record_model and (
                _is_basket_model(current_model) != _is_basket_model(record_model)
            ):
                # A carteira M23 e independente da carteira do modelo-fonte.
                # Quando ambas estao selecionadas, o mesmo sinal deve gerar uma
                # ordem em cada carteira; a defesa de duplicidade continua
                # valendo dentro de cada uma delas.
                continue
            if (
                current_model != record_model
                and _is_basket_model(current_model)
                and _is_basket_model(record_model)
            ):
                # Cada fonte ativa pode contribuir uma posicao M23 por par.
                continue
            if (
                current_model != record_model
                and current_model in INDEPENDENT_SMA_RSI_MODEL_IDS
                and record_model in INDEPENDENT_SMA_RSI_MODEL_IDS
            ):
                # M8-M17 sao modelos operacionais independentes. Mesmo quando
                # compartilham candle, entrada e stop, cada modelo precisa de
                # sua propria posicao para permitir auditoria A-E separada.
                continue
            if (
                current_model != record_model
                and (
                    is_dynamic_exit_operational_model(current_model)
                    or is_dynamic_exit_operational_model(record_model)
                )
            ):
                # A familia M8-M14 e um experimento operacional independente:
                # repete a entrada da origem para comparar apenas a saida.
                continue
            record_candle = str(record_snapshot.get("candle_time") or "").strip()
            same_identity = bool(
                record_identity
                and record_identity.upper() != "N/D"
                and record_identity == current_identity
            )
            same_executable_candle = bool(
                current_candle
                and record_candle
                and current_candle == record_candle
            )
            if self._is_pending_stop_order(order) and not same_executable_candle:
                # A identidade estrategica permanece igual durante a correcao,
                # mas cada candle fechado atualiza o gatilho da ordem pendente.
                same_identity = False
            if not same_identity and not same_executable_candle:
                continue
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=(
                    "Plano operacional duplicado bloqueado: mesmo par, direcao, "
                    "entrada, stop, alvo e candle/plano do Lab ja foram avaliados. "
                    "Aguarde novo candle ou novo plano valido do Research Lab."
                ),
            )
        return None

    def _retired_model_preflight(
        self,
        order: ExecutionOrder,
    ) -> ExecutionResult | None:
        """Defesa final para IDs historicos realmente aposentados."""
        model = getattr(order, "operational_model", "")
        if not is_retired_operational_model(model):
            return None
        return ExecutionResult(
            accepted=False,
            status="REJECTED",
            message=(
                "Modelo operacional aposentado nao pode abrir novas ordens; "
                "historico e posicoes existentes foram preservados."
            ),
        )

    def _open_position_model_limit_preflight(
        self,
        order: ExecutionOrder,
    ) -> ExecutionResult | None:
        """Aplica somente o teto tecnico de posicoes e bloqueia origem desconhecida."""
        positions = list(self.mt5.positions_get(symbol=order.symbol) or [])
        is_basket = _is_basket_model(getattr(order, "operational_model", ""))
        limit = (
            MAX_MODEL23_POSITIONS_PER_SYMBOL
            if is_basket
            else MAX_OPERATIONAL_MODELS_PER_SYMBOL
        )
        if len(positions) >= limit:
            limit_message = (
                "Limite tecnico de 64 posicoes M23 por par atingido."
                if is_basket
                else (
                    "Limite de vinte e duas posicoes por par atingido. "
                    "Permitido no maximo um por modelo operacional."
                )
            )
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=limit_message,
            )
        if is_basket:
            for position in positions:
                comment = str(getattr(position, "comment", "") or "").upper()
                if "TRADERIA" in comment and not (
                    KNOWN_MODEL_COMMENTS & set(comment.split())
                ):
                    return ExecutionResult(
                        accepted=False,
                        status="REJECTED",
                        message="Posicao TraderIA sem modelo identificado exige auditoria.",
                    )
            return None
        expected = self._model_comment(getattr(order, "operational_model", ""))
        for position in positions:
            comment = str(getattr(position, "comment", "") or "").upper()
            if expected in comment.split():
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=(
                        "Ja existe uma posicao aberta para este simbolo neste modelo."
                    ),
                )
            if "TRADERIA" in comment and not (
                KNOWN_MODEL_COMMENTS & set(comment.split())
            ):
                return ExecutionResult(
                    accepted=False,
                    status="REJECTED",
                    message=(
                        "Posicao TraderIA legada sem modelo identificado bloqueia "
                        "nova entrada ate auditoria manual."
                    ),
                )
        return None

    def _record_counts_as_plan_evaluation(self, record: dict[str, Any]) -> bool:
        """Duplicidade de plano so nasce de ordem aceita pelo MT5."""
        return bool(record.get("accepted", False))

    @staticmethod
    def _compact_execution_log_record(record: dict[str, Any]) -> dict[str, Any]:
        """Mantem no cache apenas os campos usados pela defesa de duplicidade."""
        snapshot_value = record.get("plan_snapshot")
        snapshot = snapshot_value if isinstance(snapshot_value, dict) else {}
        parameters_value = snapshot.get("stop_management_parameters")
        parameters = parameters_value if isinstance(parameters_value, dict) else {}
        return {
            "accepted": bool(record.get("accepted", False)),
            "plan_identity": record.get("plan_identity"),
            "operational_model": record.get("operational_model"),
            "symbol": record.get("symbol"),
            "side": record.get("side"),
            "entry_price": record.get("entry_price"),
            "stop": record.get("stop"),
            "target": record.get("target"),
            "plan_snapshot": {
                "candle_time": snapshot.get("candle_time"),
                "operational_model": snapshot.get("operational_model"),
                "stop_management_parameters": {
                    "active_entry_order_type": parameters.get(
                        "active_entry_order_type"
                    ),
                    "source_operational_model": parameters.get(
                        "source_operational_model"
                    ),
                },
            },
        }

    def _read_execution_log_records(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        try:
            stat = self.log_path.stat()
            signature = (int(stat.st_mtime_ns), int(stat.st_size))
        except OSError:
            return []
        if (
            self.execution_log_cache is not None
            and self.execution_log_cache_signature == signature
        ):
            return self.execution_log_cache
        try:
            lines = read_last_text_lines(self.log_path, limit=2000)
        except OSError:
            return []
        records: list[dict[str, Any]] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(self._compact_execution_log_record(payload))
        self.execution_log_cache = records
        self.execution_log_cache_signature = signature
        return records

    def _execution_plan_key(
        self,
        order: ExecutionOrder,
    ) -> tuple[str, str, float, float, float] | None:
        entry = self._positive_float(getattr(order, "entry_price", None))
        stop = self._positive_float(getattr(order, "stop", None))
        target = (
            0.0
            if self._is_no_target_model(order)
            else self._positive_float(getattr(order, "target", None))
        )
        if entry is None or stop is None or target is None:
            return None
        return (
            str(order.symbol or "").upper(),
            str(order.side or "").upper(),
            round(float(entry), 6),
            round(float(stop), 6),
            round(float(target), 6),
        )

    def _record_plan_key(
        self,
        record: dict[str, Any],
    ) -> tuple[str, str, float, float, float] | None:
        entry = self._positive_float(record.get("entry_price"))
        stop = self._positive_float(record.get("stop"))
        record_model = str(record.get("operational_model") or "").upper()
        record_snapshot = dict(record.get("plan_snapshot") or {})
        record_parameters = dict(
            record_snapshot.get("stop_management_parameters") or {}
        )
        effective_model = (
            str(record_parameters.get("source_operational_model") or "").upper()
            if _is_basket_model(record_model)
            else record_model
        ) or record_model
        record_uses_no_target = is_model24(record_model) or self._model_uses_no_target(
            effective_model,
            record_parameters.get("active_entry_order_type"),
        )
        target = (
            0.0
            if record_uses_no_target
            else self._positive_float(record.get("target"))
        )
        if entry is None or stop is None or target is None:
            return None
        return (
            str(record.get("symbol") or "").upper(),
            str(record.get("side") or "").upper(),
            round(float(entry), 6),
            round(float(stop), 6),
            round(float(target), 6),
        )

    def _order_send(self, request: dict[str, object]) -> object | None:
        try:
            with _MT5_ORDER_SEND_LOCK:
                return self.mt5.order_send(request)
        except Exception as exc:  # noqa: BLE001 - ponte externa MT5
            return _ExecutionSendException(exc)

    def _order_check(self, request: dict[str, object]) -> object | None:
        order_check = getattr(self.mt5, "order_check", None)
        if not callable(order_check):
            return None
        try:
            return order_check(request)
        except Exception:  # noqa: BLE001 - ponte externa MT5
            return None

    def _order_check_passed(self, check: object) -> bool:
        retcode = self._order_check_retcode(check)
        if retcode is None:
            return False
        return int(retcode) == 0 or int(retcode) in self._success_retcodes()

    def _order_check_message(self, check: object) -> str:
        comment = self._order_check_comment(check)
        retcode = self._order_check_retcode(check)
        if comment:
            return f"MT5 order_check rejeitou fechamento: {comment} (retcode={retcode})."
        return f"MT5 order_check rejeitou fechamento (retcode={retcode})."

    def _order_check_retcode(self, check: object | None) -> int | None:
        if check is None:
            return None
        value = getattr(check, "retcode", None)
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def _order_check_comment(self, check: object | None) -> str | None:
        if check is None:
            return None
        comment = str(getattr(check, "comment", "") or "").strip()
        return comment or None

    def _last_error_payload(self) -> object:
        last_error = getattr(self.mt5, "last_error", None)
        if not callable(last_error):
            return None
        try:
            return last_error()
        except Exception:  # noqa: BLE001 - ponte externa MT5
            return None

    def _last_error_message(self) -> str:
        error = self._last_error_payload()
        if error in (None, ""):
            return "last_error indisponivel"
        return str(error)

    def _last_error_code(self) -> int | None:
        error = self._last_error_payload()
        if isinstance(error, (tuple, list)) and error:
            try:
                return int(error[0])
            except (TypeError, ValueError):
                return None
        return None

    def _success_retcodes(self) -> set[int]:
        codes: set[int] = set()
        for name in ("TRADE_RETCODE_DONE", "TRADE_RETCODE_DONE_PARTIAL"):
            value = getattr(self.mt5, name, None)
            if value is None:
                continue
            try:
                codes.add(int(value))
            except (TypeError, ValueError):
                continue
        return codes

    def _result_from_response(
        self,
        response: object,
        *,
        order_check: object | None = None,
    ) -> ExecutionResult:
        if isinstance(response, _ExecutionSendException):
            return ExecutionResult(
                accepted=False,
                status="ERROR",
                message=f"Falha ao chamar MT5 order_send: {response.error}",
                error_code=self._last_error_code(),
            )
        if response is None:
            check_comment = self._order_check_comment(order_check)
            check_retcode = self._order_check_retcode(order_check)
            check_detail = (
                f"; order_check={check_comment} retcode={check_retcode}"
                if order_check is not None
                else ""
            )
            return ExecutionResult(
                accepted=False,
                status="ERROR",
                message=(
                    "MT5 retornou resposta vazia ao enviar ordem "
                    f"({self._last_error_message()}{check_detail})."
                ),
                error_code=self._last_error_code(),
            )
        retcode = int(getattr(response, "retcode", -1))
        done = retcode in self._success_retcodes()
        return ExecutionResult(
            accepted=done,
            status="ACCEPTED" if done else "REJECTED",
            message=str(getattr(response, "comment", "")) or self._message(done),
            ticket=self._ticket(response),
            executed_price=self._executed_price(response),
            error_code=None if done else retcode,
        )

    def _native_indicator_source_preflight(
        self,
        order: ExecutionOrder,
    ) -> ExecutionResult | None:
        """M8-M17 so entram com indicadores nativos do mesmo candle M5."""
        model = str(getattr(order, "operational_model", "") or "").upper()
        snapshot = dict(getattr(order, "plan_snapshot", None) or {})
        parameters = dict(snapshot.get("stop_management_parameters") or {})
        if _is_basket_model(model):
            # M23 nao cria sinal proprio: preserva o gate nativo do modelo que
            # originou a entrada, sem copiar seu SL ou TP.
            model = str(parameters.get("source_operational_model") or "").upper()
        native_models = {
            MODEL_8_ID,
            *XAU_TREND_FILTER_MODEL_IDS,
            *FOREX_SMA_RSI_MODEL_IDS,
        }
        if model not in native_models:
            return None
        source = str(
            snapshot.get("indicator_source")
            or parameters.get("indicator_source")
            or ""
        ).upper()
        indicator_candle = str(
            snapshot.get("indicator_closed_candle_time")
            or parameters.get("indicator_closed_candle_time")
            or ""
        ).strip()
        plan_candle = str(snapshot.get("candle_time") or "").strip()
        if (
            source in {
                "MT5_NATIVE",
                "LOCAL_MT5_CLOSED_CANDLES_200",
                "LOCAL_MT5_CANDLES_52",
            }
            and indicator_candle
            and indicator_candle == plan_candle
        ):
            return None
        return ExecutionResult(
            accepted=False,
            status="REJECTED",
            message=(
                "Modelos M5 bloqueados: indicadores devem usar a janela "
                "deslizante de 200 velas fechadas (ou snapshot MT5 nativo) e "
                "pertencer ao mesmo candle M5 fechado do Trade Plan."
            ),
        )

    def _ticket(self, response: object) -> int | None:
        for name in ("order", "deal"):
            value = getattr(response, name, None)
            if value:
                return int(value)
        return None

    def _executed_price(self, response: object) -> float | None:
        value = getattr(response, "price", None)
        if value is None:
            return None
        return float(value)

    def _message(self, accepted: bool) -> str:
        if accepted:
            return "Ordem demo aceita pelo MT5."
        return "Ordem demo rejeitada pelo MT5."

    def _write_log(
        self,
        order: ExecutionOrder,
        result: ExecutionResult,
    ) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "symbol": order.symbol,
            "side": order.side,
            "quantity": order.quantity,
            "entry_price": order.entry_price,
            "stop": order.stop,
            "target": order.target,
            "accepted": result.accepted,
            "status": result.status,
            "message": result.message,
            "ticket": result.ticket,
            "executed_price": result.executed_price,
            "error_code": result.error_code,
            "plan_identity": getattr(order, "plan_identity", "N/D"),
            "entry_setup": getattr(order, "entry_setup", "N/D"),
            "exit_setup": getattr(order, "exit_setup", "DYNAMIC_POSITION_MANAGER"),
            "exit_policy": getattr(order, "exit_policy", "DYNAMIC_POSITION_MANAGER"),
            "alpha_id": getattr(order, "alpha_id", "ALPHA001"),
            "alpha_version": getattr(order, "alpha_version", "v1"),
            "beta_id": getattr(order, "beta_id", "BETA001"),
            "beta_version": getattr(order, "beta_version", "BETA v1"),
            "beta_mode": getattr(order, "beta_mode", "PROTECT_ONLY"),
            "operational_model": getattr(
                order,
                "operational_model",
                "MODELO_1_ALPHA_ATUAL",
            ),
            "plan_snapshot": getattr(order, "plan_snapshot", None) or {},
        }
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")
        if self.execution_log_cache is not None:
            self.execution_log_cache.append(
                self._compact_execution_log_record(payload)
            )
            if len(self.execution_log_cache) > 2000:
                del self.execution_log_cache[:-2000]
            try:
                stat = self.log_path.stat()
                self.execution_log_cache_signature = (
                    int(stat.st_mtime_ns),
                    int(stat.st_size),
                )
            except OSError:
                self.execution_log_cache_signature = None

    def _order_comment(self, order: ExecutionOrder) -> str:
        if is_model24(getattr(order, "operational_model", "")):
            return model24_order_comment(getattr(order, "operational_model", ""))
        if is_model23(getattr(order, "operational_model", "")):
            return model23_order_comment(getattr(order, "operational_model", ""))
        return f"TraderIA {self._model_comment(getattr(order, 'operational_model', ''))}"

    def _model_comment(self, operational_model: object) -> str:
        model = str(operational_model or "").upper()
        match = re.search(r"(?:MODELO[_ ]?|^M)(\d{1,2})(?:_|\b)", model)
        if match is not None:
            number = int(match.group(1))
            if 1 <= number <= 24:
                return f"M{number}"
        if model in {
            "MODELO_2_ESPELHO_BETA2_RR1",
            "MODELO_2_LAB_ALPHA_SUGERIDA_1_PLUS",
        }:
            return "M2"
        if model in {
            "MODELO_3_RR3",
            "MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS",
        }:
            return "M3"
        if model in {
            "MODELO_4_ESPELHO_M1",
            "MODELO_4_LAB_CONTEXTUAL_MTF",
        }:
            return "M4"
        if model in {
            "MODELO_5_PESQUISA_CONSOLIDADO",
            "MODELO_5_PRICE_ACTION",
            "MODELO_5_LAB_CONSOLIDADO",
        }:
            return "M5"
        if model in {
            "MODELO_6_TREND_MOMENTUM_ORIGINAL",
            "MODELO_6_ESPELHO_M5",
        }:
            return "M6"
        if model == "MODELO_7_TREND_MOMENTUM_DYNAMIC":
            return "M7"
        if model == "MODELO_8_TREND_PULLBACK_H1_M5":
            return "M8"
        if model == "MODELO_9_TREND_PULLBACK_M15_M1":
            return "M9"
        if model == "MODELO_10_TREND_PULLBACK_D1_M15":
            return "M10"
        return "M1"

    def _write_management_log(self, payload: dict[str, Any]) -> None:
        self.management_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.management_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")
