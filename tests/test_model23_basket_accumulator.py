"""Testes do acumulador financeiro M23 sem acesso ao MT5 real."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from application.model23_basket_accumulator import (
    MODEL_23_FULL_EXIT_USD,
    Model23BasketManager,
    model23_entry_gate,
    model23_order_comment,
    model23_variant_id,
)


class _FakeExecutionService:
    def __init__(self, positions: list[object]) -> None:
        self.positions = positions
        self.close_calls: list[dict[str, object]] = []

    def list_open_positions(self) -> list[object]:
        return list(self.positions)

    def close_position(self, **kwargs: object) -> object:
        self.close_calls.append(dict(kwargs))
        return SimpleNamespace(accepted=True, status="ACCEPTED", message="market")


def _position(
    ticket: int,
    profit: float,
    *,
    symbol: str = "EURUSD",
    source: int = 1,
    side: int = 0,
    swap: float = 0.0,
) -> object:
    return SimpleNamespace(
        ticket=ticket,
        symbol=symbol,
        type=side,
        volume=0.1,
        profit=profit,
        swap=swap,
        commission=0.0,
        fee=0.0,
        comment=f"TraderIA M23 S{source}",
    )


class Model23BasketAccumulatorTest(unittest.TestCase):
    def _manager(
        self,
        directory: str,
        positions: list[object],
    ) -> tuple[Model23BasketManager, _FakeExecutionService]:
        service = _FakeExecutionService(positions)
        manager = Model23BasketManager(
            execution_service=service,
            state_path=Path(directory) / "state.json",
            audit_path=Path(directory) / "audit.jsonl",
        )
        return manager, service

    def test_identidade_preserva_modelo_fonte(self) -> None:
        variant = model23_variant_id("MODELO_10_XAU_M5_SMA_RSI_DISTANCE")

        self.assertTrue(variant.endswith("SOURCE_M10"))
        self.assertEqual(model23_order_comment(variant), "TraderIA M23 S10")

    def test_identidade_aceita_m26_como_fonte_adicional(self) -> None:
        variant = model23_variant_id("MODELO_26_XAU_M5_SMART_MONEY")

        self.assertTrue(variant.endswith("SOURCE_M26"))
        self.assertEqual(model23_order_comment(variant), "TraderIA M23 S26")

    def test_resultado_abaixo_dos_gates_apenas_acumula(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [_position(1, 250.0)])

            snapshot = manager.evaluate_once()

            self.assertEqual(snapshot.status, "ACCUMULATING")
            self.assertEqual(snapshot.net_result_usd, 250.0)
            self.assertEqual(service.close_calls, [])

    def test_nao_arma_trailing_nem_fecha_no_recuo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [_position(1, 400.0)])
            armed = manager.evaluate_once()
            service.positions = [_position(1, 299.0)]

            closed = manager.evaluate_once()

            self.assertEqual(armed.status, "ACCUMULATING")
            self.assertFalse(armed.trailing_armed)
            self.assertEqual(closed.status, "ACCUMULATING")
            self.assertEqual(closed.exit_reason, "")
            self.assertEqual(service.close_calls, [])

    def test_full_exit_em_1000_fecha_todos_a_mercado_por_ticket(self) -> None:
        self.assertEqual(MODEL_23_FULL_EXIT_USD, 1000.0)
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(
                directory,
                [
                    _position(11, 390.0, source=1),
                    _position(22, 620.0, source=2, side=1, swap=-10.0),
                ],
            )

            snapshot = manager.evaluate_once()

            self.assertEqual(snapshot.net_result_usd, 1000.0)
            self.assertEqual(snapshot.status, "EXIT_SUBMITTED")
            self.assertEqual(snapshot.exit_reason, "M23_FULL_EXIT_PLUS_1000_USD")
            self.assertEqual([call["ticket"] for call in service.close_calls], [22, 11])
            self.assertTrue(
                all(
                    call["reason"] == "M23_FULL_EXIT_PLUS_1000_USD"
                    for call in service.close_calls
                )
            )

    def test_full_exit_m23_nao_fecha_posicoes_dos_outros_modelos(self) -> None:
        foreign_m1 = SimpleNamespace(
            ticket=101,
            symbol="EURUSD",
            type=0,
            volume=0.1,
            profit=5000.0,
            swap=0.0,
            commission=0.0,
            fee=0.0,
            comment="TraderIA M1",
        )
        foreign_m2 = SimpleNamespace(
            ticket=102,
            symbol="GBPUSD",
            type=1,
            volume=0.1,
            profit=-300.0,
            swap=0.0,
            commission=0.0,
            fee=0.0,
            comment="TraderIA M2",
        )
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(
                directory,
                [
                    foreign_m1,
                    _position(201, 600.0, source=1),
                    foreign_m2,
                    _position(202, 400.0, source=2, side=1),
                ],
            )

            snapshot = manager.evaluate_once()

            self.assertEqual(snapshot.net_result_usd, 1000.0)
            self.assertEqual(snapshot.positions, 2)
            self.assertEqual(snapshot.status, "EXIT_SUBMITTED")
            self.assertEqual(
                [call["ticket"] for call in service.close_calls],
                [201, 202],
            )
            self.assertNotIn(101, [call["ticket"] for call in service.close_calls])
            self.assertNotIn(102, [call["ticket"] for call in service.close_calls])

    def test_prejuizo_nao_dispara_zeragem_financeira(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [_position(1, -301.0)])

            snapshot = manager.evaluate_once()

            self.assertEqual(snapshot.status, "ACCUMULATING")
            self.assertEqual(snapshot.exit_reason, "")
            self.assertEqual(service.close_calls, [])

    def test_estado_antigo_de_stop_ou_trailing_nao_fecha_a_cesta(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [_position(1, -450.0)])
            manager.state_path.write_text(
                '{"status":"EXIT_SUBMITTED",'
                '"exit_reason":"M23_GLOBAL_STOP_MINUS_300_USD",'
                '"round_id":"LEGACY","positions":1}',
                encoding="utf-8",
            )

            snapshot = manager.evaluate_once()

            self.assertEqual(snapshot.status, "ACCUMULATING")
            self.assertEqual(snapshot.exit_reason, "")
            self.assertEqual(service.close_calls, [])

    def test_zeragem_pendente_aguarda_confirmacao_sem_repetir_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [_position(1, 1000.0)])
            first = manager.evaluate_once()
            service.positions = [_position(1, -100.0)]

            second = manager.evaluate_once()

            self.assertEqual(first.status, "EXIT_SUBMITTED")
            self.assertEqual(second.status, "EXIT_SUBMITTED")
            self.assertEqual(second.exit_reason, "M23_FULL_EXIT_PLUS_1000_USD")
            self.assertEqual(len(service.close_calls), 1)

    def test_zeragem_pendente_repete_depois_da_janela_de_confirmacao(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [_position(1, 1000.0)])
            manager.close_confirmation_seconds = 0.0
            first = manager.evaluate_once()
            service.positions = [_position(1, -100.0)]

            second = manager.evaluate_once()

            self.assertEqual(first.status, "EXIT_SUBMITTED")
            self.assertEqual(second.exit_reason, "M23_FULL_EXIT_PLUS_1000_USD")
            self.assertEqual(len(service.close_calls), 2)

    def test_ignora_posicao_que_nao_pertence_ao_m23(self) -> None:
        foreign = SimpleNamespace(
            ticket=99,
            symbol="EURUSD",
            type=0,
            volume=0.1,
            profit=1200.0,
            swap=0.0,
            comment="TraderIA M1",
        )
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [foreign])

            snapshot = manager.evaluate_once()

            self.assertEqual(snapshot.status, "WAITING_NEW_ROUND")
            self.assertEqual(service.close_calls, [])

    def test_nova_rodada_exige_candle_posterior_a_zeragem(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [_position(1, 1000.0)])
            manager.evaluate_once()
            service.positions = []
            cleared = manager.evaluate_once()

            old_allowed, old_reason = model23_entry_gate(
                "2026-08-12T10:00:00+00:00",
                manager.state_path,
            )
            new_allowed, _ = model23_entry_gate(
                "2099-08-12T10:00:00+00:00",
                manager.state_path,
            )

            self.assertEqual(cleared.status, "WAITING_NEW_ROUND")
            self.assertFalse(old_allowed)
            self.assertEqual(old_reason, "M23_SINAL_ANTIGO_DA_RODADA_ANTERIOR")
            self.assertTrue(new_allowed)

    def test_zeragem_manual_tambem_exige_candle_novo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manager, service = self._manager(directory, [_position(1, 10.0)])
            active = manager.evaluate_once()
            service.positions = []

            cleared = manager.evaluate_once()
            allowed, reason = model23_entry_gate(
                active.round_started_at,
                manager.state_path,
            )

            self.assertEqual(cleared.status, "WAITING_NEW_ROUND")
            self.assertTrue(cleared.accept_signals_after)
            self.assertFalse(allowed)
            self.assertEqual(reason, "M23_SINAL_ANTIGO_DA_RODADA_ANTERIOR")

    def test_gate_aceita_timestamp_do_dashboard_em_horario_de_brasilia(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state.json"
            state_path.write_text(
                '{"status":"ACCUMULATING",'
                '"accept_signals_after":"2026-08-26T03:30:00+00:00"}',
                encoding="utf-8",
            )

            old_allowed, old_reason = model23_entry_gate(
                "26/08/2026 00:00",
                state_path,
            )
            new_allowed, new_reason = model23_entry_gate(
                "26/08/2026 01:00",
                state_path,
            )

            self.assertFalse(old_allowed)
            self.assertEqual(old_reason, "M23_SINAL_ANTIGO_DA_RODADA_ANTERIOR")
            self.assertTrue(new_allowed)
            self.assertEqual(new_reason, "M23_NOVO_SINAL_LIBERADO")


if __name__ == "__main__":
    unittest.main()
