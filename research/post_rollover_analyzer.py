from __future__ import annotations

from dataclasses import dataclass, field

from research.forex_time_layer import ForexTimeContext


POST_ROLLOVER_EVENT = "POST_ROLLOVER_DAILY_OPEN"
POST_ROLLOVER_ALPHA_ID = "EVENT_POST_ROLLOVER_DAILY_OPEN"


@dataclass(frozen=True)
class PostRolloverDecision:
    """Decisao read-only do Lab para a primeira oportunidade pos-rollover."""

    event_type: str = POST_ROLLOVER_EVENT
    alpha_id: str = POST_ROLLOVER_ALPHA_ID
    pair: str = "N/D"
    timeframe: str = "M1"
    mode: str = "NORMAL_LAB_FLOW"
    context: str = "NO_TRADE"
    status: str = "POST_ROLLOVER_SKIPPED"
    decision: str = "WAIT"
    score: float = 0.0
    confidence: float = 0.0
    entry_price: float | None = None
    stop: float | None = None
    target: float | None = None
    risk_reward: float = 0.0
    reason: str = "Fora da janela pos-rollover."
    skip_reason: str = "NORMAL_LAB_FLOW"
    spread: float | None = None
    spread_average: float | None = None
    spread_ratio: float | None = None
    atr: float | None = None
    volatility: float | None = None
    momentum: float | None = None
    tick_volume: float | None = None
    minutes_after_rollover: float | None = None
    gap_estimate: float | None = None
    metrics: dict[str, str] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()


