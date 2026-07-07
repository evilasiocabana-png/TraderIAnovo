"""Relatorio consolidado do Portfolio Research."""

from dataclasses import dataclass

from research.portfolio.alpha_correlation_engine import AlphaCorrelationResult
from research.portfolio.alpha_registry import AlphaRegistry
from research.portfolio.alpha_research_profile import AlphaResearchProfile
from research.portfolio.portfolio_research_comparator import (
    PortfolioComparisonResult,
)


@dataclass(frozen=True)
class PortfolioResearchReport:
    """Agrega resultados produzidos pelos componentes de portfolio."""

    alpha_registry: AlphaRegistry
    alpha_profiles: tuple[AlphaResearchProfile, ...]
    comparison_result: PortfolioComparisonResult
    correlation_result: AlphaCorrelationResult
