"""Integracao da Alpha301 com a infraestrutura existente de Research."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from research.alpha001_research_report import Alpha001ResearchResult
from research.alpha301.alpha301_experiment import Alpha301Experiment
from research.campaigns.campaign_builder import CampaignBuilder
from research.campaigns.campaign_runner import CampaignRunner
from research.campaigns.campaign_report import CampaignReport
from research.campaigns.research_campaign import ResearchCampaign
from research.experiment_management.experiment_definition import (
    ExperimentDefinition,
)
from research.knowledge.knowledge_artifact import KnowledgeArtifact
from research.knowledge.knowledge_extractor import KnowledgeExtractor
from research.knowledge.knowledge_index import KnowledgeIndex
from research.knowledge.knowledge_repository import KnowledgeRepository
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
from research.research_report import ResearchReport
from research.research_runner import ResearchRunner
from research.validation.experiment_validation_report import (
    ExperimentValidationReport,
)
from research.validation.experiment_validation_runner import (
    ExperimentValidationRunner,
    ValidationExecutionResult,
)
from research.validation.validation_rule_registry import ValidationRuleRegistry


@dataclass(frozen=True)
class Alpha301ResearchIntegration:
    """Permite que a Alpha301 reutilize o ecossistema de Research existente."""

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
    knowledge_extractor: KnowledgeExtractor = field(default_factory=KnowledgeExtractor)
    knowledge_repository: KnowledgeRepository = field(default_factory=KnowledgeRepository)
    knowledge_index: KnowledgeIndex = field(default_factory=KnowledgeIndex)

    def run_research(
        self,
        experiment: Alpha301Experiment,
        benchmark_results: Iterable[Alpha001ResearchResult] = (),
    ) -> ResearchPipelineResult:
        """Executa a Alpha301 no ResearchPipeline ja existente."""
        return self.pipeline.run(
            experiment=experiment,
            benchmark_results=benchmark_results,
        )

    def run_with_runner(
        self,
        runner: ResearchRunner,
        experiment: Alpha301Experiment,
        benchmark_results: Iterable[Alpha001ResearchResult] = (),
    ) -> ResearchExecutionResult:
        """Executa a Alpha301 usando um ResearchRunner configurado."""
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
        """Monta experimentos Alpha301 usando o CampaignBuilder existente."""
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

    def extract_knowledge(
        self,
        research_report: ResearchReport,
        campaign_report: CampaignReport,
        validation_report: ExperimentValidationReport,
    ) -> tuple[KnowledgeArtifact, ...]:
        """Extrai conhecimento usando a Knowledge Base existente."""
        return self.knowledge_extractor.extract(
            research_report=research_report,
            campaign_report=campaign_report,
            validation_report=validation_report,
        )

    def save_knowledge(
        self,
        artifact: KnowledgeArtifact,
    ) -> KnowledgeArtifact:
        """Salva artefato no repositorio existente de conhecimento."""
        return self.knowledge_repository.save(artifact)

    def index_knowledge(
        self,
        artifacts: Iterable[KnowledgeArtifact],
    ) -> tuple[KnowledgeArtifact, ...]:
        """Indexa artefatos usando o indice existente da Knowledge Base."""
        return self.knowledge_index.index(artifacts)

    def search_knowledge(self, query: str) -> tuple[KnowledgeArtifact, ...]:
        """Busca artefatos no repositorio existente de conhecimento."""
        return self.knowledge_repository.search(query)
