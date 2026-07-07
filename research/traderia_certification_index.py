"""Indice de Certificacao TraderIA para Alphas pesquisadas."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class TraderIACertificationInput:
    """Metricas quantitativas usadas para certificar uma Alpha."""

    win_rate: float
    profit_factor: float
    expectancy: float
    max_drawdown: float
    sample_size: int
    recovery_factor: float


@dataclass(frozen=True)
class TraderIACertificationResult:
    """Resultado institucional do Indice de Certificacao TraderIA."""

    ict_score: float
    grade: str
    status: str
    usage: str
    demo_allowed: bool
    minimum_filters_passed: bool
    rejection_reasons: tuple[str, ...]
    component_scores: dict[str, float]


class TraderIACertificationEngine:
    """Calcula ICT sem acessar UI, broker, MT5 ou infraestrutura."""

    minimum_profit_factor: float = 1.30
    minimum_expectancy: float = 0.0
    minimum_sample_size: int = 100
    maximum_drawdown: float = 0.25

    def certify(
        self,
        payload: TraderIACertificationInput,
    ) -> TraderIACertificationResult:
        """Aplica filtro eliminatorio e depois calcula o ICT ponderado."""
        components = {
            "win_rate": self._win_rate_score(payload.win_rate),
            "profit_factor": self._profit_factor_score(payload.profit_factor),
            "expectancy": self._expectancy_score(payload.expectancy),
            "drawdown": self._drawdown_score(payload.max_drawdown),
            "sample_size": self._sample_size_score(payload.sample_size),
            "recovery_factor": self._recovery_factor_score(
                payload.recovery_factor,
            ),
        }
        ict = (
            components["win_rate"] * 0.25
            + components["profit_factor"] * 0.25
            + components["expectancy"] * 0.20
            + components["drawdown"] * 0.15
            + components["sample_size"] * 0.10
            + components["recovery_factor"] * 0.05
        )
        rejections = self._minimum_rejections(payload)
        filters_passed = not rejections
        grade, status, usage, demo_allowed = self._classification(ict, filters_passed)
        return TraderIACertificationResult(
            ict_score=round(ict, 2),
            grade=grade,
            status=status,
            usage=usage,
            demo_allowed=demo_allowed,
            minimum_filters_passed=filters_passed,
            rejection_reasons=tuple(rejections),
            component_scores={key: round(value, 2) for key, value in components.items()},
        )

    def from_research_metrics(
        self,
        *,
        win_rate: float,
        profit_factor: float,
        avg_return: float,
        max_drawdown: float,
        sample_size: int,
    ) -> TraderIACertificationResult:
        """Adapta as metricas atuais do Research Lab para o contrato do ICT."""
        return self.certify(
            TraderIACertificationInput(
                win_rate=win_rate,
                profit_factor=profit_factor,
                expectancy=avg_return,
                max_drawdown=max_drawdown,
                sample_size=sample_size,
                recovery_factor=self._recovery_from_return_and_drawdown(
                    avg_return,
                    max_drawdown,
                ),
            )
        )

    def _minimum_rejections(
        self,
        payload: TraderIACertificationInput,
    ) -> list[str]:
        reasons: list[str] = []
        if (
            not isfinite(payload.profit_factor)
            and payload.profit_factor != float("inf")
        ) or payload.profit_factor < self.minimum_profit_factor:
            reasons.append("Profit Factor abaixo de 1.30.")
        if payload.expectancy <= self.minimum_expectancy:
            reasons.append("Expectancy historica menor ou igual a zero.")
        if payload.sample_size < self.minimum_sample_size:
            reasons.append("Amostra historica abaixo de 100 trades.")
        if payload.max_drawdown > self.maximum_drawdown:
            reasons.append("Drawdown maximo acima de 25%.")
        return reasons

    def _classification(
        self,
        ict: float,
        filters_passed: bool,
    ) -> tuple[str, str, str, bool]:
        if not filters_passed:
            return "E", "REJEITADA", "Rejeitada pelos filtros minimos.", False
        if ict >= 90.0:
            return "A+", "CERTIFICADA_A_PLUS", "Operacao automatica Demo liberada.", True
        if ict >= 80.0:
            return "A", "CERTIFICADA_A", "Operacao automatica Demo liberada.", True
        if ict >= 70.0:
            return "B", "CERTIFICADA_B", "Operacao Demo com monitoramento reforcado.", True
        if ict >= 60.0:
            return "C", "PESQUISA_REPLAY", "Apenas Research e Replay.", False
        if ict >= 50.0:
            return "D", "HIPOTESE_PROMISSORA", "Continuar pesquisando.", False
        return "E", "REJEITADA", "Rejeitada.", False

    def _win_rate_score(self, win_rate: float) -> float:
        value = self._ratio(win_rate)
        if value < 0.40:
            return 0.0
        if value >= 0.70:
            return 100.0
        if value <= 0.50:
            return self._linear(value, 0.40, 0.50, 0.0, 50.0)
        if value <= 0.60:
            return self._linear(value, 0.50, 0.60, 50.0, 75.0)
        return self._linear(value, 0.60, 0.70, 75.0, 100.0)

    def _profit_factor_score(self, profit_factor: float) -> float:
        if not isfinite(profit_factor):
            return 100.0 if profit_factor > 0 else 0.0
        if profit_factor < 1.0:
            return 0.0
        if profit_factor >= 2.5:
            return 100.0
        if profit_factor <= 1.2:
            return self._linear(profit_factor, 1.0, 1.2, 0.0, 40.0)
        if profit_factor <= 1.5:
            return self._linear(profit_factor, 1.2, 1.5, 40.0, 70.0)
        if profit_factor <= 2.0:
            return self._linear(profit_factor, 1.5, 2.0, 70.0, 90.0)
        return self._linear(profit_factor, 2.0, 2.5, 90.0, 100.0)

    def _expectancy_score(self, expectancy: float) -> float:
        if expectancy <= 0.0:
            return 0.0
        if expectancy >= 0.002:
            return 100.0
        if expectancy <= 0.0002:
            return self._linear(expectancy, 0.0, 0.0002, 30.0, 50.0)
        if expectancy <= 0.001:
            return self._linear(expectancy, 0.0002, 0.001, 50.0, 70.0)
        return self._linear(expectancy, 0.001, 0.002, 70.0, 100.0)

    def _drawdown_score(self, drawdown: float) -> float:
        value = max(float(drawdown or 0.0), 0.0)
        if value > 0.30:
            return 0.0
        if value <= 0.05:
            return 100.0
        if value <= 0.10:
            return self._linear(value, 0.05, 0.10, 100.0, 80.0)
        if value <= 0.20:
            return self._linear(value, 0.10, 0.20, 80.0, 40.0)
        return self._linear(value, 0.20, 0.30, 40.0, 0.0)

    def _sample_size_score(self, sample_size: int) -> float:
        value = int(sample_size or 0)
        if value < 50:
            return 20.0 if value > 0 else 0.0
        if value >= 500:
            return 100.0
        if value <= 100:
            return self._linear(float(value), 50.0, 100.0, 20.0, 50.0)
        if value <= 250:
            return self._linear(float(value), 100.0, 250.0, 50.0, 80.0)
        return self._linear(float(value), 250.0, 500.0, 80.0, 100.0)

    def _recovery_factor_score(self, recovery_factor: float) -> float:
        value = max(float(recovery_factor or 0.0), 0.0)
        if value < 1.0:
            return 0.0
        if value >= 5.0:
            return 100.0
        if value <= 2.0:
            return self._linear(value, 1.0, 2.0, 0.0, 50.0)
        if value <= 3.0:
            return self._linear(value, 2.0, 3.0, 50.0, 75.0)
        return self._linear(value, 3.0, 5.0, 75.0, 100.0)

    def _recovery_from_return_and_drawdown(
        self,
        avg_return: float,
        max_drawdown: float,
    ) -> float:
        if avg_return <= 0.0:
            return 0.0
        if max_drawdown <= 0.0:
            return 5.0
        return max(0.0, avg_return / max_drawdown)

    def _ratio(self, value: float) -> float:
        return float(value) / 100.0 if float(value) > 1.0 else float(value)

    def _linear(
        self,
        value: float,
        left: float,
        right: float,
        left_score: float,
        right_score: float,
    ) -> float:
        if right == left:
            return right_score
        bounded = min(max(value, left), right)
        position = (bounded - left) / (right - left)
        return left_score + (right_score - left_score) * position
