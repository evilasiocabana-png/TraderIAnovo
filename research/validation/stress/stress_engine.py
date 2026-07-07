"""Engine oficial de validacao por cenarios de estresse."""

from __future__ import annotations

from dataclasses import dataclass

from research.campaigns.campaign_runner import CampaignRunner
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.research_pipeline import ResearchPipeline
from research.research_runner import ResearchRunner
from research.validation.stress.stress_scenario import StressScenario


@dataclass(frozen=True)
class StressResult:
    """Resultado declarativo de uma campanha sob cenario de estresse."""

    campaign_id: str
    scenario: StressScenario
    executed_experiments: tuple[ExperimentDefinition, ...]
    total_experiments: int
    scenario_enabled: bool
    status: str


@dataclass(frozen=True)
class StressEngine:
    """Executa campanhas sob cenarios sem recalcular metricas individuais."""

    campaign_runner: CampaignRunner
    research_runner: ResearchRunner
    research_pipeline: ResearchPipeline

    def run(
        self,
        campaign: ResearchCampaign,
        scenario: StressScenario,
    ) -> StressResult:
        """Executa a campanha e consolida o resultado do cenario informado."""
        if not scenario.enabled:
            return StressResult(
                campaign_id=campaign.campaign_id,
                scenario=scenario,
                executed_experiments=(),
                total_experiments=0,
                scenario_enabled=False,
                status="SKIPPED",
            )
        executed = self.campaign_runner.run(campaign)
        return StressResult(
            campaign_id=campaign.campaign_id,
            scenario=scenario,
            executed_experiments=executed,
            total_experiments=len(executed),
            scenario_enabled=True,
            status="COMPLETED",
        )
