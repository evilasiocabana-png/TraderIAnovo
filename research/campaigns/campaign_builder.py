"""Construtor de campanhas de pesquisa."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import ExperimentDefinition


@dataclass(frozen=True)
class CampaignBuilder:
    """Monta definicoes de experimento para uma campanha."""

    def build(
        self,
        campaign: ResearchCampaign,
        template: ExperimentDefinition,
    ) -> tuple[ExperimentDefinition, ...]:
        """Gera experimentos a partir dos dados declarados da campanha."""
        datasets = self._values(campaign, "datasets", template.dataset)
        replay_periods = self._values(
            campaign,
            "replay_periods",
            template.replay_period,
        )
        configuration_versions = self._values(
            campaign,
            "configuration_versions",
            template.configuration_version,
        )
        parameters = self._values(campaign, "parameters", {})

        experiments: list[ExperimentDefinition] = []
        sequence = 1
        for dataset in datasets:
            for replay_period in replay_periods:
                for configuration_version in configuration_versions:
                    for parameter_set in parameters:
                        experiments.append(
                            self._definition(
                                campaign=campaign,
                                template=template,
                                sequence=sequence,
                                dataset=str(dataset),
                                replay_period=str(replay_period),
                                configuration_version=str(configuration_version),
                                parameters=parameter_set,
                            )
                        )
                        sequence += 1
        return tuple(experiments)

    def _definition(
        self,
        campaign: ResearchCampaign,
        template: ExperimentDefinition,
        sequence: int,
        dataset: str,
        replay_period: str,
        configuration_version: str,
        parameters: object,
    ) -> ExperimentDefinition:
        metadata = {
            **dict(template.metadata),
            "campaign_id": campaign.campaign_id,
            "campaign_name": campaign.name,
            "parameters": parameters,
        }
        return replace(
            template,
            experiment_id=f"{campaign.campaign_id}-{sequence:03d}",
            alpha_id=campaign.alpha_id,
            configuration_version=configuration_version,
            replay_period=replay_period,
            dataset=dataset,
            status="PENDING",
            created_at=campaign.created_at,
            metadata=metadata,
        )

    def _values(
        self,
        campaign: ResearchCampaign,
        key: str,
        fallback: object,
    ) -> tuple[object, ...]:
        value = campaign.metadata.get(key, fallback)
        if isinstance(value, tuple):
            return value
        if isinstance(value, list):
            return tuple(value)
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
            return tuple(value)
        return (value,)
