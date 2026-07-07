"""Motor de decomposicao por regime da Alpha 001."""

from dataclasses import dataclass, field

from domain.contracts.strategy_signal import StrategySignal
from research.alpha001_experiment import Alpha001ExperimentResult


OFFICIAL_REGIMES = ("TREND", "RANGE", "VOLATILE", "LOW_LIQUIDITY")


@dataclass(frozen=True)
class Alpha001RegimeMetrics:
    """Metricas Alpha 001 consolidadas para um regime."""

    total_trades: int
    gross_profit: float
    gross_loss: float
    net_profit: float
    win_rate: float


@dataclass(frozen=True)
class Alpha001RegimeBreakdownResult:
    """Resultado da decomposicao Alpha 001 por regime."""

    regimes: dict[str, Alpha001RegimeMetrics] = field(default_factory=dict)


@dataclass(frozen=True)
class Alpha001RegimeBreakdownEngine:
    """Agrupa resultados por regime sem alterar estrategia ou metricas globais."""

    def calculate(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001RegimeBreakdownResult:
        """Consolida sinais do experimento nos regimes oficiais."""
        grouped = self._empty_breakdown()
        for signal in experiment_result.signals:
            regime = self._signal_regime(signal)
            grouped[regime] = grouped[regime] + self._trade_count(signal)

        return Alpha001RegimeBreakdownResult(
            regimes={
                regime: self._metrics(total_trades)
                for regime, total_trades in grouped.items()
            },
        )

    def _empty_breakdown(self) -> dict[str, int]:
        return {regime: 0 for regime in OFFICIAL_REGIMES}

    def _signal_regime(self, signal: StrategySignal) -> str:
        normalized_reasons = " ".join(signal.reasons).upper()
        for regime in OFFICIAL_REGIMES:
            if regime in normalized_reasons:
                return regime
        return "TREND"

    def _trade_count(self, signal: StrategySignal) -> int:
        if signal.decision in {"BUY", "SELL"}:
            return 1
        return 0

    def _metrics(self, total_trades: int) -> Alpha001RegimeMetrics:
        return Alpha001RegimeMetrics(
            total_trades=total_trades,
            gross_profit=0.0,
            gross_loss=0.0,
            net_profit=0.0,
            win_rate=0.0,
        )
