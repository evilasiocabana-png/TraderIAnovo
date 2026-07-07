"""Comite decisorio de aprovacao da Alpha001."""

from dataclasses import dataclass

from research.quantitative_research_report import (
    QuantitativeResearchReport,
    QuantitativeResearchReportResult,
    QuantitativeReportSection,
)


@dataclass(frozen=True)
class AlphaApprovalDecision:
    """Decisao consolidada do comite de aprovacao."""

    approved: bool
    stage: str
    confidence: float
    recommendation: str
    reasons: list[str]


@dataclass(frozen=True)
class AlphaApprovalCommittee:
    """Avalia um relatorio quantitativo sem recalcular metricas."""

    minimum_paper_score: float = 75.0
    minimum_research_score: float = 40.0

    def evaluate(
        self,
        report: QuantitativeResearchReport | QuantitativeResearchReportResult,
    ) -> AlphaApprovalDecision:
        """Consolida a decisao de governanca da Alpha001."""
        result = self._to_result(report)
        reasons = self._reasons(result)
        stage = self._stage(result, reasons)
        return AlphaApprovalDecision(
            approved=stage in {"RESEARCH", "PAPER"},
            stage=stage,
            confidence=float(result.overall_score),
            recommendation=self._recommendation(stage, result),
            reasons=reasons,
        )

    def _to_result(
        self,
        report: QuantitativeResearchReport | QuantitativeResearchReportResult,
    ) -> QuantitativeResearchReportResult:
        if isinstance(report, QuantitativeResearchReportResult):
            return report
        return report.generate()

    def _stage(
        self,
        result: QuantitativeResearchReportResult,
        reasons: list[str],
    ) -> str:
        if self._has_blocking_reason(reasons):
            return "REJECTED"
        if self._paper_ready(result):
            return "PAPER"
        if result.overall_score >= self.minimum_research_score:
            return "RESEARCH"
        return "REJECTED"

    def _paper_ready(self, result: QuantitativeResearchReportResult) -> bool:
        return (
            result.overall_score >= self.minimum_paper_score
            and result.recommendation == "APPROVED_FOR_PAPER"
            and self._section_status(result, "Monte Carlo Analysis") == "ROBUST"
            and self._section_status(result, "Walk Forward Analysis") == "ROBUST"
            and self._section_status(result, "Robustness Analysis") == "ROBUST"
            and self._stress_allows_paper(result)
        )

    def _stress_allows_paper(
        self,
        result: QuantitativeResearchReportResult,
    ) -> bool:
        stress = self._section(result, "Stress Analysis")
        if stress is None:
            return False
        return stress.status in {"APPROVED", "ROBUST"}

    def _has_blocking_reason(self, reasons: list[str]) -> bool:
        blocking = (
            "Monte Carlo fragil.",
            "Walk Forward rejeitado.",
            "Robustez fragil.",
            "Stress Test rejeitado.",
            "Validacao quantitativa rejeitada.",
        )
        return any(reason in blocking for reason in reasons)

    def _reasons(self, result: QuantitativeResearchReportResult) -> list[str]:
        reasons: list[str] = []
        reasons.append(self._score_reason(result))
        reasons.append(self._validation_reason(result))
        reasons.append(self._section_reason(result, "Monte Carlo Analysis"))
        reasons.append(self._section_reason(result, "Walk Forward Analysis"))
        reasons.append(self._section_reason(result, "Robustness Analysis"))
        reasons.append(self._section_reason(result, "Stress Analysis"))
        return reasons

    def _score_reason(self, result: QuantitativeResearchReportResult) -> str:
        if result.overall_score >= self.minimum_paper_score:
            return "Score geral suficiente para paper trading."
        if result.overall_score >= self.minimum_research_score:
            return "Score geral suficiente apenas para pesquisa."
        return "Score geral insuficiente."

    def _validation_reason(self, result: QuantitativeResearchReportResult) -> str:
        if result.recommendation == "APPROVED_FOR_PAPER":
            return "Validacao quantitativa aprovada para paper."
        if result.recommendation == "REJECTED":
            return "Validacao quantitativa rejeitada."
        return "Validacao quantitativa exige mais pesquisa."

    def _section_reason(
        self,
        result: QuantitativeResearchReportResult,
        title: str,
    ) -> str:
        status = self._section_status(result, title)
        if title == "Monte Carlo Analysis" and status == "FRAGILE":
            return "Monte Carlo fragil."
        if title == "Walk Forward Analysis" and status == "OVERFITTED":
            return "Walk Forward rejeitado."
        if title == "Robustness Analysis" and status == "FRAGILE":
            return "Robustez fragil."
        if title == "Stress Analysis" and status == "REJECTED":
            return "Stress Test rejeitado."
        return f"{title}: {status}."

    def _recommendation(
        self,
        stage: str,
        result: QuantitativeResearchReportResult,
    ) -> str:
        if stage == "PAPER":
            return "Aprovado apenas para paper trading controlado."
        if stage == "RESEARCH":
            return "Manter em pesquisa quantitativa."
        if result.overall_score < self.minimum_research_score:
            return "Rejeitar ate melhoria estatistica relevante."
        return "Rejeitar ate remover bloqueios de governanca."

    def _section_status(
        self,
        result: QuantitativeResearchReportResult,
        title: str,
    ) -> str:
        section = self._section(result, title)
        if section is None:
            return "INCONCLUSIVE"
        return section.status

    def _section(
        self,
        result: QuantitativeResearchReportResult,
        title: str,
    ) -> QuantitativeReportSection | None:
        for section in result.sections:
            if section.title == title:
                return section
        return None
