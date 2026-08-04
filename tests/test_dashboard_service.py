import unittest
from types import SimpleNamespace

from application.dashboard_service import DashboardService
from application.dashboard_view_model import (
    DashboardMT5HeuristicResearchRowViewModel,
    DashboardMT5HeuristicResearchViewModel,
    DashboardMT5ScenarioViewModel,
)


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

    def test_research_only_nao_substitui_vencedor_operacional_por_par(self) -> None:
        service = DashboardService()
        operational = DashboardMT5ScenarioViewModel(
            alpha_id="ALPHA001",
            pair="EURUSD",
            timeframe="M15",
            model="TREND_MOMENTUM",
            parameters={"alpha": "ALPHA001"},
            score=0.70,
            status="APROVADO",
            decision="BUY",
        )
        research_only = DashboardMT5ScenarioViewModel(
            alpha_id="ALPHA017",
            pair="EURUSD",
            timeframe="M15",
            model="MULTI_CURRENCY_GRID_MEAN_REVERSION",
            parameters={"alpha": "ALPHA017", "research_only": "true"},
            score=0.99,
            lab_confidence=0.99,
            status="APROVADO",
            decision="SELL",
        )
        ranking = [research_only, operational]

        winners = service._best_mt5_scenarios_by_pair(ranking)

        self.assertEqual(winners, [operational])
        self.assertEqual(ranking, [research_only, operational])
        self.assertIs(
            service._select_mt5_setup_suggestion(ranking, 0.70),
            operational,
        )

    def test_research_only_e_rejeitado_dos_mapas_ativos_e_sugestoes(self) -> None:
        service = DashboardService()
        row = DashboardMT5HeuristicResearchRowViewModel(
            pair="EURUSD",
            timeframe="M15",
            ideal_timeframe="M15",
            recommended_heuristic="TREND_MOMENTUM",
            decision="BUY",
            final_configuration={
                "alpha": "ALPHA001",
                "modelo": "TREND_MOMENTUM",
                "timeframe": "M15",
                "research_only": "ON",
            },
        )
        research = DashboardMT5HeuristicResearchViewModel(rows=[row])

        self.assertEqual(service._active_mt5_research_models_by_market(research), {})
        self.assertEqual(service._active_mt5_research_rows_by_market(research), {})
        self.assertEqual(service._lab_parameters_from_research_row(row), {})
        self.assertEqual(service._mt5_setup_suggestions_from_rows(research, 0.70), [])

    def test_dashboard_propaga_research_only_ao_motor_de_trade_plan(self) -> None:
        service = DashboardService()

        plan = service._mt5_research_trade_plan_for_data(
            symbol="EURUSD",
            timeframe="M15",
            decision="BUY",
            active_model="MULTI_CURRENCY_GRID_MEAN_REVERSION",
            entry_status="SINAL_TEORICO",
            entry_price=1.1000,
            atr=0.0010,
            reason="cenario experimental",
            lab_parameters={
                "alpha": "ALPHA017",
                "atr_stop_factor": "2.5",
                "rr": "2.0",
                "research_only": "sim",
            },
        )

        self.assertEqual(plan.status, "RESEARCH_ONLY")
        self.assertEqual(plan.invalid_reason, "RESEARCH_ONLY_CONFIGURATION")
        self.assertEqual(plan.direction, "WAIT")
        self.assertFalse(plan.certification_demo_allowed)
        self.assertEqual(plan.stop_management, "FIXED_STOP")
        self.assertIn("sem aplicacao", plan.stop_management_reason)

    def test_cenario_research_only_fica_no_ranking_com_wait_e_sem_demo(self) -> None:
        service = DashboardService()
        time_context = SimpleNamespace(
            session="LONDON",
            session_label="Londres",
            brt_window="04:00-13:00",
            hour_utc=10,
            hour_brt=7,
            weekday="MONDAY",
            is_london_session=True,
            is_new_york_session=False,
            is_asia_session=False,
            is_london_new_york_overlap=False,
            is_rollover_window=False,
            is_friday_late=False,
            is_sunday_open=False,
            is_off_hours=False,
            temporal_status="JANELA_FAVORAVEL",
            temporal_blocked=False,
            temporal_score_adjustment=0.0,
            temporal_reason="Sessao valida.",
            preferred_sessions=("LONDON",),
            financial_centers=("London",),
            quality_note="Amostra historica.",
        )
        evidence = SimpleNamespace(
            win_rate=0.80,
            sample_size=500,
            profit_factor=1.60,
            avg_return=0.01,
            max_drawdown=0.10,
            source="TEST_REPLAY",
            discrimination_summary="edge",
            discrimination_metrics={},
        )
        certification = SimpleNamespace(
            ict_score=90.0,
            grade="A",
            status="CERTIFICADA_A",
            usage="Demo liberada.",
            demo_allowed=True,
            minimum_filters_passed=True,
            rejection_reasons=(),
            component_scores={},
        )
        object.__setattr__(
            service,
            "_latest_mt5_forex_candles",
            lambda *args, **kwargs: [],
        )
        object.__setattr__(
            service,
            "_mt5_scenario_time_context",
            lambda *args, **kwargs: time_context,
        )
        object.__setattr__(
            service,
            "_mt5_scenario_evidence_for_candidate",
            lambda *args, **kwargs: evidence,
        )
        object.__setattr__(
            service,
            "_mt5_research_certification_from_evidence",
            lambda *args, **kwargs: certification,
        )
        row = SimpleNamespace(
            pair="EURUSD",
            timeframe="M15",
            last_candle_time="2026-08-03T10:00:00+00:00",
            last_price=1.0950,
            bollinger_upper=1.1050,
            bollinger_lower=1.0960,
            z_score=-2.3,
            rsi=24.0,
            adx=16.0,
            atr=0.0020,
            volatility=0.0002,
            trend="LATERAL",
            momentum=0.0,
        )
        parameters = {
            "alpha": "ALPHA017",
            "modelo": "MULTI_CURRENCY_GRID_MEAN_REVERSION",
            "z_threshold": 2.0,
            "adx_max": 22.0,
            "band_width_atr_max": 6.0,
            "rsi_sobrevenda": 25.0,
            "rsi_sobrecompra": 75.0,
            "atr_stop_factor": 2.5,
            "rr": 2.0,
            "research_only": True,
        }

        scenario = service._mt5_scenario_for_parameters(
            row,
            "MULTI_CURRENCY_GRID_MEAN_REVERSION",
            parameters,
            session_filter_enabled=True,
        )

        self.assertEqual(scenario.status, "RESEARCH_ONLY")
        self.assertEqual(scenario.decision, "WAIT")
        self.assertFalse(scenario.ict_demo_allowed)
        self.assertFalse(scenario.ict_minimum_filters_passed)
        self.assertIn("RESEARCH_ONLY", scenario.reason)
        self.assertEqual(scenario.parameters["research_only"], "True")
        self.assertIn(
            scenario,
            service._mt5_research_entry_finalists([scenario]),
        )
        self.assertEqual(service._best_mt5_scenarios_by_pair([scenario]), [])
