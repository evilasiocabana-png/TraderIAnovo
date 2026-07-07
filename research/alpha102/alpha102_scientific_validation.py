"""Validacao cientifica oficial da Alpha102."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from research.alpha102.alpha102_benchmark import (
    Alpha102Benchmark,
    Alpha102BenchmarkResult,
)
from research.alpha102.alpha102_portfolio_evaluation import (
    Alpha102PortfolioEvaluation,
    Alpha102PortfolioEvaluationResult,
)
from research.alpha102.alpha102_validation_suite import (
    Alpha102ValidationSuite,
    Alpha102ValidationSuiteResult,
)
from research.campaigns.research_campaign import ResearchCampaign
from research.portfolio.allocation_weight_engine import AllocationWeightResult
from research.portfolio.portfolio_optimization_engine import (
    PortfolioOptimizationResult,
)
from research.research_execution_result import ResearchExecutionResult
from research.research_runner import ResearchRunner
from research.validation.suite.validation_suite import ValidationSuite


@dataclass(frozen=True)
class Alpha102ScientificValidationResult:
    """Resultado consolidado do processo cientifico da Alpha102."""

    research_result: ResearchExecutionResult
    validation_suite_result: Alpha102ValidationSuiteResult
    benchmark_result: Alpha102BenchmarkResult
    portfolio_evaluation: Alpha102PortfolioEvaluationResult
    certification_status: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class Alpha102ScientificValidation:
    """Orquestra o processo cientifico usando a infraestrutura existente."""

    research_runner: ResearchRunner
    validation_suite: Alpha102ValidationSuite
    benchmark: Alpha102Benchmark
    portfolio_evaluation: Alpha102PortfolioEvaluation

    def validate(
        self,
        experiment: object,
        suite: ValidationSuite,
        campaign: ResearchCampaign,
        peer_results: Mapping[str, ResearchExecutionResult],
        allocation: AllocationWeightResult,
        optimization: PortfolioOptimizationResult,
        comparison_period: str,
        created_at: str,
    ) -> Alpha102ScientificValidationResult:
        """Executa Research, Validation Suite, Benchmark e Portfolio Evaluation."""
        research_result = self.research_runner.run(experiment)
        validation_result = self.validation_suite.submit(suite, campaign)
        benchmark_result = self.benchmark.position(
            alpha102_result=research_result,
            peer_results=peer_results,
            comparison_period=comparison_period,
            created_at=created_at,
        )
        portfolio_result = self.portfolio_evaluation.evaluate(
            allocation=allocation,
            optimization=optimization,
            benchmark=benchmark_result,
        )
        return Alpha102ScientificValidationResult(
            research_result=research_result,
            validation_suite_result=validation_result,
            benchmark_result=benchmark_result,
            portfolio_evaluation=portfolio_result,
            certification_status=validation_result.certification.status,
            metadata={
                "alpha_id": "Alpha102",
                "campaign_id": campaign.campaign_id,
                "research_status": self._status_value(research_result.status),
                "portfolio_decision": portfolio_result.official_decision,
            },
        )

    def _status_value(self, status: object) -> str:
        return str(getattr(status, "value", status))
