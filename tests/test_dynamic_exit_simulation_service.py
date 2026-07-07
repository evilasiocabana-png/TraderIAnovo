"""Testes da simulacao paper de saida dinamica."""

import unittest
from pathlib import Path

from application.dynamic_exit_simulation_service import (
    DynamicExitSimulationService,
)
from domain.contracts.dynamic_exit import (
    DynamicExitMarketReading,
    DynamicExitRecommendation,
)


class DynamicExitSimulationServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.service = DynamicExitSimulationService()

    def test_buy_nao_simula_stop_para_baixo(self) -> None:
        decision = self.service.simulate(
            reading=self._reading(side="BUY", stop_price=1.0990),
            recommendation=self._recommendation(candidate_stop=1.0980),
            enabled=True,
            robot_armed=True,
            candle_key="c1",
        )

        self.assertFalse(decision.allowed_to_simulate)
        self.assertIn("BUY nao pode simular stop para baixo ou igual ao atual.", decision.rejection_reasons)

    def test_sell_nao_simula_stop_para_cima(self) -> None:
        decision = self.service.simulate(
            reading=self._reading(
                side="SELL",
                current_price=1.0960,
                entry_price=1.1000,
                stop_price=1.1020,
            ),
            recommendation=self._recommendation(candidate_stop=1.1030),
            enabled=True,
            robot_armed=True,
            candle_key="c1",
        )

        self.assertFalse(decision.allowed_to_simulate)
        self.assertIn("SELL nao pode simular stop para cima ou igual ao atual.", decision.rejection_reasons)

    def test_break_even_aprovado_quando_posicao_positiva(self) -> None:
        decision = self.service.simulate(
            reading=self._reading(
                side="BUY",
                current_price=1.1030,
                entry_price=1.1000,
                stop_price=1.0980,
            ),
            recommendation=self._recommendation(
                action="PROTECT_TO_BREAK_EVEN",
                candidate_stop=None,
            ),
            enabled=True,
            robot_armed=True,
            candle_key="c1",
        )

        self.assertTrue(decision.allowed_to_simulate)
        self.assertIsNotNone(decision.approved_stop)
        self.assertGreater(decision.approved_stop or 0.0, 1.1000)

    def test_trailing_atr_rejeitado_quando_atr_ausente(self) -> None:
        decision = self.service.simulate(
            reading=self._reading(atr=None),
            recommendation=self._recommendation(
                action="TRAIL_BY_ATR",
                candidate_stop=None,
            ),
            enabled=True,
            robot_armed=True,
            candle_key="c1",
        )

        self.assertFalse(decision.allowed_to_simulate)
        self.assertIn("ATR ausente para calcular stop candidato.", decision.rejection_reasons)

    def test_time_decay_nao_fecha_nem_simula_fechamento(self) -> None:
        decision = self.service.simulate(
            reading=self._reading(state="TIME_DECAY"),
            recommendation=self._recommendation(
                action="TIME_DECAY_EXIT_WATCH",
                candidate_stop=1.1000,
            ),
            enabled=True,
            robot_armed=True,
            candle_key="c1",
        )

        self.assertFalse(decision.allowed_to_simulate)
        self.assertIsNone(decision.approved_stop)
        self.assertIn("TIME_DECAY permanece apenas observacional nesta missao.", decision.rejection_reasons)

    def test_gate_rejeita_diferenca_irrelevante_de_stop(self) -> None:
        decision = self.service.simulate(
            reading=self._reading(stop_price=1.0990),
            recommendation=self._recommendation(candidate_stop=1.099000001),
            enabled=True,
            robot_armed=True,
            candle_key="c1",
        )

        self.assertFalse(decision.allowed_to_simulate)
        self.assertIn("Diferenca de stop irrelevante.", decision.rejection_reasons)

    def test_simulacao_idempotente_na_mesma_vela(self) -> None:
        first = self.service.simulate(
            reading=self._reading(),
            recommendation=self._recommendation(candidate_stop=1.1000),
            enabled=True,
            robot_armed=True,
            candle_key="c1",
        )
        second = self.service.simulate(
            reading=self._reading(),
            recommendation=self._recommendation(candidate_stop=1.1000),
            enabled=True,
            robot_armed=True,
            candle_key="c1",
        )

        self.assertTrue(first.allowed_to_simulate)
        self.assertFalse(second.allowed_to_simulate)
        self.assertIn("Simulacao ja registrada para esta vela/janela.", second.rejection_reasons)
        self.assertEqual(len(self.service.list_decisions()), 1)

    def test_servico_nao_chama_modificacao_mt5(self) -> None:
        source = Path("application/dynamic_exit_simulation_service.py").read_text(
            encoding="utf-8"
        )

        for forbidden in ("order_send", "order_modify", "position_close", "positions_get", "metatrader5"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source.lower())

    def _reading(
        self,
        *,
        side: str = "BUY",
        current_price: float = 1.1020,
        entry_price: float = 1.1000,
        stop_price: float = 1.0980,
        atr: float | None = 0.0010,
        state: str = "TREND_RUNNER",
    ) -> DynamicExitMarketReading:
        return DynamicExitMarketReading(
            symbol="EURUSD",
            side=side,
            is_positioned=True,
            current_price=current_price,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=1.1060 if side == "BUY" else 1.0940,
            atr=atr,
            spread=0.0001,
            state=state,
            r_multiple=1.0,
        )

    def _recommendation(
        self,
        *,
        action: str = "TRAIL_BY_ATR",
        candidate_stop: float | None = 1.1000,
    ) -> DynamicExitRecommendation:
        return DynamicExitRecommendation(
            policy="ATR_TRAILING_STOP",
            action=action,
            reason="Teste",
            confidence=0.7,
            market_state="TREND_RUNNER",
            r_multiple=1.0,
            candidate_stop=candidate_stop,
        )


if __name__ == "__main__":
    unittest.main()
