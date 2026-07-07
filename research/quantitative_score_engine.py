"""Motor de score quantitativo calibrado por evidencia observada."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class QuantitativeScoreConfiguration:
    """Configuracao explicita do score quantitativo calibrado."""

    candles_loaded: int
    feature_lookback: int
    forward_return_candles: int
    fast_ma_period: int
    slow_ma_period: int
    rsi_period: int
    volatility_period: int
    min_sample_size: int
    min_profit_factor: float
    min_win_rate: float
    confidence_floor: float
    confidence_ceiling: float
    volatility_bucket_method: str
    volatility_low_threshold: float
    volatility_high_threshold: float
    ma_flat_threshold: float
    ma_strong_threshold: float
    rsi_oversold_threshold: float
    rsi_overbought_threshold: float


@dataclass(frozen=True)
class QuantitativeScoreContext:
    """Contexto de features usado para consultar evidencia historica."""

    trend: str
    momentum: float
    volatility: float
    rsi: float
    moving_average_distance: float
    candidate_decision: str


@dataclass(frozen=True)
class QuantitativeScoreObservation:
    """Observacao historica ou simulada com retorno posterior conhecido."""

    trend: str
    momentum: float
    volatility: float
    rsi: float
    moving_average_distance: float
    candidate_decision: str
    forward_return: float


@dataclass(frozen=True)
class QuantitativeScoreResult:
    """Resultado calibrado para consumo por servicos de aplicacao."""

    decision: str
    calibrated_confidence: float
    sample_size: int
    win_rate: float
    avg_return: float
    profit_factor: float
    max_drawdown: float
    reason: str
    matched_context_count: int = 0
    rejected_reason: str = ""
    volatility_bucket: str = "UNKNOWN"
    rsi_bucket: str = "UNKNOWN"
    momentum_sign: str = "ZERO"
    ma_distance_bucket: str = "FLAT"
    confidence_penalties: tuple[str, ...] = ()
    confidence_drivers: tuple[str, ...] = ()


class QuantitativeScoreEngine:
    """Calcula confianca por estatistica observada, sem acessar infraestrutura."""

    def __init__(self, configuration: QuantitativeScoreConfiguration) -> None:
        self.configuration = configuration

    def calculate(
        self,
        context: QuantitativeScoreContext,
        observations: list[QuantitativeScoreObservation],
    ) -> QuantitativeScoreResult:
        """Retorna score calibrado para o contexto informado."""
        candidate = self._normalize_decision(context.candidate_decision)
        diagnostic = self._diagnostic(context)
        if candidate == "WAIT":
            return self._wait(
                sample_size=0,
                reason="Decisao candidata WAIT; sem exposicao estatistica.",
                diagnostic=diagnostic,
                rejected_reason="CANDIDATE_WAIT",
                confidence_penalties=("candidate_wait",),
            )
        if context.volatility < self.configuration.volatility_low_threshold:
            return self._wait(
                sample_size=0,
                reason="Volatilidade baixa; contexto penalizado para WAIT.",
                diagnostic=diagnostic,
                rejected_reason="LOW_VOLATILITY",
                confidence_penalties=("low_volatility",),
            )

        matched = self._matching_observations(context, observations)
        returns = [self._directional_return(candidate, item.forward_return) for item in matched]
        stats = self._stats(returns)

        if stats["sample_size"] < self.configuration.min_sample_size:
            confidence = min(
                self.configuration.confidence_ceiling,
                self.configuration.confidence_floor
                + (
                    stats["sample_size"]
                    / self.configuration.min_sample_size
                    * (
                        self.configuration.confidence_ceiling
                        - self.configuration.confidence_floor
                    )
                ),
            )
            return QuantitativeScoreResult(
                decision="WAIT",
                calibrated_confidence=confidence,
                sample_size=stats["sample_size"],
                win_rate=stats["win_rate"],
                avg_return=stats["avg_return"],
                profit_factor=stats["profit_factor"],
                max_drawdown=stats["max_drawdown"],
                reason="Amostra insuficiente para calibrar decisao; WAIT.",
                matched_context_count=stats["sample_size"],
                rejected_reason="LOW_SAMPLE_SIZE",
                confidence_penalties=("low_sample_size",),
                confidence_drivers=self._confidence_drivers(context, stats),
                **diagnostic,
            )

        if stats["profit_factor"] < self.configuration.min_profit_factor:
            return QuantitativeScoreResult(
                decision="WAIT",
                calibrated_confidence=max(
                    self.configuration.confidence_floor,
                    min(self.configuration.confidence_ceiling, stats["win_rate"]),
                ),
                sample_size=stats["sample_size"],
                win_rate=stats["win_rate"],
                avg_return=stats["avg_return"],
                profit_factor=stats["profit_factor"],
                max_drawdown=stats["max_drawdown"],
                reason="Profit factor insuficiente na amostra; WAIT.",
                matched_context_count=stats["sample_size"],
                rejected_reason="LOW_PROFIT_FACTOR",
                confidence_penalties=("low_profit_factor",),
                confidence_drivers=self._confidence_drivers(context, stats),
                **diagnostic,
            )

        if (
            stats["avg_return"] <= 0.0
            or stats["win_rate"] <= self.configuration.min_win_rate
        ):
            return QuantitativeScoreResult(
                decision="WAIT",
                calibrated_confidence=max(
                    self.configuration.confidence_floor,
                    min(self.configuration.confidence_ceiling, stats["win_rate"]),
                ),
                sample_size=stats["sample_size"],
                win_rate=stats["win_rate"],
                avg_return=stats["avg_return"],
                profit_factor=stats["profit_factor"],
                max_drawdown=stats["max_drawdown"],
                reason="Estatistica historica fraca; WAIT.",
                matched_context_count=stats["sample_size"],
                rejected_reason="WEAK_STATISTICS",
                confidence_penalties=("weak_statistics",),
                confidence_drivers=self._confidence_drivers(context, stats),
                **diagnostic,
            )

        confidence = self._calibrated_confidence(
            sample_size=stats["sample_size"],
            win_rate=stats["win_rate"],
            avg_return=stats["avg_return"],
            profit_factor=stats["profit_factor"],
            max_drawdown=stats["max_drawdown"],
        )
        return QuantitativeScoreResult(
            decision=candidate,
            calibrated_confidence=confidence,
            sample_size=stats["sample_size"],
            win_rate=stats["win_rate"],
            avg_return=stats["avg_return"],
            profit_factor=stats["profit_factor"],
            max_drawdown=stats["max_drawdown"],
            reason=(
                "Confianca calibrada por amostra historica semelhante: "
                f"{stats['sample_size']} ocorrencias, win rate {stats['win_rate']:.1%}, "
                f"profit factor {stats['profit_factor']:.2f}."
            ),
            matched_context_count=stats["sample_size"],
            rejected_reason="",
            confidence_penalties=self._confidence_penalties(stats),
            confidence_drivers=self._confidence_drivers(context, stats),
            **diagnostic,
        )

    def _matching_observations(
        self,
        context: QuantitativeScoreContext,
        observations: list[QuantitativeScoreObservation],
    ) -> list[QuantitativeScoreObservation]:
        return [
            item
            for item in observations
            if self._normalize_decision(item.candidate_decision)
            == self._normalize_decision(context.candidate_decision)
            and item.trend == context.trend
            and self._sign(item.momentum) == self._sign(context.momentum)
            and self._sign(item.moving_average_distance)
            == self._sign(context.moving_average_distance)
            and self._volatility_bucket(item.volatility)
            == self._volatility_bucket(context.volatility)
            and self._rsi_bucket(item.rsi) == self._rsi_bucket(context.rsi)
        ]

    def _stats(self, returns: list[float]) -> dict[str, float | int]:
        sample_size = len(returns)
        if sample_size == 0:
            return {
                "sample_size": 0,
                "win_rate": 0.0,
                "avg_return": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
            }
        wins = [value for value in returns if value > 0.0]
        losses = [-value for value in returns if value < 0.0]
        gross_profit = sum(wins)
        gross_loss = sum(losses)
        profit_factor = float("inf") if gross_loss == 0.0 and gross_profit > 0 else 0.0
        if gross_loss > 0.0:
            profit_factor = gross_profit / gross_loss
        return {
            "sample_size": sample_size,
            "win_rate": len(wins) / sample_size,
            "avg_return": sum(returns) / sample_size,
            "profit_factor": profit_factor,
            "max_drawdown": self._max_drawdown(returns),
        }

    def _calibrated_confidence(
        self,
        sample_size: int,
        win_rate: float,
        avg_return: float,
        profit_factor: float,
        max_drawdown: float,
    ) -> float:
        sample_score = min(
            sample_size / (self.configuration.min_sample_size * 3),
            1.0,
        )
        pf_score = min(max(profit_factor - 1.0, 0.0) / 2.0, 1.0)
        if not isfinite(profit_factor):
            pf_score = 1.0
        drawdown_penalty = min(max_drawdown / 0.02, 0.30)
        confidence = (0.45 * win_rate) + (0.25 * pf_score)
        confidence += 0.20 * sample_score
        confidence += 0.10 * min(max(avg_return / 0.002, 0.0), 1.0)
        confidence -= drawdown_penalty
        return max(
            self.configuration.confidence_floor,
            min(confidence, self.configuration.confidence_ceiling),
        )

    def _max_drawdown(self, returns: list[float]) -> float:
        equity = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for value in returns:
            equity += value
            peak = max(peak, equity)
            max_drawdown = max(max_drawdown, peak - equity)
        return max_drawdown

    def _directional_return(self, decision: str, forward_return: float) -> float:
        if decision == "SELL":
            return -forward_return
        if decision == "BUY":
            return forward_return
        return 0.0

    def _wait(
        self,
        sample_size: int,
        reason: str,
        diagnostic: dict[str, str],
        rejected_reason: str,
        confidence_penalties: tuple[str, ...],
    ) -> QuantitativeScoreResult:
        return QuantitativeScoreResult(
            decision="WAIT",
            calibrated_confidence=0.0,
            sample_size=sample_size,
            win_rate=0.0,
            avg_return=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            reason=reason,
            matched_context_count=sample_size,
            rejected_reason=rejected_reason,
            confidence_penalties=confidence_penalties,
            confidence_drivers=(),
            **diagnostic,
        )

    def _normalize_decision(self, value: str) -> str:
        normalized = str(value or "").upper()
        if normalized in {"BUY", "SELL"}:
            return normalized
        return "WAIT"

    def _sign(self, value: float) -> int:
        if value > 0.0:
            return 1
        if value < 0.0:
            return -1
        return 0

    def _sign_label(self, value: float) -> str:
        sign = self._sign(value)
        if sign > 0:
            return "POSITIVE"
        if sign < 0:
            return "NEGATIVE"
        return "ZERO"

    def _ma_distance_bucket(self, value: float) -> str:
        abs_value = abs(value)
        if abs_value < self.configuration.ma_flat_threshold:
            return "FLAT"
        if abs_value < self.configuration.ma_strong_threshold:
            return "MODERATE"
        return "STRONG"

    def _diagnostic(self, context: QuantitativeScoreContext) -> dict[str, str]:
        return {
            "volatility_bucket": self._volatility_bucket(context.volatility),
            "rsi_bucket": self._rsi_bucket(context.rsi),
            "momentum_sign": self._sign_label(context.momentum),
            "ma_distance_bucket": self._ma_distance_bucket(
                context.moving_average_distance
            ),
        }

    def _confidence_drivers(
        self,
        context: QuantitativeScoreContext,
        stats: dict[str, float | int],
    ) -> tuple[str, ...]:
        drivers: list[str] = []
        if context.trend in {"ALTA", "BAIXA"}:
            drivers.append("trend_aligned")
        if self._sign(context.momentum) == self._sign(context.moving_average_distance):
            drivers.append("momentum_ma_aligned")
        if int(stats["sample_size"]) >= self.configuration.min_sample_size:
            drivers.append("sample_size_sufficient")
        if float(stats["win_rate"]) > self.configuration.min_win_rate:
            drivers.append("win_rate_positive")
        if float(stats["avg_return"]) > 0.0:
            drivers.append("avg_return_positive")
        profit_factor = float(stats["profit_factor"])
        if (
            not isfinite(profit_factor)
            or profit_factor >= self.configuration.min_profit_factor
        ):
            drivers.append("profit_factor_sufficient")
        return tuple(drivers)

    def _confidence_penalties(
        self,
        stats: dict[str, float | int],
    ) -> tuple[str, ...]:
        penalties: list[str] = []
        if int(stats["sample_size"]) < self.configuration.min_sample_size:
            penalties.append("low_sample_size")
        if float(stats["profit_factor"]) < self.configuration.min_profit_factor:
            penalties.append("low_profit_factor")
        if float(stats["max_drawdown"]) > 0.0:
            penalties.append("drawdown_penalty")
        return tuple(penalties)

    def _volatility_bucket(self, value: float) -> str:
        if value < self.configuration.volatility_low_threshold:
            return "LOW"
        if value < self.configuration.volatility_high_threshold:
            return "NORMAL"
        return "HIGH"

    def _rsi_bucket(self, value: float) -> str:
        if value < self.configuration.rsi_oversold_threshold:
            return "OVERSOLD"
        if value > self.configuration.rsi_overbought_threshold:
            return "OVERBOUGHT"
        return "HEALTHY"
