"""Experimento controlado para a Alpha101."""

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
from strategies.alpha101.alpha101_config import Alpha101Config
from strategies.alpha101.alpha101_strategy import Alpha101Strategy


MarketContextFactory = Callable[[Candle], MarketContext]
FeatureReportFactory = Callable[[Candle], FeatureReport]


@dataclass(frozen=True)
class Alpha101ExperimentResult:
    """Resultado estrutural da execucao experimental da Alpha101."""

    total_candles: int
    total_signals: int
    total_buy: int
    total_sell: int
    total_wait: int
    execution_time_ms: float
    signals: tuple[StrategySignal, ...] = field(default_factory=tuple)


@dataclass
class Alpha101Experiment:
    """Executa replay da Alpha101 sem calcular metricas financeiras."""

    config: Alpha101Config
    candles: Sequence[Candle]
    strategy: Alpha101Strategy | None = None
    replay_engine: ReplayEngine | None = None
    research_pipeline: ResearchPipeline | None = None
    market_context_factory: MarketContextFactory | None = None
    feature_report_factory: FeatureReportFactory | None = None

    def run(self) -> Alpha101ExperimentResult:
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
        return Alpha101ExperimentResult(
            total_candles=len(self.candles),
            total_signals=len(generated),
            total_buy=self._count_decision(generated, "BUY"),
            total_sell=self._count_decision(generated, "SELL"),
            total_wait=self._count_decision(generated, "WAIT"),
            execution_time_ms=execution_time_ms,
            signals=generated,
        )

    def _strategy(self) -> Alpha101Strategy:
        if self.strategy is not None:
            return self.strategy
        return Alpha101Strategy(config=self.config)

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
                "research_validation_status": "PASSED",
                "research_confidence": 1.0,
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
                "trend_direction": self._trend_direction(candle),
                "pullback_depth": abs(
                    float(candle.fechamento) - float(candle.abertura),
                ),
                "volume": float(candle.volume),
                "volatility": float(candle.amplitude),
                "momentum": float(candle.fechamento) - float(candle.abertura),
                "data_quality_score": 1.0,
            },
            execution_time_ms=0.0,
        )

    def _trend_direction(self, candle: Candle) -> str:
        if candle.fechamento >= candle.abertura:
            return "UP"
        return "DOWN"

    def _count_decision(
        self,
        signals: tuple[StrategySignal, ...],
        decision: str,
    ) -> int:
        return sum(1 for signal in signals if signal.decision == decision)
