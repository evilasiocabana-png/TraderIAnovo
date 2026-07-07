"""Contrato oficial dos perfis de timeframe do Research Lab."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ResearchTimeframeProfile:
    """Representa um perfil declarativo de timeframe de pesquisa."""

    timeframe: str
    minimum_history: str
    recommended_campaign_size: int
    metadata: Mapping[str, object]


INTRADAY_TIMEFRAME_PROFILE = ResearchTimeframeProfile(
    timeframe="INTRADAY",
    minimum_history="3 months",
    recommended_campaign_size=30,
    metadata={"scope": "research"},
)

DAILY_TIMEFRAME_PROFILE = ResearchTimeframeProfile(
    timeframe="DAILY",
    minimum_history="1 year",
    recommended_campaign_size=20,
    metadata={"scope": "research"},
)

WEEKLY_TIMEFRAME_PROFILE = ResearchTimeframeProfile(
    timeframe="WEEKLY",
    minimum_history="3 years",
    recommended_campaign_size=12,
    metadata={"scope": "research"},
)

MONTHLY_TIMEFRAME_PROFILE = ResearchTimeframeProfile(
    timeframe="MONTHLY",
    minimum_history="5 years",
    recommended_campaign_size=6,
    metadata={"scope": "research"},
)

SUPPORTED_RESEARCH_TIMEFRAME_PROFILES: tuple[ResearchTimeframeProfile, ...] = (
    INTRADAY_TIMEFRAME_PROFILE,
    DAILY_TIMEFRAME_PROFILE,
    WEEKLY_TIMEFRAME_PROFILE,
    MONTHLY_TIMEFRAME_PROFILE,
)
