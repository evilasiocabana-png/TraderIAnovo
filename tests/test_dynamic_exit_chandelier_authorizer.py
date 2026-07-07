"""Testes da pre-autorizacao read-only do Chandelier Exit dinamico."""

import unittest

from application.dynamic_exit_chandelier_authorizer import (
    DynamicExitChandelierAuthorizer,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitChandelierAuthorizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = DynamicExitChandelierAuthorizer()

    def test_marca_trend_runner_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)
        self.assertEqual(authorization.candidate_stop, 1.1015)

    def test_rejeita_politica_diferente_de_chandelier(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(policy="ATR_TRAILING_STOP", action="TRAIL_BY_ATR"),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertFalse(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)

    def test_rejeita_estado_que_nao_e_trend_runner(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(state="REVERSAL_RISK"),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("trend runner", authorization.reason)

    def test_rejeita_quando_r_menor_que_um(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(r_multiple=0.8),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("1R", authorization.reason)

    def test_rejeita_momentum_contra_posicao(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(momentum=-0.2),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Momentum", authorization.reason)

    def test_rejeita_stop_candidato_que_piora_protecao(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(stop_price=1.1020),
            self._recommendation(candidate_stop=1.1015),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("nao melhora", authorization.reason)

    def test_rejeita_stop_candidato_do_lado_errado_do_mercado(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(current_price=1.1050),
            self._recommendation(candidate_stop=1.1060),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("lado errado", authorization.reason)

    def test_rejeita_stop_sem_distancia_minima_de_chandelier(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(current_price=1.1050, atr=0.0020),
            self._recommendation(candidate_stop=1.1030),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Chandelier", authorization.reason)

    def test_marca_sell_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(
                side="SELL",
                current_price=1.0950,
                entry_price=1.1000,
                stop_price=1.1020,
                momentum=-0.3,
            ),
            self._recommendation(candidate_stop=1.0985),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)

    def _reading(
        self,
        *,
        side: str = "BUY",
        current_price: float = 1.1050,
        entry_price: float = 1.1000,
        stop_price: float = 1.0980,
        atr: float | None = 0.0020,
        state: str = "TREND_RUNNER",
        momentum: float | None = 0.4,
        r_multiple: float = 1.2,
    ) -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol="EURUSD",
            side=side,
            is_positioned=True,
            current_price=current_price,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=1.1100,
            atr=atr,
            momentum=momentum,
            state=state,
            r_multiple=r_multiple,
        )

    def _recommendation(
        self,
        *,
        policy: str = "CHANDELIER_EXIT",
        action: str = "TRAIL_BY_STRUCTURE",
        candidate_stop: float = 1.1015,
    ) -> DynamicExitRecommendation:
        return DynamicExitRecommendation(
            policy=policy,
            action=action,
            reason="Read-only: Tendencia forte com estrutura favoravel.",
            confidence=0.62,
            market_state="TREND_RUNNER",
            r_multiple=1.2,
            candidate_stop=candidate_stop,
            allowed_to_execute_demo=False,
        )


if __name__ == "__main__":
    unittest.main()