class PostRolloverAnalyzer:
    """Avalia se o pos-rollover merece prioridade antes das Alphas normais."""

    def __init__(
        self,
        *,
        guard_minutes: int = 5,
        opportunity_window_minutes: int = 90,
        max_spread_ratio: float = 1.5,
        min_volume: float = 1.0,
        min_momentum: float = 0.00005,
    ) -> None:
        self.guard_minutes = guard_minutes
        self.opportunity_window_minutes = opportunity_window_minutes
        self.max_spread_ratio = max_spread_ratio
        self.min_volume = min_volume
        self.min_momentum = min_momentum

    def analyze(
        self,
        row: object,
        time_context: ForexTimeContext,
    ) -> PostRolloverDecision:
        pair = str(getattr(row, "pair", "N/D") or "N/D").upper()
        timeframe = str(getattr(row, "timeframe", "M1") or "M1")
        minutes_after = time_context.minutes_from_server_rollover
        spread = self._optional_float(getattr(row, "spread", None))
        spread_average = self._optional_float(getattr(row, "spread_average", None))
        atr = self._optional_float(getattr(row, "atr", None))
        volatility = self._optional_float(getattr(row, "volatility", None))
        momentum = self._optional_float(getattr(row, "momentum", None))
        tick_volume = self._tick_volume(row)
        entry_price = self._optional_float(
            getattr(row, "theoretical_entry_price", None)
        ) or self._optional_float(getattr(row, "last_price", None))
        spread_ratio = self._spread_ratio(spread, spread_average)
        base = {
            "pair": pair,
            "timeframe": timeframe,
            "spread": spread,
            "spread_average": spread_average,
            "spread_ratio": spread_ratio,
            "atr": atr,
            "volatility": volatility,
            "momentum": momentum,
            "tick_volume": tick_volume,
            "minutes_after_rollover": minutes_after,
            "entry_price": entry_price,
        }
        if time_context.is_rollover_window or time_context.temporal_blocked:
            return self._skip(
                **base,
                mode="POST_ROLLOVER_SKIPPED",
                context="NO_TRADE",
                skip_reason="ROLLOVER_GUARD_ACTIVE",
                reason="Janela de protecao do rollover ainda ativa.",
            )
        if minutes_after is None or minutes_after > self.opportunity_window_minutes:
            return self._skip(
                **base,
                mode="NORMAL_LAB_FLOW",
                context="NO_TRADE",
                skip_reason="OUTSIDE_POST_ROLLOVER_WINDOW",
                reason="Fora da janela prioritaria pos-rollover; seguir fluxo normal.",
            )
        if minutes_after <= self.guard_minutes:
            return self._skip(
                **base,
                mode="POST_ROLLOVER_SKIPPED",
                context="LOW_LIQUIDITY_SKIP",
                skip_reason="PROTECTION_WINDOW_NOT_FINISHED",
                reason="Fim da janela de protecao ainda nao confirmado.",
            )
        if spread_ratio is not None and spread_ratio > self.max_spread_ratio:
            return self._skip(
                **base,
                mode="POST_ROLLOVER_SKIPPED",
                context="SPREAD_TOO_HIGH_SKIP",
                skip_reason="SPREAD_TOO_HIGH",
                reason="Spread pos-rollover acima do normal recente.",
            )
        if tick_volume is not None and tick_volume < self.min_volume:
            return self._skip(
                **base,
                mode="POST_ROLLOVER_SKIPPED",
                context="LOW_LIQUIDITY_SKIP",
                skip_reason="LOW_TICK_VOLUME",
                reason="Liquidez ainda nao retornou apos rollover.",
            )
        if entry_price is None or atr is None or atr <= 0.0:
            return self._skip(
                **base,
                mode="POST_ROLLOVER_SKIPPED",
                context="NO_EDGE_SKIP",
                skip_reason="INSUFFICIENT_PRICE_OR_ATR",
                reason="Preco ou ATR indisponivel para plano completo.",
            )
        if momentum is None or abs(momentum) < self.min_momentum:
            return self._skip(
                **base,
                mode="POST_ROLLOVER_SKIPPED",
                context="NO_EDGE_SKIP",
                skip_reason="NO_POST_ROLLOVER_MOMENTUM",
                reason="Primeiros candles pos-rollover sem momentum suficiente.",
            )

        direction = self._direction(row, momentum)
        context = "CONTINUATION_CANDIDATE"
        z_score = abs(self._optional_float(getattr(row, "z_score", None)) or 0.0)
        gap_estimate = abs(momentum)
        if z_score >= 1.0 and self._trend(row) in {"ALTA", "BAIXA"}:
            context = "GAP_FILL_CANDIDATE"
        rr = 3.0
        stop_distance = max(float(atr) * 1.5, entry_price * 0.001)
        if direction == "SELL":
            stop = entry_price + stop_distance
            target = entry_price - (stop_distance * rr)
        else:
            stop = entry_price - stop_distance
            target = entry_price + (stop_distance * rr)
        confidence = min(0.95, 0.55 + min(abs(momentum) * 100.0, 0.20))
        score = min(1.0, confidence + (0.05 if spread_ratio is None or spread_ratio <= 1.0 else 0.0))
        return PostRolloverDecision(
            pair=pair,
            timeframe=timeframe,
            mode="POST_ROLLOVER_TRADE_READY",
            context=context,
            status="POST_ROLLOVER_TRADE_READY",
            decision=direction,
            score=score,
            confidence=confidence,
            entry_price=entry_price,
            stop=stop,
            target=target,
            risk_reward=rr,
            reason=(
                "Lab detectou oportunidade pos-rollover com liquidez normalizada, "
                "ATR valido e momentum dos primeiros candles."
            ),
            skip_reason="",
            spread=spread,
            spread_average=spread_average,
            spread_ratio=spread_ratio,
            atr=atr,
            volatility=volatility,
            momentum=momentum,
            tick_volume=tick_volume,
            minutes_after_rollover=minutes_after,
            gap_estimate=gap_estimate,
            metrics=self._metrics(base, context=context, decision=direction),
            diagnostics=("POST_ROLLOVER_PRIORITY_EVENT", "LAB_DECISION_REQUIRED"),
        )

    def _skip(self, **kwargs: object) -> PostRolloverDecision:
        metrics = self._metrics(kwargs, context=str(kwargs.get("context")), decision="WAIT")
        return PostRolloverDecision(
            pair=str(kwargs.get("pair") or "N/D"),
            timeframe=str(kwargs.get("timeframe") or "M1"),
            mode=str(kwargs.get("mode") or "POST_ROLLOVER_SKIPPED"),
            context=str(kwargs.get("context") or "NO_TRADE"),
            status=str(kwargs.get("mode") or "POST_ROLLOVER_SKIPPED"),
            decision="WAIT",
            reason=str(kwargs.get("reason") or "Sem edge pos-rollover."),
            skip_reason=str(kwargs.get("skip_reason") or "NO_EDGE_SKIP"),
            spread=kwargs.get("spread"),  # type: ignore[arg-type]
            spread_average=kwargs.get("spread_average"),  # type: ignore[arg-type]
            spread_ratio=kwargs.get("spread_ratio"),  # type: ignore[arg-type]
            atr=kwargs.get("atr"),  # type: ignore[arg-type]
            volatility=kwargs.get("volatility"),  # type: ignore[arg-type]
            momentum=kwargs.get("momentum"),  # type: ignore[arg-type]
            tick_volume=kwargs.get("tick_volume"),  # type: ignore[arg-type]
            minutes_after_rollover=kwargs.get("minutes_after_rollover"),  # type: ignore[arg-type]
            entry_price=kwargs.get("entry_price"),  # type: ignore[arg-type]
            metrics=metrics,
            diagnostics=("POST_ROLLOVER_PRIORITY_EVENT", str(kwargs.get("skip_reason") or "SKIP")),
        )

    def _metrics(self, values: dict[str, object], *, context: str, decision: str) -> dict[str, str]:
        return {
            "event_type": POST_ROLLOVER_EVENT,
            "context": context,
            "decision": decision,
            "minutes_after_rollover": self._label(values.get("minutes_after_rollover")),
            "spread": self._label(values.get("spread")),
            "spread_average": self._label(values.get("spread_average")),
            "spread_ratio": self._label(values.get("spread_ratio")),
            "atr": self._label(values.get("atr")),
            "volatility": self._label(values.get("volatility")),
            "momentum": self._label(values.get("momentum")),
            "tick_volume": self._label(values.get("tick_volume")),
        }

    def _direction(self, row: object, momentum: float) -> str:
        trend = self._trend(row)
        if trend == "BAIXA":
            return "SELL"
        if trend == "ALTA":
            return "BUY"
        return "BUY" if momentum > 0.0 else "SELL"

    def _trend(self, row: object) -> str:
        return str(getattr(row, "trend", "INDEFINIDA") or "INDEFINIDA").upper()

    def _tick_volume(self, row: object) -> float | None:
        for name in ("tick_volume", "volume", "last_tick_volume"):
            value = self._optional_float(getattr(row, name, None))
            if value is not None:
                return value
        return None

    def _spread_ratio(
        self,
        spread: float | None,
        spread_average: float | None,
    ) -> float | None:
        if spread is None or spread_average is None or spread_average <= 0.0:
            return None
        return spread / spread_average

    def _optional_float(self, value: object) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _label(self, value: object) -> str:
        if value is None:
            return "N/D"
        if isinstance(value, float):
            return f"{value:.6f}"
        return str(value)
