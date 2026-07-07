"""Pre-autorizador read-only do Volatility Stop dinamico demo."""

from __future__ import annotations

from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_demo_authorization import (
    DynamicExitDemoAuthorization,
)


class DynamicExitVolatilityAuthorizer:
    """Avalia elegibilidade para Volatility Stop sem liberar execucao."""

    def authorize(
        self,
        reading: DynamicExitMarketReading,
        recommendation: DynamicExitRecommendation,
    ) -> DynamicExitDemoAuthorization:
        policy = str(recommendation.policy or "N/D").upper()
        action = str(recommendation.action or "N/D").upper()
        candidate_stop = recommendation.candidate_stop

        if policy != "VOLATILITY_STOP" or action != "TRAIL_BY_ATR":
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Somente VOLATILITY_STOP com acao TRAIL_BY_ATR entra nesta fase.",
            )
        if not reading.is_positioned:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Sem posicao aberta; Volatility Stop nao pode ser elegivel.",
            )
        if reading.state in {"NO_POSITION", "BAD_EXECUTION_CONTEXT", "NEW_POSITION"}:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Estado de mercado nao permite Volatility Stop seguro nesta fase.",
            )

        side = str(reading.side or "").upper()
        current_price = reading.current_price
        entry_price = reading.entry_price
        current_stop = reading.stop_price
        atr = reading.atr
        volatility = reading.volatility
        if side not in {"BUY", "SELL"}:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Direcao da posicao invalida para validar Volatility Stop.",
            )
        if (
            current_price is None
            or entry_price is None
            or current_stop is None
            or candidate_stop is None
            or atr is None
            or atr <= 0.0
            or volatility is None
            or volatility <= 0.0
        ):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Preco, entrada, stop atual, ATR, volatilidade ou stop candidato ausente.",
            )
        if not self._moved_in_favor(side, current_price, entry_price):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Posicao ainda nao andou a favor.",
            )
        if reading.r_multiple < 0.50:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Volatility Stop exige pelo menos 0.50R de progresso nesta fase.",
            )
        if not self._improves_stop(side, candidate_stop, current_stop):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Stop candidato nao melhora a protecao atual.",
            )
        if not self._stop_before_market(side, candidate_stop, current_price):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Stop candidato ficaria do lado errado do mercado.",
            )
        if not self._respects_volatility_noise(
            side,
            candidate_stop,
            current_price,
            atr,
            volatility,
        ):
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Stop candidato ignora ruido minimo de volatilidade.",
            )
        if recommendation.confidence < 0.56:
            return self._rejected(
                policy,
                action,
                reading,
                candidate_stop,
                "Confianca insuficiente para pre-autorizacao demo.",
            )

        return DynamicExitDemoAuthorization(
            policy=policy,
            action=action,
            status="ELIGIBLE_READ_ONLY",
            reason=(
                "Elegivel para futura autorizacao demo de Volatility Stop; "
                "execucao permanece desligada nesta fase."
            ),
            eligible_to_authorize=True,
            allowed_to_execute_demo=False,
            candidate_stop=candidate_stop,
            market_state=reading.state,
            source="DYNAMIC_EXIT_VOLATILITY_DEMO_AUTHORIZER",
        )

    def _rejected(
        self,
        policy: str,
        action: str,
        reading: DynamicExitMarketReading,
        candidate_stop: float | None,
        reason: str,
    ) -> DynamicExitDemoAuthorization:
        return DynamicExitDemoAuthorization(
            policy=policy,
            action=action,
            status="REJECTED",
            reason=reason,
            eligible_to_authorize=False,
            allowed_to_execute_demo=False,
            candidate_stop=candidate_stop,
            market_state=reading.state,
            source="DYNAMIC_EXIT_VOLATILITY_DEMO_AUTHORIZER",
        )

    def _moved_in_favor(
        self,
        side: str,
        current_price: float,
        entry_price: float,
    ) -> bool:
        if side == "SELL":
            return current_price < entry_price
        return current_price > entry_price

    def _improves_stop(
        self,
        side: str,
        candidate_stop: float,
        current_stop: float,
    ) -> bool:
        epsilon = 1e-10
        if side == "SELL":
            return candidate_stop < current_stop - epsilon
        return candidate_stop > current_stop + epsilon

    def _stop_before_market(
        self,
        side: str,
        candidate_stop: float,
        current_price: float,
    ) -> bool:
        if side == "SELL":
            return candidate_stop > current_price
        return candidate_stop < current_price

    def _respects_volatility_noise(
        self,
        side: str,
        candidate_stop: float,
        current_price: float,
        atr: float,
        volatility: float,
    ) -> bool:
        distance = (
            candidate_stop - current_price
            if side == "SELL"
            else current_price - candidate_stop
        )
        minimum_distance = max(atr * 0.75, volatility * 0.50)
        return distance >= minimum_distance
