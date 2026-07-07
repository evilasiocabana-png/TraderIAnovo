"""Relatorio quantitativo consolidado da Alpha001."""

from dataclasses import dataclass, field
from typing import Any

from domain.contracts.backtest_result import BacktestResult


@dataclass(frozen=True)
class QuantitativeReportSection:
    """Secao consolidada do relatorio quantitativo."""

    title: str
    status: str
    score: float
    summary: str
    details: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class QuantitativeResearchReportResult:
    """Resultado final do relatorio quantitativo."""

    overall_score: float
    overall_status: str
    recommendation: str
    sections: list[QuantitativeReportSection]


@dataclass(frozen=True)
class QuantitativeResearchReport:
    """Consolida resultados existentes sem executar novos experimentos."""

    backtest_result: BacktestResult | None = None
    benchmark_result: object | None = None
    walk_forward_result: object | None = None
    robustness_result: object | None = None
    sensitivity_result: object | None = None
    regime_performance: object | None = None
    temporal_performance: object | None = None
    temporal_stability: object | None = None
    stress_result: object | None = None
    monte_carlo_result: object | None = None

    def generate(self) -> QuantitativeResearchReportResult:
        """Gera o relatorio consolidado da Alpha001."""
        sections = self._sections()
        score = self._overall_score(sections)
        recommendation = self._recommendation(score, sections)
        return QuantitativeResearchReportResult(
            overall_score=score,
            overall_status=self._overall_status(recommendation),
            recommendation=recommendation,
            sections=sections,
        )

    def _sections(self) -> list[QuantitativeReportSection]:
        return [
            self._executive_summary_section(),
            self._statistical_validation_section(),
            self._robustness_analysis_section(),
            self._walk_forward_analysis_section(),
            self._monte_carlo_analysis_section(),
            self._stress_analysis_section(),
            self._risk_analysis_section(),
            self._recommendation_section(),
        ]

    def _executive_summary_section(self) -> QuantitativeReportSection:
        score = self._backtest_score()
        details = self._backtest_details()
        return QuantitativeReportSection(
            title="Executive Summary",
            status=self._status_from_score(score),
            score=score,
            summary="Resumo consolidado dos resultados centrais da Alpha001.",
            details=details,
        )

    def _statistical_validation_section(self) -> QuantitativeReportSection:
        score = self._benchmark_score()
        return QuantitativeReportSection(
            title="Statistical Validation",
            status=self._status_from_score(score),
            score=score,
            summary="Valida backtest, benchmark e amostra disponivel.",
            details=self._benchmark_details(),
        )

    def _robustness_analysis_section(self) -> QuantitativeReportSection:
        score = self._robustness_score()
        details = self._robustness_details()
        details.update(self._sensitivity_details())
        return QuantitativeReportSection(
            title="Robustness Analysis",
            status=self._generic_status(self.robustness_result, score),
            score=score,
            summary="Consolida robustez e sensibilidade de parametros.",
            details=details,
        )

    def _walk_forward_analysis_section(self) -> QuantitativeReportSection:
        score = self._walk_forward_score()
        return QuantitativeReportSection(
            title="Walk Forward Analysis",
            status=self._walk_forward_status(score),
            score=score,
            summary="Avalia degradacao entre treino e teste.",
            details=self._walk_forward_details(),
        )

    def _monte_carlo_analysis_section(self) -> QuantitativeReportSection:
        score = self._monte_carlo_score()
        return QuantitativeReportSection(
            title="Monte Carlo Analysis",
            status=self._generic_status(self.monte_carlo_result, score),
            score=score,
            summary="Consolida risco simulado por Monte Carlo.",
            details=self._monte_carlo_details(),
        )

    def _stress_analysis_section(self) -> QuantitativeReportSection:
        score = self._generic_score(self.stress_result, "stress_score")
        return QuantitativeReportSection(
            title="Stress Analysis",
            status=self._generic_status(self.stress_result, score),
            score=score,
            summary="Consolida stress test quando houver resultado existente.",
            details=self._generic_details(self.stress_result),
        )

    def _risk_analysis_section(self) -> QuantitativeReportSection:
        scores = [
            self._drawdown_score(),
            self._monte_carlo_score(),
            self._generic_score(self.stress_result, "stress_score"),
        ]
        score = self._average(scores)
        return QuantitativeReportSection(
            title="Risk Analysis",
            status=self._status_from_score(score),
            score=score,
            summary="Resume drawdown, stress test e risco Monte Carlo.",
            details=self._risk_details(),
        )

    def _recommendation_section(self) -> QuantitativeReportSection:
        sections = self._sections_without_recommendation()
        score = self._overall_score(sections)
        recommendation = self._recommendation(score, sections)
        return QuantitativeReportSection(
            title="Recommendation",
            status=recommendation,
            score=score,
            summary=f"Recomendacao final: {recommendation}.",
            details={"recommendation": recommendation},
        )

    def _sections_without_recommendation(self) -> list[QuantitativeReportSection]:
        return [
            self._executive_summary_section(),
            self._statistical_validation_section(),
            self._robustness_analysis_section(),
            self._walk_forward_analysis_section(),
            self._monte_carlo_analysis_section(),
            self._stress_analysis_section(),
            self._risk_analysis_section(),
        ]

    def _backtest_score(self) -> float:
        result = self.backtest_result
        if result is None:
            return 0.0
        points = 0.0
        points += 25.0 if result.total_trades > 0 else 0.0
        points += 25.0 if result.total_profit > 0 else 0.0
        points += 25.0 if result.profit_factor >= 1.2 else 0.0
        points += 25.0 if result.win_rate >= 0.50 else 0.0
        return points

    def _benchmark_score(self) -> float:
        result = self.benchmark_result
        if result is None:
            return self._backtest_score()
        points = 0.0
        points += 25.0 if self._number(result, "total_trades") > 0 else 0.0
        points += 25.0 if self._number(result, "net_profit_points") > 0 else 0.0
        points += 25.0 if self._number(result, "profit_factor") >= 1.2 else 0.0
        points += 25.0 if self._number(result, "win_rate") >= 0.50 else 0.0
        return points

    def _robustness_score(self) -> float:
        score = self._generic_score(self.robustness_result, "robustness_score")
        if self.sensitivity_result is None:
            return score
        return self._average([score, self._sensitivity_score()])

    def _sensitivity_score(self) -> float:
        level = str(self._value(self.sensitivity_result, "sensitivity_level", ""))
        return {"LOW": 100.0, "MEDIUM": 65.0, "HIGH": 30.0}.get(level, 0.0)

    def _walk_forward_score(self) -> float:
        result = self.walk_forward_result
        if result is None:
            return 0.0
        status = str(self._value(result, "robustness_status", ""))
        if status == "ROBUST":
            return 100.0
        if status == "DEGRADED":
            return 60.0
        return max(0.0, 100.0 - self._number(result, "overfitting_score"))

    def _monte_carlo_score(self) -> float:
        return self._generic_score(self.monte_carlo_result, "monte_carlo_score")

    def _drawdown_score(self) -> float:
        drawdown = self._drawdown_value()
        if drawdown <= 0:
            return 100.0 if self.backtest_result else 0.0
        profit = abs(self.backtest_result.total_profit) if self.backtest_result else 0.0
        if profit <= 0:
            return 30.0
        return max(0.0, 100.0 - min((drawdown / profit) * 100.0, 100.0))

    def _drawdown_value(self) -> float:
        if self.backtest_result is not None:
            return float(self.backtest_result.drawdown)
        if self.benchmark_result is not None:
            return self._number(self.benchmark_result, "max_drawdown_points")
        return 0.0

    def _recommendation(
        self,
        score: float,
        sections: list[QuantitativeReportSection],
    ) -> str:
        if self._has_rejection_signal(sections) or score < 40.0:
            if not self._has_any_data():
                return "NEED_MORE_RESEARCH"
            return "REJECTED"
        if score >= 75.0 and self._has_required_core_data():
            return "APPROVED_FOR_PAPER"
        return "NEED_MORE_RESEARCH"

    def _has_rejection_signal(self, sections: list[QuantitativeReportSection]) -> bool:
        statuses = [section.status for section in sections]
        rejected = {"REJECTED", "FRAGILE", "OVERFITTED", "UNSTABLE"}
        return any(status in rejected for status in statuses)

    def _has_required_core_data(self) -> bool:
        return all(
            item is not None
            for item in (
                self.backtest_result,
                self.benchmark_result,
                self.walk_forward_result,
                self.robustness_result,
                self.monte_carlo_result,
            )
        )

    def _has_any_data(self) -> bool:
        return any(
            item is not None
            for item in (
                self.backtest_result,
                self.benchmark_result,
                self.walk_forward_result,
                self.robustness_result,
                self.sensitivity_result,
                self.regime_performance,
                self.temporal_performance,
                self.temporal_stability,
                self.stress_result,
                self.monte_carlo_result,
            )
        )

    def _overall_score(self, sections: list[QuantitativeReportSection]) -> float:
        return round(self._average([section.score for section in sections]), 2)

    def _overall_status(self, recommendation: str) -> str:
        if recommendation == "APPROVED_FOR_PAPER":
            return "APPROVED"
        if recommendation == "REJECTED":
            return "REJECTED"
        return "NEEDS_RESEARCH"

    def _status_from_score(self, score: float) -> str:
        if score >= 75.0:
            return "APPROVED"
        return "NEEDS_RESEARCH"

    def _walk_forward_status(self, score: float) -> str:
        if self.walk_forward_result is None:
            return "INCONCLUSIVE"
        status = str(self._value(self.walk_forward_result, "robustness_status", ""))
        return status or self._status_from_score(score)

    def _generic_score(self, result: object | None, field_name: str) -> float:
        if result is None:
            return 0.0
        if isinstance(result, dict):
            return float(result.get(field_name, result.get("score", 0.0)))
        return float(getattr(result, field_name, getattr(result, "score", 0.0)))

    def _generic_status(self, result: object | None, score: float) -> str:
        if result is None:
            return "INCONCLUSIVE"
        status = str(self._value(result, "status", ""))
        return status or self._status_from_score(score)

    def _backtest_details(self) -> dict[str, object]:
        result = self.backtest_result
        if result is None:
            return {"backtest": "indisponivel"}
        return {
            "total_trades": result.total_trades,
            "net_profit_points": result.total_profit,
            "win_rate": result.win_rate,
            "profit_factor": result.profit_factor,
            "max_drawdown_points": result.drawdown,
        }

    def _benchmark_details(self) -> dict[str, object]:
        result = self.benchmark_result
        if result is None:
            return {"benchmark": "indisponivel"}
        return {
            "strategy_name": self._value(result, "strategy_name", ""),
            "total_trades": self._number(result, "total_trades"),
            "net_profit_points": self._number(result, "net_profit_points"),
            "profit_factor": self._number(result, "profit_factor"),
        }

    def _robustness_details(self) -> dict[str, object]:
        result = self.robustness_result
        return {
            "robustness_score": self._generic_score(result, "robustness_score"),
            "robustness_status": self._value(result, "status", "INCONCLUSIVE"),
            "robustness_reasons": self._value(result, "reasons", []),
        }

    def _sensitivity_details(self) -> dict[str, object]:
        result = self.sensitivity_result
        return {
            "sensitivity_level": self._value(result, "sensitivity_level", ""),
            "metric_impact": self._number(result, "metric_impact"),
            "parameter_name": self._value(result, "parameter_name", ""),
        }

    def _walk_forward_details(self) -> dict[str, object]:
        result = self.walk_forward_result
        return {
            "robustness_status": self._value(result, "robustness_status", ""),
            "overfitting_score": self._number(result, "overfitting_score"),
        }

    def _monte_carlo_details(self) -> dict[str, object]:
        result = self.monte_carlo_result
        return {
            "monte_carlo_score": self._monte_carlo_score(),
            "worst_drawdown": self._number(result, "worst_drawdown"),
            "ruin_probability": self._number(result, "ruin_probability"),
            "status": self._value(result, "status", "INCONCLUSIVE"),
        }

    def _risk_details(self) -> dict[str, object]:
        return {
            "drawdown_points": self._drawdown_value(),
            "monte_carlo_status": self._value(
                self.monte_carlo_result,
                "status",
                "INCONCLUSIVE",
            ),
            "stress_status": self._value(
                self.stress_result,
                "status",
                "INCONCLUSIVE",
            ),
        }

    def _generic_details(self, result: object | None) -> dict[str, object]:
        if result is None:
            return {"status": "INCONCLUSIVE"}
        if isinstance(result, dict):
            return dict(result)
        return {
            key: value
            for key, value in vars(result).items()
            if not key.startswith("_")
        }

    def _value(self, source: object | None, name: str, default: Any) -> Any:
        if source is None:
            return default
        if isinstance(source, dict):
            return source.get(name, default)
        return getattr(source, name, default)

    def _number(self, source: object | None, name: str) -> float:
        return float(self._value(source, name, 0.0))

    def _average(self, values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)
