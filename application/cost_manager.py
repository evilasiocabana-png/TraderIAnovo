from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class SymbolCostSnapshot:
    """Snapshot read-only dos custos operacionais atuais de um simbolo."""

    symbol: str
    bid: float | None = None
    ask: float | None = None
    spread_points: float | None = None
    spread_price: float | None = None
    spread_money_estimate: float | None = None
    swap_long: float | None = None
    swap_short: float | None = None
    tick_value: float | None = None
    tick_size: float | None = None
    contract_size: float | None = None
    digits: int | None = None
    point: float | None = None
    source: str = "MT5"
    captured_at: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class TradeCostEstimate:
    """Estimativa pre-entrada sem hardcode de corretagem."""

    symbol: str
    volume: float
    direction: str
    spread_cost: float | None = None
    swap_expected: float | None = None
    commission: float | None = None
    fee: float | None = None
    total_estimated_cost: float | None = None
    unknown: tuple[str, ...] = field(default_factory=tuple)
    snapshot: SymbolCostSnapshot | None = None


@dataclass(frozen=True)
class RealTradeCost:
    """Custo real agregado do MT5 apos execucao."""

    commission: float = 0.0
    swap: float = 0.0
    fee: float = 0.0
    profit: float = 0.0
    net_profit: float = 0.0
    deals_count: int = 0
    tickets: tuple[int, ...] = field(default_factory=tuple)


