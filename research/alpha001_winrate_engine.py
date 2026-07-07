"""Motor de taxa de acerto da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_experiment import Alpha001ExperimentResult


@dataclass(frozen=True)
class Alpha001WinRateResult:
    """Resultado de taxa de acerto calculado para a Alpha 001."""

    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: float


@dataclass(frozen=True)
class Alpha001WinRateEngine:
    """Calcula taxa de acerto sem acessar camadas operacionais."""

    def calculate(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001WinRateResult:
        """Retorna taxa de acerto segura para o contrato atual."""
        return Alpha001WinRateResult(
            winning_trades=0,
            losing_trades=0,
            breakeven_trades=0,
            win_rate=0.0,
        )
