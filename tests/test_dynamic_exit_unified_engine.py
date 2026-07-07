"""Testes do motor unificado read-only de saida dinamica."""

import unittest

from application.dynamic_exit_engine import DynamicExitUnifiedEngine
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)
from domain.contracts.dynamic_exit_engine import DynamicExitEngineInput


class DynamicExitUnifiedEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = DynamicExitUnifiedEngine()

    def test_fluxo_unico_atr_trailing_elegivel_sem_execucao_demo(self) -> None:
        result = self.engine.evaluate(
            DynamicExitEngineInput(
                reading=self._reading(
                    current_price=1.1040,
                    entry_price=1.1000,
                    stop_price=1.0980,
                    atr=0.0010,
                    momentum=0.2,
                    r_multiple=2.0,
                ),
                policy="ATR_TRAILING_STOP",
                recommendation=DynamicExitRecommendation(
                    policy="ATR_TRAILING_STOP",
                    action="TRAIL_BY_ATR",
                    reason="Read-only: trailing ATR candidato.",
                    confidence=0.61,
                    candidate_stop=1.1020,
                ),
            )
        )

        self.assertEqual(result.policy, "ATR_TRAILING_STOP")
        self.assertEqual(result.market_reading.state, "TREND_RUNNER")
        self.assertEqual(result.recommendation.action, "TRAIL_BY_ATR")
        self.assertEqual(result.authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertFalse(result.allowed_to_execute_demo)
        self.assertFalse(result.authorization.allowed_to_execute_demo)

    def test_politica_sem_autorizador_usa_fallback_seguro(self) -> None:
        result = self.engine.evaluate(
            DynamicExitEngineInput(
                reading=self._reading(),
                policy="FIXED_STOP",
            )
        )

        self.assertEqual(result.authorization.status, "REJECTED")
        self.assertIn("sem autorizador", result.authorization.reason)
        self.assertFalse(result.authorization.allowed_to_execute_demo)

    def test_plano_invalido_retorna_bad_context_sem_execucao(self) -> None:
        result = self.engine.evaluate(
            DynamicExitEngineInput(
                reading=self._reading(),
                policy="ATR_TRAILING_STOP",
                plan_status="SEM_PLANO",
            )
        )

        self.assertEqual(result.recommendation.action, "NO_ACTION_BAD_CONTEXT")
        self.assertEqual(result.authorization.status, "REJECTED")
        self.assertFalse(result.authorization.allowed_to_execute_demo)

    def test_recomendacao_fornecida_e_normalizada_com_estado_classificado(self) -> None:
        result = self.engine.evaluate(
            DynamicExitEngineInput(
                reading=self._reading(
                    current_price=1.1050,
                    entry_price=1.1000,
                    stop_price=1.0980,
                    momentum=-0.3,
                    r_multiple=0.8,
                ),
                policy="PARABOLIC_SAR",
                recommendation=DynamicExitRecommendation(
                    policy="PARABOLIC_SAR",
                    action="TIGHTEN_BY_MOMENTUM_LOSS",
                    reason="Read-only: reversao rapida.",
                    confidence=0.58,
                    market_state="NEW_POSITION",
                    r_multiple=0.0,
                    candidate_stop=1.1020,
                    allowed_to_execute_demo=True,
                ),
            )
        )

        self.assertEqual(result.market_reading.state, "REVERSAL_RISK")
        self.assertEqual(result.recommendation.market_state, "REVERSAL_RISK")
        self.assertEqual(result.recommendation.r_multiple, result.market_reading.r_multiple)
        self.assertFalse(result.recommendation.allowed_to_execute_demo)
        self.assertEqual(result.authorization.status, "ELIGIBLE_READ_ONLY")
        self.assertFalse(result.authorization.allowed_to_execute_demo)

    def _reading(
        self,
        *,
        side: str = "BUY",
        current_price: float = 1.1010,
        entry_price: float = 1.1000,
        stop_price: float = 1.0990,
        target_price: float = 1.1060,
        atr: float | None = 0.0010,
        volatility: float | None = 0.0012,
        momentum: float | None = 0.1,
        spread: float | None = 0.0001,
        time_in_position_minutes: float | None = 60,
        r_multiple: float = 0.5,
    ) -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol="EURUSD",
            side=side,
            is_positioned=True,
            current_price=current_price,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            atr=atr,
            volatility=volatility,
            momentum=momentum,
            spread=spread,
            time_in_position_minutes=time_in_position_minutes,
            r_multiple=r_multiple,
        )


if __name__ == "__main__":
    unittest.main()