class CostManager:
    """Centraliza leitura e calculo de custos reais/estimados do MT5."""

    def __init__(self, provider: object | None = None) -> None:
        self.provider = provider

    def get_symbol_cost_snapshot(self, symbol: str) -> SymbolCostSnapshot:
        normalized_symbol = str(symbol or "").strip().upper()
        warnings: list[str] = []
        data = self._provider_symbol_cost_data(normalized_symbol, warnings)

        bid = self._optional_float(data.get("bid"))
        ask = self._optional_float(data.get("ask"))
        point = self._optional_float(data.get("point"))
        spread_points = self._optional_float(data.get("spread_points"))
        spread_price = self._optional_float(data.get("spread_price"))
        if spread_price is None:
            spread_price = self._optional_float(data.get("spread"))
        if spread_price is None and bid is not None and ask is not None and ask >= bid:
            spread_price = ask - bid
        if spread_price is None and point is not None and spread_points is not None:
            spread_price = point * spread_points

        tick_value = self._optional_float(data.get("tick_value"))
        tick_size = self._optional_float(data.get("tick_size"))
        spread_money_estimate = self._spread_money_estimate(
            spread_price=spread_price,
            tick_value=tick_value,
            tick_size=tick_size,
            volume=1.0,
        )

        required = {
            "bid": bid,
            "ask": ask,
            "spread_price": spread_price,
            "tick_value": tick_value,
            "tick_size": tick_size,
        }
        for name, value in required.items():
            if value is None:
                warnings.append(f"{name} indisponivel no MT5")

        return SymbolCostSnapshot(
            symbol=normalized_symbol or "N/D",
            bid=bid,
            ask=ask,
            spread_points=spread_points,
            spread_price=spread_price,
            spread_money_estimate=spread_money_estimate,
            swap_long=self._optional_float(data.get("swap_long")),
            swap_short=self._optional_float(data.get("swap_short")),
            tick_value=tick_value,
            tick_size=tick_size,
            contract_size=self._optional_float(data.get("contract_size")),
            digits=self._optional_int(data.get("digits")),
            point=point,
            source=str(data.get("source") or "MT5"),
            captured_at=str(data.get("captured_at") or datetime.now(UTC).isoformat()),
            warnings=tuple(dict.fromkeys(warnings)),
        )

    def estimate_trade_cost(
        self,
        symbol: str,
        volume: float,
        direction: str,
    ) -> TradeCostEstimate:
        snapshot = self.get_symbol_cost_snapshot(symbol)
        normalized_direction = str(direction or "").strip().upper()
        normalized_volume = float(volume or 0.0)
        spread_cost = self._spread_money_estimate(
            spread_price=snapshot.spread_price,
            tick_value=snapshot.tick_value,
            tick_size=snapshot.tick_size,
            volume=normalized_volume,
        )
        swap_source = snapshot.swap_long if normalized_direction == "BUY" else snapshot.swap_short
        swap_expected = (
            None if swap_source is None else float(swap_source) * normalized_volume
        )
        unknown: list[str] = []
        if spread_cost is None:
            unknown.append("spread_cost")
        if swap_expected is None:
            unknown.append("swap_expected")
        unknown.extend(["commission", "fee"])
        known_components = [
            value for value in (spread_cost, swap_expected) if value is not None
        ]
        total = sum(known_components) if known_components else None
        return TradeCostEstimate(
            symbol=snapshot.symbol,
            volume=normalized_volume,
            direction=normalized_direction or "N/D",
            spread_cost=spread_cost,
            swap_expected=swap_expected,
            commission=None,
            fee=None,
            total_estimated_cost=total,
            unknown=tuple(dict.fromkeys(unknown)),
            snapshot=snapshot,
        )

    def get_real_trade_cost(
        self,
        position_id: int | None = None,
        ticket: int | None = None,
    ) -> RealTradeCost:
        records = self._provider_trade_cost_records(position_id=position_id, ticket=ticket)
        return self.real_trade_cost_from_records(records)

    @classmethod
    def real_trade_cost_from_records(
        cls,
        records: list[dict[str, Any]],
    ) -> RealTradeCost:
        commission = 0.0
        swap = 0.0
        fee = 0.0
        profit = 0.0
        tickets: list[int] = []
        for record in records:
            components = cls.trade_cost_components(record)
            commission += components["commission"]
            swap += components["swap"]
            fee += components["fee"]
            profit += components["profit"]
            ticket = cls._optional_int(record.get("ticket"))
            if ticket is not None:
                tickets.append(ticket)
        return RealTradeCost(
            commission=commission,
            swap=swap,
            fee=fee,
            profit=profit,
            net_profit=profit + commission + swap + fee,
            deals_count=len(records),
            tickets=tuple(tickets),
        )

    @classmethod
    def trade_cost_components(cls, record: dict[str, Any]) -> dict[str, float]:
        commission = cls._optional_float(record.get("commission")) or 0.0
        fee = cls._optional_float(record.get("fee")) or 0.0
        swap = cls._optional_float(record.get("swap")) or 0.0
        profit = cls._optional_float(record.get("profit")) or 0.0
        return {
            "commission": commission,
            "fee": fee,
            "swap": swap,
            "profit": profit,
            "open_cost": commission + fee + swap,
            "net_profit": profit + commission + fee + swap,
        }

    def _provider_symbol_cost_data(
        self,
        symbol: str,
        warnings: list[str],
    ) -> dict[str, Any]:
        if self.provider is None:
            warnings.append("provider indisponivel")
            return {}
        reader = getattr(self.provider, "get_symbol_cost_data", None)
        if callable(reader):
            try:
                data = reader(symbol)
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                warnings.append(f"falha ao ler custos MT5: {exc}")
                return {}
            return dict(data or {}) if isinstance(data, dict) else {}
        microstructure = getattr(self.provider, "get_symbol_microstructure", None)
        if callable(microstructure):
            try:
                data = microstructure(symbol)
            except (OSError, RuntimeError, ValueError, TypeError) as exc:
                warnings.append(f"falha ao ler microestrutura MT5: {exc}")
                return {}
            return dict(data or {}) if isinstance(data, dict) else {}
        warnings.append("provider sem leitura de custos")
        return {}

    def _provider_trade_cost_records(
        self,
        *,
        position_id: int | None,
        ticket: int | None,
    ) -> list[dict[str, Any]]:
        if self.provider is None:
            return []
        reader = getattr(self.provider, "get_trade_cost_records", None)
        if not callable(reader):
            return []
        try:
            records = reader(position_id=position_id, ticket=ticket)
        except (OSError, RuntimeError, ValueError, TypeError):
            return []
        if not isinstance(records, list):
            return []
        return [dict(record) for record in records if isinstance(record, dict)]

    @staticmethod
    def _spread_money_estimate(
        *,
        spread_price: float | None,
        tick_value: float | None,
        tick_size: float | None,
        volume: float,
    ) -> float | None:
        if (
            spread_price is None
            or tick_value is None
            or tick_size is None
            or tick_size <= 0.0
        ):
            return None
        return (spread_price / tick_size) * tick_value * float(volume or 0.0)

    @staticmethod
    def _optional_float(value: object) -> float | None:
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed

    @staticmethod
    def _optional_int(value: object) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
