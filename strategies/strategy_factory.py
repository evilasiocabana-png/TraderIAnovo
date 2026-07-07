"""Factory oficial para instanciar estrategias registradas."""

from dataclasses import dataclass, field
from typing import Type

from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy
from strategies.alpha101.alpha101_strategy import Alpha101Strategy
from strategies.base import Strategy
from strategies.breakout import BreakoutStrategy
from strategies.pullback import PullbackStrategy
from strategies.score_contexto import ScoreContextoStrategy
from strategies.smart_money import SmartMoneyStrategy


@dataclass(frozen=True)
class StrategyFactory:
    """Cria estrategias pelo nome oficial registrado."""

    registry: dict[str, Type[Strategy]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.registry:
            object.__setattr__(self, "registry", self._default_registry())

    def create(self, strategy_name: str) -> Strategy:
        """Instancia uma estrategia registrada."""
        normalized = strategy_name.strip().lower()
        strategy_class = self.registry.get(normalized)
        if strategy_class is None:
            raise ValueError(f"Estrategia desconhecida: {strategy_name}")
        return strategy_class()

    def list_available(self) -> list[str]:
        """Lista nomes oficiais das estrategias registradas."""
        return sorted(self.registry.keys())

    def create_all(self) -> list[Strategy]:
        """Instancia todas as estrategias registradas."""
        return [self.create(name) for name in self.list_available()]

    def _default_registry(self) -> dict[str, Type[Strategy]]:
        return dict(
            alpha001_iorb=Alpha001IORBStrategy,
            alpha101=Alpha101Strategy,
            breakout=BreakoutStrategy,
            pullback=PullbackStrategy,
            score_contexto=ScoreContextoStrategy,
            smart_money=SmartMoneyStrategy,
        )
