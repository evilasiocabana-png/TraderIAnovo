"""Relatorio oficial do ciclo de vida de Alphas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.alpha_factory.alpha_deprecation_engine import AlphaDeprecationResult
from research.alpha_factory.alpha_health_engine import AlphaHealthResult
from research.alpha_factory.alpha_lifecycle import AlphaLifecycle


@dataclass(frozen=True)
class AlphaLifecycleReport:
    """Consolida resultados do ciclo de vida sem realizar calculos."""

    lifecycle: AlphaLifecycle
    health_result: AlphaHealthResult
    deprecation_result: AlphaDeprecationResult
    alpha_id: str
    lifecycle_status: str
    health_score: float
    robustness_score: float
    reproducibility_score: float
    recommendation: str
    execution_time: float
    metadata: Mapping[str, object]
