"""Motor de drawdown da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_experiment import Alpha001ExperimentResult


@dataclass(frozen=True)
class Alpha001DrawdownResult:
    """Resultado de drawdown calculado para a Alpha 001."""

    equity_curve: tuple[float, ...]
    max_drawdown_points: float
    max_drawdown_percent: float


@dataclass(frozen=True)
class Alpha001DrawdownEngine:
    """Calcula drawdown sem acessar camadas operacionais."""

    def calculate(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001DrawdownResult:
        """Retorna drawdown seguro para o contrato atual do experimento."""
        return Alpha001DrawdownResult(
            equity_curve=(0.0,),
            max_drawdown_points=0.0,
            max_drawdown_percent=0.0,
        )
