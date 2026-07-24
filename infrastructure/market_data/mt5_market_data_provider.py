"""Adaptador read-only de candles do MetaTrader 5."""

from __future__ import annotations

import os
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from core.configuration_manager import ConfigurationManager
from core.event_bus import EventBus
from core.events import NEW_CANDLE
from domain.candle import Candle


@dataclass
class MT5MarketDataProvider:
    """Le candles do MT5 e publica NEW_CANDLE sem capacidade operacional."""

    event_bus: EventBus = field(default_factory=EventBus)
    login: str | int | None = None
    password: str | None = None
    server: str | None = None
    terminal_path: str | None = None
    mt5_module: Any | None = None
    configuration_manager: type[ConfigurationManager] = ConfigurationManager
    connected: bool = False
    last_error: str = ""
    account: str = "N/D"
    account_type: str = "N/D"
    server_name: str = "N/D"
    symbols: list[str] = field(default_factory=list)
    external_call_cache: dict[str, tuple[float, dict[str, Any]]] = field(
        default_factory=dict
    )

    def connect(self) -> bool:
        """Inicializa o MT5 e autentica usando configuracao externa."""
        if self._use_external_mt5_process():
            if self.connected:
                return True
            payload = self._external_mt5_call("connect")
            self.connected = bool(payload.get("ok"))
            if self.connected:
                self.last_error = ""
                self.account = str(payload.get("account", "N/D"))
                self.server_name = str(payload.get("server", "N/D"))
                self.account_type = str(payload.get("account_type", "N/D"))
                self.symbols = []
            else:
                self.last_error = str(payload.get("message", "MT5 nao conectado."))
            return self.connected

        try:
            mt5 = self._mt5()
        except (ImportError, ModuleNotFoundError) as exc:
            self.connected = False
            self.last_error = f"Biblioteca MT5 indisponivel: {exc}"
            return False

        login = self._credential("MT5_LOGIN", self.login)
        password = self._credential("MT5_PASSWORD", self.password)
        server = self._credential("MT5_SERVER", self.server)
        terminal_path = self._credential("MT5_PATH", self.terminal_path)

        connection_arguments = {}
        if login and password and server:
            connection_arguments = {
                "login": int(login),
                "password": str(password),
                "server": str(server),
            }
        if terminal_path:
            connection_arguments["path"] = str(terminal_path)

        try:
            self.connected = bool(mt5.initialize(**connection_arguments))
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            self.connected = False
            self.last_error = f"Falha ao inicializar MT5: {exc}"
            return False

        if self.connected:
            self.last_error = ""
            self._refresh_connection_details(mt5)
            self.symbols = []
        else:
            self.last_error = self._last_error_message(mt5)
        return self.connected

    def select_symbol(self, symbol: str) -> bool:
        """Seleciona um simbolo no terminal MT5 em modo de leitura."""
        normalized_symbol = symbol.strip()
        if not normalized_symbol:
            return False
        if self._use_external_mt5_process():
            payload = self._external_mt5_call("select_symbol", symbol=normalized_symbol)
            if not bool(payload.get("ok")):
                self.last_error = str(payload.get("message", "Falha em symbol_select()."))
                return False
            return True
        return bool(self._mt5().symbol_select(normalized_symbol, True))

    def list_symbols(self) -> list[str]:
        """Lista simbolos disponiveis para leitura no terminal conectado."""
        return list(self.symbols)

    def symbol_exists(self, symbol: str) -> bool:
        """Verifica se um simbolo existe no MT5 sem acionar execucao."""
        normalized_symbol = symbol.strip()
        if not normalized_symbol:
            return False
        if self._use_external_mt5_process():
            payload = self._external_mt5_call("symbol_exists", symbol=normalized_symbol)
            exists = bool(payload.get("exists"))
            if exists and normalized_symbol not in self.symbols:
                self.symbols.append(normalized_symbol)
                self.symbols.sort()
            if not exists and payload.get("message"):
                self.last_error = str(payload.get("message"))
            return exists
        symbol_info = getattr(self._mt5(), "symbol_info", None)
        if callable(symbol_info):
            try:
                exists = symbol_info(normalized_symbol) is not None
            except (OSError, RuntimeError, ValueError, TypeError):
                exists = False
            if exists and normalized_symbol not in self.symbols:
                self.symbols.append(normalized_symbol)
                self.symbols.sort()
            return exists
        return True

    def get_candles(self, symbol: str, timeframe: Any, count: int) -> list[Candle]:
        """Baixa candles, converte para Candle e publica NEW_CANDLE."""
        if count <= 0:
            return []
        if self._use_external_mt5_process():
            external_limit = os.getenv(
                "TRADERIA_MT5_EXTERNAL_MAX_CANDLES",
                "",
            ).strip()
            external_count = int(count)
            if external_limit:
                try:
                    external_count = min(external_count, max(int(external_limit), 1))
                except ValueError:
                    external_count = int(count)
            payload = self._external_mt5_call(
                "get_candles",
                symbol=symbol,
                timeframe=int(timeframe),
                count=external_count,
            )
            if not bool(payload.get("ok")):
                self.last_error = str(payload.get("message", "Falha ao ler candles MT5."))
                return []
            candles = [self._to_candle(rate) for rate in list(payload.get("rates", []))]
            for candle in candles:
                self.event_bus.publish(NEW_CANDLE, candle)
            return candles

        rates = self._mt5().copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None:
            return []
        candles = [self._to_candle(rate) for rate in list(rates)]

        for candle in candles:
            self.event_bus.publish(NEW_CANDLE, candle)

        return candles

    def get_symbol_microstructure(self, symbol: str) -> dict[str, float | None]:
        """Le spread e tick atuais do MT5 em modo somente leitura."""
        if self._use_external_mt5_process():
            payload = self._external_mt5_call("microstructure", symbol=symbol)
            data = payload.get("data", {}) if bool(payload.get("ok")) else {}
            return {
                "bid": self._positive_float(data.get("bid")),
                "ask": self._positive_float(data.get("ask")),
                "point": self._positive_float(data.get("point")),
                "spread": self._positive_float(data.get("spread")),
                "spread_points": self._positive_float(data.get("spread_points")),
            }
        mt5 = self._mt5()
        symbol_info = self._safe_symbol_call(mt5, "symbol_info", symbol)
        symbol_tick = self._safe_symbol_call(mt5, "symbol_info_tick", symbol)
        point = self._positive_float(self._object_value(symbol_info, "point", None))
        spread_points = self._positive_float(
            self._object_value(symbol_info, "spread", None)
        )
        bid = self._positive_float(self._object_value(symbol_tick, "bid", None))
        ask = self._positive_float(self._object_value(symbol_tick, "ask", None))

        spread = None
        if bid is not None and ask is not None and ask >= bid:
            spread = ask - bid
        elif spread_points is not None and point is not None:
            spread = spread_points * point

        return {
            "bid": bid,
            "ask": ask,
            "point": point,
            "spread": spread,
            "spread_points": spread_points,
        }

    def get_symbol_cost_data(self, symbol: str) -> dict[str, float | int | str | None]:
        """Le dados read-only de custo operacional do simbolo no MT5."""
        normalized_symbol = str(symbol or "").strip()
        if not normalized_symbol:
            return {"source": "MT5", "symbol": "N/D"}
        if self._use_external_mt5_process():
            payload = self._external_mt5_call("cost_snapshot", symbol=normalized_symbol)
            data = payload.get("data", {}) if bool(payload.get("ok")) else {}
            return dict(data) if isinstance(data, dict) else {}

        mt5 = self._mt5()
        symbol_info = self._safe_symbol_call(mt5, "symbol_info", normalized_symbol)
        symbol_tick = self._safe_symbol_call(mt5, "symbol_info_tick", normalized_symbol)
        point = self._positive_float(self._object_value(symbol_info, "point", None))
        spread_points = self._positive_float(
            self._object_value(symbol_info, "spread", None)
        )
        bid = self._positive_float(self._object_value(symbol_tick, "bid", None))
        ask = self._positive_float(self._object_value(symbol_tick, "ask", None))
        spread_price = None
        if bid is not None and ask is not None and ask >= bid:
            spread_price = ask - bid
        elif spread_points is not None and point is not None:
            spread_price = spread_points * point
        return {
            "symbol": normalized_symbol.upper(),
            "bid": bid,
            "ask": ask,
            "spread_points": spread_points,
            "spread_price": spread_price,
            "spread": spread_price,
            "swap_long": self._object_value(symbol_info, "swap_long", None),
            "swap_short": self._object_value(symbol_info, "swap_short", None),
            "tick_value": self._object_value(symbol_info, "trade_tick_value", None),
            "tick_size": self._object_value(symbol_info, "trade_tick_size", None),
            "contract_size": self._object_value(symbol_info, "trade_contract_size", None),
            "digits": self._object_value(symbol_info, "digits", None),
            "point": point,
            "source": "MT5",
            "captured_at": datetime.now(UTC).isoformat(),
        }

    def get_server_time(self, symbol: str = "EURUSD") -> str:
        """Retorna horario do servidor MT5 usando timestamp do tick mais recente."""
        normalized_symbol = str(symbol or "EURUSD").strip() or "EURUSD"
        if self._use_external_mt5_process():
            payload = self._external_mt5_call("server_time", symbol=normalized_symbol)
            if bool(payload.get("ok")):
                return str(payload.get("server_time") or "N/D")
            self.last_error = str(payload.get("message", "Horario do servidor indisponivel."))
            return "N/D"
        try:
            mt5 = self._mt5()
            mt5.symbol_select(normalized_symbol, True)
            tick = mt5.symbol_info_tick(normalized_symbol)
        except (OSError, RuntimeError, ValueError, TypeError):
            return "N/D"
        tick_time = self._positive_float(self._object_value(tick, "time", None))
        if tick_time is None:
            return "N/D"
        return datetime.fromtimestamp(float(tick_time), tz=UTC).isoformat()

    def get_forex_batch(
        self,
        symbols_timeframes: dict[str, Any],
        count: int,
    ) -> dict[str, dict[str, Any]]:
        """Le varios pares em um unico processo MT5 externo."""
        if count <= 0 or not symbols_timeframes:
            return {}
        if not self._use_external_mt5_process():
            batch: dict[str, dict[str, Any]] = {}
            for symbol, timeframe in symbols_timeframes.items():
                exists = self.symbol_exists(symbol)
                selected = self.select_symbol(symbol) if exists else False
                candles = self.get_candles(symbol, timeframe, count) if selected else []
                batch[symbol] = {
                    "exists": exists,
                    "selected": selected,
                    "candles": candles,
                    "microstructure": self.get_symbol_microstructure(symbol)
                    if selected
                    else {},
                }
            return batch

        payload = self._external_mt5_call(
            "forex_batch",
            symbols_timeframes=symbols_timeframes,
            count=int(count),
        )
        if not bool(payload.get("ok")):
            self.last_error = str(payload.get("message", "Falha na leitura MT5 em lote."))
            return {}

        batch = {}
        for symbol, data in dict(payload.get("symbols", {})).items():
            candles = [self._to_candle(rate) for rate in list(data.get("rates", []))]
            for candle in candles:
                self.event_bus.publish(NEW_CANDLE, candle)
            if data.get("exists") and symbol not in self.symbols:
                self.symbols.append(symbol)
            batch[symbol] = {
                "exists": bool(data.get("exists")),
                "selected": bool(data.get("selected")),
                "candles": candles,
                "microstructure": data.get("microstructure", {}),
            }
        self.symbols.sort()
        self.last_error = ""
        return batch

    def get_research_batch(
        self,
        symbols: list[str] | tuple[str, ...],
        timeframes: dict[str, Any],
        count: int,
    ) -> dict[str, dict[str, dict[str, Any]]]:
        """Le pares e timeframes do Lab em uma unica sessao externa MT5."""
        if count <= 0 or not symbols or not timeframes:
            return {}
        if not self._use_external_mt5_process():
            return {
                label: self.get_forex_batch(
                    {symbol: timeframe for symbol in symbols},
                    count,
                )
                for label, timeframe in timeframes.items()
            }
        payload = self._external_mt5_call(
            "research_batch",
            symbols=[str(symbol) for symbol in symbols],
            timeframes={str(key): int(value) for key, value in timeframes.items()},
            count=int(count),
        )
        if not bool(payload.get("ok")):
            self.connected = False
            self.last_error = str(
                payload.get("message", "Falha na leitura multi-TF do Research Lab.")
            )
            return {}
        self.connected = True
        self.account = str(payload.get("account", self.account))
        self.server_name = str(payload.get("server", self.server_name))
        self.account_type = str(payload.get("account_type", self.account_type))
        result: dict[str, dict[str, dict[str, Any]]] = {}
        for label, symbols_payload in dict(payload.get("timeframes", {})).items():
            timeframe_rows: dict[str, dict[str, Any]] = {}
            for symbol, data in dict(symbols_payload or {}).items():
                candles = [
                    self._to_candle(rate)
                    for rate in list(dict(data or {}).get("rates", []))
                ]
                timeframe_rows[str(symbol)] = {
                    "exists": bool(dict(data or {}).get("exists")),
                    "selected": bool(dict(data or {}).get("selected")),
                    "candles": candles,
                    "microstructure": dict(data or {}).get("microstructure", {}),
                }
            result[str(label).upper()] = timeframe_rows
        self.last_error = ""
        return result

    def diagnose_connection(
        self,
        symbol: str,
        timeframe: Any,
    ) -> dict[str, Any]:
        """Executa diagnostico read-only detalhado da conexao MT5."""
        steps: list[dict[str, Any]] = []
        details: dict[str, Any] = {
            "connection_status": "OFFLINE",
            "steps": steps,
            "last_error_code": None,
            "last_error_message": "",
            "terminal_path": str(self.terminal_path or "N/D"),
            "build": "N/D",
            "server": self.server_name,
            "account": self.account,
            "connected": False,
            "trade_allowed": False,
            "community_connection": False,
            "failed_call": "",
            "diagnostic_message": "Diagnostico MT5 executado.",
        }

        try:
            mt5 = self._mt5()
            self._append_diagnostic_step(steps, "Terminal encontrado", True, "Modulo MetaTrader5 carregado.", mt5)
        except (ImportError, ModuleNotFoundError, OSError, RuntimeError) as exc:
            details["failed_call"] = "import MetaTrader5"
            details["diagnostic_message"] = str(exc)
            self._append_diagnostic_step(steps, "Terminal encontrado", False, str(exc), None)
            return self._finalize_diagnostic(details, None)

        initialized = self.connect()
        self._append_diagnostic_step(
            steps,
            "initialize()",
            initialized,
            "MT5 inicializado." if initialized else self._last_error_message(mt5),
            mt5,
        )
        if not initialized:
            details["failed_call"] = "initialize()"
            details["diagnostic_message"] = self._last_error_message(mt5)
            return self._finalize_diagnostic(details, mt5)

        login_result = self._diagnostic_login(mt5)
        account_info = self._safe_call(mt5, "account_info")
        login_ok = bool(login_result["ok"]) or account_info is not None
        self._append_diagnostic_step(
            steps,
            "login()",
            login_ok,
            str(login_result["message"])
            if login_result["called"]
            else (
                "login() nao chamado; sessao herdada do terminal validada por account_info()."
                if login_ok
                else self._last_error_message(mt5)
            ),
            mt5,
        )
        if not login_ok and not details["failed_call"]:
            details["failed_call"] = "login()"
        self._append_diagnostic_step(
            steps,
            "account_info()",
            account_info is not None,
            "Informacoes da conta obtidas." if account_info is not None else self._last_error_message(mt5),
            mt5,
        )
        if account_info is None:
            details["failed_call"] = "account_info()"

        terminal_info = self._safe_call(mt5, "terminal_info")
        self._append_diagnostic_step(
            steps,
            "terminal_info()",
            terminal_info is not None,
            "Informacoes do terminal obtidas." if terminal_info is not None else self._last_error_message(mt5),
            mt5,
        )
        if terminal_info is None and not details["failed_call"]:
            details["failed_call"] = "terminal_info()"

        details.update(self._diagnostic_connection_details(account_info, terminal_info))

        symbol_selected = self.select_symbol(symbol)
        self._append_diagnostic_step(
            steps,
            "symbol_select()",
            symbol_selected,
            f"Simbolo {symbol} selecionado." if symbol_selected else self._last_error_message(mt5),
            mt5,
        )
        if not symbol_selected and not details["failed_call"]:
            details["failed_call"] = "symbol_select()"

        candles_ok = False
        if symbol_selected:
            try:
                rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 1)
                candles_ok = rates is not None and len(list(rates)) > 0
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                self.last_error = f"Falha em copy_rates_from_pos(): {exc}"
                candles_ok = False
        self._append_diagnostic_step(
            steps,
            "copy_rates_from_pos()",
            candles_ok,
            "Sonda de 1 candle retornada." if candles_ok else self._last_error_message(mt5),
            mt5,
        )
        if not candles_ok and not details["failed_call"]:
            details["failed_call"] = "copy_rates_from_pos()"

        details["connection_status"] = "ONLINE" if all(
            step["status"] == "OK" for step in steps
        ) else "OFFLINE"
        if details["connection_status"] == "ONLINE":
            details["diagnostic_message"] = "Todas as etapas MT5 read-only responderam com sucesso."
        elif details["failed_call"]:
            details["diagnostic_message"] = f"Falha em {details['failed_call']}."
        return self._finalize_diagnostic(details, mt5)

    def _mt5(self) -> Any:
        if self.mt5_module is None:
            import MetaTrader5 as mt5

            self.mt5_module = mt5
        return self.mt5_module

    def _use_external_mt5_process(self) -> bool:
        return self.mt5_module is None

    def _external_mt5_call(self, action: str, **kwargs: Any) -> dict[str, Any]:
        request = {"action": action, **kwargs}
        cache_key = self._external_call_cache_key(request)
        if cache_key:
            cached = self.external_call_cache.get(cache_key)
            if cached and time.monotonic() - cached[0] <= self._external_cache_ttl():
                return dict(cached[1])
        code = r'''
import json
import sys
from datetime import UTC, datetime

request = json.loads(sys.argv[1])
try:
    import MetaTrader5 as mt5
except Exception as exc:
    print(json.dumps({"ok": False, "message": f"Biblioteca MT5 indisponivel: {exc}"}))
    raise SystemExit(0)

def emit(payload):
    print(json.dumps(payload, default=str))

try:
    if not mt5.initialize():
        emit({"ok": False, "message": f"MT5 initialize() falhou: {mt5.last_error()}"})
        raise SystemExit(0)
    action = request.get("action")
    if action == "connect":
        account = mt5.account_info()
        terminal = mt5.terminal_info()
        emit({
            "ok": account is not None,
            "account": getattr(account, "login", "N/D") if account else "N/D",
            "server": getattr(account, "server", "N/D") if account else "N/D",
            "account_type": getattr(account, "trade_mode", "N/D") if account else "N/D",
            "connected": bool(getattr(terminal, "connected", False)) if terminal else False,
            "message": "MT5 conectado." if account else "Conta MT5 indisponivel.",
        })
    elif action == "select_symbol":
        symbol = str(request.get("symbol", ""))
        emit({"ok": bool(mt5.symbol_select(symbol, True))})
    elif action == "symbol_exists":
        symbol = str(request.get("symbol", ""))
        mt5.symbol_select(symbol, True)
        emit({"ok": True, "exists": mt5.symbol_info(symbol) is not None})
    elif action == "get_candles":
        symbol = str(request.get("symbol", ""))
        timeframe = int(request.get("timeframe", 0))
        count = int(request.get("count", 0))
        mt5.symbol_select(symbol, True)
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        rows = []
        if rates is not None:
            for rate in list(rates):
                rows.append({
                    "time": int(rate["time"]),
                    "open": float(rate["open"]),
                    "high": float(rate["high"]),
                    "low": float(rate["low"]),
                    "close": float(rate["close"]),
                    "tick_volume": int(rate["tick_volume"]),
                    "real_volume": int(rate["real_volume"]) if "real_volume" in rate.dtype.names else 0,
                })
        emit({"ok": rates is not None, "rates": rows, "message": mt5.last_error()})
    elif action == "microstructure":
        symbol = str(request.get("symbol", ""))
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        point = float(getattr(info, "point", 0.0) or 0.0) if info else None
        spread_points = float(getattr(info, "spread", 0.0) or 0.0) if info else None
        bid = float(getattr(tick, "bid", 0.0) or 0.0) if tick else None
        ask = float(getattr(tick, "ask", 0.0) or 0.0) if tick else None
        spread = ask - bid if bid is not None and ask is not None and ask >= bid else None
        if spread is None and point is not None and spread_points is not None:
            spread = point * spread_points
        emit({"ok": True, "data": {
            "bid": bid,
            "ask": ask,
            "point": point,
            "spread": spread,
            "spread_points": spread_points,
        }})
    elif action == "cost_snapshot":
        symbol = str(request.get("symbol", ""))
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        point = float(getattr(info, "point", 0.0) or 0.0) if info else None
        spread_points = float(getattr(info, "spread", 0.0) or 0.0) if info else None
        bid = float(getattr(tick, "bid", 0.0) or 0.0) if tick else None
        ask = float(getattr(tick, "ask", 0.0) or 0.0) if tick else None
        spread = ask - bid if bid is not None and ask is not None and ask >= bid else None
        if spread is None and point is not None and spread_points is not None:
            spread = point * spread_points
        emit({"ok": info is not None, "data": {
            "symbol": symbol.upper(),
            "bid": bid,
            "ask": ask,
            "spread_points": spread_points,
            "spread_price": spread,
            "spread": spread,
            "swap_long": float(getattr(info, "swap_long", 0.0) or 0.0) if info else None,
            "swap_short": float(getattr(info, "swap_short", 0.0) or 0.0) if info else None,
            "tick_value": float(getattr(info, "trade_tick_value", 0.0) or 0.0) if info else None,
            "tick_size": float(getattr(info, "trade_tick_size", 0.0) or 0.0) if info else None,
            "contract_size": float(getattr(info, "trade_contract_size", 0.0) or 0.0) if info else None,
            "digits": int(getattr(info, "digits", 0) or 0) if info else None,
            "point": point,
            "source": "MT5_EXTERNAL",
            "captured_at": datetime.now(UTC).isoformat(),
        }})
    elif action == "server_time":
        symbol = str(request.get("symbol", "EURUSD") or "EURUSD")
        mt5.symbol_select(symbol, True)
        tick = mt5.symbol_info_tick(symbol)
        tick_time = getattr(tick, "time", None) if tick else None
        server_time = (
            datetime.fromtimestamp(float(tick_time), tz=UTC).isoformat()
            if tick_time
            else "N/D"
        )
        emit({"ok": tick_time is not None, "server_time": server_time})
    elif action == "forex_batch":
        symbols_timeframes = dict(request.get("symbols_timeframes", {}))
        count = int(request.get("count", 0))
        response = {}
        for symbol, timeframe in symbols_timeframes.items():
            symbol = str(symbol)
            selected = bool(mt5.symbol_select(symbol, True))
            info = mt5.symbol_info(symbol)
            exists = info is not None
            rates = None
            if exists and selected:
                rates = mt5.copy_rates_from_pos(symbol, int(timeframe), 0, count)
            rows = []
            if rates is not None:
                for rate in list(rates):
                    rows.append({
                        "time": int(rate["time"]),
                        "open": float(rate["open"]),
                        "high": float(rate["high"]),
                        "low": float(rate["low"]),
                        "close": float(rate["close"]),
                        "tick_volume": int(rate["tick_volume"]),
                        "real_volume": int(rate["real_volume"]) if "real_volume" in rate.dtype.names else 0,
                    })
            tick = mt5.symbol_info_tick(symbol) if exists else None
            point = float(getattr(info, "point", 0.0) or 0.0) if info else None
            spread_points = float(getattr(info, "spread", 0.0) or 0.0) if info else None
            bid = float(getattr(tick, "bid", 0.0) or 0.0) if tick else None
            ask = float(getattr(tick, "ask", 0.0) or 0.0) if tick else None
            spread = ask - bid if bid is not None and ask is not None and ask >= bid else None
            if spread is None and point is not None and spread_points is not None:
                spread = point * spread_points
            response[symbol] = {
                "exists": exists,
                "selected": selected,
                "rates": rows,
                "microstructure": {
                    "bid": bid,
                    "ask": ask,
                    "point": point,
                    "spread": spread,
                    "spread_points": spread_points,
                },
            }
        emit({"ok": True, "symbols": response})
    elif action == "research_batch":
        symbols = [str(item) for item in list(request.get("symbols", []))]
        timeframes = dict(request.get("timeframes", {}))
        count = int(request.get("count", 0))
        response = {}
        for label, timeframe in timeframes.items():
            timeframe_response = {}
            for symbol in symbols:
                selected = bool(mt5.symbol_select(symbol, True))
                info = mt5.symbol_info(symbol)
                exists = info is not None
                rates = None
                if exists and selected:
                    rates = mt5.copy_rates_from_pos(symbol, int(timeframe), 0, count)
                rows = []
                if rates is not None:
                    for rate in list(rates):
                        rows.append({
                            "time": int(rate["time"]),
                            "open": float(rate["open"]),
                            "high": float(rate["high"]),
                            "low": float(rate["low"]),
                            "close": float(rate["close"]),
                            "tick_volume": int(rate["tick_volume"]),
                            "real_volume": int(rate["real_volume"]) if "real_volume" in rate.dtype.names else 0,
                        })
                tick = mt5.symbol_info_tick(symbol) if exists else None
                point = float(getattr(info, "point", 0.0) or 0.0) if info else None
                spread_points = float(getattr(info, "spread", 0.0) or 0.0) if info else None
                bid = float(getattr(tick, "bid", 0.0) or 0.0) if tick else None
                ask = float(getattr(tick, "ask", 0.0) or 0.0) if tick else None
                spread = ask - bid if bid is not None and ask is not None and ask >= bid else None
                if spread is None and point is not None and spread_points is not None:
                    spread = point * spread_points
                timeframe_response[symbol] = {
                    "exists": exists,
                    "selected": selected,
                    "rates": rows,
                    "microstructure": {
                        "bid": bid,
                        "ask": ask,
                        "point": point,
                        "spread": spread,
                        "spread_points": spread_points,
                    },
                }
            response[str(label).upper()] = timeframe_response
        account = mt5.account_info()
        emit({
            "ok": True,
            "timeframes": response,
            "account": getattr(account, "login", "N/D") if account else "N/D",
            "server": getattr(account, "server", "N/D") if account else "N/D",
            "account_type": getattr(account, "trade_mode", "N/D") if account else "N/D",
        })
    else:
        emit({"ok": False, "message": f"Acao MT5 desconhecida: {action}"})
finally:
    try:
        mt5.shutdown()
    except Exception:
        pass
'''
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
        try:
            completed = subprocess.run(
                [sys.executable, "-c", code, json.dumps(request)],
                capture_output=True,
                text=True,
                timeout=float(os.getenv("TRADERIA_MT5_EXTERNAL_TIMEOUT_SECONDS", "120")),
                creationflags=creationflags,
            )
        except subprocess.TimeoutExpired:
            return {"ok": False, "message": "Timeout no processo externo MT5."}
        except OSError as exc:
            return {"ok": False, "message": f"Falha ao executar processo MT5: {exc}"}
        output = (completed.stdout or "").strip().splitlines()
        if not output:
            return {
                "ok": False,
                "message": (completed.stderr or "Processo MT5 sem resposta.").strip(),
            }
        try:
            payload = json.loads(output[-1])
        except json.JSONDecodeError:
            payload = {"ok": False, "message": output[-1]}
        if cache_key:
            self.external_call_cache[cache_key] = (time.monotonic(), dict(payload))
        return payload

    def _external_call_cache_key(self, request: dict[str, Any]) -> str:
        if request.get("action") not in {
            "get_candles",
            "microstructure",
            "forex_batch",
            "symbol_exists",
            "server_time",
        }:
            return ""
        try:
            return json.dumps(request, sort_keys=True, default=str)
        except TypeError:
            return ""

    def _external_cache_ttl(self) -> float:
        return float(os.getenv("TRADERIA_MT5_REQUEST_QUEUE_TTL_SECONDS", "2.0"))

    def _credential(self, name: str, explicit_value: str | int | None) -> str | None:
        if explicit_value not in (None, ""):
            return str(explicit_value)

        configuration = self.configuration_manager.get_configuration()
        configured_value = getattr(configuration, name, None)
        if configured_value in (None, ""):
            configured_value = getattr(configuration, name.lower(), None)
        if configured_value not in (None, ""):
            return str(configured_value)

        environment_value = os.getenv(name)
        if environment_value not in (None, ""):
            return environment_value
        return None

    def _refresh_connection_details(self, mt5: Any) -> None:
        account_info = self._safe_call(mt5, "account_info")
        if account_info is not None:
            self.account = str(self._object_value(account_info, "login", "N/D"))
            self.server_name = str(
                self._object_value(account_info, "server", self.server_name)
            )
            self.account_type = str(
                self._object_value(account_info, "trade_mode", self.account_type)
            )

    def _safe_call(self, mt5: Any, name: str) -> Any:
        method = getattr(mt5, name, None)
        if not callable(method):
            return None
        try:
            return method()
        except (OSError, RuntimeError, ValueError, TypeError):
            return None

    def _safe_symbol_call(self, mt5: Any, name: str, symbol: str) -> Any:
        method = getattr(mt5, name, None)
        if not callable(method):
            return None
        try:
            return method(symbol)
        except (OSError, RuntimeError, ValueError, TypeError):
            return None

    def _diagnostic_login(self, mt5: Any) -> dict[str, Any]:
        login = self._credential("MT5_LOGIN", self.login)
        password = self._credential("MT5_PASSWORD", self.password)
        server = self._credential("MT5_SERVER", self.server)
        login_method = getattr(mt5, "login", None)
        if not (login and password and server and callable(login_method)):
            return {
                "called": False,
                "ok": False,
                "message": "login() nao chamado; credenciais explicitas ausentes.",
            }
        try:
            ok = bool(login_method(int(login), password=str(password), server=str(server)))
        except TypeError:
            try:
                ok = bool(login_method(int(login), str(password), str(server)))
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                self.last_error = f"Falha em login(): {exc}"
                return {"called": True, "ok": False, "message": self.last_error}
        except (OSError, RuntimeError, ValueError) as exc:
            self.last_error = f"Falha em login(): {exc}"
            return {"called": True, "ok": False, "message": self.last_error}
        return {
            "called": True,
            "ok": ok,
            "message": "login() executado com sucesso."
            if ok
            else self._last_error_message(mt5),
        }

    def _object_value(self, item: Any, name: str, default: Any) -> Any:
        if hasattr(item, name):
            return getattr(item, name)
        if isinstance(item, dict):
            return item.get(name, default)
        return default

    def _positive_float(self, value: Any) -> float | None:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric <= 0.0:
            return None
        return numeric

    def _diagnostic_connection_details(
        self,
        account_info: Any,
        terminal_info: Any,
    ) -> dict[str, Any]:
        details: dict[str, Any] = {}
        if account_info is not None:
            details["server"] = str(
                self._object_value(account_info, "server", self.server_name)
            )
            details["account"] = str(self._object_value(account_info, "login", self.account))
            details["trade_allowed"] = bool(
                self._object_value(account_info, "trade_allowed", False)
            )
        if terminal_info is not None:
            details["terminal_path"] = str(
                self._object_value(terminal_info, "path", self.terminal_path or "N/D")
            )
            details["build"] = str(self._object_value(terminal_info, "build", "N/D"))
            details["connected"] = bool(
                self._object_value(terminal_info, "connected", self.connected)
            )
            details["community_connection"] = bool(
                self._object_value(terminal_info, "community_connection", False)
            )
        else:
            details["connected"] = bool(self.connected)
        return details

    def _append_diagnostic_step(
        self,
        steps: list[dict[str, Any]],
        name: str,
        ok: bool,
        message: str,
        mt5: Any | None,
    ) -> None:
        code, error_message = self._last_error_tuple(mt5)
        steps.append(
            {
                "name": name,
                "status": "OK" if ok else "FALHOU",
                "message": message,
                "last_error_code": code,
                "last_error_message": error_message,
            }
        )

    def _finalize_diagnostic(
        self,
        details: dict[str, Any],
        mt5: Any | None,
    ) -> dict[str, Any]:
        code, message = self._last_error_tuple(mt5)
        details["last_error_code"] = code
        details["last_error_message"] = message
        return details

    def _last_error_tuple(self, mt5: Any | None) -> tuple[int | None, str]:
        if mt5 is None:
            return None, str(self.last_error or "MT5 nao conectado.")
        last_error = getattr(mt5, "last_error", None)
        if callable(last_error):
            try:
                value = last_error()
            except (OSError, RuntimeError, ValueError, TypeError):
                return None, "MT5 nao conectado."
            if isinstance(value, tuple):
                code = value[0] if value else None
                message = value[1] if len(value) > 1 else ""
                return int(code) if isinstance(code, int) else None, str(message)
            return None, str(value)
        return None, str(self.last_error or "")

    def _last_error_message(self, mt5: Any) -> str:
        code, message = self._last_error_tuple(mt5)
        if code is None and not message:
            return "MT5 nao conectado."
        if code is None:
            return message
        return f"{code}: {message}"

    def _to_candle(self, rate: Any) -> Candle:
        return Candle(
            data=self._to_timestamp(self._rate_value(rate, "time")),
            abertura=float(self._rate_value(rate, "open")),
            maxima=float(self._rate_value(rate, "high")),
            minima=float(self._rate_value(rate, "low")),
            fechamento=float(self._rate_value(rate, "close")),
            volume=int(
                self._rate_value(
                    rate,
                    "tick_volume",
                    fallback_names=("real_volume", "volume"),
                )
                or 0
            ),
        )

    def _rate_value(
        self,
        rate: Any,
        name: str,
        fallback_names: tuple[str, ...] = (),
    ) -> Any:
        for candidate in (name, *fallback_names):
            if hasattr(rate, candidate):
                return getattr(rate, candidate)
            try:
                return rate[candidate]
            except (KeyError, TypeError, IndexError, ValueError):
                continue
        raise ValueError(f"Campo ausente no candle MT5: {name}")

    def _to_timestamp(self, value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return datetime.fromtimestamp(int(value), tz=UTC).isoformat()
