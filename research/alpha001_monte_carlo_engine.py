"""Motor Monte Carlo da Alpha 001 usando resultados ja calculados."""

from dataclasses import dataclass
import random
from statistics import median

from research.alpha001_research_report import Alpha001ResearchResult


@dataclass(frozen=True)
class Alpha001MonteCarloResult:
    """Resultado consolidado da simulacao Monte Carlo Alpha 001."""

    total_simulations: int
    average_net_profit: float
    median_net_profit: float
    worst_simulation: float
    best_simulation: float
    average_drawdown: float


@dataclass(frozen=True)
class Alpha001MonteCarloEngine:
    """Simula reordenacoes aleatorias sem modificar o resultado original."""

    total_simulations: int = 100
    seed: int | None = None

    def calculate(
        self,
        research_result: Alpha001ResearchResult,
    ) -> Alpha001MonteCarloResult:
        """Executa simulacoes Monte Carlo a partir das operacoes agregadas."""
        trades = self._trade_results(research_result)
        if not trades or self.total_simulations <= 0:
            return Alpha001MonteCarloResult(
                total_simulations=0,
                average_net_profit=0.0,
                median_net_profit=0.0,
                worst_simulation=0.0,
                best_simulation=0.0,
                average_drawdown=0.0,
            )

        simulations = self._simulate(trades)
        net_profits = [result.net_profit for result in simulations]
        drawdowns = [result.drawdown for result in simulations]
        return Alpha001MonteCarloResult(
            total_simulations=len(simulations),
            average_net_profit=self._average(net_profits),
            median_net_profit=float(median(net_profits)),
            worst_simulation=min(net_profits),
            best_simulation=max(net_profits),
            average_drawdown=self._average(drawdowns),
        )

    def _trade_results(self, research_result: Alpha001ResearchResult) -> list[float]:
        wins = [
            max(float(research_result.expectancy.average_win), 0.0)
            for _ in range(research_result.win_rate.winning_trades)
        ]
        losses = [
            -abs(float(research_result.expectancy.average_loss))
            for _ in range(research_result.win_rate.losing_trades)
        ]
        breakevens = [
            0.0
            for _ in range(research_result.win_rate.breakeven_trades)
        ]
        return [*wins, *losses, *breakevens]

    def _simulate(self, trades: list[float]) -> list["_SimulationResult"]:
        rng = random.Random(self.seed)
        simulations: list[_SimulationResult] = []
        for _ in range(self.total_simulations):
            sequence = list(trades)
            rng.shuffle(sequence)
            simulations.append(self._simulate_sequence(sequence))
        return simulations

    def _simulate_sequence(self, trades: list[float]) -> "_SimulationResult":
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for trade in trades:
            equity += trade
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return _SimulationResult(net_profit=equity, drawdown=max_drawdown)

    def _average(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return float(sum(values) / len(values))


@dataclass(frozen=True)
class _SimulationResult:
    """Resultado interno de uma simulacao."""

    net_profit: float
    drawdown: float
