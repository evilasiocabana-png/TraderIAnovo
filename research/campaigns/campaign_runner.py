"""Executor oficial de campanhas de pesquisa."""

from __future__ import annotations

from dataclasses import dataclass

from research.campaigns.campaign_builder import CampaignBuilder
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import ExperimentDefinition
from research.experiment_management.experiment_queue import ExperimentQueue
from research.experiment_management.experiment_scheduler import ExperimentScheduler


@dataclass(frozen=True)
class CampaignRunner:
    """Enfileira experimentos de campanha e delega a execucao ao scheduler."""

    queue: ExperimentQueue
    scheduler: ExperimentScheduler
    builder: CampaignBuilder
    template: ExperimentDefinition

    def run(
        self,
        campaign: ResearchCampaign,
    ) -> tuple[ExperimentDefinition, ...]:
        """Monta, enfileira e delega a campanha para execucao sequencial."""
        experiments = self.builder.build(campaign, self.template)
        for experiment in experiments:
            self.queue.enqueue(experiment)
        return self.scheduler.run_all()
