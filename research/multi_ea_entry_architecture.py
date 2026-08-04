"""Reconstrucao estrutural, baseada somente nas entradas, do Multi EA Trading.

O objetivo deste modulo nao e adivinhar o codigo privado do fornecedor. Ele
mede comportamentos que deixam uma assinatura observavel no extrato: tickets
fracionados, hedge simultaneo, sequencias de grade, piramidagem e cestas entre
ativos. Campos de saida e resultado financeiro sao deliberadamente ignorados.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Mapping, Sequence

from research.multi_ea_trading_lab import MultiEATradePosition


@dataclass(frozen=True)
class MultiEAEntryArchitectureConfiguration:
    """Janelas conservadoras usadas para identificar mecanicas observaveis."""

    split_seconds: int = 90
    basket_seconds: int = 300
    sequence_hours: int = 6
    same_level_bps: float = 3.0


class MultiEAEntryArchitectureEngine:
    """Classifica cada entrada por sua relacao com entradas anteriores."""

    def __init__(
        self,
        configuration: MultiEAEntryArchitectureConfiguration | None = None,
    ) -> None:
        self.configuration = (
            configuration or MultiEAEntryArchitectureConfiguration()
        )
        if self.configuration.split_seconds < 1:
            raise ValueError("split_seconds deve ser positivo.")
        if self.configuration.basket_seconds < 1:
            raise ValueError("basket_seconds deve ser positivo.")
        if self.configuration.sequence_hours < 1:
            raise ValueError("sequence_hours deve ser positivo.")
        if self.configuration.same_level_bps < 0:
            raise ValueError("same_level_bps nao pode ser negativo.")

    def analyze(
        self,
        positions: Sequence[MultiEATradePosition],
    ) -> dict[str, object]:
        """Retorna a arquitetura observavel sem ler fechamentos ou P&L."""

        ordered = sorted(positions, key=lambda item: _time_key(item.open_time))
        if not ordered:
            return self._empty_report()

        sequence_window = timedelta(hours=self.configuration.sequence_hours)
        split_window = timedelta(seconds=self.configuration.split_seconds)
        basket_window = timedelta(seconds=self.configuration.basket_seconds)
        previous_by_symbol: dict[str, MultiEATradePosition] = {}
        classifications: list[dict[str, object]] = []
        primary_counts: Counter[str] = Counter()
        cross_asset_followers = 0
        same_second_entries = 0
        prior_entry: MultiEATradePosition | None = None

        symbol_rows: dict[str, list[MultiEATradePosition]] = defaultdict(list)
        same_side_gaps: dict[str, list[tuple[float, float, str]]] = defaultdict(list)

        for position in ordered:
            symbol = str(position.symbol).strip().upper()
            direction = str(getattr(position, "direction", "")).strip().upper()
            now = _time_key(position.open_time)
            previous = previous_by_symbol.get(symbol)
            relation = "SEED"
            gap_seconds: float | None = None
            gap_bps: float | None = None
            adverse: bool | None = None

            if previous is not None:
                gap = now - _time_key(previous.open_time)
                if timedelta(0) <= gap <= sequence_window:
                    gap_seconds = gap.total_seconds()
                    gap_bps = _absolute_bps(
                        float(getattr(position, "open_price", 0.0) or 0.0),
                        float(getattr(previous, "open_price", 0.0) or 0.0),
                    )
                    previous_direction = str(
                        getattr(previous, "direction", "")
                    ).strip().upper()
                    same_side = direction == previous_direction
                    if gap <= split_window and gap_bps <= self.configuration.same_level_bps:
                        relation = "SPLIT_TICKET" if same_side else "HEDGE_PAIR"
                    elif same_side:
                        adverse = _is_adverse_move(
                            direction,
                            previous_price=float(
                                getattr(previous, "open_price", 0.0) or 0.0
                            ),
                            current_price=float(
                                getattr(position, "open_price", 0.0) or 0.0
                            ),
                        )
                        if gap_bps <= self.configuration.same_level_bps:
                            relation = "SAME_LEVEL_REENTRY"
                        elif adverse:
                            relation = "GRID_AVERAGING"
                        else:
                            relation = "PYRAMIDING"
                        same_side_gaps[symbol].append(
                            (gap_seconds, gap_bps, relation)
                        )
                    else:
                        relation = "OPPOSITE_ROTATION"

            cross_asset_basket = False
            if prior_entry is not None:
                prior_time = _time_key(prior_entry.open_time)
                if (
                    timedelta(0) <= now - prior_time <= basket_window
                    and str(prior_entry.symbol).strip().upper() != symbol
                ):
                    cross_asset_basket = True
                    cross_asset_followers += 1
                if now == prior_time:
                    same_second_entries += 1

            primary_counts[relation] += 1
            source_row = int(getattr(position, "source_row", 0) or 0)
            position_id = str(getattr(position, "position_id", "") or source_row)
            classifications.append(
                {
                    "position_id": position_id,
                    "source_row": source_row,
                    "symbol": symbol,
                    "direction": direction,
                    "open_time": position.open_time.isoformat(),
                    "open_price": float(
                        getattr(position, "open_price", 0.0) or 0.0
                    ),
                    "volume": float(getattr(position, "volume", 0.0) or 0.0),
                    "primary_mechanic": relation,
                    "previous_same_symbol_gap_seconds": gap_seconds,
                    "previous_same_symbol_gap_bps": gap_bps,
                    "adverse_move": adverse,
                    "cross_asset_basket": cross_asset_basket,
                }
            )
            previous_by_symbol[symbol] = position
            prior_entry = position
            symbol_rows[symbol].append(position)

        volume_counts = Counter(
            round(float(getattr(item, "volume", 0.0) or 0.0), 8)
            for item in ordered
        )
        base_lot, base_lot_count = sorted(
            volume_counts.items(), key=lambda item: (-item[1], item[0])
        )[0]
        hedge_evidence = primary_counts["HEDGE_PAIR"] > 0
        follower_count = len(ordered) - primary_counts["SEED"]
        per_symbol = {
            symbol: _symbol_summary(
                rows,
                same_side_gaps.get(symbol, ()),
                base_lot=base_lot,
            )
            for symbol, rows in sorted(symbol_rows.items())
        }

        return {
            "schema_version": "multi_ea_entry_architecture_v1",
            "status": "OK",
            "name": "Multi EA Trading",
            "timeframe_context": "M15",
            "uses_exit_data": False,
            "uses_profit_data": False,
            "research_only": True,
            "operational_eligible": False,
            "configuration": {
                "split_seconds": self.configuration.split_seconds,
                "basket_seconds": self.configuration.basket_seconds,
                "sequence_hours": self.configuration.sequence_hours,
                "same_level_bps": self.configuration.same_level_bps,
            },
            "observed_architecture": {
                "portfolio_form": "MULTI_EA_STATEFUL_COMPATIBLE",
                "account_mode": "HEDGING_COMPATIBLE" if hedge_evidence else "UNDETERMINED",
                "execution_clock": "TICK_OR_M1_REQUIRED_FOR_EXACT_REPLAY",
                "base_lot": base_lot,
                "base_lot_share_percent": _percent(base_lot_count, len(ordered)),
                "lot_levels": [
                    {"volume": lot, "entries": count}
                    for lot, count in sorted(volume_counts.items())
                ],
                "compatible_mechanics": [
                    mechanic
                    for mechanic in (
                        "SPLIT_TICKET",
                        "HEDGE_PAIR",
                        "GRID_AVERAGING",
                        "PYRAMIDING",
                        "OPPOSITE_ROTATION",
                        "CROSS_ASSET_BASKET",
                    )
                    if (
                        cross_asset_followers > 0
                        if mechanic == "CROSS_ASSET_BASKET"
                        else primary_counts[mechanic] > 0
                    )
                ],
            },
            "evidence": {
                "entries": len(ordered),
                "seed_entries": primary_counts["SEED"],
                "stateful_followers": follower_count,
                "stateful_follower_share_percent": _percent(follower_count, len(ordered)),
                "primary_mechanic_counts": dict(sorted(primary_counts.items())),
                "cross_asset_basket_followers": cross_asset_followers,
                "same_timestamp_as_previous_entries": same_second_entries,
                "symbols": len(symbol_rows),
            },
            "per_symbol": per_symbol,
            "entry_records": classifications,
            "interpretation": {
                "compatible_patterns": (
                    "Padroes compativeis com um portfolio de EAs com estado, "
                    "hedge, tickets fracionados, grade/piramidagem e cestas "
                    "entre ativos."
                ),
                "not_identified": (
                    "Gatilho privado de cada entrada-semente, magic/comment, "
                    "spread/tick de execucao e codigo-fonte."
                ),
                "claim_limit": "ARQUITETURA_OBSERVAVEL_NAO_CODIGO_ORIGINAL",
            },
            "warnings": [
                "ENTRADAS_SOMENTE: fechamentos, lucro, swap e comissao nao sao lidos.",
                (
                    "M15 fornece contexto; segundos e precos exatos exigem tick/M1 "
                    "e o feed da corretora."
                ),
                (
                    "SEED nao significa operacao manual; significa apenas que nao ha "
                    "entrada anterior do mesmo ativo dentro da janela analisada."
                ),
                (
                    "CLASSIFICACAO_POS_EVENTO: split, hedge, grade, piramidagem e "
                    "cesta sao rotulos descritivos aplicados depois de observar as "
                    "entradas; nao provam a configuracao nem o modo da conta original."
                ),
                (
                    "ARQUITETURA_NAO_ACIONA_OS_GATILHOS: este modulo nao simula a "
                    "entrada-semente seguida de ordens condicionais e, portanto, nao "
                    "constitui um setup causal completo."
                ),
            ],
        }

    run = analyze

    def _empty_report(self) -> dict[str, object]:
        return {
            "schema_version": "multi_ea_entry_architecture_v1",
            "status": "SEM_ENTRADAS",
            "name": "Multi EA Trading",
            "timeframe_context": "M15",
            "uses_exit_data": False,
            "uses_profit_data": False,
            "research_only": True,
            "operational_eligible": False,
            "configuration": {
                "split_seconds": self.configuration.split_seconds,
                "basket_seconds": self.configuration.basket_seconds,
                "sequence_hours": self.configuration.sequence_hours,
                "same_level_bps": self.configuration.same_level_bps,
            },
            "observed_architecture": {},
            "evidence": {"entries": 0},
            "per_symbol": {},
            "entry_records": [],
            "warnings": ["SEM_ENTRADAS: nenhuma amostra foi informada."],
        }


def _symbol_summary(
    rows: Sequence[MultiEATradePosition],
    gaps: Sequence[tuple[float, float, str]],
    *,
    base_lot: float,
) -> dict[str, object]:
    directions = Counter(
        str(getattr(item, "direction", "")).strip().upper() for item in rows
    )
    volumes = Counter(
        round(float(getattr(item, "volume", 0.0) or 0.0), 8)
        for item in rows
    )
    gap_seconds = [item[0] for item in gaps]
    gap_bps = [item[1] for item in gaps]
    relationships = Counter(item[2] for item in gaps)
    return {
        "entries": len(rows),
        "buy": directions.get("BUY", 0),
        "sell": directions.get("SELL", 0),
        "base_lot_entries": volumes.get(base_lot, 0),
        "lot_levels": [
            {"volume": lot, "entries": count}
            for lot, count in sorted(volumes.items())
        ],
        "same_side_sequence_count": len(gaps),
        "median_same_side_gap_seconds": _rounded_median(gap_seconds),
        "median_same_side_gap_bps": _rounded_median(gap_bps),
        "sequence_mechanics": dict(sorted(relationships.items())),
    }


def _absolute_bps(current: float, previous: float) -> float:
    denominator = abs(previous)
    if denominator <= 0:
        return 0.0
    return abs(current - previous) / denominator * 10_000.0


def _is_adverse_move(direction: str, *, previous_price: float, current_price: float) -> bool:
    if direction == "BUY":
        return current_price < previous_price
    if direction == "SELL":
        return current_price > previous_price
    return False


def _rounded_median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    return round(float(median(values)), 6)


def _percent(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100.0, 6) if denominator else 0.0


def _time_key(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


__all__ = [
    "MultiEAEntryArchitectureConfiguration",
    "MultiEAEntryArchitectureEngine",
]
