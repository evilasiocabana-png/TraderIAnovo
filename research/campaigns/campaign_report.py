"""Relatorio oficial das campanhas de pesquisa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.campaigns.campaign_analyzer import CampaignAnalysisResult
from research.campaigns.research_campaign import ResearchCampaign


@dataclass(frozen=True)
class CampaignReport:
    """Consolida informacoes produzidas pela campanha e sua analise."""

    campaign: ResearchCampaign
    analysis: CampaignAnalysisResult
    campaign_id: str
    alpha_id: str
    total_experiments: int
    successful_experiments: int
    failed_experiments: int
    approved_experiments: int
    rejected_experiments: int
    campaign_success_rate: float
    execution_time: float
    metadata: Mapping[str, object]
