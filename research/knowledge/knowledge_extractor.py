"""Extrator deterministico de artefatos de conhecimento."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from research.campaigns.campaign_report import CampaignReport
from research.knowledge.knowledge_artifact import KnowledgeArtifact
from research.research_report import ResearchReport, ResearchReportResult
from research.validation.experiment_validation_report import (
    ExperimentValidationReport,
)


@dataclass(frozen=True)
class KnowledgeExtractor:
    """Extrai conhecimento estruturado sem IA ou execucao de pesquisa."""

    def extract(
        self,
        research_report: ResearchReport,
        campaign_report: CampaignReport,
        validation_report: ExperimentValidationReport,
        created_at: datetime | None = None,
    ) -> tuple[KnowledgeArtifact, ...]:
        """Gera artefatos deterministivos a partir de relatorios existentes."""
        report_result = research_report.generate()
        timestamp = created_at or datetime.now()
        confidence = self._confidence(campaign_report)
        return (
            self._artifact(
                key="stable_parameters",
                title="Parametros estaveis",
                default_evidence=self._stable_parameter_evidence(report_result),
                research_result=report_result,
                campaign_report=campaign_report,
                created_at=timestamp,
                confidence=confidence,
            ),
            self._artifact(
                key="unstable_parameters",
                title="Parametros instaveis",
                default_evidence=self._unstable_parameter_evidence(validation_report),
                research_result=report_result,
                campaign_report=campaign_report,
                created_at=timestamp,
                confidence=confidence,
            ),
            self._artifact(
                key="favorable_contexts",
                title="Contextos favoraveis",
                default_evidence=self._metadata_values(
                    campaign_report,
                    "contexts",
                    ("Contexto favoravel nao informado.",),
                ),
                research_result=report_result,
                campaign_report=campaign_report,
                created_at=timestamp,
                confidence=confidence,
            ),
            self._artifact(
                key="unfavorable_contexts",
                title="Contextos desfavoraveis",
                default_evidence=self._validation_messages(validation_report),
                research_result=report_result,
                campaign_report=campaign_report,
                created_at=timestamp,
                confidence=confidence,
            ),
            self._artifact(
                key="predominant_regimes",
                title="Regimes predominantes",
                default_evidence=self._metadata_values(
                    campaign_report,
                    "regimes",
                    ("Regime predominante nao informado.",),
                ),
                research_result=report_result,
                campaign_report=campaign_report,
                created_at=timestamp,
                confidence=confidence,
            ),
            self._artifact(
                key="limitations",
                title="Limitacoes identificadas",
                default_evidence=self._limitations(validation_report),
                research_result=report_result,
                campaign_report=campaign_report,
                created_at=timestamp,
                confidence=confidence,
            ),
        )

    def _artifact(
        self,
        key: str,
        title: str,
        default_evidence: tuple[str, ...],
        research_result: ResearchReportResult,
        campaign_report: CampaignReport,
        created_at: datetime,
        confidence: float,
    ) -> KnowledgeArtifact:
        evidence = self._metadata_values(
            campaign_report,
            key,
            default_evidence,
        )
        return KnowledgeArtifact(
            artifact_id=f"{campaign_report.campaign_id}:{key}",
            alpha_id=campaign_report.alpha_id,
            research_id=str(
                campaign_report.metadata.get(
                    "research_id",
                    campaign_report.campaign_id,
                )
            ),
            campaign_id=campaign_report.campaign_id,
            hypothesis=title,
            conclusion=research_result.conclusion,
            evidence=evidence,
            confidence=confidence,
            created_at=created_at,
            metadata={
                "category": key,
                "research_conclusion": research_result.conclusion,
                "campaign_success_rate": campaign_report.campaign_success_rate,
            },
        )

    def _stable_parameter_evidence(
        self,
        report_result: ResearchReportResult,
    ) -> tuple[str, ...]:
        if not report_result.parameters:
            return ("Parametros nao informados.",)
        return tuple(f"{key}={value}" for key, value in report_result.parameters.items())

    def _unstable_parameter_evidence(
        self,
        validation_report: ExperimentValidationReport,
    ) -> tuple[str, ...]:
        if validation_report.failed_rules:
            return tuple(rule.rule_id for rule in validation_report.failed_rules)
        return ("Nenhum parametro instavel identificado.",)

    def _validation_messages(
        self,
        validation_report: ExperimentValidationReport,
    ) -> tuple[str, ...]:
        if validation_report.validation_messages:
            return validation_report.validation_messages
        return ("Nenhum contexto desfavoravel identificado.",)

    def _limitations(
        self,
        validation_report: ExperimentValidationReport,
    ) -> tuple[str, ...]:
        limitations = [
            f"Regra falhou: {rule.rule_id}"
            for rule in validation_report.failed_rules
        ]
        limitations.extend(validation_report.validation_messages)
        return tuple(limitations) or ("Nenhuma limitacao identificada.",)

    def _metadata_values(
        self,
        campaign_report: CampaignReport,
        key: str,
        fallback: tuple[str, ...],
    ) -> tuple[str, ...]:
        value = campaign_report.metadata.get(key)
        if value is None:
            return fallback
        if isinstance(value, str):
            return (value,)
        if isinstance(value, Iterable):
            return tuple(str(item) for item in value)
        return (str(value),)

    def _confidence(self, campaign_report: CampaignReport) -> float:
        value = campaign_report.metadata.get(
            "knowledge_confidence",
            campaign_report.campaign_success_rate,
        )
        if not isinstance(value, (int, float)):
            return 0.0
        return max(0.0, min(1.0, float(value)))
