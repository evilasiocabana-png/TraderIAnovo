"""Executor oficial da Validation Suite."""

from __future__ import annotations

from dataclasses import dataclass

from research.campaigns.research_campaign import ResearchCampaign
from research.validation.monte_carlo.monte_carlo_engine import (
    MonteCarloEngine,
    MonteCarloResult,
)
from research.validation.monte_carlo.monte_carlo_profile import MonteCarloProfile
from research.validation.stress.stress_engine import StressEngine, StressResult
from research.validation.stress.stress_scenario import StressScenario
from research.validation.suite.validation_suite import (
    ValidationSuite,
    ValidationSuiteStep,
)
from research.validation.walk_forward_engine import (
    WalkForwardEngine,
    WalkForwardResult,
)
from research.validation.walk_forward_profile import WalkForwardProfile


EXECUTION_ORDER = (
    ValidationSuiteStep.WALK_FORWARD,
    ValidationSuiteStep.MONTE_CARLO,
    ValidationSuiteStep.STRESS_TESTING,
)


@dataclass(frozen=True)
class ValidationSuiteResult:
    """Resultado consolidado da execucao da Validation Suite."""

    suite_id: str
    campaign_id: str
    executed_steps: tuple[ValidationSuiteStep, ...]
    skipped_steps: tuple[ValidationSuiteStep, ...]
    walk_forward_result: WalkForwardResult | None
    monte_carlo_result: MonteCarloResult | None
    stress_result: StressResult | None
    status: str


@dataclass(frozen=True)
class ValidationSuiteRunner:
    """Orquestra validacoes cientificas sem duplicar logica das tecnicas."""

    walk_forward_engine: WalkForwardEngine
    monte_carlo_engine: MonteCarloEngine
    stress_engine: StressEngine
    walk_forward_profile: WalkForwardProfile
    monte_carlo_profile: MonteCarloProfile
    stress_scenario: StressScenario

    def run(
        self,
        suite: ValidationSuite,
        campaign: ResearchCampaign,
    ) -> ValidationSuiteResult:
        """Executa as validacoes habilitadas na ordem institucional."""
        executed_steps: list[ValidationSuiteStep] = []
        skipped_steps: list[ValidationSuiteStep] = []
        walk_forward_result: WalkForwardResult | None = None
        monte_carlo_result: MonteCarloResult | None = None
        stress_result: StressResult | None = None

        for step in EXECUTION_ORDER:
            if step not in suite.enabled_steps:
                skipped_steps.append(step)
                continue
            if step is ValidationSuiteStep.WALK_FORWARD:
                walk_forward_result = self.walk_forward_engine.run(
                    campaign,
                    self.walk_forward_profile,
                )
            elif step is ValidationSuiteStep.MONTE_CARLO:
                monte_carlo_result = self.monte_carlo_engine.run(
                    campaign,
                    self.monte_carlo_profile,
                )
            elif step is ValidationSuiteStep.STRESS_TESTING:
                stress_result = self.stress_engine.run(
                    campaign,
                    self.stress_scenario,
                )
            executed_steps.append(step)

        return ValidationSuiteResult(
            suite_id=suite.suite_id,
            campaign_id=campaign.campaign_id,
            executed_steps=tuple(executed_steps),
            skipped_steps=tuple(skipped_steps),
            walk_forward_result=walk_forward_result,
            monte_carlo_result=monte_carlo_result,
            stress_result=stress_result,
            status=self._status(tuple(executed_steps), suite.required_steps),
        )

    def _status(
        self,
        executed_steps: tuple[ValidationSuiteStep, ...],
        required_steps: tuple[ValidationSuiteStep, ...],
    ) -> str:
        for step in required_steps:
            if step not in executed_steps:
                return "INCOMPLETE"
        return "COMPLETED"
