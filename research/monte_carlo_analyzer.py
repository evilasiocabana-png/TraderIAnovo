"""Analise Monte Carlo da Alpha001 usando trades existentes."""

from dataclasses import dataclass
import random
from typing import Iterable


@dataclass(frozen=True)
class MonteCarloResult:
    """Resultado consolidado da simulacao Monte Carlo."""

    monte_carlo_score: float
    worst_drawdown: float
    average_net_profit: float
    ruin_probability: float
    status: str


@dataclass(frozen=True)
class MonteCarloAnalyzer:
    """Executa Monte Carlo sem rodar novos experimentos."""

    seed: int | None = None
    ruin_threshold: float = -300.0
    fragile_ruin_probability: float = 0.25
    fragile_drawdown_ratio: float = 0.75

    def analyze(
        self,
        trades: Iterable[object],
        simulations: int,
    ) -> MonteCarloResult:
        """Embaralha trades existentes e consolida risco simulado."""
        trade_results = self._trade_results(trades)
        if not trade_results or simulations <= 0:
            return MonteCarloResult(
                monte_carlo_score=0.0,
                worst_drawdown=0.0,
                average_net_profit=0.0,
                ruin_probability=0.0,
                status="INCONCLUSIVE",
            )
        simulation_results = self._simulate(trade_results, simulations)
        ruin_probability = self._ruin_probability(simulation_results)
        worst_drawdown = max(result["drawdown"] for result in simulation_results)
        average_net_profit = self._average(
            [result["net_profit"] for result in simulation_results]
        )
        score = self._score(trade_results, worst_drawdown, ruin_probability)
        return MonteCarloResult(
            monte_carlo_score=score,
            worst_drawdown=worst_drawdown,
            average_net_profit=average_net_profit,
            ruin_probability=ruin_probability,
            status=self._status(score, ruin_probability, trade_results),
        )

    def _trade_results(self, trades: Iterable[object]) -> list[float]:
        return [self._trade_value(trade) for trade in trades]

    def _trade_value(self, trade: object) -> float:
        if isinstance(trade, (int, float)):
            return float(trade)
        if isinstance(trade, dict):
            return float(
                trade.get(
                    "result_points",
                    trade.get("net_profit_points", trade.get("profit", 0.0)),
                )
            )
        return float(
            getattr(
                trade,
                "result_points",
                getattr(trade, "net_profit_points", getattr(trade, "profit", 0.0)),
            )
        )

    def _simulate(
        self,
        trades: list[float],
        simulations: int,
    ) -> list[dict[str, float | bool]]:
        rng = random.Random(self.seed)
        results: list[dict[str, float | bool]] = []
        for _ in range(simulations):
            sequence = list(trades)
            rng.shuffle(sequence)
            results.append(self._simulate_sequence(sequence))
        return results

    def _simulate_sequence(self, trades: list[float]) -> dict[str, float | bool]:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        min_equity = 0.0
        for trade in trades:
            equity += trade
            peak = max(peak, equity)
            min_equity = min(min_equity, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return {
            "drawdown": max_drawdown,
            "net_profit": equity,
            "ruined": min_equity <= self.ruin_threshold,
        }

    def _ruin_probability(
        self,
        simulation_results: list[dict[str, float | bool]],
    ) -> float:
        ruined = sum(1 for result in simulation_results if result["ruined"])
        return ruined / len(simulation_results)

    def _score(
        self,
        trades: list[float],
        worst_drawdown: float,
        ruin_probability: float,
    ) -> float:
        drawdown_penalty = self._drawdown_penalty(trades, worst_drawdown)
        ruin_penalty = ruin_probability * 100.0
        return max(0.0, 100.0 - drawdown_penalty - ruin_penalty)

    def _drawdown_penalty(
        self,
        trades: list[float],
        worst_drawdown: float,
    ) -> float:
        gross_profit = sum(trade for trade in trades if trade > 0)
        if gross_profit <= 0:
            return 100.0 if worst_drawdown > 0 else 0.0
        return min((worst_drawdown / gross_profit) * 100.0, 100.0)

    def _status(
        self,
        score: float,
        ruin_probability: float,
        trades: list[float],
    ) -> str:
        if len(trades) < 2:
            return "INCONCLUSIVE"
        if score >= 70.0 and ruin_probability < self.fragile_ruin_probability:
            return "ROBUST"
        return "FRAGILE"

    def _average(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)
