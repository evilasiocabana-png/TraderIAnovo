"""Estrategias Beta operacionais do Position Manager."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from domain.contracts.beta_strategy import BetaDecision, BetaStrategyContext

BETA002_ID = "BETA002"
BETA002_VERSION = "M1_EMA14_MOMENTUM_VOLATILITY"


@dataclass(frozen=True)
class Beta002Config:
    """Configuracao centralizada da BETA002."""

    timeframe: str = "M1"
    ema_period: int = 14
    momentum_period: int = 14
    atr_period: int = 14
    slope_lookback: int = 3
    recent_structure_period: int = 8
    attention_confirmations: int = 2
    weakening_confirmations: int = 3
    defensive_confirmations: int = 3
    exit_confirmations: int = 6
    minimum_exit_evidence_groups: int = 4
    allow_stop_protection: bool = True
    allow_full_exit: bool = False
    modify_target: bool = False
    use_closed_candle_for_execution: bool = True
    healthy_min_score: float = 0.50
    attention_min_score: float = 0.15
    weakening_min_score: float = -0.15
    defensive_min_score: float = -0.49
    exit_candidate_max_score: float = -0.65
    minimum_candles: int = 20
    atr_protection_factor: float = 1.5
    ema_protection_atr_buffer: float = 0.5
    structure_buffer_pips: float = 2.0
    protection_activation_r: float = 1.0

    @classmethod
    def load(cls, path: Path | None = None) -> "Beta002Config":
        """Carrega config ajustavel sem exigir mudanca de codigo."""
        config_path = path or Path("config") / "beta_strategies.json"
        if not config_path.exists():
            return cls()
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return cls()
        raw = payload.get("beta002", {}) if isinstance(payload, dict) else {}
        if not isinstance(raw, dict):
            return cls()
        allowed = {name for name in cls.__dataclass_fields__}
        values = {key: value for key, value in raw.items() if key in allowed}
        return cls(**values)


@dataclass
class Beta002Strategy:
    """Gestao pos-entrada M1 por EMA14, momentum e volatilidade."""

    config: Beta002Config = field(default_factory=Beta002Config.load)
    beta_id: str = BETA002_ID
    beta_version: str = BETA002_VERSION

    def evaluate(self, context: BetaStrategyContext) -> BetaDecision:
        """Retorna HOLD, PROTECT ou FULL_EXIT sem decidir entrada."""
        evaluated_at = context.evaluated_at or datetime.now().astimezone().isoformat()
        if not context.position_open:
            return self._hold(
                context,
                state="HEALTHY",
                reason="Sem posicao aberta confirmada; BETA002 preserva.",
                evaluated_at=evaluated_at,
                missing=("position",),
            )
        candles = self._closed_candles(context.candles)
        closed_candle_time = self._closed_candle_time(candles)
        if len(candles) < self.config.minimum_candles:
            return self._hold(
                context,
                state="HEALTHY",
                reason="Candles M1 insuficientes; decisao obrigatoria HOLD_POSITION.",
                evaluated_at=evaluated_at,
                closed_candle_time=closed_candle_time,
                missing=("m1_candles",),
            )
        metrics = self._metrics(candles, context.side, context.symbol)
        missing = tuple(
            name for name in ("ema14_value", "ema14_slope", "momentum_14", "atr_14")
            if metrics.get(name) is None
        )
        if missing or (
            self.config.use_closed_candle_for_execution and not context.candle_closed
        ):
            extra = missing or ("closed_m1_candle",)
            return self._hold(
                context,
                state="HEALTHY",
                reason="Dados M1 incompletos; BETA002 preserva posicao.",
                evaluated_at=evaluated_at,
                closed_candle_time=closed_candle_time,
                missing=extra,
                metrics=metrics,
            )

        evidence = self._evidence(context, metrics)
        score = self._strength_score(context, metrics, evidence)
        raw_state = self._state_from_score(score)
        confirmation, duration = self._persistence(context, raw_state)
        state = self._confirmed_state(raw_state, confirmation)
        action = "HOLD_POSITION"
        candidate_stop: float | None = None
        final_exit_reason = "N/D"

        if state in {"WEAKENING", "DEFENSIVE", "EXIT_CANDIDATE"} and self.config.allow_stop_protection:
            if self._can_protect(context, state):
                candidate_stop = self._candidate_stop(context, candles, metrics)
                if candidate_stop is not None:
                    action = "PROTECT_POSITION"
        if (
            raw_state == "EXIT_CANDIDATE"
            and state == "EXIT_CANDIDATE"
            and self.config.allow_full_exit
            and len(evidence) >= self.config.minimum_exit_evidence_groups
            and action != "PROTECT_POSITION"
        ):
            action = "FULL_EXIT"
            final_exit_reason = "BETA002_EXIT_CANDIDATE"
            candidate_stop = None

        reason = self._reason(state, action, evidence, confirmation)
        return BetaDecision(
            beta_id=self.beta_id,
            beta_version=self.beta_version,
            state=state,
            raw_state=raw_state,
            action=action,
            reason=reason,
            strength_score=round(score, 6),
            confirmation_count=confirmation,
            state_duration=duration,
            candidate_stop=candidate_stop,
            current_r=context.current_r,
            ema14_value=metrics.get("ema14_value"),
            ema14_slope=metrics.get("ema14_slope"),
            momentum_14=metrics.get("momentum_14"),
            atr_14=metrics.get("atr_14"),
            atr_relative_change=metrics.get("atr_relative_change"),
            structure_signal=str(metrics.get("structure_signal") or "NEUTRAL"),
            evaluated_at=evaluated_at,
            closed_candle_time=closed_candle_time,
            evidence=evidence,
            confidence=min(0.95, max(0.10, abs(score) + confirmation * 0.05)),
            final_exit_reason=final_exit_reason,
        )

    def _closed_candles(self, candles: tuple[object, ...]) -> list[object]:
        ordered = sorted(list(candles), key=lambda item: self._value(item, "time") or 0)
        if self.config.use_closed_candle_for_execution and len(ordered) > 1:
            return ordered[:-1]
        return ordered

    def _closed_candle_time(self, candles: list[object]) -> str:
        if not candles:
            return "N/D"
        value = self._value(candles[-1], "time")
        if value is None:
            return "N/D"
        try:
            return datetime.fromtimestamp(float(value)).astimezone().isoformat()
        except (OSError, OverflowError, ValueError):
            return str(value)

    def _metrics(self, candles: list[object], side: str, symbol: str) -> dict[str, Any]:
        closes = [self._value(candle, "close") for candle in candles]
        highs = [self._value(candle, "high") for candle in candles]
        lows = [self._value(candle, "low") for candle in candles]
        if any(value is None for value in closes + highs + lows):
            return {}
        close_values = [float(value) for value in closes if value is not None]
        high_values = [float(value) for value in highs if value is not None]
        low_values = [float(value) for value in lows if value is not None]
        ema_values = self._ema(close_values, int(self.config.ema_period))
        atr_values = self._atr(high_values, low_values, close_values, int(self.config.atr_period))
        if not ema_values or not atr_values:
            return {}
        atr = atr_values[-1]
        lookback = max(int(self.config.slope_lookback), 1)
        if len(ema_values) <= lookback:
            return {}
        direction = 1.0 if str(side).upper() == "BUY" else -1.0
        slope = ((ema_values[-1] - ema_values[-1 - lookback]) / max(atr, 1e-12)) * direction
        momentum = (
            (close_values[-1] - close_values[-1 - int(self.config.momentum_period)])
            / max(atr, 1e-12)
        ) * direction
        previous_atr = atr_values[-2] if len(atr_values) >= 2 else atr
        atr_relative = (atr - previous_atr) / max(previous_atr, 1e-12)
        recent = max(int(self.config.recent_structure_period), 2)
        structure_signal = self._structure_signal(
            side=str(side).upper(),
            symbol=str(symbol).upper(),
            closes=close_values,
            highs=high_values,
            lows=low_values,
            recent=recent,
        )
        advance = ((close_values[-1] - close_values[-2]) / max(atr, 1e-12)) * direction
        candle_range = sum(h - l for h, l in zip(high_values[-recent:], low_values[-recent:])) / recent
        return {
            "ema14_value": ema_values[-1],
            "ema14_slope": slope,
            "momentum_14": momentum,
            "atr_14": atr,
            "atr_relative_change": atr_relative,
            "structure_signal": structure_signal,
            "advance": advance,
            "range_ratio": candle_range / max(atr, 1e-12),
            "last_close": close_values[-1],
            "recent_low": min(low_values[-recent:]),
            "recent_high": max(high_values[-recent:]),
        }

    def _strength_score(
        self,
        context: BetaStrategyContext,
        metrics: dict[str, Any],
        evidence: tuple[str, ...],
    ) -> float:
        ema_component = self._clamp(float(metrics.get("ema14_slope") or 0.0), -1.0, 1.0)
        momentum_component = self._clamp(float(metrics.get("momentum_14") or 0.0), -1.0, 1.0)
        volatility_component = self._clamp(float(metrics.get("atr_relative_change") or 0.0) * 5.0, -1.0, 1.0)
        advance_component = self._clamp(float(metrics.get("advance") or 0.0), -1.0, 1.0)
        structure_component = {
            "FAVORABLE": 0.60,
            "NEUTRAL": 0.0,
            "AGAINST": -0.80,
        }.get(str(metrics.get("structure_signal")), 0.0)
        r_component = self._clamp(float(context.current_r) / 2.0, -1.0, 1.0)
        penalty = min(len(evidence) * 0.08, 0.32)
        score = (
            ema_component * 0.25
            + momentum_component * 0.25
            + volatility_component * 0.15
            + advance_component * 0.15
            + structure_component * 0.15
            + r_component * 0.05
            - penalty
        )
        return self._clamp(score, -1.0, 1.0)

    def _evidence(
        self,
        context: BetaStrategyContext,
        metrics: dict[str, Any],
    ) -> tuple[str, ...]:
        evidence: list[str] = []
        if float(metrics.get("ema14_slope") or 0.0) < -0.10:
            evidence.append("EMA14_SLOPE_AGAINST")
        elif float(metrics.get("ema14_slope") or 0.0) < 0.05:
            evidence.append("EMA14_SLOPE_WEAK")
        if float(metrics.get("momentum_14") or 0.0) < -0.10:
            evidence.append("MOMENTUM14_AGAINST")
        elif float(metrics.get("momentum_14") or 0.0) < 0.05:
            evidence.append("MOMENTUM14_WEAK")
        if float(metrics.get("atr_relative_change") or 0.0) < -0.10:
            evidence.append("ATR14_CONTRACTION")
        if str(metrics.get("structure_signal")) == "AGAINST":
            evidence.append("STRUCTURE_AGAINST")
        if float(metrics.get("advance") or 0.0) <= 0.0:
            evidence.append("NO_FAVORABLE_ADVANCE")
        if float(context.current_r) < 0.0:
            evidence.append("NEGATIVE_R")
        return tuple(evidence)

    def _state_from_score(self, score: float) -> str:
        if score <= self.config.exit_candidate_max_score:
            return "EXIT_CANDIDATE"
        if score >= self.config.healthy_min_score:
            return "HEALTHY"
        if score >= self.config.attention_min_score:
            return "ATTENTION"
        if score >= self.config.weakening_min_score:
            return "WEAKENING"
        return "DEFENSIVE"

    def _persistence(self, context: BetaStrategyContext, state: str) -> tuple[int, int]:
        if state == context.previous_state:
            return context.previous_confirmation_count + 1, context.previous_state_duration + 1
        return 1, 1

    def _confirmed_state(self, raw_state: str, confirmations: int) -> str:
        required = {
            "ATTENTION": self.config.attention_confirmations,
            "WEAKENING": self.config.weakening_confirmations,
            "DEFENSIVE": self.config.defensive_confirmations,
            "EXIT_CANDIDATE": self.config.exit_confirmations,
        }.get(raw_state, 1)
        if confirmations >= required:
            return raw_state
        if raw_state == "EXIT_CANDIDATE" and confirmations >= self.config.defensive_confirmations:
            return "DEFENSIVE"
        if raw_state in {"DEFENSIVE", "EXIT_CANDIDATE"} and confirmations >= self.config.weakening_confirmations:
            return "WEAKENING"
        if raw_state in {"WEAKENING", "DEFENSIVE", "EXIT_CANDIDATE"} and confirmations >= self.config.attention_confirmations:
            return "ATTENTION"
        return "HEALTHY"

    def _can_protect(self, context: BetaStrategyContext, state: str) -> bool:
        return (
            context.current_r >= float(self.config.protection_activation_r)
            and state in {"WEAKENING", "DEFENSIVE", "EXIT_CANDIDATE"}
        )

    def _candidate_stop(
        self,
        context: BetaStrategyContext,
        candles: list[object],
        metrics: dict[str, Any],
    ) -> float | None:
        atr = float(metrics.get("atr_14") or 0.0)
        if atr <= 0.0:
            return None
        pip = 0.01 if context.symbol.upper().endswith("JPY") else 0.0001
        buffer = pip * float(self.config.structure_buffer_pips)
        candidates: list[float] = []
        if context.current_r >= 1.0:
            candidates.append(context.entry_price)
        if context.side == "BUY":
            candidates.extend(
                [
                    float(metrics.get("recent_low") or 0.0) - buffer,
                    float(metrics.get("ema14_value") or 0.0) - atr * self.config.ema_protection_atr_buffer,
                    context.current_price - atr * self.config.atr_protection_factor,
                ]
            )
            valid = [
                item
                for item in candidates
                if item > context.current_stop and item < context.current_price
            ]
            return max(valid) if valid else None
        candidates.extend(
            [
                float(metrics.get("recent_high") or 0.0) + buffer,
                float(metrics.get("ema14_value") or 0.0) + atr * self.config.ema_protection_atr_buffer,
                context.current_price + atr * self.config.atr_protection_factor,
            ]
        )
        valid = [
            item
            for item in candidates
            if item < context.current_stop and item > context.current_price
        ]
        return min(valid) if valid else None

    def _structure_signal(
        self,
        *,
        side: str,
        symbol: str,
        closes: list[float],
        highs: list[float],
        lows: list[float],
        recent: int,
    ) -> str:
        previous_high = max(highs[-recent - 1 : -1])
        previous_low = min(lows[-recent - 1 : -1])
        last_close = closes[-1]
        pip = 0.01 if symbol.endswith("JPY") else 0.0001
        buffer = pip * float(self.config.structure_buffer_pips)
        if side == "BUY":
            if last_close < previous_low - buffer:
                return "AGAINST"
            if last_close > previous_high + buffer:
                return "FAVORABLE"
            return "NEUTRAL"
        if last_close > previous_high + buffer:
            return "AGAINST"
        if last_close < previous_low - buffer:
            return "FAVORABLE"
        return "NEUTRAL"

    def _reason(
        self,
        state: str,
        action: str,
        evidence: tuple[str, ...],
        confirmations: int,
    ) -> str:
        evidence_text = ", ".join(evidence) if evidence else "sem enfraquecimento relevante"
        return (
            f"BETA002 {state}: acao {action}; confirmacoes={confirmations}; "
            f"evidencias={evidence_text}."
        )

    def _hold(
        self,
        context: BetaStrategyContext,
        *,
        state: str,
        reason: str,
        evaluated_at: str,
        closed_candle_time: str = "N/D",
        missing: tuple[str, ...] = (),
        metrics: dict[str, Any] | None = None,
    ) -> BetaDecision:
        metrics = metrics or {}
        return BetaDecision(
            beta_id=self.beta_id,
            beta_version=self.beta_version,
            state=state,
            raw_state=state,
            action="HOLD_POSITION",
            reason=reason,
            strength_score=0.0,
            confirmation_count=0,
            state_duration=0,
            candidate_stop=None,
            current_r=context.current_r,
            ema14_value=metrics.get("ema14_value"),
            ema14_slope=metrics.get("ema14_slope"),
            momentum_14=metrics.get("momentum_14"),
            atr_14=metrics.get("atr_14"),
            atr_relative_change=metrics.get("atr_relative_change"),
            structure_signal=str(metrics.get("structure_signal") or "N/D"),
            evaluated_at=evaluated_at,
            closed_candle_time=closed_candle_time,
            missing_data=missing,
            confidence=0.0,
        )

    def _ema(self, values: list[float], period: int) -> list[float]:
        if len(values) < period:
            return []
        alpha = 2.0 / (period + 1.0)
        ema = sum(values[:period]) / period
        result = [ema]
        for value in values[period:]:
            ema = value * alpha + ema * (1.0 - alpha)
            result.append(ema)
        return result

    def _atr(
        self,
        highs: list[float],
        lows: list[float],
        closes: list[float],
        period: int,
    ) -> list[float]:
        if len(closes) < period + 1:
            return []
        true_ranges = []
        for index in range(1, len(closes)):
            true_ranges.append(
                max(
                    highs[index] - lows[index],
                    abs(highs[index] - closes[index - 1]),
                    abs(lows[index] - closes[index - 1]),
                )
            )
        if len(true_ranges) < period:
            return []
        return [
            sum(true_ranges[index - period : index]) / period
            for index in range(period, len(true_ranges) + 1)
        ]

    def _value(self, candle: object, name: str) -> float | None:
        if isinstance(candle, dict):
            value = candle.get(name)
        else:
            try:
                value = candle[name]  # type: ignore[index]
            except (TypeError, KeyError, IndexError, ValueError):
                value = getattr(candle, name, None)
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _clamp(self, value: float, minimum: float, maximum: float) -> float:
        return max(minimum, min(maximum, value))
