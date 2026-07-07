"""Servico read-only para a aba Forex MT5."""

from __future__ import annotations

from datetime import datetime, timezone

from domain.contracts.forex_signal import ForexSignal
from domain.contracts.mt5_status import MT5Status
from infrastructure.mt5.mt5_readonly_provider import MT5ReadonlyProvider


class ForexMT5Service:
    """Exibe estado de mercado sem executar ordens."""

    def __init__(self, provider: MT5ReadonlyProvider | None = None) -> None:
        self.provider = provider or MT5ReadonlyProvider()

    def get_status(self) -> MT5Status:
        return self.provider.get_status()

    def get_signals(self, timeframe: str = "M1") -> list[ForexSignal]:
        positions = {
            str(position.get("symbol", "")).upper(): position
            for position in self.provider.get_open_positions()
        }
        rows: list[ForexSignal] = []
        for symbol in self.provider.get_symbols():
            tick = self.provider.get_tick(symbol)
            price = self.provider.get_latest_price(symbol)
            position = positions.get(symbol.upper())
            if tick:
                bid = self._to_float(tick.get("bid"))
                ask = self._to_float(tick.get("ask"))
                spread = self._spread(bid, ask)
                reason = "MT5 online: leitura de tick em modo read-only."
                last_update = str(tick.get("read_at") or datetime.now(timezone.utc).isoformat())
            else:
                bid = None
                ask = None
                spread = None
                reason = "MT5 offline ou simbolo indisponivel; aguardando leitura."
                last_update = "N/D"
            is_positioned = position is not None
            stop_management = "ATR_TRAILING_STOP"
            rows.append(
                ForexSignal(
                    pair=symbol,
                    timeframe=timeframe,
                    decision=self._decision_for_position(position),
                    price=float(price or 0.0),
                    bid=bid,
                    ask=ask,
                    spread=spread,
                    reason=reason,
                    last_update=last_update,
                    lab_setup="TREND_MOMENTUM",
                    stop_management=stop_management,
                    dynamic_exit_policy=stop_management,
                    dynamic_exit_action=(
                        "KEEP_ORIGINAL_PLAN" if is_positioned else "NO_ACTION_BAD_CONTEXT"
                    ),
                    dynamic_exit_reason=(
                        "Contrato read-only preserva politica base do Lab; execucao demo desabilitada."
                        if is_positioned
                        else "Sem posicao aberta; saida dinamica apenas auditavel."
                    ),
                    dynamic_exit_confidence=0.0,
                    dynamic_exit_market_state=(
                        "NEW_POSITION" if is_positioned else "NO_POSITION"
                    ),
                    dynamic_exit_allowed_to_execute_demo=False,
                    is_positioned=is_positioned,
                    position_side=str(position.get("side", "N/D")) if position else "N/D",
                    position_volume=float(position.get("volume", 0.0) or 0.0) if position else 0.0,
                    position_price=self._to_float(position.get("price_open")) if position else None,
                    position_profit=float(position.get("profit", 0.0) or 0.0) if position else 0.0,
                )
            )
        return rows

    def get_open_positions(self) -> list[dict[str, object]]:
        return self.provider.get_open_positions()

    def _decision_for_position(self, position: dict[str, object] | None) -> str:
        if not position:
            return "WAIT"
        side = str(position.get("side", "")).upper()
        return side if side in {"BUY", "SELL"} else "WAIT"

    def _spread(self, bid: float | None, ask: float | None) -> float | None:
        if bid is None or ask is None:
            return None
        return max(ask - bid, 0.0)

    def _to_float(self, value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
