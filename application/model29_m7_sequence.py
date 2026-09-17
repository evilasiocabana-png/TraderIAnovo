"""Causal M29/M7 sequence detector; no broker calls or live enablement."""

from __future__ import annotations

from dataclasses import dataclass, field
import math


@dataclass
class M7SequenceState:
    mode: str = "NORMAL"
    outcomes: list[str] = field(default_factory=list)
    seen: set[str] = field(default_factory=set)
    initialized: bool = False
    four_result_trigger: bool = False

    def record(self, position_id: str, net_profit: float) -> bool:
        """Call in close-time order, once the entire position is reconciled."""
        value = float(net_profit)
        if not position_id or not math.isfinite(value):
            raise ValueError("Resultado encerrado invalido")
        if position_id in self.seen:
            return False
        self.seen.add(position_id)
        self.outcomes.append("G" if value > 0 else "P" if value < 0 else "E")
        self.outcomes = self.outcomes[-6:]
        if self.four_result_trigger:
            recent = self.outcomes[-4:]
            next_mode = ("ESPELHADO" if recent == ["P"] * 4
                         else "NORMAL" if recent == ["G"] * 4 else None)
            if next_mode is not None and next_mode != self.mode:
                self.mode = next_mode
                self.outcomes.clear()
                return True
        prefix = "".join(self.outcomes[:4])
        tail = "".join(self.outcomes[4:])
        if len(self.outcomes) == 6 and prefix in {"GPGP", "PGPG"}:
            if self.mode == "NORMAL" and tail == "PP":
                self.mode = "ESPELHADO"
                self.outcomes.clear()
                return True
            if self.mode == "ESPELHADO" and tail == "GG":
                self.mode = "NORMAL"
                self.outcomes.clear()
                return True
        return False

    def bootstrap(self, closed_source_results: list[float]) -> None:
        """Classify the observed source sequence once; not a mirror backtest."""
        if self.initialized:
            return
        if self.seen:
            raise ValueError("Bootstrap deve preceder resultados M29")
        for index, value in enumerate(closed_source_results):
            self.record(f"seed:{index}", value)
        self.initialized = True


def mirrored_prices(direction: str, entry: float, original_stop: float) -> tuple[str, float, float]:
    """Return opposite direction, symmetric stop and original stop as target."""
    entry, original_stop = float(entry), float(original_stop)
    if not all(math.isfinite(p) and p > 0 for p in (entry, original_stop)):
        raise ValueError("Entrada e stop devem ser precos positivos finitos")
    side = str(direction).upper()
    if (side == "BUY" and original_stop < entry) or (side == "SELL" and original_stop > entry):
        stop = 2 * entry - original_stop
        if stop <= 0:
            raise ValueError("Stop espelhado invalido")
        return ("SELL" if side == "BUY" else "BUY", stop, original_stop)
    raise ValueError("Stop original no lado incorreto")
