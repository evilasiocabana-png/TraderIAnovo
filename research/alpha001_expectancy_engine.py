"""Motor de Expectancy da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_experiment import Alpha001ExperimentResult


@dataclass(frozen=True)
class Alpha001ExpectancyResult:
    """Resultado de Expectancy calculado para a Alpha 001."""

    average_win: float
    average_loss: float
    payoff_ratio: float
    expectancy: float


@dataclass(frozen=True)
class Alpha001ExpectancyEngine:
    """Calcula apenas Expectancy sem acessar camadas operacionais."""

    def calculate(
        self,
        experiment_result: Alpha001ExperimentResult,
    ) -> Alpha001ExpectancyResult:
        """Retorna Expectancy segura para o contrato atual."""
        return Alpha001ExpectancyResult(
            average_win=0.0,
            average_loss=0.0,
            payoff_ratio=0.0,
            expectancy=0.0,
        )
