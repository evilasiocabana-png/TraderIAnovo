"""Experimento live em memoria para sinais do Live Research."""

from __future__ import annotations

from dataclasses import dataclass, field

from domain.contracts.strategy_signal import StrategySignal


@dataclass(frozen=True)
class LiveExperimentSignal:
    """Registro read-only de um sinal produzido em sessao live."""

    timestamp: str
    symbol: str
    timeframe: str
    strategy_name: str
    decision: str
    confidence: float
    regime: str


@dataclass(frozen=True)
class LiveExperimentSummary:
    """Resumo estatistico dos sinais live em memoria."""

    total_signals: int = 0
    buy_count: int = 0
    sell_count: int = 0
    wait_count: int = 0
    average_confidence: float = 0.0
    confidence_std: float = 0.0
    by_regime: dict[str, int] = field(default_factory=dict)
    by_strategy: dict[str, int] = field(default_factory=dict)


@dataclass
class LiveExperimentRunner:
    """Registra sinais live e calcula estatisticas sem avaliar resultado."""

    signals: list[LiveExperimentSignal] = field(default_factory=list)

    def record_signal(
        self,
        strategy_signal: StrategySignal,
        timestamp: str,
        symbol: str,
        timeframe: str,
        strategy_name: str,
        regime: str,
    ) -> LiveExperimentSignal:
        """Registra um StrategySignal no experimento live em memoria."""
        record = LiveExperimentSignal(
            timestamp=timestamp,
            symbol=symbol,
            timeframe=timeframe,
            strategy_name=strategy_name,
            decision=strategy_signal.decision,
            confidence=float(strategy_signal.confidence),
            regime=regime,
        )
        self.signals.append(record)
        return record

    def list_signals(self) -> list[LiveExperimentSignal]:
        """Lista copia dos sinais do experimento live."""
        return list(self.signals)

    def summary(self) -> LiveExperimentSummary:
        """Calcula estatisticas da sessao live em memoria."""
        if not self.signals:
            return LiveExperimentSummary()

        decisions = [signal.decision.upper() for signal in self.signals]
        confidences = [signal.confidence for signal in self.signals]
        return LiveExperimentSummary(
            total_signals=len(self.signals),
            buy_count=decisions.count("BUY"),
            sell_count=decisions.count("SELL"),
            wait_count=decisions.count("WAIT"),
            average_confidence=sum(confidences) / len(confidences),
            confidence_std=self._population_std(confidences),
            by_regime=self._distribution("regime"),
            by_strategy=self._distribution("strategy_name"),
        )

    def clear(self) -> None:
        """Limpa somente a memoria do experimento live."""
        self.signals.clear()

    def _distribution(self, field_name: str) -> dict[str, int]:
        distribution: dict[str, int] = {}
        for signal in self.signals:
            key = str(getattr(signal, field_name))
            distribution[key] = distribution.get(key, 0) + 1
        return distribution

    def _population_std(self, values: list[float]) -> float:
        if not values:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        return variance**0.5
