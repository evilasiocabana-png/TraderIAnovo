"""Strategy oficial da Alpha002."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from domain.contracts.strategy_signal import StrategySignal
from market.context.market_context import MarketContext
from market.features.feature_report import FeatureReport
from strategies.alpha002.alpha002_config import Alpha002Config


SCORE_MULTIPLIER = 100
FORBIDDEN_REGIMES = {
    "STRONG_TREND",
    "TREND_STRONG",
    "HIGH_TREND",
    "LOW_LIQUIDITY",
}


@dataclass(frozen=True)
class Alpha002Strategy:
    """Aplica as regras de reversao contextual para VWAP."""

    config: Alpha002Config
    nome: str = "alpha002_vwap_mean_reversion"

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
        vwap = self._feature_float(feature_report, "vwap")
        vwap_distance = self._feature_float(
            feature_report,
            "vwap_distance_percent",
        )
        momentum = self._feature_float(feature_report, "momentum")

        if price < vwap and vwap_distance < 0 and momentum >= 0:
            return self._signal(
                decision="BUY",
                confidence=market_context.confidence,
                reasons=[
                    "preco abaixo da VWAP",
                    "perda de momentum vendedor",
                    "contexto aprovado para reversao",
                ],
            )

        if price > vwap and vwap_distance > 0 and momentum <= 0:
            return self._signal(
                decision="SELL",
                confidence=market_context.confidence,
                reasons=[
                    "preco acima da VWAP",
                    "perda de momentum comprador",
                    "contexto aprovado para reversao",
                ],
            )

        return self._wait(["gatilho de reversao VWAP nao confirmado"])

    def _rejection_reasons(
        self,
        market_context: MarketContext,
        feature_report: FeatureReport,
    ) -> list[str]:
        reasons: list[str] = []
        required_features = (
            "price",
            "vwap",
            "vwap_distance_percent",
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
            reasons.append("regime proibido para reversao VWAP")
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
