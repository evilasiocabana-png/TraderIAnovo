"""Testes da pre-autorizacao read-only do Donchian Channel Stop dinamico."""

import unittest

from application.dynamic_exit_donchian_authorizer import (
    DynamicExitDonchianAuthorizer,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitDonchianAuthorizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = DynamicExitDonchianAuthorizer()

    def test_marca_trend_runner_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)
        self.assertEqual(authorization.candidate_stop, 1.1020)

    def test_marca_posicao_protegida_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(state="PROTECTED_POSITION", stop_price=1.1000),
            self._recommendation(candidate_stop=1.1020),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)

    def test_rejeita_politica_diferente_de_donchian(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(policy="CHANDELIER_EXIT", action="TRAIL_BY_STRUCTURE"),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertFalse(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)

    def test_rejeita_estado_sem_tendencia_ou_protecao(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(state="REVERSAL_RISK"),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("tendencia", authorization.reason)

    def test_rejeita_quando_r_menor_que_minimo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(r_multiple=0.5),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("0.75R", authorization.reason)

    def test_rejeita_momentum_contra_posicao(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(momentum=-0.2),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Momentum", authorization.reason)

    def test_rejeita_stop_candidato_que_piora_protecao(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(stop_price=1.1030),
            self._recommendation(candidate_stop=1.1020),
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

    def test_rejeita_volatilidade_invalida(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(volatility=0.0),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Volatilidade", authorization.reason)

    def test_marca_sell_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(
                side="SELL",
                current_price=1.0950,
                entry_price=1.1000,
                stop_price=1.1020,
                momentum=-0.3,
            ),
            self._recommendation(candidate_stop=1.0980),
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
        state: str = "TREND_RUNNER",
        momentum: float | None = 0.4,
        volatility: float | None = 0.0030,
        r_multiple: float = 1.1,
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
            volatility=volatility,
            state=state,
            r_multiple=r_multiple,
        )

    def _recommendation(
        self,
        *,
        policy: str = "DONCHIAN_CHANNEL_STOP",
        action: str = "TRAIL_BY_STRUCTURE",
        candidate_stop: float = 1.1020,
    ) -> DynamicExitRecommendation:
        return DynamicExitRecommendation(
            policy=policy,
            action=action,
            reason="Read-only: Rompimento com estrutura favoravel.",
            confidence=0.60,
            market_state="TREND_RUNNER",
            r_multiple=1.1,
            candidate_stop=candidate_stop,
            allowed_to_execute_demo=False,
        )


if __name__ == "__main__":
    unittest.main()
