"""Metricas consolidadas de validacao quantitativa de Alpha."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class AlphaValidationMetricInput:
    """Snapshot de metricas ja apuradas para uma Alpha."""

    alpha_id: str
    market: str
    timeframe: str
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float
    mae: float
    mfe: float
    net_profit: float
    walk_forward_score: float = 0.0
    walk_forward_status: str = "NOT_EVALUATED"
    out_of_sample_score: float = 0.0
    out_of_sample_status: str = "NOT_EVALUATED"


@dataclass(frozen=True)
class AlphaValidationMetricsReport:
    """Relatorio consolidado de metricas de validacao."""

    alpha_id: str
    total_trades: int
    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float
    mae: float
    mfe: float
    recovery_factor: float
    consistency_by_market: Mapping[str, float] = field(default_factory=dict)
    consistency_by_timeframe: Mapping[str, float] = field(default_factory=dict)
    walk_forward_score: float = 0.0
    walk_forward_status: str = "NOT_EVALUATED"
    out_of_sample_score: float = 0.0
    out_of_sample_status: str = "NOT_EVALUATED"
    validation_status: str = "INSUFFICIENT_DATA"
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class AlphaValidationMetricsEngine:
    """Consolida metricas existentes sem executar pesquisa."""

    minimum_trades: int = 30
    minimum_profit_factor: float = 1.2
    minimum_walk_forward_score: float = 0.6
    minimum_out_of_sample_score: float = 0.6

    def summarize(
        self,
        alpha_id: str,
        metrics: tuple[AlphaValidationMetricInput, ...],
    ) -> AlphaValidationMetricsReport:
        """Agrega metricas ja apuradas para uma Alpha."""
        selected = tuple(metric for metric in metrics if metric.alpha_id == alpha_id)
        if not selected:
            return AlphaValidationMetricsReport(
                alpha_id=alpha_id,
                total_trades=0,
                win_rate=0.0,
                profit_factor=0.0,
                expectancy=0.0,
                max_drawdown=0.0,
                mae=0.0,
                mfe=0.0,
                recovery_factor=0.0,
                warnings=("Sem metricas para a Alpha.",),
            )

        total_trades = sum(max(0, int(metric.total_trades)) for metric in selected)
        net_profit = sum(float(metric.net_profit) for metric in selected)
        max_drawdown = max(float(metric.max_drawdown) for metric in selected)
        report = AlphaValidationMetricsReport(
            alpha_id=alpha_id,
            total_trades=total_trades,
            win_rate=self._weighted_average(selected, "win_rate"),
            profit_factor=self._weighted_average(selected, "profit_factor"),
            expectancy=self._weighted_average(selected, "expectancy"),
            max_drawdown=max_drawdown,
            mae=self._weighted_average(selected, "mae"),
            mfe=self._weighted_average(selected, "mfe"),
            recovery_factor=self._recovery_factor(net_profit, max_drawdown),
            consistency_by_market=self._consistency(selected, "market"),
            consistency_by_timeframe=self._consistency(selected, "timeframe"),
            walk_forward_score=self._weighted_average(selected, "walk_forward_score"),
            walk_forward_status=self._status_by_score(
                self._weighted_average(selected, "walk_forward_score"),
                self.minimum_walk_forward_score,
            ),
            out_of_sample_score=self._weighted_average(selected, "out_of_sample_score"),
            out_of_sample_status=self._status_by_score(
                self._weighted_average(selected, "out_of_sample_score"),
                self.minimum_out_of_sample_score,
            ),
            validation_status="",
            warnings=(),
        )
        warnings = self._warnings(report)
        return AlphaValidationMetricsReport(
            alpha_id=report.alpha_id,
            total_trades=report.total_trades,
            win_rate=report.win_rate,
            profit_factor=report.profit_factor,
            expectancy=report.expectancy,
            max_drawdown=report.max_drawdown,
            mae=report.mae,
            mfe=report.mfe,
            recovery_factor=report.recovery_factor,
            consistency_by_market=report.consistency_by_market,
            consistency_by_timeframe=report.consistency_by_timeframe,
            walk_forward_score=report.walk_forward_score,
            walk_forward_status=report.walk_forward_status,
            out_of_sample_score=report.out_of_sample_score,
            out_of_sample_status=report.out_of_sample_status,
            validation_status="APPROVED" if not warnings else "REVIEW_REQUIRED",
            warnings=warnings,
        )

    def _weighted_average(
        self,
        metrics: tuple[AlphaValidationMetricInput, ...],
        attribute: str,
    ) -> float:
        total_trades = sum(max(0, int(metric.total_trades)) for metric in metrics)
        if total_trades <= 0:
            return 0.0
        weighted = sum(
            float(getattr(metric, attribute)) * max(0, int(metric.total_trades))
            for metric in metrics
        )
        return weighted / total_trades

    def _recovery_factor(self, net_profit: float, max_drawdown: float) -> float:
        if max_drawdown <= 0.0:
            return 0.0
        return net_profit / max_drawdown

    def _consistency(
        self,
        metrics: tuple[AlphaValidationMetricInput, ...],
        attribute: str,
    ) -> dict[str, float]:
        grouped: dict[str, list[AlphaValidationMetricInput]] = {}
        for metric in metrics:
            key = str(getattr(metric, attribute))
            grouped.setdefault(key, []).append(metric)
        return {
            key: self._group_consistency(tuple(values))
            for key, values in sorted(grouped.items(), key=lambda item: item[0])
        }

    def _group_consistency(
        self,
        metrics: tuple[AlphaValidationMetricInput, ...],
    ) -> float:
        if not metrics:
            return 0.0
        approved = sum(
            1
            for metric in metrics
            if metric.profit_factor >= self.minimum_profit_factor
            and metric.total_trades >= self.minimum_trades
        )
        return approved / len(metrics)

    def _status_by_score(self, score: float, minimum_score: float) -> str:
        if score <= 0.0:
            return "NOT_EVALUATED"
        if score >= minimum_score:
            return "APPROVED"
        return "FAILED"

    def _warnings(self, report: AlphaValidationMetricsReport) -> tuple[str, ...]:
        warnings: list[str] = []
        if report.total_trades < self.minimum_trades:
            warnings.append("Amostra insuficiente.")
        if report.profit_factor < self.minimum_profit_factor:
            warnings.append("Profit factor abaixo do minimo.")
        if report.walk_forward_status != "APPROVED":
            warnings.append("Walk-forward nao aprovado.")
        if report.out_of_sample_status != "APPROVED":
            warnings.append("Out-of-sample nao aprovado.")
        return tuple(warnings)
