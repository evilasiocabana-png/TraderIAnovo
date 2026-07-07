"""Classificador read-only de estado de mercado para saida dinamica."""

from __future__ import annotations

from dataclasses import replace

from domain.contracts.dynamic_exit import (
    DYNAMIC_EXIT_MARKET_STATES,
    DynamicExitMarketReading,
)


class DynamicExitMarketStateClassifier:
    """Classifica contexto de saida sem autorizar execucao operacional."""

    def classify(self, reading: DynamicExitMarketReading) -> DynamicExitMarketReading:
        if not reading.is_positioned:
            return replace(
                reading,
                state="NO_POSITION",
                r_multiple=0.0,
                reason="Sem posicao aberta; saida dinamica apenas auditavel.",
                candidate_stop=None,
            )

        validation_error = self._validation_error(reading)
        if validation_error:
            return replace(
                reading,
                state="BAD_EXECUTION_CONTEXT",
                r_multiple=0.0,
                reason=validation_error,
                candidate_stop=reading.stop_price,
            )

        assert reading.current_price is not None
        assert reading.entry_price is not None
        assert reading.stop_price is not None

        risk = abs(reading.entry_price - reading.stop_price)
        favorable_move = self._favorable_move(reading)
        r_multiple = favorable_move / risk
        protected = self._is_protected(reading)
        momentum_against = self._momentum_against(reading)
        high_spread = self._high_spread(reading, risk)

        if high_spread:
            return replace(
                reading,
                state="BAD_EXECUTION_CONTEXT",
                r_multiple=r_multiple,
                reason="Spread alto em relacao ao risco; nenhuma acao dinamica recomendada.",
                candidate_stop=reading.stop_price,
            )
        if momentum_against and r_multiple > 0.15:
            return replace(
                reading,
                state="REVERSAL_RISK",
                r_multiple=r_multiple,
                reason="Posicao positiva com perda de momentum; observar risco de reversao.",
                candidate_stop=reading.stop_price,
            )
        if self._is_time_decay(reading, r_multiple):
            return replace(
                reading,
                state="TIME_DECAY",
                r_multiple=r_multiple,
                reason="Tempo em posicao alto sem progresso suficiente.",
                candidate_stop=reading.stop_price,
            )
        if r_multiple >= 1.0 and not momentum_against:
            return replace(
                reading,
                state="TREND_RUNNER",
                r_multiple=r_multiple,
                reason="Posicao avancou ao menos 1R com contexto favoravel.",
                candidate_stop=reading.stop_price,
            )
        if protected:
            return replace(
                reading,
                state="PROTECTED_POSITION",
                r_multiple=r_multiple,
                reason="Stop atual ja protege entrada ou lucro.",
                candidate_stop=reading.stop_price,
            )
        return replace(
            reading,
            state="NEW_POSITION",
            r_multiple=r_multiple,
            reason="Posicao aberta ainda sem confirmacao suficiente para ajuste dinamico.",
            candidate_stop=reading.stop_price,
        )

    def _validation_error(self, reading: DynamicExitMarketReading) -> str:
        side = reading.side.upper()
        if side not in {"BUY", "SELL"}:
            return "Direcao da posicao ausente ou invalida."
        if reading.current_price is None:
            return "Preco atual ausente."
        if reading.entry_price is None:
            return "Preco de entrada ausente."
        if reading.stop_price is None:
            return "Stop atual ausente."
        risk = abs(reading.entry_price - reading.stop_price)
        if risk <= 0:
            return "Risco inicial invalido para calcular R."
        return ""

    def _favorable_move(self, reading: DynamicExitMarketReading) -> float:
        assert reading.current_price is not None
        assert reading.entry_price is not None
        if reading.side.upper() == "SELL":
            return reading.entry_price - reading.current_price
        return reading.current_price - reading.entry_price

    def _is_protected(self, reading: DynamicExitMarketReading) -> bool:
        assert reading.entry_price is not None
        assert reading.stop_price is not None
        if reading.side.upper() == "SELL":
            return reading.stop_price <= reading.entry_price
        return reading.stop_price >= reading.entry_price

    def _momentum_against(self, reading: DynamicExitMarketReading) -> bool:
        momentum = reading.momentum
        if momentum is None:
            return False
        if reading.side.upper() == "SELL":
            return momentum > 0
        return momentum < 0

    def _high_spread(self, reading: DynamicExitMarketReading, risk: float) -> bool:
        if reading.spread is None:
            return False
        return reading.spread > risk * 0.35

    def _is_time_decay(
        self,
        reading: DynamicExitMarketReading,
        r_multiple: float,
    ) -> bool:
        minutes = reading.time_in_position_minutes
        return minutes is not None and minutes >= 240 and r_multiple < 0.25


def is_dynamic_exit_market_state(value: str) -> bool:
    """Retorna se o estado pertence ao contrato oficial."""

    return value in DYNAMIC_EXIT_MARKET_STATES
