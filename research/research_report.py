"""Relatorio consolidado de um experimento de pesquisa."""

from dataclasses import asdict, dataclass, field, is_dataclass
from typing import Any

from research.alpha001_experiment import Alpha001ExperimentResult


@dataclass(frozen=True)
class ResearchReportResult:
    """Resultado tipado do relatorio consolidado de pesquisa."""

    parameters: dict[str, object]
    metrics: dict[str, float | int]
    statistical_summary: str
    conclusion: str
    conclusion_reasons: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class ResearchReport:
    """Gera relatorio deterministico sem IA e sem executar experimentos."""

    parameters: object
    experiment_result: Alpha001ExperimentResult

    def generate(self) -> ResearchReportResult:
        """Consolida parametros, metricas, resumo e conclusao automatica."""
        metrics = self._metrics()
        conclusion, reasons = self._conclusion(metrics)
        return ResearchReportResult(
            parameters=self._parameters(),
            metrics=metrics,
            statistical_summary=self._statistical_summary(metrics),
            conclusion=conclusion,
            conclusion_reasons=reasons,
        )

    def _parameters(self) -> dict[str, object]:
        if is_dataclass(self.parameters):
            return dict(asdict(self.parameters))
        if isinstance(self.parameters, dict):
            return dict(self.parameters)
        return {
            key: value
            for key, value in vars(self.parameters).items()
            if not key.startswith("_")
        }

    def _metrics(self) -> dict[str, float | int]:
        result = self.experiment_result
        return {
            "total_candles": result.total_candles,
            "total_signals": result.total_signals,
            "total_buy": result.total_buy,
            "total_sell": result.total_sell,
            "total_wait": result.total_wait,
            "execution_time_ms": result.execution_time_ms,
        }

    def _statistical_summary(self, metrics: dict[str, float | int]) -> str:
        return (
            f"{metrics['total_candles']} candle(s), "
            f"{metrics['total_signals']} signal(s), "
            f"{metrics['total_buy']} BUY, "
            f"{metrics['total_sell']} SELL, "
            f"{metrics['total_wait']} WAIT."
        )

    def _conclusion(
        self,
        metrics: dict[str, float | int],
    ) -> tuple[str, tuple[str, ...]]:
        if int(metrics["total_candles"]) == 0:
            return ("INCONCLUSIVE", ("sem candles avaliados",))
        if int(metrics["total_signals"]) == 0:
            return ("INCONCLUSIVE", ("sem sinais gerados",))
        return ("ACCEPTABLE", ("infraestrutura de experimentacao executada",))
