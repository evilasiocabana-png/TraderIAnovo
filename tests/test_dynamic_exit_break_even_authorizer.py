"""Testes da pre-autorizacao read-only do break-even dinamico."""

import unittest

from application.dynamic_exit_break_even_authorizer import (
    DynamicExitBreakEvenAuthorizer,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitBreakEvenAuthorizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = DynamicExitBreakEvenAuthorizer()

    def test_marca_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)
        self.assertEqual(authorization.candidate_stop, 1.1000)

    def test_rejeita_politica_diferente_de_break_even(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(policy="ATR_TRAILING_STOP", action="TRAIL_BY_ATR"),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertFalse(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)

    def test_rejeita_tendencia_forte_para_nao_cortar_trade_promissor(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(state="TREND_RUNNER"),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Estado de mercado", authorization.reason)

    def test_rejeita_quando_posicao_nao_andou_a_favor(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(current_price=1.0990),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("nao andou a favor", authorization.reason)

    def test_rejeita_stop_candidato_que_piora_protecao(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(stop_price=1.1005),
            self._recommendation(candidate_stop=1.1000),
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

    def test_marca_sell_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(
                side="SELL",
                current_price=1.0950,
                entry_price=1.1000,
                stop_price=1.1020,
            ),
            self._recommendation(candidate_stop=1.1000),
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
        state: str = "REVERSAL_RISK",
    ) -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol="EURUSD",
            side=side,
            is_positioned=True,
            current_price=current_price,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=1.1100,
            state=state,
            r_multiple=1.2,
        )

    def _recommendation(
        self,
        *,
        policy: str = "BREAK_EVEN",
        action: str = "PROTECT_TO_BREAK_EVEN",
        candidate_stop: float = 1.1000,
    ) -> DynamicExitRecommendation:
        return DynamicExitRecommendation(
            policy=policy,
            action=action,
            reason="Read-only: Risco de reversao.",
            confidence=0.58,
            market_state="REVERSAL_RISK",
            r_multiple=1.2,
            candidate_stop=candidate_stop,
            allowed_to_execute_demo=False,
        )


if __name__ == "__main__":
    unittest.main()
