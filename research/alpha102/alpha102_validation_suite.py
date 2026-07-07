"""Submissao da Alpha102 a Validation Suite oficial."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from research.campaigns.research_campaign import ResearchCampaign
from research.validation.monte_carlo.monte_carlo_analyzer import (
    MonteCarloAnalyzer,
)
from research.validation.monte_carlo.monte_carlo_approval import (
    MonteCarloApproval,
)
from research.validation.monte_carlo.monte_carlo_report import MonteCarloReport
from research.validation.stress.stress_analyzer import StressAnalyzer
from research.validation.stress.stress_approval import StressApproval
from research.validation.stress.stress_report import StressReport
from research.validation.suite.validation_certification import (
    ValidationCertification,
    ValidationCertificationResult,
)
from research.validation.suite.validation_suite import (
    ValidationSuite,
    ValidationSuiteStep,
)
from research.validation.suite.validation_suite_report import ValidationSuiteReport
from research.validation.suite.validation_suite_result import ValidationSuiteResult
from research.validation.suite.validation_suite_runner import (
    ValidationSuiteResult as ValidationSuiteExecutionResult,
)
from research.validation.suite.validation_suite_runner import ValidationSuiteRunner
from research.validation.walk_forward_analyzer import WalkForwardAnalyzer
from research.validation.walk_forward_approval import WalkForwardApproval
from research.validation.walk_forward_report import WalkForwardReport


@dataclass(frozen=True)
class Alpha102ValidationSuiteResult:
    """Resultado da submissao cientifica da Alpha102."""

    suite_execution: ValidationSuiteExecutionResult
    validation_report: ValidationSuiteReport
    certification: ValidationCertificationResult
    status: str


@dataclass(frozen=True)
class Alpha102ValidationSuite:
    """Orquestra a certificacao da Alpha102 usando validacoes existentes."""

    suite_runner: ValidationSuiteRunner
    walk_forward_analyzer: WalkForwardAnalyzer = WalkForwardAnalyzer()
    monte_carlo_analyzer: MonteCarloAnalyzer = MonteCarloAnalyzer()
    stress_analyzer: StressAnalyzer = StressAnalyzer()
    walk_forward_approval: WalkForwardApproval = WalkForwardApproval()
    monte_carlo_approval: MonteCarloApproval = MonteCarloApproval()
    stress_approval: StressApproval = StressApproval()
    certification: ValidationCertification = ValidationCertification()

    def submit(
        self,
        suite: ValidationSuite,
        campaign: ResearchCampaign,
    ) -> Alpha102ValidationSuiteResult:
        """Executa a suite oficial e certifica a Alpha102."""
        started = perf_counter()
        suite_execution = self.suite_runner.run(suite, campaign)
        execution_time = perf_counter() - started

        walk_forward_approval = self.walk_forward_approval.evaluate(
            self._walk_forward_report(suite_execution, execution_time),
        )
        monte_carlo_approval = self.monte_carlo_approval.evaluate(
            self._monte_carlo_report(suite_execution, execution_time),
        )
        stress_approval = self.stress_approval.evaluate(
            self._stress_report(suite_execution, execution_time),
        )
        validation_result = ValidationSuiteResult.from_approvals(
            walk_forward_approval=walk_forward_approval,
            monte_carlo_approval=monte_carlo_approval,
            stress_approval=stress_approval,
        )
        certification_result = self.certification.certify(validation_result)
        validation_report = ValidationSuiteReport(
            validation_result=validation_result,
            certification_result=certification_result,
            scientific_score=validation_result.scientific_score,
            robustness_score=validation_result.robustness_score,
            reproducibility_score=validation_result.reproducibility_score,
            certification=certification_result.status,
            executed_validations=self._executed_validations(suite_execution),
            execution_time=execution_time,
            metadata={
                "alpha_id": campaign.alpha_id,
                "campaign_id": campaign.campaign_id,
                "suite_status": suite_execution.status,
            },
        )
        return Alpha102ValidationSuiteResult(
            suite_execution=suite_execution,
            validation_report=validation_report,
            certification=certification_result,
            status=certification_result.status,
        )

    def _walk_forward_report(
        self,
        suite_execution: ValidationSuiteExecutionResult,
        execution_time: float,
    ) -> WalkForwardReport:
        result = suite_execution.walk_forward_result
        if result is None:
            raise RuntimeError("Walk Forward result is required for Alpha102.")
        analysis = self.walk_forward_analyzer.analyze(result)
        return WalkForwardReport(
            walk_forward_result=result,
            analysis_result=analysis,
            training_summary="Alpha102 training window processed.",
            validation_summary="Alpha102 validation window processed.",
            testing_summary="Alpha102 testing window processed.",
            degradation_score=analysis.degradation_score,
            stability_score=analysis.stability_score,
            consistency_score=analysis.consistency_score,
            execution_time=execution_time,
            metadata={"alpha_id": "Alpha102"},
        )

    def _monte_carlo_report(
        self,
        suite_execution: ValidationSuiteExecutionResult,
        execution_time: float,
    ) -> MonteCarloReport:
        result = suite_execution.monte_carlo_result
        if result is None:
            raise RuntimeError("Monte Carlo result is required for Alpha102.")
        analysis = self.monte_carlo_analyzer.analyze(result)
        return MonteCarloReport(
            monte_carlo_result=result,
            analysis_result=analysis,
            simulations=result.total_simulations,
            confidence_level=result.confidence_level,
            average_return=analysis.average_return,
            worst_case_return=analysis.worst_case_return,
            best_case_return=analysis.best_case_return,
            expected_drawdown=analysis.expected_drawdown,
            robustness_score=analysis.robustness_score,
            execution_time=execution_time,
            metadata={"alpha_id": "Alpha102"},
        )

    def _stress_report(
        self,
        suite_execution: ValidationSuiteExecutionResult,
        execution_time: float,
    ) -> StressReport:
        result = suite_execution.stress_result
        if result is None:
            raise RuntimeError("Stress result is required for Alpha102.")
        analysis = self.stress_analyzer.analyze(result)
        return StressReport(
            stress_result=result,
            analysis_result=analysis,
            scenario=result.scenario,
            degradation_score=analysis.degradation_score,
            recovery_score=analysis.recovery_score,
            resilience_score=analysis.resilience_score,
            stability_score=analysis.stability_score,
            execution_time=execution_time,
            metadata={"alpha_id": "Alpha102"},
        )

    def _executed_validations(
        self,
        suite_execution: ValidationSuiteExecutionResult,
    ) -> tuple[str, ...]:
        ordered_steps = (
            ValidationSuiteStep.WALK_FORWARD,
            ValidationSuiteStep.MONTE_CARLO,
            ValidationSuiteStep.STRESS_TESTING,
        )
        return tuple(
            step.value
            for step in ordered_steps
            if step in suite_execution.executed_steps
        )
