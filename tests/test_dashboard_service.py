import unittest
from types import SimpleNamespace

from application.dashboard_service import DashboardService


class DashboardServiceTest(unittest.TestCase):
    def test_instantiates_without_error(self) -> None:
        service = DashboardService()

        self.assertIsInstance(service, DashboardService)

    def test_exposes_forex_lab_and_report_views(self) -> None:
        service = DashboardService()
        view_model = service.get_dashboard_view_model()

        self.assertTrue(hasattr(view_model, "mt5_forex_signals"))
        self.assertTrue(hasattr(view_model, "mt5_heuristic_research"))
        self.assertTrue(hasattr(view_model, "mt5_trade_audit"))

    def test_report_consolidates_lab_and_forex_mt5(self) -> None:
        service = DashboardService()
        view_model = service.get_dashboard_view_model()

        self.assertIsNotNone(view_model.mt5_forex_signals)
        self.assertIsNotNone(view_model.mt5_heuristic_research)
        self.assertIsNotNone(view_model.mt5_trade_audit)

    def test_position_manager_nao_usa_fallback_por_simbolo_em_trade_fechado(self) -> None:
        service = DashboardService()

        record = {"ticket": 123, "symbol": "EURUSD"}
        mt5_record = {"ticket": 123, "source": "DEAL", "symbol": "EURUSD"}
        index = {
            "symbol:EURUSD": {
                "symbol": "EURUSD",
                "beta_mode": "ADAPTIVE_FULL_EXIT",
                "action": "FULL_EXIT",
            }
        }

        resolved = service._position_manager_record_for_trade(record, mt5_record, index)

        self.assertIsNone(resolved)

    def test_position_manager_ainda_usa_fallback_por_simbolo_em_posicao_aberta(self) -> None:
        service = DashboardService()

        record = {"ticket": 123, "symbol": "EURUSD"}
        mt5_record = {"ticket": 123, "source": "POSITION", "symbol": "EURUSD"}
        position_manager_record = {
            "symbol": "EURUSD",
            "beta_mode": "ADAPTIVE_FULL_EXIT",
            "action": "HOLD_POSITION",
        }
        index = {"symbol:EURUSD": position_manager_record}

        resolved = service._position_manager_record_for_trade(record, mt5_record, index)

        self.assertEqual(resolved, position_manager_record)

    def test_alpha016_reversal_entra_na_biblioteca_e_grade_mt5(self) -> None:
        service = DashboardService()

        self.assertEqual(
            service._mt5_alpha_library()["ALPHA016"],
            "BETA002 Reversal Signal",
        )
        grid = service._mt5_scenario_parameter_grid(None, expand_exits=False)

        self.assertTrue(
            any(
                str(item.get("alpha")) == "ALPHA016"
                and str(item.get("modelo")) == "BETA002_REVERSAL_SIGNAL"
                for item in grid
            )
        )

    def test_alpha016_gera_compra_quando_baixa_perde_forca_e_momentum_vira(self) -> None:
        service = DashboardService()
        row = SimpleNamespace(
            trend="BAIXA",
            momentum=0.0008,
            volatility=0.0004,
            confidence=0.55,
        )
        parameters = {
            "alpha": "ALPHA016",
            "modelo": "BETA002_REVERSAL_SIGNAL",
            "ema_curta": 14,
            "ema_longa": 50,
            "atr_stop_factor": 2.0,
            "rr": 3.0,
            "reversal_strength": 0.0003,
            "volatility_threshold": 0.0001,
        }

        candidate = service._mt5_parameterized_candidate(
            row,
            "BETA002_REVERSAL_SIGNAL",
            parameters,
        )

        self.assertEqual(candidate["decision"], "BUY")
        self.assertGreater(candidate["score"], 0.0)

    def test_alpha016_gera_venda_quando_alta_perde_forca_e_momentum_vira(self) -> None:
        service = DashboardService()
        row = SimpleNamespace(
            trend="ALTA",
            momentum=-0.0008,
            volatility=0.0004,
            confidence=0.55,
        )
        parameters = {
            "alpha": "ALPHA016",
            "modelo": "BETA002_REVERSAL_SIGNAL",
            "ema_curta": 14,
            "ema_longa": 50,
            "atr_stop_factor": 2.0,
            "rr": 3.0,
            "reversal_strength": 0.0003,
            "volatility_threshold": 0.0001,
        }

        candidate = service._mt5_parameterized_candidate(
            row,
            "BETA002_REVERSAL_SIGNAL",
            parameters,
        )

        self.assertEqual(candidate["decision"], "SELL")
        self.assertGreater(candidate["score"], 0.0)
