"""Testes da pre-autorizacao read-only do Moving Average Exit dinamico."""

import unittest

from application.dynamic_exit_moving_average_authorizer import (
    DynamicExitMovingAverageAuthorizer,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitMovingAverageAuthorizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = DynamicExitMovingAverageAuthorizer()

    def test_marca_reversal_risk_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)
        self.assertIsNone(authorization.candidate_stop)

    def test_rejeita_politica_diferente_de_moving_average_exit(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(policy="TIME_STOP", action="TIME_DECAY_EXIT_WATCH"),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertFalse(authorization.eligible_to_authorize)

    def test_rejeita_estado_sem_perda_de_tendencia(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(state="TREND_RUNNER"),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("perda de tendencia", authorization.reason)

    def test_rejeita_momentum_ainda_favoravel(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(momentum=0.2),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Momentum", authorization.reason)

    def test_rejeita_perda_deteriorada(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(r_multiple=-0.6),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("perda", authorization.reason)

    def test_rejeita_confianca_baixa(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(confidence=0.50),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Confianca", authorization.reason)

    def test_marca_sell_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(side="SELL", momentum=0.2),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)

    def _reading(
        self,
        *,
        side: str = "BUY",
        current_price: float = 1.1010,
        entry_price: float = 1.1000,
        state: str = "REVERSAL_RISK",
        momentum: float | None = -0.2,
        r_multiple: float = 0.25,
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
            state=state,
            r_multiple=r_multiple,
        )

    def _recommendation(
        self,
        *,
        policy: str = "MOVING_AVERAGE_EXIT",
        action: str = "TIGHTEN_BY_MOMENTUM_LOSS",
        confidence: float = 0.56,
    ) -> DynamicExitRecommendation:
        return DynamicExitRecommendation(
            policy=policy,
            action=action,
            reason="Read-only: Perda de tendencia por media movel.",
            confidence=confidence,
            market_state="REVERSAL_RISK",
            r_multiple=0.25,
            candidate_stop=None,
            allowed_to_execute_demo=False,
        )


if __name__ == "__main__":
    unittest.main()
