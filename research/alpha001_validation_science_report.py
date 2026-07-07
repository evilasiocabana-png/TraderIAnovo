"""Relatorio consolidado de validacao cientifica da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_monte_carlo_engine import Alpha001MonteCarloResult
from research.alpha001_sensitivity_engine import Alpha001SensitivityResult
from research.alpha001_statistical_significance_engine import (
    Alpha001StatisticalSignificanceResult,
)
from research.alpha001_walk_forward_engine import Alpha001WalkForwardResult


@dataclass(frozen=True)
class Alpha001ValidationScienceResult:
    """Agrega resultados cientificos produzidos por engines anteriores."""

    walk_forward: Alpha001WalkForwardResult
    monte_carlo: Alpha001MonteCarloResult
    sensitivity: Alpha001SensitivityResult
    statistical_significance: Alpha001StatisticalSignificanceResult
