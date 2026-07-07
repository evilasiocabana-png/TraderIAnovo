"""Testes da pre-autorizacao read-only do Time Stop dinamico."""

import unittest

from application.dynamic_exit_time_stop_authorizer import (
    DynamicExitTimeStopAuthorizer,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitTimeStopAuthorizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = DynamicExitTimeStopAuthorizer()

    def test_marca_time_decay_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)
        self.assertIsNone(authorization.candidate_stop)

    def test_rejeita_politica_diferente_de_time_stop(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(policy="VOLATILITY_STOP", action="TRAIL_BY_ATR"),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertFalse(authorization.eligible_to_authorize)

    def test_rejeita_estado_diferente_de_time_decay(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(state="TREND_RUNNER"),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("TIME_DECAY", authorization.reason)

    def test_rejeita_tempo_insuficiente(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(time_in_position_minutes=120),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("240", authorization.reason)

    def test_rejeita_operacao_com_progresso_relevante(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(r_multiple=0.6),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("progresso", authorization.reason)

    def test_rejeita_momentum_favoravel(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(momentum=0.3),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Momentum", authorization.reason)

    def test_rejeita_confianca_baixa(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(confidence=0.40),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Confianca", authorization.reason)

    def test_marca_sell_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(side="SELL", momentum=0.1),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)

    def _reading(
        self,
        *,
        side: str = "BUY",
        current_price: float = 1.1005,
        entry_price: float = 1.1000,
        state: str = "TIME_DECAY",
        momentum: float | None = -0.1,
        time_in_position_minutes: float | None = 260,
        r_multiple: float = 0.12,
    ) -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol="EURUSD",
            side=side,
            is_positioned=True,
            current_price=current_price,
            entry_price=entry_price,
            stop_price=1.0980,
            target_price=1.1100,
            momentum=momentum,
            time_in_position_minutes=time_in_position_minutes,
            state=state,
            r_multiple=r_multiple,
        )

    def _recommendation(
        self,
        *,
        policy: str = "TIME_STOP",
        action: str = "TIME_DECAY_EXIT_WATCH",
        confidence: float = 0.45,
    ) -> DynamicExitRecommendation:
        return DynamicExitRecommendation(
            policy=policy,
            action=action,
            reason="Read-only: Tempo em posicao alto sem progresso.",
            confidence=confidence,
            market_state="TIME_DECAY",
            r_multiple=0.12,
            candidate_stop=None,
            allowed_to_execute_demo=False,
        )


if __name__ == "__main__":
    unittest.main()
