"""Testes da pre-autorizacao read-only do Volatility Stop dinamico."""

import unittest

from application.dynamic_exit_volatility_authorizer import (
    DynamicExitVolatilityAuthorizer,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitVolatilityAuthorizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.authorizer = DynamicExitVolatilityAuthorizer()

    def test_marca_trend_runner_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertTrue(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)
        self.assertEqual(authorization.candidate_stop, 1.1020)

    def test_rejeita_politica_diferente_de_volatility_stop(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(),
            self._recommendation(policy="ATR_TRAILING_STOP", action="TRAIL_BY_ATR"),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertFalse(authorization.eligible_to_authorize)
        self.assertFalse(authorization.allowed_to_execute_demo)

    def test_rejeita_estado_inseguro(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(state="NEW_POSITION"),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("Estado de mercado", authorization.reason)

    def test_rejeita_atr_ausente(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(atr=None),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("ATR", authorization.reason)

    def test_rejeita_volatilidade_invalida(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(volatility=0.0),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("volatilidade", authorization.reason)

    def test_rejeita_quando_r_menor_que_minimo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(r_multiple=0.2),
            self._recommendation(),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("0.50R", authorization.reason)

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

    def test_rejeita_stop_muito_colado_no_ruido(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(current_price=1.1050, atr=0.0020, volatility=0.0040),
            self._recommendation(candidate_stop=1.1035),
        )

        self.assertEqual(authorization.status, "REJECTED")
        self.assertIn("ruido", authorization.reason)

    def test_marca_sell_elegivel_sem_liberar_execucao_demo(self) -> None:
        authorization = self.authorizer.authorize(
            self._reading(
                side="SELL",
                current_price=1.0950,
                entry_price=1.1000,
                stop_price=1.1020,
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
        atr: float | None = 0.0020,
        volatility: float | None = 0.0030,
        state: str = "TREND_RUNNER",
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
            atr=atr,
            volatility=volatility,
            state=state,
            r_multiple=r_multiple,
        )

    def _recommendation(
        self,
        *,
        policy: str = "VOLATILITY_STOP",
        action: str = "TRAIL_BY_ATR",
        candidate_stop: float = 1.1020,
    ) -> DynamicExitRecommendation:
        return DynamicExitRecommendation(
            policy=policy,
            action=action,
            reason="Read-only: Volatilidade favorece ajuste contextual.",
            confidence=0.60,
            market_state="TREND_RUNNER",
            r_multiple=1.1,
            candidate_stop=candidate_stop,
            allowed_to_execute_demo=False,
        )


if __name__ == "__main__":
    unittest.main()
