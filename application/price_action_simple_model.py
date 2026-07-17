"""Modelo operacional simples de Price Action para o TraderIA Novo."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PriceActionInput:
    """Leitura leve do mercado usada pelo M5."""

    symbol: str
    timeframe: str
    last_price: float | None
    pivot: float | None
    support: float | None
    resistance: float | None
    swing_high: float | None = None
    swing_low: float | None = None
    short_average: float | None = None
    long_average: float | None = None
    atr: float | None = None
    spread: float | None = None
    confirmation_status: str = "SEM_GATILHO"
    confirmation_direction: str = "WAIT"


@dataclass(frozen=True)
class PriceActionDecision:
    """Resultado auditavel do modelo M5."""

    status: str
    direction: str = "WAIT"
    entry_price: float | None = None
    stop: float | None = None
    target: float | None = None
    risk_reward: float = 0.0
    market_structure: str = "NO_STRUCTURE"
    interest_zone: str = "N/D"
    confirmation_type: str = "N/D"
    stop_reason: str = ""
    target_reason: str = ""
    reason: str = ""
    blocking_reasons: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ready(self) -> bool:
        return self.status == "ENTRY_READY" and self.direction in {"BUY", "SELL"}


class PriceActionSimpleModel:
    """Primeira versao operacional: estrutura, zona, confirmacao e risco."""

    minimum_risk_reward = 1.5
    default_buffer_factor = 0.20

    def evaluate(self, payload: PriceActionInput) -> PriceActionDecision:
        price = self._positive(payload.last_price)
        pivot = self._positive(payload.pivot)
        support = self._positive(payload.support)
        resistance = self._positive(payload.resistance)
        atr = self._positive(payload.atr) or self._fallback_atr(price, support, resistance)
        if price is None or pivot is None or support is None or resistance is None:
            return PriceActionDecision(
                status="NO_STRUCTURE",
                reason="M5 aguardando preco, pivot, suporte e resistencia.",
                blocking_reasons=("DADOS_ESTRUTURAIS_AUSENTES",),
            )
        if not (support < pivot < resistance):
            return PriceActionDecision(
                status="RANGE_STRUCTURE",
                market_structure="RANGE_STRUCTURE",
                reason="M5 bloqueado: suporte, pivot e resistencia sem ordem estrutural.",
                blocking_reasons=("ESTRUTURA_SEM_ORDEM",),
            )

        direction, structure = self._structure(payload, price, pivot)
        if direction == "WAIT":
            return PriceActionDecision(
                status="RANGE_STRUCTURE",
                market_structure=structure,
                reason="M5 aguardando estrutura direcional clara.",
                blocking_reasons=("ESTRUTURA_LATERAL",),
                diagnostics=(self._ma_diagnostic(payload),),
            )

        zone_ok, zone_label = self._interest_zone(direction, price, pivot, support, resistance, atr)
        if not zone_ok:
            return PriceActionDecision(
                status="WAITING_ZONE",
                direction=direction,
                market_structure=structure,
                interest_zone=zone_label,
                reason=f"M5 aguardando preco voltar para zona de interesse {zone_label}.",
                blocking_reasons=("FORA_DA_ZONA_PRICE_ACTION",),
                diagnostics=(self._ma_diagnostic(payload),),
            )

        confirmed, confirmation = self._confirmation(payload, direction)
        if not confirmed:
            return PriceActionDecision(
                status="WAITING_CONFIRMATION",
                direction=direction,
                market_structure=structure,
                interest_zone=zone_label,
                confirmation_type=confirmation,
                reason="M5 aguardando confirmacao viva do candle na direcao da estrutura.",
                blocking_reasons=("SEM_CONFIRMACAO_PRICE_ACTION",),
                diagnostics=(self._ma_diagnostic(payload),),
            )

        stop, stop_reason = self._stop(direction, price, payload, support, resistance, atr)
        target, target_reason = self._target(direction, price, stop, support, resistance)
        if stop is None or target is None:
            return PriceActionDecision(
                status="ENTRY_BLOCKED",
                direction=direction,
                market_structure=structure,
                interest_zone=zone_label,
                confirmation_type=confirmation,
                reason="M5 bloqueado: nao foi possivel calcular stop/alvo estrutural.",
                blocking_reasons=("STOP_ALVO_INVALIDOS",),
            )

        risk = abs(price - stop)
        reward = abs(target - price)
        rr = reward / risk if risk > 0 else 0.0
        if rr < self.minimum_risk_reward:
            return PriceActionDecision(
                status="ENTRY_BLOCKED",
                direction=direction,
                entry_price=price,
                stop=stop,
                target=target,
                risk_reward=rr,
                market_structure=structure,
                interest_zone=zone_label,
                confirmation_type=confirmation,
                stop_reason=stop_reason,
                target_reason=target_reason,
                reason=f"M5 bloqueado: RR {rr:.2f} menor que {self.minimum_risk_reward:.2f}.",
                blocking_reasons=("RR_PRICE_ACTION_INSUFICIENTE",),
            )

        return PriceActionDecision(
            status="ENTRY_READY",
            direction=direction,
            entry_price=price,
            stop=stop,
            target=target,
            risk_reward=rr,
            market_structure=structure,
            interest_zone=zone_label,
            confirmation_type=confirmation,
            stop_reason=stop_reason,
            target_reason=target_reason,
            reason=(
                f"M5 Price Action pronto: {structure}, zona {zone_label}, "
                f"confirmacao {confirmation}, RR {rr:.2f}."
            ),
            diagnostics=(
                self._ma_diagnostic(payload),
                f"ATR usado={atr:.6f}",
                f"Suporte={support:.6f}",
                f"Pivot={pivot:.6f}",
                f"Resistencia={resistance:.6f}",
            ),
        )

    def _structure(
        self,
        payload: PriceActionInput,
        price: float,
        pivot: float,
    ) -> tuple[str, str]:
        short = self._positive(payload.short_average)
        long = self._positive(payload.long_average)
        if short is not None and long is not None:
            if short > long:
                return "BUY", "BULLISH_STRUCTURE"
            if short < long:
                return "SELL", "BEARISH_STRUCTURE"
        if price >= pivot:
            return "BUY", "BULLISH_STRUCTURE"
        if price <= pivot:
            return "SELL", "BEARISH_STRUCTURE"
        return "WAIT", "RANGE_STRUCTURE"

    def _interest_zone(
        self,
        direction: str,
        price: float,
        pivot: float,
        support: float,
        resistance: float,
        atr: float,
    ) -> tuple[bool, str]:
        tolerance = max(atr * 0.50, abs(resistance - support) * 0.05)
        if direction == "BUY":
            in_zone = support <= price <= pivot or abs(price - support) <= tolerance
            return in_zone, "BUY_INTEREST_ZONE"
        in_zone = pivot <= price <= resistance or abs(price - resistance) <= tolerance
        return in_zone, "SELL_INTEREST_ZONE"

    def _confirmation(
        self,
        payload: PriceActionInput,
        direction: str,
    ) -> tuple[bool, str]:
        status = str(payload.confirmation_status or "").upper()
        confirmed_direction = str(payload.confirmation_direction or "").upper()
        if status == "SINAL_TEORICO" and confirmed_direction == direction:
            return True, "MICRO_STRUCTURE_BREAK"
        return False, "WAITING_CONFIRMATION"

    def _stop(
        self,
        direction: str,
        price: float,
        payload: PriceActionInput,
        support: float,
        resistance: float,
        atr: float,
    ) -> tuple[float | None, str]:
        buffer = max(atr * self.default_buffer_factor, (self._positive(payload.spread) or 0.0) * 2.0)
        if direction == "BUY":
            base = min(value for value in (support, self._positive(payload.swing_low)) if value is not None)
            stop = base - buffer
            if stop >= price:
                return None, "Stop estrutural da compra ficou acima da entrada."
            return stop, "Stop M5 abaixo do fundo/suporte estrutural com buffer."
        base = max(value for value in (resistance, self._positive(payload.swing_high)) if value is not None)
        stop = base + buffer
        if stop <= price:
            return None, "Stop estrutural da venda ficou abaixo da entrada."
        return stop, "Stop M5 acima do topo/resistencia estrutural com buffer."

    def _target(
        self,
        direction: str,
        price: float,
        stop: float,
        support: float,
        resistance: float,
    ) -> tuple[float | None, str]:
        risk = abs(price - stop)
        if risk <= 0:
            return None, "Risco estrutural nulo."
        projected = price + risk * self.minimum_risk_reward if direction == "BUY" else price - risk * self.minimum_risk_reward
        structural = resistance if direction == "BUY" else support
        if direction == "BUY":
            return max(structural, projected), "Alvo M5 no topo/resistencia ou projecao minima 1.5R."
        return min(structural, projected), "Alvo M5 no fundo/suporte ou projecao minima 1.5R."

    def _fallback_atr(
        self,
        price: float | None,
        support: float | None,
        resistance: float | None,
    ) -> float | None:
        if price is None or support is None or resistance is None:
            return None
        return max(abs(resistance - support) * 0.10, price * 0.0002)

    def _ma_diagnostic(self, payload: PriceActionInput) -> str:
        short = self._positive(payload.short_average)
        long = self._positive(payload.long_average)
        if short is None or long is None:
            return "Medias indisponiveis; estrutura baseada em pivot/preco."
        return f"Media curta={short:.6f}; media longa={long:.6f}."

    def _positive(self, value: float | None) -> float | None:
        try:
            parsed = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None
        if parsed <= 0.0:
            return None
        return parsed
