"""Motor de metricas estruturais da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_experiment import Alpha001ExperimentResult


@dataclass(frozen=True)
class Alpha001MetricsResult:
    """Metricas estruturais calculadas a partir do experimento Alpha 001."""

    total_trades: int
    total_buy: int
    total_sell: int
    total_wait: int


@dataclass(frozen=True)
class Alpha001MetricsEngine:
    """Transforma o resultado do experimento em metricas estruturais."""

    def calculate(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001MetricsResult:
        """Calcula metricas estruturais sem acessar camadas operacionais."""
        return Alpha001MetricsResult(
            total_trades=experiment_result.total_buy + experiment_result.total_sell,
            total_buy=experiment_result.total_buy,
            total_sell=experiment_result.total_sell,
            total_wait=experiment_result.total_wait,
        )
