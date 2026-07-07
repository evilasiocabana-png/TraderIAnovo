"""Pipeline de autorizacao por regime de mercado para o robo demo."""

from __future__ import annotations

from dataclasses import dataclass


MARKET_UPTREND = "MARKET_UPTREND"
MARKET_DOWNTREND = "MARKET_DOWNTREND"
MARKET_RANGE = "MARKET_RANGE"
MARKET_UNDEFINED = "MARKET_UNDEFINED"


@dataclass(frozen=True)
class MarketRegimePipelineResult:
    """Resultado da avaliacao institucional de regime."""

    regime: str
    state: str
    authorized: bool
    direction: str
    block_reason: str = ""
    message: str = ""


class MarketRegimePipeline:
    """Autoriza entrada a partir de regime, zona e confirmacao de retomada."""

    def evaluate(self, signal: object) -> MarketRegimePipelineResult:
        decision = str(getattr(signal, "decision", "WAIT") or "WAIT").upper()
        regime = self._classify_regime(signal)
        if regime == MARKET_UNDEFINED:
            return MarketRegimePipelineResult(
                regime=MARKET_UNDEFINED,
                state="SEM_ESTRUTURA",
                authorized=False,
                direction="WAIT",
                block_reason="REGIME_INDEFINIDO",
                message="Regime indefinido; nao operar.",
            )
        if regime == MARKET_UPTREND:
            return self._evaluate_trend(signal, decision, expected="BUY")
        if regime == MARKET_DOWNTREND:
            return self._evaluate_trend(signal, decision, expected="SELL")
        return self._evaluate_range(signal, decision)

    def _classify_regime(self, signal: object) -> str:
        trend = str(getattr(signal, "trend", "") or "").upper()
        if "RANGE" in trend or "LATERAL" in trend:
            return MARKET_RANGE
        if "ALTA" in trend or "UP" in trend:
            return MARKET_UPTREND
        if "BAIXA" in trend or "DOWN" in trend:
            return MARKET_DOWNTREND

        short_average = self._number(getattr(signal, "short_average", None))
        long_average = self._number(getattr(signal, "long_average", None))
        if short_average is not None and long_average is not None:
            distance = abs(short_average - long_average)
            base = max(abs(long_average), 1.0)
            if distance / base <= 0.0002:
                return MARKET_RANGE
            if short_average > long_average:
                return MARKET_UPTREND
            if short_average < long_average:
                return MARKET_DOWNTREND

        support = self._number(getattr(signal, "support", None))
        resistance = self._number(getattr(signal, "resistance", None))
        if support is not None and resistance is not None and resistance > support:
            return MARKET_RANGE
        return MARKET_UNDEFINED

    def _evaluate_trend(
        self,
        signal: object,
        decision: str,
        *,
        expected: str,
    ) -> MarketRegimePipelineResult:
        if decision != expected:
            return MarketRegimePipelineResult(
                regime=MARKET_UPTREND if expected == "BUY" else MARKET_DOWNTREND,
                state="SETUP_DETECTADO",
                authorized=False,
                direction="WAIT",
                block_reason="SEM_CONFIRMACAO_DE_RETOMADA",
                message=(
                    f"Regime pede {expected}, mas a decisao atual e {decision}."
                ),
            )

        stretched = self._is_stretched(signal)
        if stretched:
            return MarketRegimePipelineResult(
                regime=MARKET_UPTREND if expected == "BUY" else MARKET_DOWNTREND,
                state="AGUARDANDO_RETRACAO",
                authorized=False,
                direction="WAIT",
                block_reason="MOVIMENTO_ESTICADO",
                message="Movimento esticado; aguardando retracao.",
            )

        if not self._in_value_zone(signal):
            return MarketRegimePipelineResult(
                regime=MARKET_UPTREND if expected == "BUY" else MARKET_DOWNTREND,
                state="AGUARDANDO_RETRACAO",
                authorized=False,
                direction="WAIT",
                block_reason="FORA_DA_ZONA_DE_VALOR",
                message="Preco fora da zona de valor do regime.",
            )

        if not self._has_resumption_confirmation(signal, expected):
            return MarketRegimePipelineResult(
                regime=MARKET_UPTREND if expected == "BUY" else MARKET_DOWNTREND,
                state="EM_ZONA_DE_VALOR",
                authorized=False,
                direction="WAIT",
                block_reason="SEM_CONFIRMACAO_DE_RETOMADA",
                message="Zona de valor sem confirmacao de retomada.",
            )

        return MarketRegimePipelineResult(
            regime=MARKET_UPTREND if expected == "BUY" else MARKET_DOWNTREND,
            state="BUY_AUTORIZADO" if expected == "BUY" else "SELL_AUTORIZADO",
            authorized=True,
            direction=expected,
            message=(
                "Regime de alta com retomada autorizada."
                if expected == "BUY"
                else "Regime de baixa com retomada autorizada."
            ),
        )

    def _evaluate_range(
        self,
        signal: object,
        decision: str,
    ) -> MarketRegimePipelineResult:
        price = self._price(signal)
        support = self._number(getattr(signal, "support", None))
        resistance = self._number(getattr(signal, "resistance", None))
        if price is None or support is None or resistance is None:
            return MarketRegimePipelineResult(
                regime=MARKET_RANGE,
                state="CONFIRMACAO_DE_REJEICAO",
                authorized=False,
                direction="WAIT",
                block_reason="RANGE_SEM_REJEICAO",
                message="Range sem suporte/resistencia suficientes.",
            )
        tolerance = self._range_tolerance(signal, price)
        near_support = abs(price - support) <= tolerance
        near_resistance = abs(price - resistance) <= tolerance
        if not near_support and not near_resistance:
            return MarketRegimePipelineResult(
                regime=MARKET_RANGE,
                state="CONFIRMACAO_DE_REJEICAO",
                authorized=False,
                direction="WAIT",
                block_reason="MEIO_DO_RANGE",
                message="Preco no meio do range; nao operar.",
            )
        if near_support and decision == "BUY" and self._range_rejection(signal, "BUY"):
            return MarketRegimePipelineResult(
                regime=MARKET_RANGE,
                state="BUY_NO_SUPORTE",
                authorized=True,
                direction="BUY",
                message="Rejeicao validada no suporte do range.",
            )
        if near_resistance and decision == "SELL" and self._range_rejection(signal, "SELL"):
            return MarketRegimePipelineResult(
                regime=MARKET_RANGE,
                state="SELL_NA_RESISTENCIA",
                authorized=True,
                direction="SELL",
                message="Rejeicao validada na resistencia do range.",
            )
        return MarketRegimePipelineResult(
            regime=MARKET_RANGE,
            state="CONFIRMACAO_DE_REJEICAO",
            authorized=False,
            direction="WAIT",
            block_reason="RANGE_SEM_REJEICAO",
            message="Range sem rejeicao compativel com a direcao.",
        )

    def _is_stretched(self, signal: object) -> bool:
        price = self._price(signal)
        anchor = self._trend_anchor(signal)
        if price is None or anchor is None:
            return False
        atr = self._number(getattr(signal, "atr", None))
        threshold = max((atr or 0.0) * 5.0, abs(price) * 0.02)
        return abs(price - anchor) > threshold

    def _in_value_zone(self, signal: object) -> bool:
        price = self._price(signal)
        anchor = self._trend_anchor(signal)
        if price is None or anchor is None:
            return True
        atr = self._number(getattr(signal, "atr", None))
        threshold = max((atr or 0.0) * 5.0, abs(price) * 0.02)
        return abs(price - anchor) <= threshold

    def _has_resumption_confirmation(self, signal: object, direction: str) -> bool:
        momentum = self._number(getattr(signal, "momentum", None))
        price = self._price(signal)
        fast = self._number(getattr(signal, "ema_fast", None))
        if fast is None:
            fast = self._number(getattr(signal, "short_average", None))
        if direction == "BUY":
            return (momentum is None or momentum >= 0.0) and (
                price is None or fast is None or price >= fast * 0.998
            )
        return (momentum is None or momentum <= 0.0) and (
            price is None or fast is None or price <= fast * 1.002
        )

    def _range_rejection(self, signal: object, direction: str) -> bool:
        momentum = self._number(getattr(signal, "momentum", None))
        rsi = self._number(getattr(signal, "rsi", None))
        if direction == "BUY":
            return (momentum is None or momentum >= 0.0) or (
                rsi is not None and rsi <= 45.0
            )
        return (momentum is None or momentum <= 0.0) or (
            rsi is not None and rsi >= 55.0
        )

    def _trend_anchor(self, signal: object) -> float | None:
        for name in ("ema_mid", "mid_average", "ema_fast", "short_average", "long_average"):
            value = self._number(getattr(signal, name, None))
            if value is not None:
                return value
        return None

    def _range_tolerance(self, signal: object, price: float) -> float:
        atr = self._number(getattr(signal, "atr", None))
        return max((atr or 0.0) * 1.5, abs(price) * 0.003)

    def _price(self, signal: object) -> float | None:
        for name in ("last_price", "entry_price", "price"):
            value = self._number(getattr(signal, name, None))
            if value is not None and value > 0:
                return value
        return None

    def _number(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if not math_is_finite(parsed):
            return None
        return parsed


def math_is_finite(value: float) -> bool:
    return value == value and value not in (float("inf"), float("-inf"))
