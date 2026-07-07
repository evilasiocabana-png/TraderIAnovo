"""Contrato oficial de campanha de pesquisa."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class ResearchCampaign:
    """Representa uma campanha de pesquisa do TraderIA_WDO."""

    campaign_id: str
    name: str
    description: str
    alpha_id: str
    objective: str
    status: str
    created_at: str
    created_by: str
    metadata: Mapping[str, object]
