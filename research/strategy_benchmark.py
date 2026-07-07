"""Benchmark quantitativo isolado de estrategias em replay."""

from dataclasses import dataclass

from domain.candle import Candle
from strategies.base import Strategy


@dataclass(frozen=True)
class StrategyBenchmarkResult:
    """Resultado quantitativo de uma estrategia em replay."""

    strategy_name: str
    total_trades: int
    wins: int
    losses: int
    net_profit_points: float
    win_rate: float
    profit_factor: float
    max_drawdown_points: float
    equity_curve: list[float]


@dataclass(frozen=True)
class StrategyBenchmark:
    """Executa benchmark de uma estrategia por vez."""

    def run(
        self,
        strategy: Strategy,
        candles: list[Candle],
    ) -> StrategyBenchmarkResult:
        """Executa a estrategia em replay e retorna metricas paper."""
        replay_data = self._run_replay(strategy, candles)
        return self._to_result(strategy, replay_data)

    def _run_replay(
        self,
        strategy: Strategy,
        candles: list[Candle],
    ) -> object:
        from application.replay_service import ReplayService

        replay_service = ReplayService(strategy=strategy)
        replay_service.replay_engine.load_candles(list(candles))
        replay_service.status = self._initial_status(candles)
        data = replay_service.get_replay_data()
        while candles and not data.is_finished:
            data = replay_service.next_candle()
        return data

    def _initial_status(self, candles: list[Candle]) -> object:
        from application.replay_service import ReplayStatus

        if candles:
            return ReplayStatus.READY
        return ReplayStatus.EMPTY

    def _to_result(
        self,
        strategy: Strategy,
        replay_data: object,
    ) -> StrategyBenchmarkResult:
        metrics = replay_data.paper_metrics
        return StrategyBenchmarkResult(
            strategy_name=self._strategy_name(strategy),
            total_trades=metrics.total_trades,
            wins=metrics.wins,
            losses=metrics.losses,
            net_profit_points=float(metrics.net_profit_points),
            win_rate=float(metrics.win_rate),
            profit_factor=float(metrics.profit_factor),
            max_drawdown_points=float(metrics.max_drawdown_points),
            equity_curve=list(replay_data.paper_equity_curve),
        )

    def _strategy_name(self, strategy: Strategy) -> str:
        return getattr(strategy, "nome", strategy.__class__.__name__)
