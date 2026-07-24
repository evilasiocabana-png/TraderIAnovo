"""Testes da Camada Tempo Forex do Research Lab."""

from dataclasses import is_dataclass
from pathlib import Path
import unittest

from research.forex_time_layer import ForexTimeContext, ForexTimeLayer
from tests.architecture_test_utils import calls_from, imports_from, read_source


class ForexTimeLayerTest(unittest.TestCase):
    """Valida classificacao temporal sem acesso operacional."""

    def test_contexto_temporal_e_dataclass_frozen(self) -> None:
        self.assertTrue(is_dataclass(ForexTimeContext))
        self.assertTrue(ForexTimeContext.__dataclass_params__.frozen)

    def test_classifica_overlap_londres_nova_york_como_favoravel_para_eurusd(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-01T14:30:00+00:00",
        )

        self.assertEqual(context.session, "LONDON_NEW_YORK_OVERLAP")
        self.assertEqual(context.forex_session, "LONDON_NEW_YORK_OVERLAP")
        self.assertEqual(context.hour_utc, 14)
        self.assertEqual(context.hour_brt, 11)
        self.assertEqual(context.brt_window, "11:00-12:00")
        self.assertTrue(context.is_london_new_york_overlap)
        self.assertTrue(context.is_london_ny_overlap)
        self.assertEqual(context.temporal_status, "SESSAO_FAVORAVEL")
        self.assertFalse(context.temporal_blocked)
        self.assertGreater(context.temporal_score_adjustment, 0.0)

    def test_classifica_asia_como_favoravel_para_audusd(self) -> None:
        context = ForexTimeLayer().classify(
            "AUDUSD",
            "2026-07-01T02:00:00+00:00",
        )

        self.assertEqual(context.session, "ASIA")
        self.assertTrue(context.is_asia_session)
        self.assertEqual(context.temporal_status, "SESSAO_FAVORAVEL")

    def test_bloqueia_rollover(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-01T21:10:00+00:00",
        )

        self.assertEqual(context.session, "ROLLOVER")
        self.assertEqual(context.forex_session, "ROLLOVER")
        self.assertTrue(context.is_rollover_window)
        self.assertTrue(context.is_rollover)
        self.assertTrue(context.temporal_blocked)
        self.assertEqual(context.temporal_status, "ROLLOVER_BLOQUEADO")

    def test_bloqueia_cinco_minutos_antes_do_rollover_do_servidor_mt5(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-01T14:30:00+00:00",
            server_timestamp="2026-07-01T23:56:00+00:00",
        )

        self.assertEqual(context.session, "ROLLOVER")
        self.assertTrue(context.is_rollover_window)
        self.assertTrue(context.temporal_blocked)
        self.assertEqual(context.temporal_status, "ROLLOVER_SERVIDOR_MT5_BLOQUEADO")
        self.assertEqual(context.server_day, "2026-07-01")
        self.assertLessEqual(context.minutes_to_server_rollover or 999.0, 5.0)

    def test_bloqueia_cinco_minutos_depois_do_rollover_do_servidor_mt5(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-01T14:30:00+00:00",
            server_timestamp="2026-07-02T00:03:00+00:00",
        )

        self.assertEqual(context.session, "ROLLOVER")
        self.assertTrue(context.is_rollover)
        self.assertTrue(context.temporal_blocked)
        self.assertEqual(context.temporal_status, "ROLLOVER_SERVIDOR_MT5_BLOQUEADO")
        self.assertEqual(context.server_day, "2026-07-02")
        self.assertLessEqual(context.minutes_from_server_rollover or 999.0, 5.0)

    def test_bloqueia_domingo_abertura(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-05T21:10:00+00:00",
        )

        self.assertTrue(context.is_sunday_open)
        self.assertTrue(context.temporal_blocked)
        self.assertEqual(context.temporal_status, "DOMINGO_ABERTURA_BLOQUEADO")

    def test_bloqueia_sabado_inteiro(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-04T14:30:00+00:00",
        )

        self.assertTrue(context.temporal_blocked)
        self.assertEqual(context.temporal_status, "FIM_DE_SEMANA_BLOQUEADO")

    def test_bloqueia_domingo_antes_da_abertura(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-05T14:30:00+00:00",
        )

        self.assertTrue(context.temporal_blocked)
        self.assertEqual(context.temporal_status, "FIM_DE_SEMANA_BLOQUEADO")

    def test_bloqueia_sexta_final(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-03T20:30:00+00:00",
        )

        self.assertTrue(context.is_friday_late)
        self.assertTrue(context.temporal_blocked)
        self.assertEqual(context.temporal_status, "SEXTA_FINAL_BLOQUEADO")

    def test_fora_de_janela_fica_inelegivel(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-01T23:00:00+00:00",
        )

        self.assertEqual(context.session, "OFF_HOURS")
        self.assertTrue(context.is_off_hours)
        self.assertTrue(context.temporal_blocked)
        self.assertEqual(context.temporal_status, "FORA_DA_JANELA")

    def test_modulo_permanece_puro_e_desacoplado(self) -> None:
        path = Path("research/forex_time_layer.py")
        imports = imports_from(path)
        calls = calls_from(path)
        source = read_source(path)

        forbidden_imports = {
            "application",
            "dashboard_app",
            "streamlit",
            "MetaTrader5",
            "mt5",
            "broker",
            "infrastructure",
        }
        forbidden_calls = {"open", "write", "send_order", "order_send"}

        self.assertTrue(forbidden_imports.isdisjoint(imports))
        self.assertTrue(forbidden_calls.isdisjoint(calls))
        self.assertNotIn("MetaTrader5", source)
        self.assertNotIn("order_send", source)


if __name__ == "__main__":
    unittest.main()
