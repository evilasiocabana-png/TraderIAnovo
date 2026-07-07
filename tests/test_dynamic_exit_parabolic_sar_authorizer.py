"""Testes da pre-autorizacao read-only do Parabolic SAR dinamico."""

import unittest

from application.dynamic_exit_parabolic_sar_authorizer import (
    DynamicExitParabolicSarAuthorizer,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitParabolicSarAuthorizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = DynamicExitParabolicSarAuthorizer()

    def test_marca_buy_reversal_risk_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)
        self.assertEqual(authorization.candidate_stop, 1.1020)

    def test_marca_sell_reversal_risk_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(
                side="SELL",
                current_price=1.0950,
                stop_price=1.1020,
                momentum=0.3,
                r_multiple=0.8,
            ),
            self._recommendation(candidate_stop=1.0980),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)
        self.assertEqual(authorization.candidate_stop, 1.0980)

    def test_rejeita_politica_diferente_de_parabolic_sar(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(policy="MOVING_AVERAGE_EXIT"),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertFalse(authorization.eligible_to_authorize)

    def test_rejeita_estado_sem_reversao_rapida(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(state="TREND_RUNNER"),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("reversao rapida", authorization.reason)

    def test_rejeita_momentum_ainda_favoravel(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(momentum=0.2),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Momentum", authorization.reason)

    def test_rejeita_perda_deteriorada(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(r_multiple=-0.3),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("perda", authorization.reason)

    def test_rejeita_stop_candidato_que_piora_protecao(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(candidate_stop=1.0970),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Stop candidato", authorization.reason)

    def test_rejeita_stop_candidato_do_lado_errado_do_mercado(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(candidate_stop=1.1060),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("lado errado", authorization.reason)

    def test_rejeita_confianca_baixa(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(confidence=0.52),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Confianca", authorization.reason)

    def _reading(
        self,
        *,
        side: str = "BUY",
        current_price: float = 1.1050,
        entry_price: float = 1.1000,
        stop_price: float = 1.0980,
        state: str = "REVERSAL_RISK",
        momentum: float | None = -0.3,
        r_multiple: float = 0.8,
    ) -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol="EURUSD",
            side=side,
            is_positioned=True,
            current_price=current_price,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=1.1100,
            momentum=momentum,
            state=state,
            r_multiple=r_multiple,
        )

    def _recommendation(
        self,
        *,
        policy: str = "PARABOLIC_SAR",
        action: str = "TIGHTEN_BY_MOMENTUM_LOSS",
        confidence: float = 0.58,
        candidate_stop: float | None = 1.1020,
    ) -> DynamicExitRecommendation:
        return DynamicExitRecommendation(
            policy=policy,
            action=action,
            reason="Read-only: Parabolic SAR detectou risco de reversao rapida.",
            confidence=confidence,
            market_state="REVERSAL_RISK",
            r_multiple=0.8,
            candidate_stop=candidate_stop,
            allowed_to_execute_demo=False,
        )


if __name__ == "__main__":
    unittest.main()
