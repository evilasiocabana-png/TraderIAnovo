"""Integracao da Alpha003 com a infraestrutura existente de Research."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha003.alpha003_experiment import Alpha003Experiment
from research.campaigns.campaign_builder import CampaignBuilder
from research.campaigns.campaign_runner import CampaignRunner
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.reproducibility.experiment_fingerprint import (
    ExperimentFingerprint,
    ExperimentFingerprintResult,
)
from research.reproducibility.reproducibility_validator import (
    ReproducibilityValidationResult,
    ReproducibilityValidator,
)
from research.reproducibility.research_snapshot import ResearchSnapshot
from research.research_execution_result import ResearchExecutionResult
from research.research_pipeline import ResearchPipeline, ResearchPipelineResult
from research.research_runner import ResearchRunner
from research.validation.experiment_validation_runner import (
    ExperimentValidationRunner,
    ValidationExecutionResult,
)
from research.validation.validation_rule_registry import ValidationRuleRegistry


@dataclass(frozen=True)
class Alpha003ResearchIntegration:
    """Permite que a Alpha003 reutilize o ecossistema de Research existente."""

    pipeline: ResearchPipeline = field(default_factory=ResearchPipeline)
    validation_runner: ExperimentValidationRunner = field(
        default_factory=ExperimentValidationRunner,
    )
    fingerprint_generator: ExperimentFingerprint = field(
        default_factory=ExperimentFingerprint,
    )
    reproducibility_validator: ReproducibilityValidator = field(
        default_factory=ReproducibilityValidator,
    )
    campaign_builder: CampaignBuilder = field(default_factory=CampaignBuilder)

    def run_research(
        self,
        experiment: Alpha003Experiment,
        benchmark_results: Iterable[Alpha001ResearchResult] = (),
    ) -> ResearchPipelineResult:
        """Executa a Alpha003 no ResearchPipeline ja existente."""
        return self.pipeline.run(
            experiment=experiment,
            benchmark_results=benchmark_results,
        )

    def run_with_runner(
        self,
        runner: ResearchRunner,
        experiment: Alpha003Experiment,
        benchmark_results: Iterable[Alpha001ResearchResult] = (),
    ) -> ResearchExecutionResult:
        """Executa a Alpha003 usando um ResearchRunner configurado."""
        return runner.run(
            experiment=experiment,
            benchmark_results=benchmark_results,
        )

    def run_validation(
        self,
        execution_result: ResearchExecutionResult,
        registry: ValidationRuleRegistry,
    ) -> ValidationExecutionResult:
        """Delegacao para o runner institucional de validacao."""
        return self.validation_runner.run(
            execution_result=execution_result,
            registry=registry,
        )

    def generate_fingerprint(
        self,
        snapshot: ResearchSnapshot,
    ) -> ExperimentFingerprintResult:
        """Gera fingerprint usando o componente de reprodutibilidade existente."""
        return self.fingerprint_generator.generate(snapshot)

    def validate_reproducibility(
        self,
        snapshot: ResearchSnapshot,
        fingerprint_result: ExperimentFingerprintResult,
    ) -> ReproducibilityValidationResult:
        """Valida reprodutibilidade sem executar replay ou metricas."""
        return self.reproducibility_validator.validate(
            snapshot=snapshot,
            fingerprint_result=fingerprint_result,
        )

    def build_campaign(
        self,
        campaign: ResearchCampaign,
        template: ExperimentDefinition,
    ) -> tuple[ExperimentDefinition, ...]:
        """Monta experimentos Alpha003 usando o CampaignBuilder existente."""
        return self.campaign_builder.build(
            campaign=campaign,
            template=template,
        )

    def run_campaign(
        self,
        runner: CampaignRunner,
        campaign: ResearchCampaign,
    ) -> tuple[ExperimentDefinition, ...]:
        """Delega campanhas ao CampaignRunner existente."""
        return runner.run(campaign)
