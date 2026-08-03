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

    def test_alpha017_entra_na_biblioteca_e_grade_de_pesquisa(self) -> None:
        service = DashboardService()

        self.assertEqual(
            service._mt5_alpha_library()["ALPHA017"],
            "Multi-Currency Grid Mean Reversion",
        )
        grid = service._mt5_scenario_parameter_grid(None, expand_exits=False)
        alpha017 = [item for item in grid if item.get("alpha") == "ALPHA017"]

        self.assertTrue(alpha017)
        self.assertTrue(all(item.get("research_only") is True for item in alpha017))
        self.assertEqual(
            {item.get("modelo") for item in alpha017},
            {"MULTI_CURRENCY_GRID_MEAN_REVERSION"},
        )

    def test_alpha017_compra_extremo_inferior_em_regime_lateral(self) -> None:
        service = DashboardService()
        row = SimpleNamespace(
            last_price=1.0950,
            bollinger_upper=1.1050,
            bollinger_lower=1.0960,
            z_score=-2.3,
            rsi=24.0,
            adx=16.0,
            atr=0.0020,
        )

        candidate = service._mt5_parameterized_candidate(
            row,
            "MULTI_CURRENCY_GRID_MEAN_REVERSION",
            {
                "alpha": "ALPHA017",
                "z_threshold": 2.0,
                "adx_max": 22.0,
                "band_width_atr_max": 6.0,
                "rsi_sobrevenda": 25.0,
                "rsi_sobrecompra": 75.0,
            },
        )

        self.assertEqual(candidate["decision"], "BUY")
        self.assertGreater(candidate["score"], 0.0)

    def test_alpha017_vende_extremo_superior_em_regime_lateral(self) -> None:
        service = DashboardService()
        row = SimpleNamespace(
            last_price=1.1060,
            bollinger_upper=1.1050,
            bollinger_lower=1.0960,
            z_score=2.4,
            rsi=78.0,
            adx=17.0,
            atr=0.0020,
        )

        candidate = service._mt5_parameterized_candidate(
            row,
            "MULTI_CURRENCY_GRID_MEAN_REVERSION",
            {
                "alpha": "ALPHA017",
                "z_threshold": 2.0,
                "adx_max": 22.0,
                "band_width_atr_max": 6.0,
                "rsi_sobrevenda": 25.0,
                "rsi_sobrecompra": 75.0,
            },
        )

        self.assertEqual(candidate["decision"], "SELL")
        self.assertGreater(candidate["score"], 0.0)

    def test_alpha017_bloqueia_grade_quando_adx_indica_tendencia(self) -> None:
        service = DashboardService()
        row = SimpleNamespace(
            last_price=1.0950,
            bollinger_upper=1.1050,
            bollinger_lower=1.0960,
            z_score=-2.5,
            rsi=22.0,
            adx=31.0,
            atr=0.0020,
        )

        candidate = service._mt5_parameterized_candidate(
            row,
            "MULTI_CURRENCY_GRID_MEAN_REVERSION",
            {
                "alpha": "ALPHA017",
                "z_threshold": 2.0,
                "adx_max": 22.0,
                "band_width_atr_max": 6.0,
                "rsi_sobrevenda": 25.0,
                "rsi_sobrecompra": 75.0,
            },
        )

        self.assertEqual(candidate["decision"], "WAIT")
        self.assertIn("ADX alto", candidate["reason"])
