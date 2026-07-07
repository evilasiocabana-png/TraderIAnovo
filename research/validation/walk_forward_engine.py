"""Engine oficial de Walk-Forward para campanhas de pesquisa."""

from __future__ import annotations

from dataclasses import dataclass

from research.campaigns.campaign_runner import CampaignRunner
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.research_pipeline import ResearchPipeline
from research.research_runner import ResearchRunner
from research.validation.walk_forward_profile import WalkForwardProfile


@dataclass(frozen=True)
class WalkForwardResult:
    """Resultado declarativo de Walk-Forward sobre uma campanha."""

    campaign_id: str
    profile: WalkForwardProfile
    executed_experiments: tuple[ExperimentDefinition, ...]
    training_experiments: tuple[ExperimentDefinition, ...]
    validation_experiments: tuple[ExperimentDefinition, ...]
    testing_experiments: tuple[ExperimentDefinition, ...]
    rolling_window: int
    minimum_samples: int


@dataclass(frozen=True)
class WalkForwardEngine:
    """Executa Walk-Forward de campanha sem otimizar parametros."""

    campaign_runner: CampaignRunner
    research_runner: ResearchRunner
    research_pipeline: ResearchPipeline

    def run(
        self,
        campaign: ResearchCampaign,
        profile: WalkForwardProfile,
    ) -> WalkForwardResult:
        """Executa a campanha e separa experimentos nas janelas declaradas."""
        executed = self.campaign_runner.run(campaign)
        training_end = profile.training_window
        validation_end = training_end + profile.validation_window
        testing_end = validation_end + profile.testing_window

        return WalkForwardResult(
            campaign_id=campaign.campaign_id,
            profile=profile,
            executed_experiments=executed,
            training_experiments=executed[:training_end],
            validation_experiments=executed[training_end:validation_end],
            testing_experiments=executed[validation_end:testing_end],
            rolling_window=profile.rolling_window,
            minimum_samples=profile.minimum_samples,
        )
