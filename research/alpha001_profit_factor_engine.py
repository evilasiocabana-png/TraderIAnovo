"""Motor de Profit Factor da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_profit_engine import Alpha001ProfitResult


@dataclass(frozen=True)
class Alpha001ProfitFactorResult:
    """Resultado de Profit Factor calculado para a Alpha 001."""

    profit_factor: float


@dataclass(frozen=True)
class Alpha001ProfitFactorEngine:
    """Calcula apenas o Profit Factor a partir do resultado financeiro."""

    def calculate(
        self,
        profit_result: Alpha001ProfitResult,
    ) -> Alpha001ProfitFactorResult:
        """Retorna Profit Factor sem propagar divisao por zero."""
        if profit_result.gross_loss_points == 0:
            return Alpha001ProfitFactorResult(profit_factor=0.0)

        return Alpha001ProfitFactorResult(
            profit_factor=profit_result.gross_profit_points
            / abs(profit_result.gross_loss_points),
        )
