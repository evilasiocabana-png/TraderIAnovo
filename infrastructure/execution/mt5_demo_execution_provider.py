"""Adaptador exclusivo para envio de ordens em conta demo do MetaTrader 5."""

from __future__ import annotations

import importlib
import json
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.contracts.dynamic_exit_demo_sl import DynamicExitDemoSLExecutionResult


_MT5_ORDER_SEND_LOCK = threading.Lock()


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

    def has_open_position_for_model(
        self,
        symbol: str,
        operational_model: str,
    ) -> bool:
        """Consulta posicao aberta do mesmo simbolo e modelo operacional."""
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return True
        positions = self.mt5.positions_get(symbol=symbol) or []
        expected = self._model_comment(operational_model)
        for position in positions:
            comment = str(getattr(position, "comment", "") or "").upper()
            if expected in comment:
                return True
            if "TRADERIA" in comment and " M1" not in comment and " M2" not in comment:
                return True
        return False

    def get_open_position(self, symbol: str) -> object | None:
        """Retorna a primeira posicao aberta do simbolo em conta demo."""
        initialize_check = self._initialize_check()
        if initialize_check is not None:
            return None
        positions = self.mt5.positions_get(symbol=symbol) or []
        return positions[0] if positions else None

    def get_current_price(self, symbol: str) -> float | None:
        """Retorna preco atual read-only para validacao de SL."""
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

        response = self._order_send(self._request(order, tick))
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
        price = self._positive_float(
            getattr(tick, "ask", None) if side == "BUY" else getattr(tick, "bid", None)
        )
        stop = self._positive_float(getattr(order, "stop", None))
        target = self._positive_float(getattr(order, "target", None))
        if price is None:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=f"Preco executavel indisponivel para {order.symbol}.",
            )
        if stop is None or target is None:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Stop Loss e Take Profit invalidos para envio MT5 Demo.",
            )
        if side == "BUY" and not (stop < price < target):
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=(
                    "Plano MT5 Demo stale: preco atual tornou SL/TP invalidos "
                    f"para BUY ({stop:.6f} < {price:.6f} < {target:.6f})."
                ),
                executed_price=price,
            )
        if side == "SELL" and not (target < price < stop):
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message=(
                    "Plano MT5 Demo stale: preco atual tornou SL/TP invalidos "
                    f"para SELL ({target:.6f} < {price:.6f} < {stop:.6f})."
                ),
                executed_price=price,
            )
        if side not in {"BUY", "SELL"}:
            return ExecutionResult(
                accepted=False,
                status="REJECTED",
                message="Direcao invalida para envio MT5 Demo.",
            )
        return None

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
        for record in self._read_execution_log_records():
            if not self._record_counts_as_plan_evaluation(record):
                continue
            record_identity = str(record.get("plan_identity") or "").strip()
            if not record_identity or record_identity.upper() == "N/D":
                continue
            if record_identity != current_identity:
                continue
            if self._record_plan_key(record) != current_key:
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

    def _record_counts_as_plan_evaluation(self, record: dict[str, Any]) -> bool:
        """Duplicidade de plano so nasce de ordem aceita pelo MT5."""
        return bool(record.get("accepted", False))

    def _read_execution_log_records(self) -> list[dict[str, Any]]:
        if not self.log_path.exists():
            return []
        try:
            lines = self.log_path.read_text(
                encoding="utf-8",
                errors="ignore",
            ).splitlines()
        except OSError:
            return []
        records: list[dict[str, Any]] = []
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

    def _execution_plan_key(
        self,
        order: ExecutionOrder,
    ) -> tuple[str, str, float, float, float] | None:
        entry = self._positive_float(getattr(order, "entry_price", None))
        stop = self._positive_float(getattr(order, "stop", None))
        target = self._positive_float(getattr(order, "target", None))
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
        target = self._positive_float(record.get("target"))
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
        }
        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _order_comment(self, order: ExecutionOrder) -> str:
        return f"TraderIA {self._model_comment(getattr(order, 'operational_model', ''))}"

    def _model_comment(self, operational_model: object) -> str:
        model = str(operational_model or "").upper()
        if model == "MODELO_2_ESPELHO_BETA2_RR1":
            return "M2"
        return "M1"

    def _write_management_log(self, payload: dict[str, Any]) -> None:
        self.management_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.management_log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(payload, ensure_ascii=True) + "\n")
