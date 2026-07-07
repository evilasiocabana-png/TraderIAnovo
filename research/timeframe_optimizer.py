"""Otimizador conservador de timeframes para pesquisa quantitativa."""

from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite


@dataclass(frozen=True)
class TimeframeOptimizerConfiguration:
    """Parametros institucionais do otimizador de timeframes."""

    min_sample_size: int
    min_profit_factor: float
    min_win_rate: float
    max_allowed_drawdown: float
    min_confidence: float


@dataclass(frozen=True)
class TimeframeCandidate:
    """Resultado de pesquisa de uma combinacao par/timeframe."""

    symbol: str
    timeframe: str
    sample_size: int
    win_rate: float
    avg_return: float
    profit_factor: float
    max_drawdown: float
    calibrated_confidence: float
    rank_score: float = 0.0
    rejection_reason: str = ""


@dataclass(frozen=True)
class TimeframeOptimizationResult:
    """Ranking final read-only de timeframes para um par."""

    symbol: str
    best_timeframe: str
    candidates: tuple[TimeframeCandidate, ...]
    selected_reason: str
    rejected_candidates: tuple[TimeframeCandidate, ...]
    is_research_only: bool = True


class TimeframeOptimizer:
    """Escolhe timeframe por robustez estatistica, sem efeito operacional."""

    def optimize(
        self,
        symbol: str,
        candidates: list[TimeframeCandidate],
        configuration: TimeframeOptimizerConfiguration,
    ) -> TimeframeOptimizationResult:
        """Retorna ranking conservador de timeframes para o par informado."""
        ranked = tuple(
            self._rank_candidate(candidate, configuration)
            for candidate in candidates
        )
        accepted = [
            candidate
            for candidate in ranked
            if not candidate.rejection_reason
        ]
        rejected = tuple(
            candidate
            for candidate in ranked
            if candidate.rejection_reason
        )
        if not accepted:
            return TimeframeOptimizationResult(
                symbol=symbol,
                best_timeframe="NONE",
                candidates=ranked,
                selected_reason=(
                    "Nenhum timeframe aprovado pelos criterios minimos de pesquisa."
                ),
                rejected_candidates=rejected,
            )

        best = max(
            accepted,
            key=lambda candidate: (
                candidate.rank_score,
                candidate.sample_size,
                candidate.profit_factor,
                candidate.win_rate,
                -candidate.max_drawdown,
            ),
        )
        return TimeframeOptimizationResult(
            symbol=symbol,
            best_timeframe=best.timeframe,
            candidates=ranked,
            selected_reason=(
                f"{best.timeframe} selecionado por robustez: "
                f"amostra {best.sample_size}, win rate {best.win_rate:.1%}, "
                f"profit factor {best.profit_factor:.2f}, "
                f"drawdown {best.max_drawdown:.2%}, "
                f"confianca {best.calibrated_confidence:.1%}."
            ),
            rejected_candidates=rejected,
        )

    def _rank_candidate(
        self,
        candidate: TimeframeCandidate,
        configuration: TimeframeOptimizerConfiguration,
    ) -> TimeframeCandidate:
        rejection = self._rejection_reason(candidate, configuration)
        if rejection:
            return replace(
                candidate,
                rank_score=0.0,
                rejection_reason=rejection,
            )
        return replace(
            candidate,
            rank_score=self._rank_score(candidate, configuration),
            rejection_reason="",
        )

    def _rejection_reason(
        self,
        candidate: TimeframeCandidate,
        configuration: TimeframeOptimizerConfiguration,
    ) -> str:
        if candidate.rejection_reason:
            return candidate.rejection_reason
        if candidate.sample_size < configuration.min_sample_size:
            return "LOW_SAMPLE_SIZE"
        if candidate.profit_factor < configuration.min_profit_factor:
            return "LOW_PROFIT_FACTOR"
        if candidate.win_rate < configuration.min_win_rate:
            return "LOW_WIN_RATE"
        if candidate.max_drawdown > configuration.max_allowed_drawdown:
            return "HIGH_DRAWDOWN"
        if candidate.calibrated_confidence < configuration.min_confidence:
            return "LOW_CONFIDENCE"
        return ""

    def _rank_score(
        self,
        candidate: TimeframeCandidate,
        configuration: TimeframeOptimizerConfiguration,
    ) -> float:
        sample_score = min(
            candidate.sample_size / (configuration.min_sample_size * 3),
            1.0,
        )
        profit_factor_score = self._profit_factor_score(
            candidate.profit_factor,
            configuration.min_profit_factor,
        )
        win_rate_score = self._bounded_ratio(
            candidate.win_rate - configuration.min_win_rate,
            1.0 - configuration.min_win_rate,
        )
        confidence_score = self._bounded_ratio(
            candidate.calibrated_confidence - configuration.min_confidence,
            1.0 - configuration.min_confidence,
        )
        drawdown_score = 1.0 - self._bounded_ratio(
            candidate.max_drawdown,
            configuration.max_allowed_drawdown,
        )
        return round(
            (20.0 * sample_score)
            + (25.0 * profit_factor_score)
            + (20.0 * win_rate_score)
            + (20.0 * confidence_score)
            + (15.0 * drawdown_score),
            4,
        )

    def _profit_factor_score(self, value: float, minimum: float) -> float:
        if not isfinite(value):
            return 1.0
        denominator = max(minimum, 1.0)
        return self._bounded_ratio(value - minimum, denominator)

    def _bounded_ratio(self, value: float, denominator: float) -> float:
        if denominator <= 0.0:
            return 0.0
        return max(0.0, min(value / denominator, 1.0))
