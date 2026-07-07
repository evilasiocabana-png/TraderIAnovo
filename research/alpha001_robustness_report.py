"""Relatorio consolidado de robustez da Alpha 001."""

from dataclasses import dataclass

from research.alpha001_outlier_engine import Alpha001OutlierResult
from research.alpha001_parameter_stability_engine import (
    Alpha001ParameterStabilityResult,
)
from research.alpha001_regime_breakdown_engine import (
    Alpha001RegimeBreakdownResult,
)
from research.alpha001_sample_quality_engine import Alpha001SampleQualityResult


@dataclass(frozen=True)
class Alpha001RobustnessResult:
    """Agrega resultados de robustez produzidos por engines anteriores."""

    sample_quality: Alpha001SampleQualityResult
    outlier: Alpha001OutlierResult
    regime_breakdown: Alpha001RegimeBreakdownResult
    parameter_stability: Alpha001ParameterStabilityResult
