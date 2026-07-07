"""Provider MT5 estritamente read-only."""

from __future__ import annotations

from datetime import datetime, timezone
import importlib
from typing import Any

from domain.contracts.mt5_status import MT5Status


class MT5ReadonlyProvider:
    """Fronteira read-only para leitura MT5 sem metodos operacionais."""

    DEFAULT_FOREX_SYMBOLS = (
        "EURUSD",
        "GBPUSD",
        "USDCHF",
        "USDJPY",
        "AUDUSD",
        "NZDUSD",
        "USDCAD",
        "EURJPY",
    )

    def __init__(self) -> None:
        self._module: Any | None = None
        self._last_error = ""

    def _mt5(self) -> Any | None:
        if self._module is not None:
            return self._module
        try:
            self._module = importlib.import_module("MetaTrader5")
        except Exception as exc:  # noqa: BLE001 - dependency externa opcional
            self._last_error = f"MetaTrader5 indisponivel: {exc}"
            return None
        return self._module

    def _ensure_initialized(self) -> tuple[Any | None, str]:
        mt5 = self._mt5()
        if mt5 is None:
            return None, self._last_error or "MetaTrader5 indisponivel."
        initialize = getattr(mt5, "initialize", None)
        if callable(initialize):
            try:
                if not bool(initialize()):
                    last_error = getattr(mt5, "last_error", lambda: None)()
                    return None, f"MT5 nao inicializou: {last_error}"
            except Exception as exc:  # noqa: BLE001 - terminal externo
                return None, f"Falha ao inicializar MT5: {exc}"
        return mt5, "MT5 inicializado em modo leitura."

    def get_status(self) -> MT5Status:
        mt5, message = self._ensure_initialized()
        if mt5 is None:
            return MT5Status(
                status="OFFLINE",
                server="N/D",
                account="N/D",
                timeframe="M1",
                connected=False,
                message=message,
            )

        account_info = self._safe_asdict(getattr(mt5, "account_info", lambda: None)())
        terminal_info = self._safe_asdict(getattr(mt5, "terminal_info", lambda: None)())
        server = str(account_info.get("server") or terminal_info.get("name") or "N/D")
        account = str(account_info.get("login") or "N/D")
        return MT5Status(
            status="ONLINE",
            server=server,
            account=account,
            timeframe="M1",
            connected=True,
            message=message,
        )

    def get_symbols(self) -> list[str]:
        mt5, _message = self._ensure_initialized()
        if mt5 is None:
            return list(self.DEFAULT_FOREX_SYMBOLS)

        symbols_get = getattr(mt5, "symbols_get", None)
        if not callable(symbols_get):
            return list(self.DEFAULT_FOREX_SYMBOLS)
        try:
            symbols = symbols_get() or []
        except Exception:
            return list(self.DEFAULT_FOREX_SYMBOLS)

        available = {str(getattr(symbol, "name", "")).upper() for symbol in symbols}
        mapped = [symbol for symbol in self.DEFAULT_FOREX_SYMBOLS if symbol in available]
        return mapped or list(self.DEFAULT_FOREX_SYMBOLS)

    def get_latest_price(self, symbol: str) -> float | None:
        tick = self.get_tick(symbol)
        if not tick:
            return None
        bid = self._to_float(tick.get("bid"))
        ask = self._to_float(tick.get("ask"))
        if bid is not None and ask is not None and ask > 0:
            return (bid + ask) / 2.0
        return bid or ask

    def get_tick(self, symbol: str) -> dict[str, Any] | None:
        mt5, _message = self._ensure_initialized()
        if mt5 is None:
            return None
        symbol = str(symbol).replace("/", "").upper()
        symbol_select = getattr(mt5, "symbol_select", None)
        if callable(symbol_select):
            try:
                symbol_select(symbol, True)
            except Exception:
                pass
        symbol_info_tick = getattr(mt5, "symbol_info_tick", None)
        if not callable(symbol_info_tick):
            return None
        try:
            tick = symbol_info_tick(symbol)
        except Exception:
            return None
        data = self._safe_asdict(tick)
        if not data:
            return None
        data["read_at"] = datetime.now(timezone.utc).isoformat()
        return data

    def get_open_positions(self) -> list[dict[str, Any]]:
        mt5, _message = self._ensure_initialized()
        if mt5 is None:
            return []
        positions_get = getattr(mt5, "positions_get", None)
        if not callable(positions_get):
            return []
        try:
            positions = positions_get() or []
        except Exception:
            return []
        return [self._normalize_position(position) for position in positions]

    def _normalize_position(self, position: Any) -> dict[str, Any]:
        data = self._safe_asdict(position)
        position_type = int(data.get("type", -1) or -1)
        return {
            "symbol": str(data.get("symbol") or "").upper(),
            "side": "BUY" if position_type == 0 else "SELL" if position_type == 1 else "N/D",
            "volume": self._to_float(data.get("volume")) or 0.0,
            "price_open": self._to_float(data.get("price_open")),
            "price_current": self._to_float(data.get("price_current")),
            "profit": self._to_float(data.get("profit")) or 0.0,
            "ticket": data.get("ticket"),
            "time": data.get("time"),
        }

    def _safe_asdict(self, value: Any) -> dict[str, Any]:
        if value is None:
            return {}
        if hasattr(value, "_asdict"):
            try:
                return dict(value._asdict())
            except Exception:
                return {}
        if isinstance(value, dict):
            return dict(value)
        return {}

    def _to_float(self, value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
