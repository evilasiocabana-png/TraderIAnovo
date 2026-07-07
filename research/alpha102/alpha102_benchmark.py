"""Benchmark da Alpha102 dentro do portfolio de Alphas."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from research.benchmark.alpha_benchmark_engine import (
    AlphaBenchmarkEngine,
)
from research.benchmark.alpha_benchmark_profile import AlphaBenchmarkProfile
from research.benchmark.alpha_benchmark_report import AlphaBenchmarkReport
from research.benchmark.alpha_dominance_engine import (
    ALPHA_A_DOMINATES,
    ALPHA_B_DOMINATES,
    AlphaDominanceEngine,
)
from research.benchmark.alpha_similarity_engine import AlphaSimilarityEngine
from research.research_execution_result import ResearchExecutionResult


ALPHA102 = "Alpha102"
DEFAULT_PEERS = ("Alpha101", "Alpha001", "Alpha002", "Alpha003")
DEFAULT_METRICS = (
    "net_profit",
    "max_drawdown",
    "profit_factor",
    "win_rate",
    "expectancy",
    "robustness",
    "reproducibility",
)


@dataclass(frozen=True)
class Alpha102PeerBenchmark:
    """Benchmark par-a-par da Alpha102 contra uma Alpha do portfolio."""

    peer_alpha: str
    report: AlphaBenchmarkReport


@dataclass(frozen=True)
class Alpha102BenchmarkResult:
    """Posicionamento consolidado da Alpha102 no portfolio."""

    alpha_id: str
    peers: tuple[str, ...]
    peer_benchmarks: tuple[Alpha102PeerBenchmark, ...]
    dominance_summary: Mapping[str, str]
    similarity_summary: Mapping[str, float]
    portfolio_position: str


@dataclass(frozen=True)
class Alpha102Benchmark:
    """Compara Alpha102 com Alphas existentes usando engines oficiais."""

    benchmark_engine: AlphaBenchmarkEngine = field(
        default_factory=AlphaBenchmarkEngine,
    )
    dominance_engine: AlphaDominanceEngine = field(
        default_factory=AlphaDominanceEngine,
    )
    similarity_engine: AlphaSimilarityEngine = field(
        default_factory=AlphaSimilarityEngine,
    )

    def position(
        self,
        alpha102_result: ResearchExecutionResult,
        peer_results: Mapping[str, ResearchExecutionResult],
        comparison_period: str,
        created_at: str,
        peers: tuple[str, ...] = DEFAULT_PEERS,
    ) -> Alpha102BenchmarkResult:
        """Posiciona a Alpha102 contra os pares informados."""
        peer_benchmarks = tuple(
            self._peer_benchmark(
                alpha102_result=alpha102_result,
                peer_alpha=peer_alpha,
                peer_result=peer_results[peer_alpha],
                comparison_period=comparison_period,
                created_at=created_at,
            )
            for peer_alpha in peers
            if peer_alpha in peer_results
        )
        dominance_summary = {
            item.peer_alpha: item.report.dominance_result
            for item in peer_benchmarks
        }
        similarity_summary = {
            item.peer_alpha: item.report.similarity_score
            for item in peer_benchmarks
        }
        return Alpha102BenchmarkResult(
            alpha_id=ALPHA102,
            peers=tuple(item.peer_alpha for item in peer_benchmarks),
            peer_benchmarks=peer_benchmarks,
            dominance_summary=dominance_summary,
            similarity_summary=similarity_summary,
            portfolio_position=self._portfolio_position(dominance_summary),
        )

    def _peer_benchmark(
        self,
        alpha102_result: ResearchExecutionResult,
        peer_alpha: str,
        peer_result: ResearchExecutionResult,
        comparison_period: str,
        created_at: str,
    ) -> Alpha102PeerBenchmark:
        profile = AlphaBenchmarkProfile(
            benchmark_id=f"benchmark-alpha102-{peer_alpha.lower()}",
            alpha_a=ALPHA102,
            alpha_b=peer_alpha,
            experiment_ids=(
                f"experiment-{ALPHA102.lower()}",
                f"experiment-{peer_alpha.lower()}",
            ),
            campaign_ids=(
                f"campaign-{ALPHA102.lower()}",
                f"campaign-{peer_alpha.lower()}",
            ),
            comparison_period=comparison_period,
            metrics=DEFAULT_METRICS,
            created_at=created_at,
            metadata={"target_alpha": ALPHA102, "peer_alpha": peer_alpha},
        )
        benchmark_result = self.benchmark_engine.compare(
            profile=profile,
            results=(alpha102_result, peer_result),
        )
        dominance = self.dominance_engine.decide(benchmark_result)
        similarity = self.similarity_engine.calculate(benchmark_result)
        return Alpha102PeerBenchmark(
            peer_alpha=peer_alpha,
            report=AlphaBenchmarkReport(
                benchmark_result=benchmark_result,
                dominance=dominance,
                similarity=similarity,
                alpha_a=ALPHA102,
                alpha_b=peer_alpha,
                benchmark_summary=f"{ALPHA102} benchmarked against {peer_alpha}.",
                dominance_result=dominance.decision,
                similarity_score=similarity.similarity_score,
                diversification_score=similarity.diversification_score,
                recommendation=self._recommendation(
                    dominance.decision,
                    similarity.diversification_score,
                ),
                execution_time=0.0,
                metadata={"target_alpha": ALPHA102, "peer_alpha": peer_alpha},
            ),
        )

    def _recommendation(
        self,
        dominance_decision: str,
        diversification_score: float,
    ) -> str:
        if (
            dominance_decision == ALPHA_A_DOMINATES
            and diversification_score >= 0.4
        ):
            return "PORTFOLIO_CANDIDATE"
        if dominance_decision == ALPHA_B_DOMINATES:
            return "UNDER_REVIEW"
        return "NEUTRAL"

    def _portfolio_position(
        self,
        dominance_summary: Mapping[str, str],
    ) -> str:
        if not dominance_summary:
            return "UNPOSITIONED"
        wins = sum(
            1
            for decision in dominance_summary.values()
            if decision == ALPHA_A_DOMINATES
        )
        losses = sum(
            1
            for decision in dominance_summary.values()
            if decision == ALPHA_B_DOMINATES
        )
        if wins > losses:
            return "LEADING"
        if losses > wins:
            return "LAGGING"
        return "COMPETITIVE"
