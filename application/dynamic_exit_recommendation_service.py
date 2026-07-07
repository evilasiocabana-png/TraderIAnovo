"""Motor read-only de recomendacao de saida dinamica."""

from __future__ import annotations

from dataclasses import replace

from domain.contracts.dynamic_exit import (
    DYNAMIC_EXIT_ACTIONS,
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitRecommendationEngine:
    """Transforma leitura de mercado em recomendacao auditavel sem executar."""

    def recommend(
        self,
        reading: DynamicExitMarketReading,
        *,
        policy: str = "FIXED_STOP",
        plan_status: str = "PLANO_VALIDO",
    ) -> DynamicExitRecommendation:
        normalized_policy = str(policy or "FIXED_STOP").upper()
        normalized_status = str(plan_status or "SEM_PLANO").upper()
        if normalized_status != "PLANO_VALIDO":
            return self._recommendation(
                policy=normalized_policy,
                action="NO_ACTION_BAD_CONTEXT",
                reason="Plano invalido ou ausente; saida dinamica mantida apenas em auditoria.",
                confidence=0.0,
                reading=reading,
            )
        if reading.state in {"NO_POSITION", "BAD_EXECUTION_CONTEXT"}:
            return self._recommendation(
                policy=normalized_policy,
                action="NO_ACTION_BAD_CONTEXT",
                reason=reading.reason,
                confidence=0.0,
                reading=reading,
            )
        if reading.state == "NEW_POSITION":
            return self._recommendation(
                policy=normalized_policy,
                action="KEEP_ORIGINAL_PLAN",
                reason="Posicao nova; preservar stop inicial e politica base do Lab.",
                confidence=0.40,
                reading=reading,
            )
        if reading.state == "PROTECTED_POSITION":
            return self._recommendation(
                policy=normalized_policy,
                action="KEEP_ORIGINAL_PLAN",
                reason="Posicao ja protegida; manter plano original em modo read-only.",
                confidence=0.50,
                reading=reading,
            )
        if reading.state == "TREND_RUNNER":
            return self._trend_runner_recommendation(normalized_policy, reading)
        if reading.state == "REVERSAL_RISK":
            if normalized_policy == "BREAK_EVEN":
                return self._recommendation(
                    policy=normalized_policy,
                    action="PROTECT_TO_BREAK_EVEN",
                    reason="Risco de reversao; observar protecao em break-even sem executar.",
                    confidence=0.58,
                    reading=replace(
                        reading,
                        candidate_stop=reading.entry_price or reading.candidate_stop,
                    ),
                )
            return self._recommendation(
                policy=normalized_policy,
                action="TIGHTEN_BY_MOMENTUM_LOSS",
                reason="Risco de reversao por perda de momentum; observar stop candidato sem executar.",
                confidence=0.55,
                reading=reading,
            )
        if reading.state == "TIME_DECAY":
            return self._recommendation(
                policy=normalized_policy,
                action="TIME_DECAY_EXIT_WATCH",
                reason="Tempo em posicao alto sem progresso; acompanhar saida temporal sem executar.",
                confidence=0.45,
                reading=reading,
            )
        return self._recommendation(
            policy=normalized_policy,
            action="KEEP_ORIGINAL_PLAN",
            reason="Estado de mercado desconhecido; manter politica base em auditoria.",
            confidence=0.20,
            reading=reading,
        )

    def _trend_runner_recommendation(
        self,
        policy: str,
        reading: DynamicExitMarketReading,
    ) -> DynamicExitRecommendation:
        if policy == "ATR_TRAILING_STOP":
            return self._recommendation(
                policy=policy,
                action="TRAIL_BY_ATR",
                reason="Tendencia forte; ATR trailing favorecido em modo read-only.",
                confidence=0.65,
                reading=reading,
            )
        if policy in {"DONCHIAN_CHANNEL_STOP", "CHANDELIER_EXIT"}:
            return self._recommendation(
                policy=policy,
                action="TRAIL_BY_STRUCTURE",
                reason="Tendencia forte; trailing por estrutura deve ser observado sem executar.",
                confidence=0.60,
                reading=reading,
            )
        if policy == "BREAK_EVEN":
            return self._recommendation(
                policy=policy,
                action="KEEP_ORIGINAL_PLAN",
                reason="Tendencia forte; evitar break-even automatico dominante e preservar plano.",
                confidence=0.55,
                reading=reading,
            )
        return self._recommendation(
            policy=policy,
            action="KEEP_ORIGINAL_PLAN",
            reason="Tendencia favoravel; manter politica base do Lab em auditoria.",
            confidence=0.50,
            reading=reading,
        )

    def _recommendation(
        self,
        *,
        policy: str,
        action: str,
        reason: str,
        confidence: float,
        reading: DynamicExitMarketReading,
    ) -> DynamicExitRecommendation:
        normalized_action = action if action in DYNAMIC_EXIT_ACTIONS else "KEEP_ORIGINAL_PLAN"
        return DynamicExitRecommendation(
            policy=policy,
            action=normalized_action,
            reason=f"Read-only: {reason}",
            confidence=max(0.0, min(float(confidence), 1.0)),
            market_state=reading.state,
            r_multiple=reading.r_multiple,
            candidate_stop=reading.candidate_stop,
            allowed_to_execute_demo=False,
            source="DYNAMIC_EXIT_RECOMMENDATION_ENGINE_READ_ONLY",
        )
