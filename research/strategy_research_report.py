"""Relatorio oficial das pesquisas por familia de estrategia."""

from __future__ import annotations

from dataclasses import dataclass

from research.research_configuration_profile import ResearchConfigurationProfile
from research.research_execution_result import ResearchExecutionResult
from strategies.strategy_profile import StrategyProfile


@dataclass(frozen=True)
class StrategyResearchReport:
    """Consolida informacoes de pesquisa por familia de estrategia."""

    strategy_profile: StrategyProfile
    research_configuration: ResearchConfigurationProfile
    research_execution: ResearchExecutionResult
    strategy_family: str
    timeframe: str
    total_experiments: int
    approved_experiments: int
    rejected_experiments: int
    reproducibility: str
    robustness: str
    validation_status: str
