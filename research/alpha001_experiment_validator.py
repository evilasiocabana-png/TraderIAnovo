"""Validador de experimentos da Alpha 001 IORB."""

from dataclasses import dataclass

from domain.contracts.backtest_result import BacktestResult


@dataclass(frozen=True)
class Alpha001ValidationResult:
    """Resultado da validacao de experimento da Alpha 001."""

    approved: bool
    status: str
    reasons: list[str]
    metrics: dict[str, float | int]


@dataclass(frozen=True)
class Alpha001ExperimentValidator:
    """Valida metricas finais sem executar replay, backtest ou estrategia."""

    minimum_total_trades: int
    minimum_win_rate: float
    minimum_profit_factor: float
    maximum_drawdown_points: float
    minimum_net_profit_points: float

    def validate(
        self,
        backtest_result: BacktestResult,
    ) -> Alpha001ValidationResult:
        """Avalia um resultado ja produzido contra thresholds configuraveis."""
        metrics = self._metrics(backtest_result)
        reasons = self._rejection_reasons(metrics)
        status = self._status(metrics, reasons)
        return Alpha001ValidationResult(
            approved=status == "APPROVED",
            status=status,
            reasons=reasons or ["Experimento aprovado."],
            metrics=metrics,
        )

    def _rejection_reasons(
        self,
        metrics: dict[str, float | int],
    ) -> list[str]:
        reasons: list[str] = []
        if metrics["total_trades"] < self.minimum_total_trades:
            reasons.append("Poucas operacoes para validar a Alpha 001.")
        if metrics["profit_factor"] < self.minimum_profit_factor:
            reasons.append("Profit factor abaixo do minimo configurado.")
        if metrics["max_drawdown_points"] > self.maximum_drawdown_points:
            reasons.append("Drawdown acima do limite configurado.")
        if metrics["win_rate"] < self.minimum_win_rate:
            reasons.append("Win rate abaixo do minimo configurado.")
        if metrics["net_profit_points"] < self.minimum_net_profit_points:
            reasons.append("Resultado liquido abaixo do minimo configurado.")
        return reasons

    def _status(
        self,
        metrics: dict[str, float | int],
        reasons: list[str],
    ) -> str:
        if metrics["total_trades"] < self.minimum_total_trades:
            return "INSUFFICIENT_SAMPLE"
        if metrics["profit_factor"] < self.minimum_profit_factor:
            return "LOW_PROFIT_FACTOR"
        if metrics["max_drawdown_points"] > self.maximum_drawdown_points:
            return "HIGH_DRAWDOWN"
        if reasons:
            return "VALIDATION_REJECTED"
        return "APPROVED"

    def _metrics(self, result: BacktestResult) -> dict[str, float | int]:
        return {
            "total_trades": result.total_trades,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "max_drawdown_points": result.drawdown,
            "net_profit_points": result.total_profit,
        }
