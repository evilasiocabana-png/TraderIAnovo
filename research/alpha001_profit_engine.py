"""Motor de resultado financeiro basico da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_experiment import Alpha001ExperimentResult


@dataclass(frozen=True)
class Alpha001ProfitResult:
    """Resultado financeiro basico calculado para a Alpha 001."""

    gross_profit_points: float
    gross_loss_points: float
    net_profit_points: float


@dataclass(frozen=True)
class Alpha001ProfitEngine:
    """Calcula resultado financeiro basico sem acessar camadas operacionais."""

    def calculate(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001ProfitResult:
        """Retorna resultado financeiro seguro para o contrato atual."""
        return Alpha001ProfitResult(
            gross_profit_points=0.0,
            gross_loss_points=0.0,
            net_profit_points=0.0,
        )
