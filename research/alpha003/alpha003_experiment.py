"""Experimento controlado para a Alpha003."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable, Sequence

from domain.candle import Candle
from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from replay.replay_engine import ReplayEngine
from research.research_pipeline import ResearchPipeline
from strategies.alpha003.alpha003_config import Alpha003Config
from strategies.alpha003.alpha003_strategy import Alpha003Strategy


MarketContextFactory = Callable[[Candle], MarketContext]
FeatureReportFactory = Callable[[Candle], FeatureReport]


@dataclass(frozen=True)
class Alpha003ExperimentResult:
    """Resultado estrutural da execucao experimental da Alpha003."""

    total_candles: int
    total_signals: int
    total_buy: int
    total_sell: int
    total_wait: int
    execution_time_ms: float
    signals: tuple[StrategySignal, ...] = field(default_factory=tuple)


@dataclass
class Alpha003Experiment:
    """Executa replay da Alpha003 sem calcular metricas financeiras."""

    config: Alpha003Config
    candles: Sequence[Candle]
    strategy: Alpha003Strategy | None = None
    replay_engine: ReplayEngine | None = None
    research_pipeline: ResearchPipeline | None = None
    market_context_factory: MarketContextFactory | None = None
    feature_report_factory: FeatureReportFactory | None = None

    def run(self) -> Alpha003ExperimentResult:
        """Executa replay candle a candle e consolida sinais estruturais."""
        start = perf_counter()
        replay = self._replay_engine()
        replay.load_candles(list(self.candles))
        replay.start()

        signals: list[StrategySignal] = []
        while replay.is_running:
            candle = replay.next_candle()
            if candle is None:
                break
            signals.append(
                self._strategy().generate_signal(
                    self._market_context(candle),
                    self._feature_report(candle),
                )
            )

        generated = tuple(signals)
        execution_time_ms = (perf_counter() - start) * 1000
        return Alpha003ExperimentResult(
            total_candles=len(self.candles),
            total_signals=len(generated),
            total_buy=self._count_decision(generated, "BUY"),
            total_sell=self._count_decision(generated, "SELL"),
            total_wait=self._count_decision(generated, "WAIT"),
            execution_time_ms=execution_time_ms,
            signals=generated,
        )

    def _strategy(self) -> Alpha003Strategy:
        if self.strategy is not None:
            return self.strategy
        return Alpha003Strategy(config=self.config)

    def _replay_engine(self) -> ReplayEngine:
        if self.replay_engine is not None:
            return self.replay_engine
        return ReplayEngine()

    def _research_pipeline(self) -> ResearchPipeline:
        if self.research_pipeline is not None:
            return self.research_pipeline
        return ResearchPipeline()

    def _market_context(self, candle: Candle) -> MarketContext:
        if self.market_context_factory is not None:
            return self.market_context_factory(candle)
        return MarketContext(
            timestamp=str(candle.data),
            regime="TREND",
            volatility=float(candle.amplitude),
            liquidity=float(candle.volume),
            momentum=float(candle.fechamento) - float(candle.abertura),
            session="REGULAR",
            market_dna={},
            confidence=1.0,
            metadata={
                "decision_approval_score": 1.0,
                "risk_policy_decision": "ALLOW",
            },
        )

    def _feature_report(self, candle: Candle) -> FeatureReport:
        if self.feature_report_factory is not None:
            return self.feature_report_factory(candle)
        return FeatureReport(
            feature_definitions=(),
            validation_results=(),
            calculated_values={
                "price": float(candle.fechamento),
                "opening_range_high": float(candle.maxima),
                "opening_range_low": float(candle.minima),
                "volume": float(candle.volume),
                "volatility": float(candle.amplitude),
                "momentum": float(candle.fechamento) - float(candle.abertura),
                "data_quality_score": 1.0,
            },
            execution_time_ms=0.0,
        )

    def _count_decision(
        self,
        signals: tuple[StrategySignal, ...],
        decision: str,
    ) -> int:
        return sum(1 for signal in signals if signal.decision == decision)
