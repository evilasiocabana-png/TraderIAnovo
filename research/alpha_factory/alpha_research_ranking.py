"""Ranking consolidado de cenarios pesquisados por Alpha."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True)
class AlphaResearchScenario:
    """Snapshot de um cenario ja pesquisado."""

    scenario_id: str
    alpha_id: str
    market: str
    timeframe: str
    technical_score: float
    historical_confirmation: float
    total_trades: int
    profit_factor: float
    max_drawdown: float
    overfitting_score: float
    status: str
    rejection_reason: str = ""


@dataclass(frozen=True)
class AlphaRejectionReport:
    """Resumo de reprovacao de um cenario."""

    scenario_id: str
    alpha_id: str
    market: str
    timeframe: str
    reason: str
    overfitting_score: float


@dataclass(frozen=True)
class AlphaOverfittingControl:
    """Sinalizacao de risco de overfitting em pesquisa."""

    scenario_id: str
    alpha_id: str
    market: str
    timeframe: str
    overfitting_score: float
    risk_level: str
    blocked: bool


@dataclass(frozen=True)
class AlphaResearchRankingReport:
    """Relatorio consolidado de rankings de pesquisa."""

    ranking_by_alpha: dict[str, tuple[AlphaResearchScenario, ...]] = field(
        default_factory=dict
    )
    ranking_by_market: dict[str, tuple[AlphaResearchScenario, ...]] = field(
        default_factory=dict
    )
    ranking_by_timeframe: dict[str, tuple[AlphaResearchScenario, ...]] = field(
        default_factory=dict
    )
    alpha_comparison: tuple[AlphaResearchScenario, ...] = ()
    rejection_reports: tuple[AlphaRejectionReport, ...] = ()
    overfitting_controls: tuple[AlphaOverfittingControl, ...] = ()


@dataclass(frozen=True)
class AlphaResearchRankingEngine:
    """Consolida rankings sem executar pesquisa ou gerar sinais."""

    overfitting_block_threshold: float = 70.0
    overfitting_warning_threshold: float = 40.0

    def build(
        self,
        scenarios: Iterable[AlphaResearchScenario],
    ) -> AlphaResearchRankingReport:
        """Retorna rankings e alertas para cenarios ja calculados."""
        scenario_list = tuple(scenarios)
        ranked = self._rank(scenario_list)
        return AlphaResearchRankingReport(
            ranking_by_alpha=self._group_and_rank(scenario_list, "alpha_id"),
            ranking_by_market=self._group_and_rank(scenario_list, "market"),
            ranking_by_timeframe=self._group_and_rank(scenario_list, "timeframe"),
            alpha_comparison=self._best_by_alpha(ranked),
            rejection_reports=tuple(
                self._rejection_report(scenario)
                for scenario in scenario_list
                if self._is_rejected(scenario)
            ),
            overfitting_controls=tuple(
                self._overfitting_control(scenario) for scenario in scenario_list
            ),
        )

    def _group_and_rank(
        self,
        scenarios: tuple[AlphaResearchScenario, ...],
        attribute: str,
    ) -> dict[str, tuple[AlphaResearchScenario, ...]]:
        grouped: dict[str, list[AlphaResearchScenario]] = {}
        for scenario in scenarios:
            key = str(getattr(scenario, attribute))
            grouped.setdefault(key, []).append(scenario)
        return {
            key: self._rank(values)
            for key, values in sorted(grouped.items(), key=lambda item: item[0])
        }

    def _best_by_alpha(
        self,
        ranked: tuple[AlphaResearchScenario, ...],
    ) -> tuple[AlphaResearchScenario, ...]:
        best: dict[str, AlphaResearchScenario] = {}
        for scenario in ranked:
            if scenario.alpha_id not in best:
                best[scenario.alpha_id] = scenario
        return self._rank(tuple(best.values()))

    def _rank(
        self,
        scenarios: Iterable[AlphaResearchScenario],
    ) -> tuple[AlphaResearchScenario, ...]:
        return tuple(sorted(tuple(scenarios), key=self._ranking_key))

    def _ranking_key(self, scenario: AlphaResearchScenario) -> tuple[bool, float, float, float, float, int]:
        return (
            scenario.status != "APPROVED",
            scenario.overfitting_score,
            -scenario.profit_factor,
            scenario.max_drawdown,
            -scenario.historical_confirmation,
            -scenario.total_trades,
        )

    def _is_rejected(self, scenario: AlphaResearchScenario) -> bool:
        return scenario.status == "REJECTED" or bool(scenario.rejection_reason.strip())

    def _rejection_report(
        self,
        scenario: AlphaResearchScenario,
    ) -> AlphaRejectionReport:
        reason = scenario.rejection_reason.strip() or "Cenario reprovado pela pesquisa."
        return AlphaRejectionReport(
            scenario_id=scenario.scenario_id,
            alpha_id=scenario.alpha_id,
            market=scenario.market,
            timeframe=scenario.timeframe,
            reason=reason,
            overfitting_score=scenario.overfitting_score,
        )

    def _overfitting_control(
        self,
        scenario: AlphaResearchScenario,
    ) -> AlphaOverfittingControl:
        risk_level = "LOW"
        if scenario.overfitting_score >= self.overfitting_block_threshold:
            risk_level = "HIGH"
        elif scenario.overfitting_score >= self.overfitting_warning_threshold:
            risk_level = "WARNING"
        return AlphaOverfittingControl(
            scenario_id=scenario.scenario_id,
            alpha_id=scenario.alpha_id,
            market=scenario.market,
            timeframe=scenario.timeframe,
            overfitting_score=scenario.overfitting_score,
            risk_level=risk_level,
            blocked=risk_level == "HIGH",
        )
