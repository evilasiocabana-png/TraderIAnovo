"""Strategy oficial da Alpha102."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha102.alpha102_config import Alpha102Config


SCORE_MULTIPLIER = 100
FORBIDDEN_REGIMES = {
    "LOW_LIQUIDITY",
    "ERRATIC",
    "NOISE",
    "BLACK_SWAN",
}
BLOCKING_RISK_DECISIONS = {
    "BLOCK_RESEARCH",
    "BLOCK_PAPER",
}
BLOCKING_RESEARCH_STATUSES = {
    "FAILED",
    "REJECTED",
    "BLOCKED",
}


@dataclass(frozen=True)
class Alpha102Strategy:
    """Aplica as regras de pullback de continuidade Swing Trade."""

    config: Alpha102Config
    nome: str = "alpha102_swing_pullback_momentum_continuation"

    def generate_signal(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> StrategySignal:
        """Gera StrategySignal a partir de contexto e features aprovadas."""
        rejection_reasons = self._rejection_reasons(market_context, feature_report)
        if rejection_reasons:
            return self._wait(rejection_reasons)

        trend_direction = self._feature_float(feature_report, "trend_direction")
        momentum = self._feature_float(feature_report, "momentum")
        recovery_confirmation = self._feature_float(
            feature_report,
            "recovery_confirmation",
        )

        if (
            trend_direction > 0
            and momentum >= self.config.momentum_confirmation_threshold
            and recovery_confirmation > 0
        ):
            return self._signal(
                decision="BUY",
                confidence=market_context.confidence,
                reasons=[
                    "tendencia superior positiva qualificada",
                    "pullback controlado preservou a estrutura",
                    "momentum comprador alinhado",
                ],
            )

        if (
            trend_direction < 0
            and momentum <= -self.config.momentum_confirmation_threshold
            and recovery_confirmation < 0
        ):
            return self._signal(
                decision="SELL",
                confidence=market_context.confidence,
                reasons=[
                    "tendencia superior negativa qualificada",
                    "pullback controlado preservou a estrutura",
                    "momentum vendedor alinhado",
                ],
            )

        return self._wait(["retomada pos-pullback nao confirmada"])

    def _rejection_reasons(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> list[str]:
        reasons: list[str] = []
        required_features = (
            "price",
            "trend_direction",
            "trend_strength",
            "pullback_depth",
            "structure_intact",
            "recovery_confirmation",
            "volume",
            "volatility",
            "momentum",
        )
        missing = [
            feature
            for feature in required_features
            if self._feature_value(feature_report, feature) is None
        ]
        if missing:
            reasons.append(f"features ausentes: {', '.join(missing)}")
            return reasons

        if market_context.regime.strip().upper() in FORBIDDEN_REGIMES:
            reasons.append("regime proibido para rompimento Swing Trade")
        if market_context.liquidity < self.config.minimum_volume:
            reasons.append("liquidez abaixo do minimo")
        if market_context.volatility < self.config.minimum_volatility:
            reasons.append("volatilidade abaixo do minimo")
        if market_context.confidence < self.config.minimum_confidence:
            reasons.append("confianca abaixo do minimo")
        if self._feature_float(feature_report, "volume") < self.config.minimum_volume:
            reasons.append("volume abaixo do minimo")
        if (
            self._feature_float(feature_report, "volatility")
            < self.config.minimum_volatility
        ):
            reasons.append("feature de volatilidade abaixo do minimo")
        if (
            self._feature_float(feature_report, "trend_strength")
            < self.config.minimum_trend_strength
        ):
            reasons.append("forca de tendencia abaixo do minimo")
        if (
            self._feature_float(feature_report, "pullback_depth")
            < self.config.minimum_pullback_depth
        ):
            reasons.append("pullback abaixo da profundidade minima")
        if (
            self._feature_float(feature_report, "pullback_depth")
            > self.config.maximum_pullback_depth
        ):
            reasons.append("pullback acima da profundidade maxima")
        if not self._feature_bool(feature_report, "structure_intact"):
            reasons.append("estrutura principal do pullback violada")
        if self._data_quality_score(feature_report) < self.config.minimum_confidence:
            reasons.append("Data Lab abaixo do minimo")
        if self._decision_approval_score(market_context) < self.config.minimum_confidence:
            reasons.append("Decision Lab abaixo do minimo")
        if self._risk_decision(market_context) in BLOCKING_RISK_DECISIONS:
            reasons.append("Risk Lab bloqueou a pesquisa")
        if self._research_status(market_context) in BLOCKING_RESEARCH_STATUSES:
            reasons.append("Research Lab rejeitou o cenario")
        if self._research_confidence(market_context) < self.config.minimum_confidence:
            reasons.append("Research Lab abaixo do minimo")
        return reasons

    def _feature_float(
        self,
        feature_report: FeatureReport,
        name: str,
    ) -> float | None:
        value = self._feature_value(feature_report, name)
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(converted):
            return None
        return converted

    def _feature_value(
        self,
        feature_report: FeatureReport,
        name: str,
    ) -> object | None:
        value = feature_report.calculated_values.get(name)
        if value is None:
            value = feature_report.calculated_values.get(name.upper())
        if value is None:
            value = feature_report.calculated_values.get(name.capitalize())
        return value

    def _feature_bool(
        self,
        feature_report: FeatureReport,
        name: str,
    ) -> bool:
        value = self._feature_value(feature_report, name)
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().upper() in {"TRUE", "1", "YES", "Y"}
        return False

    def _data_quality_score(self, feature_report: FeatureReport) -> float:
        value = feature_report.calculated_values.get("data_quality_score", 1.0)
        return self._metadata_score(value)

    def _decision_approval_score(self, market_context: MarketContext) -> float:
        value = market_context.metadata.get("decision_approval_score", 1.0)
        return self._metadata_score(value)

    def _research_confidence(self, market_context: MarketContext) -> float:
        value = market_context.metadata.get("research_confidence", 1.0)
        return self._metadata_score(value)

    def _risk_decision(self, market_context: MarketContext) -> str:
        value = market_context.metadata.get("risk_policy_decision", "ALLOW")
        return str(value).strip().upper()

    def _research_status(self, market_context: MarketContext) -> str:
        value = market_context.metadata.get("research_validation_status", "PASSED")
        return str(value).strip().upper()

    def _metadata_score(self, value: object) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not isfinite(score):
            return 0.0
        return score

    def _signal(
        self,
        decision: str,
        confidence: float,
        reasons: list[str],
    ) -> StrategySignal:
        return StrategySignal(
            decision=decision,
            score=self._score(confidence),
            confidence=confidence,
            reasons=reasons,
        )

    def _wait(self, reasons: list[str]) -> StrategySignal:
        return StrategySignal(
            decision="WAIT",
            score=0,
            confidence=0.0,
            reasons=reasons,
        )

    def _score(self, confidence: float) -> int:
        if not isfinite(confidence):
            return 0
        normalized = min(max(confidence, 0.0), 1.0)
        return int(round(normalized * SCORE_MULTIPLIER))
