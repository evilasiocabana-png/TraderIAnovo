"""Engine oficial de validacao Monte Carlo."""

from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Iterable

from research.campaigns.campaign_runner import CampaignRunner
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.research_pipeline import ResearchPipeline
from research.research_runner import ResearchRunner
from research.validation.monte_carlo.monte_carlo_profile import MonteCarloProfile


BOOTSTRAP_TRADES = "BOOTSTRAP_TRADES"


@dataclass(frozen=True)
class MonteCarloResult:
    """Resultado deterministico da validacao Monte Carlo."""

    campaign_id: str
    profile: MonteCarloProfile
    executed_experiments: tuple[ExperimentDefinition, ...]
    total_simulations: int
    simulated_returns: tuple[float, ...]
    simulated_drawdowns: tuple[float, ...]
    average_return: float
    worst_return: float
    best_return: float
    confidence_level: float


@dataclass(frozen=True)
class MonteCarloEngine:
    """Executa simulacoes Monte Carlo sem recalcular metricas individuais."""

    campaign_runner: CampaignRunner
    research_runner: ResearchRunner
    research_pipeline: ResearchPipeline

    def run(
        self,
        campaign: ResearchCampaign,
        profile: MonteCarloProfile,
    ) -> MonteCarloResult:
        """Executa campanha e simula reamostragens deterministicas de trades."""
        executed = self.campaign_runner.run(campaign)
        trades = self._trades(campaign)
        simulated_paths = self._simulate_paths(trades, profile)
        simulated_returns = tuple(sum(path) for path in simulated_paths)
        simulated_drawdowns = tuple(
            self._max_drawdown(path)
            for path in simulated_paths
        )
        return MonteCarloResult(
            campaign_id=campaign.campaign_id,
            profile=profile,
            executed_experiments=executed,
            total_simulations=len(simulated_paths),
            simulated_returns=simulated_returns,
            simulated_drawdowns=simulated_drawdowns,
            average_return=self._average(simulated_returns),
            worst_return=min(simulated_returns) if simulated_returns else 0.0,
            best_return=max(simulated_returns) if simulated_returns else 0.0,
            confidence_level=profile.confidence_level,
        )

    def _simulate_paths(
        self,
        trades: tuple[float, ...],
        profile: MonteCarloProfile,
    ) -> tuple[tuple[float, ...], ...]:
        if not trades or profile.simulations <= 0:
            return ()
        randomizer = Random(profile.random_seed)
        return tuple(
            self._bootstrap(trades, randomizer)
            if profile.resampling_method == BOOTSTRAP_TRADES
            else self._reordered(trades, randomizer)
            for _ in range(profile.simulations)
        )

    def _bootstrap(
        self,
        trades: tuple[float, ...],
        randomizer: Random,
    ) -> tuple[float, ...]:
        return tuple(randomizer.choice(trades) for _ in trades)

    def _reordered(
        self,
        trades: tuple[float, ...],
        randomizer: Random,
    ) -> tuple[float, ...]:
        reordered = list(trades)
        randomizer.shuffle(reordered)
        return tuple(reordered)

    def _trades(self, campaign: ResearchCampaign) -> tuple[float, ...]:
        raw_trades = campaign.metadata.get("trades", ())
        if isinstance(raw_trades, str):
            return ()
        if not isinstance(raw_trades, Iterable):
            return ()
        trades: list[float] = []
        for value in raw_trades:
            if isinstance(value, (int, float)):
                trades.append(float(value))
        return tuple(trades)

    def _max_drawdown(self, trades: tuple[float, ...]) -> float:
        peak = 0.0
        equity = 0.0
        drawdown = 0.0
        for trade in trades:
            equity += trade
            peak = max(peak, equity)
            drawdown = max(drawdown, peak - equity)
        return drawdown

    def _average(self, values: tuple[float, ...]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)
