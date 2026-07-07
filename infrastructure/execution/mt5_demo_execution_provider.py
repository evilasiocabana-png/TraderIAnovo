"""Adaptador exclusivo para envio de ordens em conta demo do MetaTrader 5."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.contracts.dynamic_exit_demo_sl import DynamicExitDemoSLExecutionResult


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

    def __post_init__(self) -> None:
        if self.mt5 is None:
            self.mt5 = importlib.import_module("MetaTrader5")

    def has_open_position(self, symbol: str) -> bool:
        """Consulta posicoes abertas para impedir duplicidade por simbolo."""
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return True
        positions = self.mt5.positions_get(symbol=symbol)
        return bool(positions)

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        """Converte ExecutionOrder em request MT5 e envia para conta demo."""
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

        tick = self.mt5.symbol_info_tick(order.symbol)
        if tick is None:
            result = ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=f"Tick indisponivel para {order.symbol}.",
            )
            self._write_log(order, result)
            return result

        response = self.mt5.order_send(self._request(order, tick))
        result = self._result_from_response(response)
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
            "comment": "TraderIA DYNAMIC_EXIT_ASSISTED_SL",
        }
        response = self.mt5.order_send(request)
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

    def _positive_float(self, value: object) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if parsed <= 0.0:
            return None
        return parsed

    def _non_negative_float(self, value: object) -> float:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(parsed, 0.0)

    def _pip_size(self, symbol: str) -> float:
        return 0.01 if str(symbol).upper().endswith("JPY") else 0.0001

    def _initialize_check(self) -> ExecutionResult | None:
        initialize = getattr(self.mt5, "initialize", None)
        if callable(initialize) and not bool(initialize()):
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
            "tp": float(order.target),
            "deviation": self.deviation,
            "magic": self.magic,
            "comment": "TraderIA DEMO",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

    def _result_from_response(self, response: object) -> ExecutionResult:
        if response is None:
            return ExecutionResult(
                accepted=False,
                status="ERROR",
                message="MT5 retornou resposta vazia ao enviar ordem.",
            )
        retcode = int(getattr(response, "retcode", -1))
        success_code = getattr(self.mt5, "TRADE_RETCODE_DONE", None)
        done = success_code is not None and retcode == int(success_code)
        return ExecutionResult(
            accepted=done,
            status="ACCEPTED" if done else "REJECTED",
            message=str(getattr(response, "comment", "")) or self._message(done),
            ticket=self._ticket(response),
            executed_price=self._executed_price(response),
            error_code=None if done else retcode,
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
        }
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _write_management_log(self, payload: dict[str, Any]) -> None:
        self.management_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.management_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")
