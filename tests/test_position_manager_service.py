"""Testes do Position Manager MT5 Demo."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace

from application.position_manager_service import (
    PositionManagerService,
    PositionTradePlan,
)


class PositionManagerServiceTest(unittest.TestCase):
    """Cobre gestao de SL sem abrir novas entradas."""

    def test_buy_move_stop_para_cima_por_atr_trailing(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="ATR_TRAILING_STOP",
                atr=0.0010,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertEqual(result.beta_id, "BETA001")
        self.assertEqual(result.beta_mode, "PROTECT_ONLY")
        self.assertAlmostEqual(provider.modified_stop, 1.1020)
        self.assertEqual(provider.modify_calls, 1)
        self.assertEqual(provider.submit_order_calls, 0)

    def test_sell_move_stop_para_baixo_por_atr_trailing(self) -> None:
        provider = _FakePositionProvider(
            position=_position("USDCHF", "SELL", 0.8060, 0.8070, 0.8030),
            price=0.8040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "USDCHF",
                "SELL",
                entry=0.8060,
                stop=0.8070,
                target=0.8030,
                stop_management="ATR_TRAILING_STOP",
                atr=0.0005,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop, 0.8050)
        self.assertEqual(provider.modify_calls, 1)
        self.assertEqual(provider.submit_order_calls, 0)

    def test_nao_afasta_stop_contra_o_trader(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.1030, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="ATR_TRAILING_STOP",
                atr=0.0020,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "POSITION_HELD")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertEqual(provider.modify_calls, 0)

    def test_sem_plano_nao_move(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        results = manager.manage_signals(
            [
                {
                    "symbol": "EURUSD",
                    "decision": "BUY",
                    "stop_management": "ATR_TRAILING_STOP",
                }
            ]
        )

        self.assertEqual(results[0].status, "TRADE_PLAN_ABSENT")
        self.assertEqual(provider.modify_calls, 0)

    def test_estado_atual_eh_atualizado_sem_repetir_historico_inutil(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            provider = _FakePositionProvider(
                position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
                price=1.1040,
            )
            manager = self._manager(
                provider,
                enabled=True,
                log_path=temp_path / "position_manager.jsonl",
                current_state_path=temp_path / "position_manager_current.json",
                state_path=temp_path / "position_manager_state.json",
            )
            signal = {
                "symbol": "EURUSD",
                "decision": "BUY",
                "stop_management": "ATR_TRAILING_STOP",
            }

            manager.manage_signals([signal])
            manager.manage_signals([signal])

            current = json.loads(
                (temp_path / "position_manager_current.json").read_text(
                    encoding="utf-8"
                )
            )
            records = current["records"]
            self.assertEqual(records["symbol:EURUSD"]["status"], "TRADE_PLAN_ABSENT")
            history_lines = (
                temp_path / "position_manager.jsonl"
            ).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(history_lines), 1)

    def test_posicao_aberta_nao_depende_de_novo_gatilho_teorico(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
            candles=_trend_candles(1.1000, step=0.0002),
        )
        manager = self._manager(provider, enabled=True)

        results = manager.manage_signals(
            [
                {
                    "symbol": "EURUSD",
                    "decision": "BUY",
                    "entry": 1.1000,
                    "stop": 1.0980,
                    "target": 1.1060,
                    "plan_status": "SEM_GATILHO_VALIDO",
                    "robot_status": "POSICAO_ABERTA_MT5",
                    "is_positioned": True,
                    "stop_management": "ATR_TRAILING_STOP",
                    "beta_id": "BETA002",
                    "beta_mode": "PROTECT_ONLY",
                    "market_indicators": {"atr": 0.001},
                }
            ]
        )

        self.assertNotEqual(results[0].status, "TRADE_PLAN_ABSENT")
        self.assertIn(
            results[0].status,
            {"POSITION_HELD", "STOP_MOVED", "EXECUTION_DISABLED"},
        )

    def test_sem_posicao_nao_move(self) -> None:
        provider = _FakePositionProvider(position=None, price=1.1040)
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(self._plan("EURUSD", "BUY"))

        self.assertEqual(result.status, "POSITION_ABSENT")
        self.assertEqual(provider.modify_calls, 0)

    def test_sem_atr_ainda_pode_proteger_por_break_even(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", stop_management="ATR_TRAILING_STOP", atr=None)
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 1.1000)
        self.assertEqual(provider.modify_calls, 1)

    def test_break_even_move_para_entrada(self) -> None:
        provider = _FakePositionProvider(
            position=_position("GBPUSD", "BUY", 1.33637, 1.33508, 1.34043),
            price=1.33908,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "GBPUSD",
                "BUY",
                entry=1.33637,
                stop=1.33508,
                target=1.34043,
                stop_management="BREAK_EVEN",
                atr=None,
                parameters={
                    "break_even_trigger_rr": "1.0",
                    "break_even_offset_pips": "0.0",
                },
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop, 1.33637)

    def test_atr_trailing_calcula_sem_recalcular_lab(self) -> None:
        provider = _FakePositionProvider(
            position=_position("AUDUSD", "BUY", 0.6900, 0.6880, 0.6960),
            price=0.6940,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "AUDUSD",
                "BUY",
                entry=0.6900,
                stop=0.6880,
                target=0.6960,
                stop_management="ATR_TRAILING_STOP",
                atr=0.0007,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop, 0.6926)
        self.assertEqual(provider.lab_recalculate_calls, 0)

    def test_default_execucao_assistida_false_calcula_mas_nao_envia(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="ATR_TRAILING_STOP",
                atr=0.0010,
                parameters={"atr_trailing_factor": "2.0"},
            )
        )

        self.assertEqual(result.status, "EXECUTION_DISABLED")
        self.assertAlmostEqual(result.new_stop or 0.0, 1.1020)
        self.assertEqual(provider.modify_calls, 0)

    def test_politica_legada_unsupported_nao_bloqueia_decisao_dinamica(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", stop_management="UNSUPPORTED_EXIT")
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertEqual(provider.modify_calls, 1)

    def test_fixed_stop_mantem_posicao_sem_acao_operacional(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1030),
            price=1.1024,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", stop_management="FIXED_STOP")
        )

        self.assertEqual(result.status, "POSITION_HELD")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertEqual(result.position_state, "TREND_RUNNER")
        self.assertEqual(provider.modify_calls, 0)
        self.assertEqual(provider.close_calls, 0)

    def test_abaixo_de_um_r_preserva_plano_do_lab(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1008,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="ATR_TRAILING_STOP",
                atr=0.0002,
                parameters={
                    "break_even_trigger_rr": "0.25",
                    "atr_trailing_activation_rr": "0.25",
                },
            )
        )

        self.assertEqual(result.status, "POSITION_HELD")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertIn("PROTECTION_WAIT_UNDER_1_00R", result.evidence)
        self.assertEqual(provider.modify_calls, 0)

    def test_entre_um_r_e_um_meio_r_monitora_sem_mover_stop(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1024,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="ATR_TRAILING_STOP",
                atr=0.0002,
                parameters={
                    "break_even_trigger_rr": "0.25",
                    "atr_trailing_activation_rr": "0.25",
                },
            )
        )

        self.assertEqual(result.status, "POSITION_HELD")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertIn("PROTECTION_WAIT_UNDER_1_50R", result.evidence)
        self.assertEqual(provider.modify_calls, 0)

    def test_market_aware_stop_protection_move_stop_seguro(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="MARKET_AWARE_STOP_PROTECTION",
                atr=0.0010,
                support=1.1025,
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 1.1024)

    def test_sem_estrutura_ainda_pode_proteger_por_break_even(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="STRUCTURE_BASED_STOP_PROTECTION",
                atr=None,
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 1.1000)
        self.assertEqual(provider.modify_calls, 1)

    def test_volatility_stop_protection_move_stop_seguro(self) -> None:
        provider = _FakePositionProvider(
            position=_position("USDCHF", "SELL", 0.8060, 0.8070, 0.8030),
            price=0.8040,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "USDCHF",
                "SELL",
                entry=0.8060,
                stop=0.8070,
                target=0.8030,
                stop_management="VOLATILITY_STOP_PROTECTION",
                atr=0.0005,
                volatility=0.0010,
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 0.80475)

    def test_momentum_weakness_stop_tightening_move_para_entrada(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1032,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="MOMENTUM_WEAKNESS_STOP_TIGHTENING",
                momentum=-0.0002,
            )
        )

        self.assertEqual(result.status, "STOP_MOVED")
        self.assertAlmostEqual(provider.modified_stop or 0.0, 1.1000)

    def test_auditoria_registra_campos_obrigatorios_da_validacao(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "position-manager.jsonl"
            manager = PositionManagerService(
                provider=provider,
                assisted_execution_enabled=True,
                log_path=log_path,
            )

            result = manager.manage_plan(
                self._plan(
                    "EURUSD",
                    "BUY",
                    stop_management="ATR_TRAILING_STOP",
                    atr=0.0010,
                    parameters={"atr_trailing_factor": "2.0"},
                )
            )

            payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(result.status, "STOP_MOVED")
        for key in (
            "timestamp",
            "symbol",
            "ticket",
            "side",
            "policy",
            "entry",
            "current_price",
            "old_stop",
            "new_stop",
            "action",
            "execution_mode",
            "execution_status",
            "message",
            "missing_data",
            "provider_result",
        ):
            self.assertIn(key, payload)
        self.assertEqual(payload["execution_mode"], "AUTOMATIC_DEMO")
        self.assertEqual(payload["execution_status"], "EXECUTED")
        self.assertEqual(provider.submit_order_calls, 0)

    def test_evidencia_simples_nao_fecha_e_aguarda_um_meio_r(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1030),
            price=1.1024,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="EARLY_EXIT",
                momentum=-0.0002,
                target=1.1030,
            )
        )

        self.assertEqual(result.status, "POSITION_HELD")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertIn("PROTECTION_WAIT_UNDER_1_50R", result.evidence)
        self.assertIsNone(provider.modified_stop)
        self.assertEqual(provider.close_calls, 0)

    def test_early_exit_fica_desligado_e_preserva_posicao(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060, volume=0.1),
            price=1.1010,
        )
        manager = self._manager(provider, enabled=False)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="EARLY_EXIT",
                momentum=-0.0002,
                target=1.1100,
            )
        )

        self.assertEqual(result.status, "POSITION_HELD")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertEqual(result.final_exit_reason, "N/D")
        self.assertIn("MOMENTUM_AGAINST", result.evidence)
        self.assertIn("LOW_PROBABILITY_TO_TARGET", result.evidence)
        self.assertEqual(provider.close_calls, 0)

    def test_full_exit_fica_desligado_mesmo_com_execucao_assistida(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1100, volume=0.1),
            price=1.1010,
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "EURUSD",
                "BUY",
                stop_management="FULL_EXIT",
                momentum=-0.0002,
                target=1.1100,
            )
        )

        self.assertEqual(result.status, "POSITION_HELD")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertEqual(result.execution_status, "BLOCKED")
        self.assertEqual(provider.close_calls, 0)
        self.assertEqual(provider.close_reason, "")
        self.assertEqual(provider.submit_order_calls, 0)

    def test_beta002_compra_saudavel_mantem_posicao(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1100),
            price=1.1060,
            candles=_trend_candles(1.1000, step=0.0002),
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", beta_id="BETA002", stop_management="FIXED_STOP")
        )

        self.assertEqual(result.beta_id, "BETA002")
        self.assertEqual(result.beta_version, "M1_EMA14_MOMENTUM_VOLATILITY")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertEqual(result.position_state, "HEALTHY")
        self.assertEqual(provider.modify_calls, 0)
        self.assertEqual(provider.close_calls, 0)

    def test_beta002_venda_saudavel_mantem_posicao(self) -> None:
        provider = _FakePositionProvider(
            position=_position("USDCHF", "SELL", 0.8060, 0.8070, 0.8000),
            price=0.8030,
            candles=_trend_candles(0.8060, step=-0.00015),
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan(
                "USDCHF",
                "SELL",
                entry=0.8060,
                stop=0.8070,
                target=0.8000,
                beta_id="BETA002",
                stop_management="FIXED_STOP",
            )
        )

        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertEqual(result.position_state, "HEALTHY")
        self.assertEqual(provider.close_calls, 0)

    def test_beta002_ema_sozinha_nao_fecha(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1100),
            price=1.1030,
            candles=_weakening_candles(1.1000, groups=("ema",)),
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", beta_id="BETA002", stop_management="FIXED_STOP")
        )

        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertNotEqual(result.position_state, "EXIT_CANDIDATE")
        self.assertEqual(provider.close_calls, 0)

    def test_beta002_dados_ausentes_hold(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1100),
            price=1.1030,
            candles=[],
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", beta_id="BETA002", stop_management="FIXED_STOP")
        )

        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertIn("m1_candles", result.missing_data)
        self.assertEqual(provider.modify_calls, 0)
        self.assertEqual(provider.close_calls, 0)

    def test_beta002_protecao_persistente_move_stop(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = _FakePositionProvider(
                position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1100),
                price=1.1040,
                candles=_weakening_candles(1.1060, groups=("ema", "momentum", "advance")),
            )
            manager = self._manager(
                provider,
                enabled=True,
                state_path=Path(temp_dir) / "state.json",
            )
            plan = self._plan(
                "EURUSD",
                "BUY",
                beta_id="BETA002",
                stop_management="FIXED_STOP",
            )

            for _ in range(3):
                result = manager.manage_plan(plan)

        self.assertEqual(result.beta_id, "BETA002")
        self.assertIn(result.action, {"STOP_MOVED", "HOLD_POSITION"})
        self.assertGreaterEqual(result.beta_confirmation_count, 3)
        self.assertGreaterEqual(provider.modify_calls, 1)
        self.assertGreater(provider.modified_stop or 0.0, 1.0980)
        self.assertEqual(provider.close_calls, 0)

    def test_beta002_exit_persistente_nao_fecha_posicao(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = _FakePositionProvider(
                position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1100),
                price=1.1010,
                candles=_weakening_candles(
                    1.1080,
                    groups=("ema", "momentum", "advance", "structure"),
                    strong=True,
                ),
            )
            manager = self._manager(
                provider,
                enabled=True,
                state_path=Path(temp_dir) / "state.json",
            )
            plan = self._plan(
                "EURUSD",
                "BUY",
                beta_id="BETA002",
                stop_management="FIXED_STOP",
            )

            for _ in range(6):
                result = manager.manage_plan(plan)

        self.assertEqual(result.status, "POSITION_HELD")
        self.assertEqual(result.action, "HOLD_POSITION")
        self.assertEqual(result.position_state, "EXIT_CANDIDATE")
        self.assertEqual(result.final_exit_reason, "N/D")
        self.assertEqual(provider.modify_calls, 0)
        self.assertEqual(provider.close_calls, 0)

    def test_beta002_exit_persistente_protege_depois_de_1r(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            provider = _FakePositionProvider(
                position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1100),
                price=1.1040,
                candles=_weakening_candles(
                    1.1080,
                    groups=("ema", "momentum", "advance", "structure"),
                    strong=True,
                ),
            )
            manager = self._manager(
                provider,
                enabled=True,
                state_path=Path(temp_dir) / "state.json",
            )
            plan = self._plan(
                "EURUSD",
                "BUY",
                beta_id="BETA002",
                stop_management="FIXED_STOP",
            )

            for _ in range(6):
                result = manager.manage_plan(plan)

        self.assertIn(result.status, {"STOP_MOVED", "POSITION_HELD"})
        self.assertIn(result.action, {"STOP_MOVED", "HOLD_POSITION"})
        self.assertEqual(result.final_exit_reason, "N/D")
        self.assertGreaterEqual(provider.modify_calls, 1)
        self.assertGreater(provider.modified_stop or 0.0, 1.0980)
        self.assertEqual(provider.close_calls, 0)

    def test_plano_antigo_sem_beta_continua_beta001(self) -> None:
        provider = _FakePositionProvider(
            position=_position("EURUSD", "BUY", 1.1000, 1.0980, 1.1060),
            price=1.1040,
            candles=_weakening_candles(
                1.1080,
                groups=("ema", "momentum", "advance", "structure"),
                strong=True,
            ),
        )
        manager = self._manager(provider, enabled=True)

        result = manager.manage_plan(
            self._plan("EURUSD", "BUY", stop_management="FIXED_STOP")
        )

        self.assertEqual(result.beta_id, "BETA001")
        self.assertNotEqual(result.action, "FULL_EXIT")
        self.assertEqual(provider.close_calls, 0)

    def _manager(
        self,
        provider: "_FakePositionProvider",
        enabled: bool = False,
        state_path: Path | None = None,
        log_path: Path | None = None,
        current_state_path: Path | None = None,
    ) -> PositionManagerService:
        return PositionManagerService(
            provider=provider,
            assisted_execution_enabled=enabled,
            log_path=log_path
            or Path(tempfile.gettempdir()) / "traderia-position-manager-test.jsonl",
            state_path=state_path
            or Path(tempfile.gettempdir()) / "traderia-position-manager-state-test.json",
            current_state_path=current_state_path
            or Path(tempfile.gettempdir())
            / "traderia-position-manager-current-test.json",
        )

    def _plan(
        self,
        symbol: str,
        side: str,
        *,
        entry: float = 1.1000,
        stop: float = 1.0980,
        target: float = 1.1060,
        stop_management: str = "ATR_TRAILING_STOP",
        atr: float | None = 0.0010,
        parameters: dict[str, str] | None = None,
        momentum: float | None = None,
        volatility: float | None = None,
        support: float | None = None,
        resistance: float | None = None,
        swing_high: float | None = None,
        swing_low: float | None = None,
        beta_id: str = "BETA001",
    ) -> PositionTradePlan:
        return PositionTradePlan(
            symbol=symbol,
            side=side,
            entry=entry,
            stop=stop,
            target=target,
            stop_management=stop_management,
            stop_management_parameters=parameters or {},
            atr=atr,
            momentum=momentum,
            volatility=volatility,
            support=support,
            resistance=resistance,
            swing_high=swing_high,
            swing_low=swing_low,
            beta_id=beta_id,
        )


def _position(
    symbol: str,
    side: str,
    entry: float,
    stop: float,
    target: float,
    volume: float = 0.1,
) -> SimpleNamespace:
    return SimpleNamespace(
        ticket=123,
        symbol=symbol,
        side=side,
        type=0 if side == "BUY" else 1,
        price_open=entry,
        sl=stop,
        tp=target,
        volume=volume,
    )


class _FakePositionProvider:
    def __init__(
        self,
        position: object | None,
        price: float | None,
        candles: list[dict[str, float]] | None = None,
    ) -> None:
        self.position = position
        self.price = price
        self.candles = candles or []
        self.modified_stop: float | None = None
        self.modify_calls = 0
        self.close_calls = 0
        self.close_reason = ""
        self.submit_order_calls = 0
        self.lab_recalculate_calls = 0

    def get_open_position(self, symbol: str) -> object | None:
        if self.position is None:
            return None
        if str(getattr(self.position, "symbol", "")).upper() != symbol.upper():
            return None
        return self.position

    def get_current_price(self, symbol: str) -> float | None:
        return self.price

    def get_recent_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[object]:
        return self.candles[-limit:]

    def get_atr(
        self,
        symbol: str,
        timeframe: str,
        period: int,
    ) -> float | None:
        return None

    def modify_position_sl(
        self,
        symbol: str,
        ticket: int,
        new_stop: float,
    ) -> SimpleNamespace:
        self.modify_calls += 1
        self.modified_stop = new_stop
        return SimpleNamespace(success=True, message="SL atualizado.")

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> SimpleNamespace:
        self.close_calls += 1
        self.close_reason = reason
        return SimpleNamespace(accepted=True, status="ACCEPTED", message="Posicao fechada.")


def _trend_candles(start: float, step: float, count: int = 45) -> list[dict[str, float]]:
    candles: list[dict[str, float]] = []
    price = start
    for index in range(count):
        close = price + step
        high = max(price, close) + abs(step) * 0.4
        low = min(price, close) - abs(step) * 0.4
        candles.append(
            {"time": float(index), "open": price, "high": high, "low": low, "close": close}
        )
        price = close
    return candles


def _weakening_candles(
    start: float,
    groups: tuple[str, ...],
    strong: bool = False,
    count: int = 45,
) -> list[dict[str, float]]:
    candles = _trend_candles(start, step=0.00012, count=20)
    price = candles[-1]["close"]
    step = -0.00035 if strong else -0.00012
    for index in range(20, count):
        local_step = step
        if "ema" not in groups:
            local_step = 0.00002
        if "momentum" not in groups and index % 2 == 0:
            local_step = 0.00008
        open_price = price
        close = price + local_step
        high = max(open_price, close) + (0.00006 if "structure" not in groups else 0.00002)
        low = min(open_price, close) - (0.00006 if "structure" in groups else 0.00002)
        if "advance" in groups:
            close = min(close, open_price - abs(local_step) * 0.5)
        candles.append(
            {
                "time": float(index),
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
            }
        )
        price = close
    return candles


if __name__ == "__main__":
    unittest.main()

