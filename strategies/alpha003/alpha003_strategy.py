"""Strategy oficial da Alpha003."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha003.alpha003_config import Alpha003Config


SCORE_MULTIPLIER = 100
FORBIDDEN_REGIMES = {
    "RANGE_WEAK",
    "LOW_LIQUIDITY",
    "NO_TREND",
    "ERRATIC",
}
BLOCKING_RISK_DECISIONS = {
    "BLOCK_RESEARCH",
    "BLOCK_PAPER",
}


@dataclass(frozen=True)
class Alpha003Strategy:
    """Aplica as regras de rompimento contextual da Opening Range."""

    config: Alpha003Config
    nome: str = "alpha003_opening_range_breakout"

    def generate_signal(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> StrategySignal:
        """Gera StrategySignal a partir de contexto e features aprovadas."""
        rejection_reasons = self._rejection_reasons(market_context, feature_report)
        if rejection_reasons:
            return self._wait(rejection_reasons)

        price = self._feature_float(feature_report, "price")
        opening_range_high = self._feature_float(feature_report, "opening_range_high")
        opening_range_low = self._feature_float(feature_report, "opening_range_low")
        momentum = self._feature_float(feature_report, "momentum")

        if price > opening_range_high and momentum > 0:
            return self._signal(
                decision="BUY",
                confidence=market_context.confidence,
                reasons=[
                    "rompimento acima da Opening Range",
                    "momentum comprador alinhado",
                    "contexto aprovado para breakout",
                ],
            )

        if price < opening_range_low and momentum < 0:
            return self._signal(
                decision="SELL",
                confidence=market_context.confidence,
                reasons=[
                    "rompimento abaixo da Opening Range",
                    "momentum vendedor alinhado",
                    "contexto aprovado para breakout",
                ],
            )

        return self._wait(["gatilho de rompimento da Opening Range nao confirmado"])

    def _rejection_reasons(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> list[str]:
        reasons: list[str] = []
        required_features = (
            "price",
            "opening_range_high",
            "opening_range_low",
            "volume",
            "volatility",
            "momentum",
        )
        missing = [
            feature
            for feature in required_features
            if self._feature_float(feature_report, feature) is None
        ]
        if missing:
            reasons.append(f"features ausentes: {', '.join(missing)}")
            return reasons

        if not self._is_inside_session(market_context.timestamp):
            reasons.append("fora da sessao configurada")
        if market_context.regime.strip().upper() in FORBIDDEN_REGIMES:
            reasons.append("regime proibido para Opening Range breakout")
        if market_context.liquidity < self.config.minimum_volume:
            reasons.append("liquidez abaixo do minimo")
        if market_context.volatility < self.config.minimum_volatility:
            reasons.append("volatilidade abaixo do minimo")
        if market_context.confidence < self.config.minimum_confidence:
            reasons.append("confianca abaixo do minimo")
        if self._feature_float(feature_report, "volume") < self.config.minimum_volume:
            reasons.append("volume abaixo do minimo")
        if self._feature_float(feature_report, "volatility") < self.config.minimum_volatility:
            reasons.append("feature de volatilidade abaixo do minimo")
        if self._data_quality_score(feature_report) < self.config.minimum_confidence:
            reasons.append("Data Lab abaixo do minimo")
        if self._decision_approval_score(market_context) < self.config.minimum_confidence:
            reasons.append("Decision Lab abaixo do minimo")
        if self._risk_decision(market_context) in BLOCKING_RISK_DECISIONS:
            reasons.append("Risk Lab bloqueou a pesquisa")
        return reasons

    def _feature_float(
        self,
        feature_report: FeatureReport,
        name: str,
    ) -> float | None:
        value = feature_report.calculated_values.get(name)
        if value is None:
            value = feature_report.calculated_values.get(name.upper())
        if value is None:
            value = feature_report.calculated_values.get(name.capitalize())
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return None
        if not isfinite(converted):
            return None
        return converted

    def _data_quality_score(self, feature_report: FeatureReport) -> float:
        value = feature_report.calculated_values.get("data_quality_score", 1.0)
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not isfinite(score):
            return 0.0
        return score

    def _decision_approval_score(self, market_context: MarketContext) -> float:
        value = market_context.metadata.get("decision_approval_score", 1.0)
        try:
            score = float(value)
        except (TypeError, ValueError):
            return 0.0
        if not isfinite(score):
            return 0.0
        return score

    def _risk_decision(self, market_context: MarketContext) -> str:
        value = market_context.metadata.get("risk_policy_decision", "ALLOW")
        return str(value).strip().upper()

    def _is_inside_session(self, timestamp: str) -> bool:
        current_time = self._time_part(timestamp)
        return self.config.session_start <= current_time <= self.config.session_end

    def _time_part(self, timestamp: str) -> str:
        try:
            return datetime.fromisoformat(timestamp).strftime("%H:%M")
        except ValueError:
            return timestamp[:5]

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
