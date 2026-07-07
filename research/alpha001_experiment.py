"""Experimento controlado para a Alpha 001."""

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable, Sequence

from alpha.alpha001_config import Alpha001Config
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.strategy_signal import StrategySignal
from strategies.alpha001_iorb_strategy import Alpha001IORBStrategy


MarketSnapshotFactory = Callable[[Any], MarketSnapshot]


@dataclass(frozen=True)
class Alpha001ExperimentResult:
    """Resultado estrutural da execucao experimental da Alpha 001."""

    total_candles: int
    total_signals: int
    total_buy: int
    total_sell: int
    total_wait: int
    execution_time_ms: float
    signals: tuple[StrategySignal, ...] = field(default_factory=tuple)


@dataclass
class Alpha001Experiment:
    """Executa uma configuracao da Alpha 001 sobre uma sequencia de candles."""

    config: Alpha001Config
    candles: Sequence[Any]
    strategy: Alpha001IORBStrategy | None = None
    market_snapshot_factory: MarketSnapshotFactory | None = None

    def run(self) -> Alpha001ExperimentResult:
        """Executa a Alpha 001 candle a candle e consolida sinais gerados."""
        start = perf_counter()
        signals = tuple(self._generate_signals())
        execution_time_ms = (perf_counter() - start) * 1000
        return Alpha001ExperimentResult(
            total_candles=len(self.candles),
            total_signals=len(signals),
            total_buy=self._count_decision(signals, "BUY"),
            total_sell=self._count_decision(signals, "SELL"),
            total_wait=self._count_decision(signals, "WAIT"),
            execution_time_ms=execution_time_ms,
            signals=signals,
        )

    def _generate_signals(self) -> list[StrategySignal]:
        strategy = self._strategy()
        generated: list[StrategySignal] = []
        for index, candle in enumerate(self.candles):
            candle_window = self.candles[: index + 1]
            generated.append(
                strategy.generate_signal(
                    candles=candle_window,
                    market_snapshot=self._market_snapshot(candle),
                    current_price=float(candle.fechamento),
                    config=self.config,
                )
            )
        return generated

    def _strategy(self) -> Alpha001IORBStrategy:
        if self.strategy is not None:
            return self.strategy
        return Alpha001IORBStrategy(config=self.config)

    def _market_snapshot(self, candle: Any) -> MarketSnapshot:
        if self.market_snapshot_factory is not None:
            return self.market_snapshot_factory(candle)
        return MarketSnapshot(
            symbol="WDO",
            datetime=str(candle.data),
            regime="TREND",
            volatility=float(candle.maxima) - float(candle.minima),
            liquidity=float(candle.volume),
            trend_strength=1.0,
            market_dna_score=100.0,
        )

    def _count_decision(
        self,
        signals: tuple[StrategySignal, ...],
        decision: str,
    ) -> int:
        return sum(1 for signal in signals if signal.decision == decision)
