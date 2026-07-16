"""Testes do contrato unico DashboardViewModel."""

import json
import os
import tempfile
import unittest
from dataclasses import fields
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from application.dashboard_service import DashboardService
from application.dashboard_view_model import (
    DASHBOARD_VIEW_MODEL_CONTRACT_VERSION,
    DashboardMT5HeuristicResearchRowViewModel,
    DashboardMT5HeuristicResearchViewModel,
    DashboardMT5ScenarioViewModel,
    DashboardMT5ForexSignalRowViewModel,
    DashboardMT5ForexSignalViewModel,
    DashboardViewModel,
    format_dashboard_timestamp,
)
from application.dashboard_service import DashboardData
from application.configuration_service import ConfigurationService
from application.mt5_market_data_service import MT5ForexSignalDashboard, MT5ForexSignalRow
from application.system_service import SystemStatus
from application.mt5_visual_signal_exporter import MT5VisualSignalExporter
from core.configuration_manager import ConfigurationManager
from domain.candle import Candle
from research.mt5_research_trade_plan import MT5ResearchTradePlan
from tests.architecture_test_utils import read_source


class DashboardViewModelContractTest(unittest.TestCase):
    """Valida o contrato estavel entre backend e UI."""

    REQUIRED_SECTIONS = {
        "system_status",
        "replay_status",
        "live_research_status",
        "live_session_summary",
        "live_signal_quality",
        "live_history",
        "research_status",
        "safety_status",
        "mt5_market_data",
        "mt5_forex_signals",
        "timeframe_optimizer",
        "mt5_heuristic_research",
        "demo_robot",
        "mt5_trade_audit",
        "contract_version",
    }

    def setUp(self) -> None:
        ConfigurationManager.reset_configuration()

    def tearDown(self) -> None:
        ConfigurationManager.reset_configuration()

    def test_view_model_possui_secoes_obrigatorias(self) -> None:
        field_names = {field.name for field in fields(DashboardViewModel)}

        self.assertTrue(self.REQUIRED_SECTIONS.issubset(field_names))

    def test_dashboard_service_expoe_view_model_com_fallbacks(self) -> None:
        service = DashboardService()

        self.assertTrue(hasattr(service, "get_dashboard_view_model"))
        self.assertTrue(hasattr(service, "get_dashboard_contract_version"))
        self.assertEqual(
            service.get_dashboard_contract_version(),
            DASHBOARD_VIEW_MODEL_CONTRACT_VERSION,
        )
        view_model = service.get_dashboard_view_model()

        self.assertIsInstance(view_model, DashboardViewModel)
        self.assertEqual(
            view_model.contract_version,
            DASHBOARD_VIEW_MODEL_CONTRACT_VERSION,
        )
        self.assertIsNotNone(view_model)
        self.assertEqual(view_model.safety_status.status, "READ ONLY")
        self.assertTrue(view_model.safety_status.read_only)
        self.assertFalse(view_model.safety_status.order_execution_enabled)
        self.assertGreaterEqual(view_model.replay_status.total_candles, 0)
        self.assertIsInstance(view_model.live_signal_quality, list)
        self.assertIsInstance(view_model.live_history, list)
        self.assertEqual(
            view_model.mt5_market_data.read_only_status,
            "SOMENTE MARKET DATA",
        )
        self.assertFalse(view_model.mt5_market_data.real_operation_authorized)
        self.assertEqual(
            view_model.mt5_forex_signals.read_only_status,
            "SOMENTE ANALISE DE MERCADO",
        )
        self.assertFalse(view_model.mt5_forex_signals.real_operation_authorized)
        self.assertIsInstance(view_model.timeframe_optimizer, list)
        self.assertTrue(view_model.mt5_heuristic_research.is_research_only)
        self.assertFalse(view_model.demo_robot.real_order_enabled)
        self.assertFalse(view_model.demo_robot.mt5_order_send_enabled)
        self.assertEqual(view_model.demo_robot.provider, "MT5_DEMO_DISABLED")
        self.assertIsInstance(view_model.mt5_trade_audit.rows, list)
        self.assertIsInstance(view_model.mt5_heuristic_research.rows, list)
        self.assertIsInstance(
            view_model.mt5_heuristic_research.scenario_ranking,
            list,
        )
        self.assertIsInstance(
            view_model.mt5_heuristic_research.best_scenarios_by_market,
            list,
        )
        self.assertIsInstance(
            view_model.mt5_heuristic_research.winner_configuration,
            dict,
        )
        self.assertIsInstance(
            view_model.mt5_heuristic_research.winner_score_breakdown,
            dict,
        )
        self.assertIsInstance(
            view_model.mt5_heuristic_research.winner_diagnostics,
            list,
        )
        self.assertIsInstance(
            view_model.mt5_heuristic_research.winner_research_configuration,
            dict,
        )

    def test_view_model_nao_recalcula_research_mt5_automaticamente(self) -> None:
        class NoAutoResearchDashboardService(DashboardService):
            def _to_view_model_mt5_heuristic_research(self, data: object):
                raise AssertionError("Research MT5 nao deve rodar no refresh online")

        service = NoAutoResearchDashboardService()
        object.__setattr__(
            service,
            "mt5_research_constants",
            DashboardMT5HeuristicResearchViewModel(
                status="RESEARCH_ONLY",
                message="Calibracao armazenada.",
            ),
        )

        view_model = service.get_dashboard_view_model()

        self.assertEqual(view_model.mt5_heuristic_research.status, "RESEARCH_ONLY")
        self.assertEqual(
            view_model.mt5_heuristic_research.message,
            "Calibracao armazenada.",
        )

    def test_scenario_runner_gera_ranking_e_melhor_cenario_por_par(self) -> None:
        service = DashboardService()
        buy_row = MT5ForexSignalRow(
            pair="EURUSD",
            status="OK",
            last_price=1.1,
            last_candle_time="2026-07-01T10:00:00+00:00",
            trend="ALTA",
            momentum=0.001,
            volatility=0.001,
            rsi=55.0,
            short_average=1.11,
            long_average=1.10,
            decision="BUY",
            confidence=0.60,
            reason="Snapshot de teste.",
            sample_size=100,
            win_rate=0.70,
            timeframe="M1",
            received_candles=5000,
        )
        sell_row = MT5ForexSignalRow(
            pair="EURUSD",
            status="OK",
            last_price=1.09,
            last_candle_time="2026-07-01T11:00:00+00:00",
            trend="BAIXA",
            momentum=-0.001,
            volatility=0.001,
            rsi=72.0,
            short_average=1.08,
            long_average=1.10,
            decision="SELL",
            confidence=0.62,
            reason="Snapshot de teste.",
            sample_size=100,
            win_rate=0.72,
            timeframe="M5",
            received_candles=5000,
        )
        data = DashboardData(
            system_status=SystemStatus(
                status="READ_ONLY",
                version="test",
                active_symbol="EURUSD",
                event_count=0,
                loaded_strategies_count=0,
            ),
            market_snapshot=None,
            strategy_signal=None,
            mt5_forex_signals=MT5ForexSignalDashboard(
                timeframe="MULTI",
                pairs=[buy_row, sell_row],
            ),
            configuration_data=ConfigurationService().get_configuration_data(),
        )

        research = service._to_view_model_mt5_heuristic_research(data)

        self.assertTrue(research.scenario_ranking)
        self.assertEqual(len(research.best_scenarios_by_market), 1)
        self.assertIsInstance(research.best_scenario, DashboardMT5ScenarioViewModel)
        self.assertEqual(research.best_pair, "EURUSD")
        self.assertEqual(len(research.rows), 1)
        self.assertEqual(research.rows[0].pair, "EURUSD")
        self.assertIn(research.rows[0].ideal_timeframe, {"M1", "M5"})
        self.assertEqual(research.rows[0].buy_scenario["timeframe"], "M1")
        self.assertEqual(research.rows[0].sell_scenario["timeframe"], "M5")
        self.assertGreater(research.rows[0].buy_score, 0.0)
        self.assertGreater(research.rows[0].sell_score, 0.0)
        self.assertNotEqual(
            research.best_scenario.score,
            research.best_scenario.lab_confidence,
        )
        self.assertIn(
            research.best_heuristic,
            {
                "TREND_MOMENTUM",
                "TREND_PULLBACK",
                "BREAKOUT_CONSOLIDATION",
                "RSI_REVERSAL",
                "DONCHIAN_BREAKOUT",
            },
        )
        self.assertEqual(research.rows[0].status, "APROVADO")
        self.assertIn("atr_stop_factor", research.best_scenario.parameters)
        self.assertIn("rr", research.best_scenario.parameters)
        self.assertEqual(
            research.winner_research_configuration["Fonte"],
            "MT5_RESEARCH_SCENARIO_RUNNER",
        )
        self.assertIn(
            "Confirmacao Historica",
            research.winner_research_configuration,
        )
        self.assertEqual(
            research.winner_research_configuration["Confirmacao Historica"],
            f"{research.best_scenario.lab_confidence:.4f}",
        )

    def test_scenario_runner_prioriza_confirmacao_historica_antes_do_encaixe(
        self,
    ) -> None:
        service = DashboardService()
        scenarios = [
            DashboardMT5ScenarioViewModel(
                pair="EURUSD",
                timeframe="M1",
                model="TREND_MOMENTUM",
                score=0.95,
                lab_confidence=0.40,
                status="APROVADO",
                decision="BUY",
            ),
            DashboardMT5ScenarioViewModel(
                pair="EURUSD",
                timeframe="M5",
                model="MA_RSI_FILTER",
                score=0.72,
                lab_confidence=0.70,
                status="APROVADO",
                decision="BUY",
            ),
        ]

        best = service._best_mt5_scenarios_by_pair(scenarios)

        self.assertEqual(len(best), 1)
        self.assertEqual(best[0].timeframe, "M5")
        self.assertEqual(best[0].lab_confidence, 0.70)

    def test_scenario_runner_pesquisa_biblioteca_institucional_de_alphas(self) -> None:
        grid = DashboardService()._mt5_scenario_parameter_grid(None)

        ema_pairs = {
            (parameters["ema_curta"], parameters["ema_longa"])
            for parameters in grid
        }
        atr_values = {parameters["atr_stop_factor"] for parameters in grid}
        rr_values = {parameters["rr"] for parameters in grid}
        stop_management_values = {parameters["stop_management"] for parameters in grid}
        beta_values = {parameters["beta_id"] for parameters in grid}
        models = {parameters["modelo"] for parameters in grid}
        alphas = {parameters["alpha"] for parameters in grid}

        self.assertIn((9, 21), ema_pairs)
        self.assertIn((20, 50), ema_pairs)
        self.assertIn((50, 200), ema_pairs)
        self.assertIn(2.5, atr_values)
        self.assertIn(3.0, rr_values)
        self.assertEqual(
            stop_management_values,
            {
                "FIXED_STOP",
                "ATR_TRAILING_STOP",
                "BREAK_EVEN",
                "CHANDELIER_EXIT",
                "PARABOLIC_SAR",
                "DONCHIAN_CHANNEL_STOP",
                "MOVING_AVERAGE_EXIT",
                "TIME_STOP",
                "VOLATILITY_STOP",
            },
        )
        self.assertEqual(
            alphas,
            {
                "ALPHA001",
                "ALPHA002",
                "ALPHA003",
                "ALPHA004",
                "ALPHA005",
                "ALPHA006",
                "ALPHA007",
                "ALPHA008",
                "ALPHA009",
                "ALPHA010",
                "ALPHA011",
                "ALPHA012",
                "ALPHA013",
                "ALPHA014",
                "ALPHA015",
                "ALPHA016",
            },
        )
        self.assertEqual(
            beta_values,
            {
                "BETA003",
                "BETA004",
                "BETA005",
                "BETA006",
                "BETA007",
                "BETA008",
                "BETA009",
                "BETA010",
                "BETA011",
            },
        )
        self.assertEqual(
            models,
            {
                "TREND_MOMENTUM",
                "TREND_PULLBACK",
                "BREAKOUT_CONSOLIDATION",
                "RSI_REVERSAL",
                "DONCHIAN_BREAKOUT",
                "ADX_TREND_STRENGTH",
                "MACD_MOMENTUM_SHIFT",
                "BOLLINGER_VOLATILITY_EXPANSION",
                "ATR_VOLATILITY_REGIME",
                "DONCHIAN_STRUCTURE_BREAKOUT",
                "PIVOT_REJECTION",
                "VWAP_MEAN_REVERSION",
                "SUPPORT_RESISTANCE_REACTION",
                "MULTI_TIMEFRAME_ALIGNMENT",
                "LIQUIDITY_SPREAD_FILTER",
                "BETA002_REVERSAL_SIGNAL",
            },
        )
        self.assertGreater(len(grid), 600)

    def test_modelo2_espelho_inverte_plano_valido_com_rr_um(self) -> None:
        service = DashboardService()
        plan = MT5ResearchTradePlan(
            symbol="EURUSD",
            timeframe="M1",
            direction="BUY",
            entry_price=1.1000,
            stop=1.0950,
            target=1.1150,
            risk_reward=3.0,
            stop_multiplier=2.0,
            exit_model="INITIAL_RISK_PLAN",
            exit_score=0.0,
            exit_candidates=1,
            status="PLANO_VALIDO",
            alpha_id="ALPHA001",
            beta_id="BETA005",
            beta_version="ATR_TRAILING_STOP_MANAGER",
            beta_mode="ATR_TRAILING_ONLY",
        )

        transformed = service._mt5_model2_inverse_plan(plan)

        self.assertIsNotNone(transformed)
        assert transformed is not None
        self.assertEqual(transformed.direction, "SELL")
        self.assertAlmostEqual(transformed.target or 0.0, 1.0950)
        self.assertAlmostEqual(transformed.stop or 0.0, 1.1050)
        self.assertEqual(transformed.risk_reward, 1.0)
        self.assertEqual(transformed.beta_id, "BETA002")
        self.assertEqual(transformed.beta_mode, "INVERSE_QUICK_TRADE")

    def test_modelo2_operacional_so_inverte_com_adx_forte(self) -> None:
        service = DashboardService()
        service.set_mt5_operational_model("MODELO_2_ESPELHO_BETA2_RR1")
        row = DashboardMT5ForexSignalRowViewModel(
            pair="EURUSD",
            decision="BUY",
            theoretical_entry_direction="BUY",
            theoretical_entry_status="SINAL_TEORICO",
            active_model="TREND_MOMENTUM",
            entry_filter_status="OK",
        )
        plan = MT5ResearchTradePlan(
            symbol="EURUSD",
            timeframe="M1",
            direction="BUY",
            entry_price=1.1000,
            stop=1.0950,
            target=1.1150,
            risk_reward=3.0,
            stop_multiplier=2.0,
            exit_model="INITIAL_RISK_PLAN",
            exit_score=0.0,
            exit_candidates=1,
            status="PLANO_VALIDO",
            alpha_id="ALPHA001",
            beta_id="BETA005",
        )

        transformed_row, transformed_plan = service._mt5_apply_operational_model(
            row,
            plan,
        )

        self.assertEqual(transformed_row.decision, "WAIT")
        self.assertEqual(transformed_row.theoretical_entry_direction, "WAIT")
        self.assertIn("AGUARDA_ADX_BAIXO", transformed_row.active_model)
        self.assertIs(transformed_plan, plan)

    def test_modelo2_operacional_inverte_quando_adx_baixo_presente(self) -> None:
        service = DashboardService()
        service.set_mt5_operational_model("MODELO_2_ESPELHO_BETA2_RR1")
        row = DashboardMT5ForexSignalRowViewModel(
            pair="EURUSD",
            decision="BUY",
            theoretical_entry_direction="BUY",
            theoretical_entry_status="SINAL_TEORICO",
            active_model="TREND_MOMENTUM",
            entry_filter_status="BLOQUEADO",
            entry_filter_reason="Filtro ADX < 20 presente.",
            adx=19.5,
        )
        plan = MT5ResearchTradePlan(
            symbol="EURUSD",
            timeframe="M1",
            direction="BUY",
            entry_price=1.1000,
            stop=1.0950,
            target=1.1150,
            risk_reward=3.0,
            stop_multiplier=2.0,
            exit_model="INITIAL_RISK_PLAN",
            exit_score=0.0,
            exit_candidates=1,
            status="PLANO_VALIDO",
            alpha_id="ALPHA001",
            beta_id="BETA005",
        )

        transformed_row, transformed_plan = service._mt5_apply_operational_model(
            row,
            plan,
        )

        self.assertEqual(transformed_row.decision, "SELL")
        self.assertEqual(transformed_plan.direction, "SELL")
        self.assertEqual(transformed_plan.beta_id, "BETA002")
        self.assertEqual(transformed_plan.exit_model, "BETA002_ESPELHO_STOP_RR1")

    def test_modelo2_operacional_nao_inverte_sem_adx_baixo(self) -> None:
        service = DashboardService()
        service.set_mt5_operational_model("MODELO_2_ESPELHO_BETA2_RR1")
        row = DashboardMT5ForexSignalRowViewModel(
            pair="EURUSD",
            decision="BUY",
            theoretical_entry_direction="BUY",
            theoretical_entry_status="SINAL_TEORICO",
            active_model="TREND_MOMENTUM",
            entry_filter_status="BLOQUEADO",
            entry_filter_reason="Filtro NV-V presente: Momentum contra.",
            adx=25.0,
        )
        plan = MT5ResearchTradePlan(
            symbol="EURUSD",
            timeframe="M1",
            direction="BUY",
            entry_price=1.1000,
            stop=1.0950,
            target=1.1150,
            risk_reward=3.0,
            stop_multiplier=2.0,
            exit_model="INITIAL_RISK_PLAN",
            exit_score=0.0,
            exit_candidates=1,
            status="PLANO_VALIDO",
            alpha_id="ALPHA001",
            beta_id="BETA005",
        )

        transformed_row, transformed_plan = service._mt5_apply_operational_model(
            row,
            plan,
        )

        self.assertEqual(transformed_row.decision, "WAIT")
        self.assertIn("ADX atual: 25.00", transformed_row.reason)
        self.assertIs(transformed_plan, plan)

    def test_chaveamento_todos_expande_modelo1_e_modelo2(self) -> None:
        service = DashboardService()
        service.set_mt5_operational_model("TODOS_MODELOS")

        self.assertEqual(
            service._mt5_operational_models_to_evaluate(),
            ("MODELO_1_ALPHA_ATUAL", "MODELO_2_ESPELHO_BETA2_RR1"),
        )

    def test_scenario_runner_novas_alphas_usam_indicadores_especificos(self) -> None:
        service = DashboardService()
        row = MT5ForexSignalRow(
            pair="EURUSD",
            status="OK",
            last_price=1.105,
            last_candle_time="2026-07-01T10:00:00+00:00",
            trend="ALTA",
            momentum=0.0008,
            volatility=0.0005,
            rsi=58.0,
            short_average=1.104,
            long_average=1.100,
            decision="BUY",
            confidence=0.60,
            reason="Snapshot de teste.",
            sample_size=100,
            win_rate=0.70,
            timeframe="M15",
            ema_fast=1.105,
            ema_slow=1.100,
            adx=32.0,
            atr=0.001,
            atr_average=0.0008,
            macd=0.0004,
            macd_signal=0.0001,
            bollinger_upper=1.104,
            bollinger_lower=1.096,
            tick_volume=1300,
            tick_volume_average=1000.0,
            day_high=1.105,
            day_low=1.095,
            donchian_high=1.105,
            donchian_low=1.095,
            pivot=1.103,
            vwap=1.101,
            z_score=1.8,
            support=1.096,
            resistance=1.105,
            swing_high=1.105,
            swing_low=1.096,
            received_candles=5000,
        )

        alpha006 = service._mt5_scenario_for_parameters(
            row,
            "ADX_TREND_STRENGTH",
            {
                "alpha": "ALPHA006",
                "modelo": "ADX_TREND_STRENGTH",
                "ema_curta": 20,
                "ema_longa": 50,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 2.0,
                "rr": 2.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
                "adx_min": 25.0,
            },
        )
        alpha007 = service._mt5_scenario_for_parameters(
            row,
            "MACD_MOMENTUM_SHIFT",
            {
                "alpha": "ALPHA007",
                "modelo": "MACD_MOMENTUM_SHIFT",
                "ema_curta": 20,
                "ema_longa": 50,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 2.0,
                "rr": 2.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
            },
        )

        self.assertEqual(alpha006.alpha_id, "ALPHA006")
        self.assertEqual(alpha006.model, "ADX_TREND_STRENGTH")
        self.assertEqual(alpha006.decision, "BUY")
        self.assertGreater(alpha006.score, 0.0)
        self.assertEqual(alpha007.alpha_id, "ALPHA007")
        self.assertEqual(alpha007.decision, "BUY")
        self.assertGreater(alpha007.score, 0.0)

    def test_alpha_rejeita_indicador_obrigatorio_indisponivel(self) -> None:
        service = DashboardService()
        row = MT5ForexSignalRow(
            pair="EURUSD",
            status="OK",
            last_price=1.105,
            last_candle_time="2026-07-01T10:00:00+00:00",
            trend="ALTA",
            momentum=0.0008,
            volatility=0.0005,
            rsi=58.0,
            short_average=1.104,
            long_average=1.100,
            decision="BUY",
            confidence=0.60,
            reason="Snapshot de teste.",
            sample_size=100,
            win_rate=0.70,
            timeframe="M15",
            tick_volume=1300,
            tick_volume_average=1000.0,
            received_candles=5000,
        )

        scenario = service._mt5_scenario_for_parameters(
            row,
            "LIQUIDITY_SPREAD_FILTER",
            {
                "alpha": "ALPHA015",
                "modelo": "LIQUIDITY_SPREAD_FILTER",
                "ema_curta": 20,
                "ema_longa": 50,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 2.0,
                "rr": 2.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
                "volume_factor": 1.0,
            },
        )

        self.assertEqual(scenario.alpha_id, "ALPHA015")
        self.assertEqual(scenario.decision, "WAIT")
        self.assertEqual(scenario.score, 0.0)
        self.assertIn("INDICADOR_INDISPONIVEL", scenario.reason)
        self.assertIn("spread", scenario.reason)

    def test_scenario_runner_parametros_alteram_pontuacao_do_cenario(self) -> None:
        service = DashboardService()
        row = MT5ForexSignalRow(
            pair="EURUSD",
            status="OK",
            last_price=1.1,
            last_candle_time="2026-07-01T10:00:00+00:00",
            trend="ALTA",
            momentum=0.0007,
            volatility=0.0006,
            rsi=58.0,
            short_average=1.11,
            long_average=1.10,
            decision="BUY",
            confidence=0.55,
            reason="Snapshot de teste.",
            sample_size=100,
            win_rate=0.70,
            timeframe="M1",
            received_candles=5000,
        )
        short_setup = service._mt5_scenario_for_parameters(
            row,
            "TREND_MOMENTUM",
            {
                "alpha": "Alpha001",
                "modelo": "TREND_MOMENTUM",
                "ema_curta": 9,
                "ema_longa": 21,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 1.5,
                "rr": 2.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
            },
        )
        expanded_setup = service._mt5_scenario_for_parameters(
            row,
            "TREND_MOMENTUM",
            {
                "alpha": "Alpha001",
                "modelo": "TREND_MOMENTUM",
                "ema_curta": 20,
                "ema_longa": 50,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 2.5,
                "rr": 3.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
            },
        )

        self.assertNotEqual(short_setup.score, expanded_setup.score)
        self.assertEqual(expanded_setup.parameters["ema_curta"], "20")
        self.assertEqual(expanded_setup.parameters["rr"], "3.0")

    def test_confianca_lab_do_cenario_nao_reaproveita_win_rate_generico(self) -> None:
        service = DashboardService()
        row = MT5ForexSignalRow(
            pair="EURUSD",
            status="OK",
            last_price=1.1,
            last_candle_time="2026-07-01T10:00:00+00:00",
            trend="ALTA",
            momentum=0.001,
            volatility=0.001,
            rsi=55.0,
            short_average=1.11,
            long_average=1.10,
            decision="BUY",
            confidence=0.55,
            reason="Snapshot de teste.",
            sample_size=100,
            win_rate=0.70,
            timeframe="M1",
            received_candles=5000,
        )

        scenario = service._mt5_scenario_for_parameters(
            row,
            "TREND_MOMENTUM",
            {
                "modelo": "TREND_MOMENTUM",
                "ema_curta": 9,
                "ema_longa": 21,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 1.5,
                "rr": 2.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
            },
        )

        self.assertEqual(scenario.lab_confidence, 0.0)
        self.assertEqual(scenario.lab_confidence_sample_size, 0)
        self.assertEqual(
            scenario.lab_confidence_source,
            "SCENARIO_NO_CANDLES",
        )
        self.assertNotEqual(scenario.lab_confidence, row.confidence)

    def test_confianca_lab_do_cenario_fica_zero_sem_amostra(self) -> None:
        service = DashboardService()
        row = MT5ForexSignalRow(
            pair="EURUSD",
            status="OK",
            last_price=1.1,
            last_candle_time="2026-07-01T10:00:00+00:00",
            trend="ALTA",
            momentum=0.001,
            volatility=0.001,
            rsi=55.0,
            short_average=1.11,
            long_average=1.10,
            decision="BUY",
            confidence=0.55,
            reason="Snapshot de teste.",
            sample_size=0,
            win_rate=0.0,
            timeframe="M1",
            received_candles=5000,
        )

        scenario = service._mt5_scenario_for_parameters(
            row,
            "TREND_MOMENTUM",
            {
                "modelo": "TREND_MOMENTUM",
                "ema_curta": 9,
                "ema_longa": 21,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 1.5,
                "rr": 2.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
            },
        )

        self.assertEqual(scenario.lab_confidence, 0.0)

    def test_confianca_lab_usa_todos_os_pontos_elegiveis_da_amostra(self) -> None:
        service = DashboardService()

        indexes = service._scenario_evidence_indexes(minimum=21, end_index=5000)

        self.assertEqual(len(indexes), 4980)
        self.assertEqual(indexes[0], 20)
        self.assertEqual(indexes[-1], 4999)
        self.assertGreater(len(indexes), 6)

    def test_confianca_lab_processa_pontos_elegiveis_em_lotes(self) -> None:
        service = DashboardService()

        batches = service._scenario_evidence_index_batches(
            minimum=21,
            end_index=5000,
            batch_size=500,
        )
        flattened = [index for batch in batches for index in batch]

        self.assertEqual(len(batches), 10)
        self.assertTrue(all(len(batch) <= 500 for batch in batches))
        self.assertEqual(flattened, service._scenario_evidence_indexes(21, 5000))
        self.assertEqual(flattened[0], 20)
        self.assertEqual(flattened[-1], 4999)

    def test_confianca_lab_usa_lote_padrao_equilibrado_para_evitar_trava(self) -> None:
        service = DashboardService()

        batches = service._scenario_evidence_index_batches(
            minimum=21,
            end_index=221,
        )
        flattened = [index for batch in batches for index in batch]

        self.assertTrue(all(len(batch) <= 100 for batch in batches))
        self.assertEqual(flattened, service._scenario_evidence_indexes(21, 221))

    def test_confianca_lab_pula_backtest_pesado_para_cenario_sem_gatilho(self) -> None:
        service = DashboardService()

        wait_evidence = service._mt5_scenario_evidence_for_candidate(
            object(),
            "TREND_MOMENTUM",
            {},
            "WAIT",
            0.90,
        )
        low_score_evidence = service._mt5_scenario_evidence_for_candidate(
            object(),
            "TREND_MOMENTUM",
            {},
            "BUY",
            0.10,
        )

        self.assertEqual(wait_evidence.source, "SCENARIO_WAIT_NO_EXPOSURE")
        self.assertEqual(
            low_score_evidence.source,
            "SCENARIO_SCORE_BELOW_RESEARCH_CUT",
        )
        self.assertEqual(wait_evidence.sample_size, 0)
        self.assertEqual(low_score_evidence.sample_size, 0)

    def test_snapshot_historico_reconstroi_indicadores_do_lab_a_partir_dos_candles(
        self,
    ) -> None:
        service = DashboardService()
        candles = [
            Candle(
                data=f"2026-07-01T00:{index:02d}:00+00:00",
                abertura=1.0000 + index * 0.0001,
                maxima=1.0004 + index * 0.0001,
                minima=0.9997 + index * 0.0001,
                fechamento=1.0002 + index * 0.0001,
                volume=100 + index,
            )
            for index in range(60)
        ]

        snapshot = service._theoretical_entry_snapshot(
            MT5ForexSignalRow(
                pair="EURUSD",
                status="OK",
                last_price=1.0060,
                last_candle_time="2026-07-01T01:00:00+00:00",
                trend="ALTA",
                momentum=0.0,
                volatility=0.0,
                rsi=50.0,
                short_average=1.0,
                long_average=1.0,
                decision="WAIT",
                confidence=0.55,
                reason="Teste",
                timeframe="M1",
            ),
            candles,
        )

        self.assertNotEqual(snapshot.macd, 0.0)
        self.assertNotEqual(snapshot.macd_signal, 0.0)
        self.assertGreater(snapshot.atr_average, 0.0)
        self.assertGreater(snapshot.tick_volume_average, 0.0)
        self.assertIsNotNone(snapshot.pivot)
        self.assertIsNotNone(snapshot.vwap)
        self.assertIsNotNone(snapshot.support)
        self.assertIsNotNone(snapshot.resistance)

    def test_auditoria_de_divergencia_nao_usa_adx_aproximado(self) -> None:
        service = DashboardService()
        source = read_source(Path("application/dashboard_service.py"))

        self.assertNotIn("adx_proxy", source)
        self.assertIn("_adx_from_candles", source)

        candles = [
            Candle(
                data=f"2026-07-01T00:{index:02d}:00+00:00",
                abertura=1.0000,
                maxima=1.0000,
                minima=1.0000,
                fechamento=1.0000,
                volume=100 + index,
            )
            for index in range(8)
        ]

        event = service._scenario_discrimination_event(
            candles,
            len(candles) - 1,
            "BUY",
            -0.001,
        )

        self.assertTrue(event["ADX indisponivel"])
        self.assertFalse(event["ADX baixo"])

    def test_filtro_operacional_nv_menos_v_usa_corte_de_dois_porcento(self) -> None:
        service = DashboardService()
        active_research_row = SimpleNamespace(
            lab_confidence_sample_size=350,
            lab_discrimination_metrics={
                "ATR subindo": {
                    "winner_rate": 0.4437,
                    "loser_rate": 0.4779,
                },
                "MACD hist divergente": {
                    "winner_rate": 0.0775,
                    "loser_rate": 0.0885,
                },
            },
        )

        rules = service._entry_filter_rules_from_research_row(active_research_row)

        self.assertEqual([rule["indicator"] for rule in rules], ["ATR subindo"])
        self.assertAlmostEqual(float(rules[0]["entry_edge"]), 0.0342)

    def test_macd_signal_historico_usa_ema_real_da_serie_macd(self) -> None:
        service = DashboardService()
        values = [1.0 + index * 0.001 for index in range(80)]

        macd, signal = service._macd_last(values, 12, 26, 9)
        fast_series = service._ema_series_last_aligned(values, 12)
        slow_series = service._ema_series_last_aligned(values, 26)
        expected_macd_series = [
            fast - slow for fast, slow in zip(fast_series, slow_series)
        ]

        self.assertAlmostEqual(macd, expected_macd_series[-1])
        self.assertAlmostEqual(signal, service._ema_last(expected_macd_series, 9))

    def test_research_calibration_roda_um_par_por_vez(self) -> None:
        class FakeMT5MarketDataService:
            def load_forex_research_snapshot(self, timeframe, count):
                return MT5ForexSignalDashboard(
                    timeframe=timeframe,
                    pairs=[
                        MT5ForexSignalRow(
                            pair="EURUSD",
                            status="OK",
                            last_price=1.1,
                            last_candle_time="2026-07-01T10:00:00+00:00",
                            trend="ALTA",
                            momentum=0.001,
                            volatility=0.001,
                            rsi=55.0,
                            short_average=1.11,
                            long_average=1.10,
                            decision="BUY",
                            confidence=0.70,
                            reason="Snapshot EURUSD.",
                            sample_size=100,
                            win_rate=0.70,
                            timeframe=timeframe,
                            received_candles=5000,
                        ),
                        MT5ForexSignalRow(
                            pair="GBPUSD",
                            status="OK",
                            last_price=1.3,
                            last_candle_time="2026-07-01T10:00:00+00:00",
                            trend="BAIXA",
                            momentum=-0.001,
                            volatility=0.001,
                            rsi=65.0,
                            short_average=1.29,
                            long_average=1.30,
                            decision="SELL",
                            confidence=0.72,
                            reason="Snapshot GBPUSD.",
                            sample_size=100,
                            win_rate=0.72,
                            timeframe=timeframe,
                            received_candles=5000,
                        ),
                    ],
                )

        class PairByPairDashboardService(DashboardService):
            def __init__(self):
                super().__init__(mt5_market_data_service=FakeMT5MarketDataService())
                object.__setattr__(self, "calls", [])

            def get_dashboard_data(self):
                return DashboardData(
                    system_status=SystemStatus(
                        status="READ_ONLY",
                        version="test",
                        active_symbol="EURUSD",
                        event_count=0,
                        loaded_strategies_count=0,
                    ),
                    market_snapshot=None,
                    strategy_signal=None,
                    mt5_forex_signals=MT5ForexSignalDashboard(),
                    configuration_data=ConfigurationService().get_configuration_data(),
                )

            def _mt5_research_timeframes(self, configuration, selected_timeframe):
                return ("M1", "M5")

            def _to_view_model_mt5_heuristic_research(self, data):
                pairs = tuple(
                    sorted(
                        {
                            str(getattr(row, "pair", "") or "").upper()
                            for row in getattr(data.mt5_forex_signals, "pairs", [])
                        }
                    )
                )
                self.calls.append(pairs)
                pair = pairs[0] if pairs else "N/D"
                scenario = DashboardMT5ScenarioViewModel(
                    pair=pair,
                    timeframe="M1",
                    model="TREND_MOMENTUM",
                    parameters={"rr": "2.0"},
                    score=0.80,
                    lab_confidence=0.70,
                    status="APROVADO",
                    decision="BUY",
                    reason="Cenario isolado por par.",
                )
                row = DashboardMT5HeuristicResearchRowViewModel(
                    pair=pair,
                    timeframe="M1",
                    ideal_timeframe="M1",
                    recommended_heuristic="TREND_MOMENTUM",
                    final_configuration={"modelo": "TREND_MOMENTUM"},
                    decision="BUY",
                    score=0.80,
                    confidence=0.70,
                    status="APROVADO",
                    reason="Cenario isolado por par.",
                )
                return DashboardMT5HeuristicResearchViewModel(
                    rows=[row],
                    scenario_ranking=[scenario],
                    best_scenarios_by_market=[scenario],
                    best_scenario=scenario,
                    status="RESEARCH_ONLY",
                )

            def _save_mt5_research_snapshot(self, research):
                return None

        service = PairByPairDashboardService()

        research = service.run_mt5_research_calibration("M1")

        self.assertIn(("EURUSD",), service.calls)
        self.assertIn(("GBPUSD",), service.calls)
        self.assertNotIn(("EURUSD", "GBPUSD"), service.calls)
        self.assertEqual(
            [row.pair for row in research.rows],
            ["EURUSD", "GBPUSD"],
        )

        service.calls.clear()
        pair_research = service.run_mt5_research_calibration_for_pair(
            "GBPUSD",
            "M1",
        )

        self.assertEqual(service.calls, [("GBPUSD",)])
        self.assertEqual([row.pair for row in pair_research.rows], ["GBPUSD"])
        self.assertEqual(
            pair_research.source,
            "MT5_RESEARCH_ALPHA_LIBRARY_SINGLE_PAIR_SEARCH_SPACE_5000",
        )

    def test_research_ranking_retorna_biblioteca_institucional_de_alphas(self) -> None:
        class RankingDashboardService(DashboardService):
            def _load_mt5_research_snapshot(self):
                return DashboardMT5HeuristicResearchViewModel(
                    scenario_ranking=[
                        DashboardMT5ScenarioViewModel(
                            alpha_id="ALPHA001",
                            pair="EURUSD",
                            timeframe="M15",
                            model="TREND_MOMENTUM",
                            score=0.71,
                            lab_confidence=0.60,
                            status="APROVADO",
                            decision="SELL",
                        ),
                        DashboardMT5ScenarioViewModel(
                            alpha_id="ALPHA002",
                            pair="USDCHF",
                            timeframe="H1",
                            model="TREND_PULLBACK",
                            score=0.83,
                            lab_confidence=0.72,
                            ict_score=82.0,
                            ict_grade="A",
                            ict_status="CERTIFICADA_A",
                            ict_usage="Operacao automatica Demo liberada.",
                            ict_demo_allowed=True,
                            ict_minimum_filters_passed=True,
                            status="APROVADO",
                            decision="BUY",
                        ),
                    ],
                    source="MT5_RESEARCH_ALPHA_LIBRARY_SEARCH_SPACE_5000",
                )

        ranking = RankingDashboardService().get_mt5_alpha_research_ranking()

        self.assertEqual(len(ranking), 16)
        self.assertEqual(ranking[0].alpha_id, "ALPHA002")
        self.assertEqual(ranking[0].status, "APROVADA")
        alpha006 = next(report for report in ranking if report.alpha_id == "ALPHA006")
        self.assertIn("ADX", alpha006.used_indicators or ())
        self.assertEqual(
            {report.alpha_id for report in ranking},
            {
                "ALPHA001",
                "ALPHA002",
                "ALPHA003",
                "ALPHA004",
                "ALPHA005",
                "ALPHA006",
                "ALPHA007",
                "ALPHA008",
                "ALPHA009",
                "ALPHA010",
                "ALPHA011",
                "ALPHA012",
                "ALPHA013",
                "ALPHA014",
                "ALPHA015",
                "ALPHA016",
            },
        )

    def test_research_ranking_nao_zera_confirmacao_por_filtro_operacional(
        self,
    ) -> None:
        class RankingDashboardService(DashboardService):
            def _load_mt5_research_snapshot(self):
                return DashboardMT5HeuristicResearchViewModel(
                    scenario_ranking=[
                        DashboardMT5ScenarioViewModel(
                            alpha_id="ALPHA003",
                            pair="EURUSD",
                            timeframe="M15",
                            model="BREAKOUT_CONSOLIDATION",
                            score=0.80,
                            lab_confidence=0.0,
                            status="APROVADO",
                            decision="BUY",
                        ),
                        DashboardMT5ScenarioViewModel(
                            alpha_id="ALPHA003",
                            pair="EURUSD",
                            timeframe="H1",
                            model="BREAKOUT_CONSOLIDATION",
                            score=0.50,
                            lab_confidence=0.59,
                            lab_confidence_sample_size=120,
                            status="REJEITADO",
                            decision="SELL",
                        ),
                    ],
                    source="MT5_RESEARCH_ALPHA_LIBRARY_SEARCH_SPACE_5000",
                )

        report = RankingDashboardService().get_mt5_alpha_research_report("ALPHA003")

        self.assertEqual(report.alpha_id, "ALPHA003")
        self.assertEqual(report.best_confidence, 0.59)
        self.assertEqual(report.best_timeframe, "H1")
        self.assertEqual(report.status, "REPROVADA")

    def test_sugestao_setup_lab_prioriza_confianca_de_70(self) -> None:
        class SuggestionDashboardService(DashboardService):
            def _load_mt5_research_snapshot(self):
                return DashboardMT5HeuristicResearchViewModel(
                    scenario_ranking=[
                        DashboardMT5ScenarioViewModel(
                            pair="EURUSD",
                            timeframe="M1",
                            model="TREND_MOMENTUM",
                            parameters={
                                "rr": "2.0",
                                "stop_management": "BREAK_EVEN",
                            },
                            score=0.90,
                            lab_confidence=0.62,
                            status="APROVADO",
                            decision="BUY",
                        ),
                        DashboardMT5ScenarioViewModel(
                            pair="EURUSD",
                            timeframe="H1",
                            model="MA_RSI_FILTER",
                            parameters={
                                "rr": "1.5",
                                "stop_management": "ATR_TRAILING_STOP",
                            },
                            score=0.80,
                            lab_confidence=0.70,
                            status="APROVADO",
                            decision="SELL",
                        ),
                    ],
                    source="MT5_RESEARCH_SNAPSHOT",
                )

        suggestions = SuggestionDashboardService().suggest_mt5_lab_setups()

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].pair, "EURUSD")
        self.assertEqual(suggestions[0].model, "MA_RSI_FILTER")
        self.assertEqual(suggestions[0].lab_confidence, 0.70)
        self.assertEqual(suggestions[0].status, "SUGERIDO_70")
        self.assertEqual(suggestions[0].stop_management, "ATR_TRAILING_STOP")
        self.assertEqual(
            suggestions[0].exit_model,
            "INITIAL_RISK_PLAN",
        )

    def test_sugestao_setup_lab_declara_quando_nao_atinge_70(self) -> None:
        class SuggestionDashboardService(DashboardService):
            def _load_mt5_research_snapshot(self):
                return DashboardMT5HeuristicResearchViewModel(
                    scenario_ranking=[
                        DashboardMT5ScenarioViewModel(
                            pair="USDCHF",
                            timeframe="M1",
                            model="TREND_MOMENTUM",
                            score=0.83,
                            lab_confidence=0.54,
                            status="APROVADO",
                            decision="BUY",
                        )
                    ],
                    source="MT5_RESEARCH_SNAPSHOT",
                )

        suggestions = SuggestionDashboardService().suggest_mt5_lab_setups()

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].pair, "USDCHF")
        self.assertEqual(suggestions[0].status, "MAIS_PROXIMO_DE_70")
        self.assertLess(suggestions[0].lab_confidence, 0.70)

    def test_sugestao_setup_lab_deriva_beta_vencedora_pela_saida(self) -> None:
        class SuggestionDashboardService(DashboardService):
            def _load_mt5_research_snapshot(self):
                return DashboardMT5HeuristicResearchViewModel(
                    scenario_ranking=[
                        DashboardMT5ScenarioViewModel(
                            pair="EURJPY",
                            timeframe="M1",
                            model="ADX_TREND_STRENGTH",
                            parameters={
                                "rr": "3.0",
                                "stop_management": "ATR_TRAILING_STOP",
                                "beta_id": "BETA002",
                                "beta_version": "M1_EMA14_MOMENTUM_VOLATILITY",
                            },
                            beta_id="BETA002",
                            beta_version="M1_EMA14_MOMENTUM_VOLATILITY",
                            beta_mode="PROTECT_ONLY",
                            beta_reason="Pesquisa pesada selecionou BETA002.",
                            score=0.91,
                            lab_confidence=0.74,
                            status="APROVADO",
                            decision="BUY",
                        )
                    ],
                    source="MT5_RESEARCH_SNAPSHOT",
                )

        suggestions = SuggestionDashboardService().suggest_mt5_lab_setups()

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].pair, "EURJPY")
        self.assertEqual(suggestions[0].beta_id, "BETA005")
        self.assertEqual(
            suggestions[0].beta_version,
            "ATR_TRAILING_STOP_MANAGER",
        )

    def test_lab_pesado_expande_alphas_com_betas(self) -> None:
        service = DashboardService()

        expanded = service._mt5_expand_position_management_grid(
            [
                {
                    "alpha": "ALPHA007",
                    "modelo": "MACD_MOMENTUM_SHIFT",
                    "atr_stop_factor": "2.0",
                    "rr": "3.0",
                }
            ]
        )

        self.assertEqual(
            {item["beta_id"] for item in expanded},
            {
                "BETA003",
                "BETA004",
                "BETA005",
                "BETA006",
                "BETA007",
                "BETA008",
                "BETA009",
                "BETA010",
                "BETA011",
            },
        )

    def test_research_report_reprova_alpha_sem_confianca_minima(self) -> None:
        class ReportDashboardService(DashboardService):
            def _load_mt5_research_snapshot(self):
                return DashboardMT5HeuristicResearchViewModel(
                    scenario_ranking=[
                        DashboardMT5ScenarioViewModel(
                            pair="EURUSD",
                            timeframe="M15",
                            model="TREND_MOMENTUM",
                            score=0.71,
                            lab_confidence=0.5897,
                            status="APROVADO",
                            decision="SELL",
                        )
                    ],
                    source="MT5_RESEARCH_ALPHA001_SEARCH_SPACE_5000",
                )

        report = ReportDashboardService().get_mt5_alpha_research_report()

        self.assertEqual(report.status, "REPROVADA")
        self.assertEqual(report.tested_scenarios, 1)
        self.assertEqual(report.best_pair, "EURUSD")
        self.assertEqual(report.best_timeframe, "M15")
        self.assertIn("Nao atingiu confianca minima", report.failure_reasons[0])
        self.assertIn("Walk-forward por cenario", report.unavailable_evidence)

    def test_relatorio_mt5_confere_log_local_com_historico_da_plataforma(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "mt5_demo_execution.jsonl"
            log_path.write_text(
                json.dumps(
                    {
                        "timestamp": "2026-06-30T21:00:00-03:00",
                        "symbol": "EURUSD",
                        "side": "BUY",
                        "quantity": 0.1,
                        "entry_price": 1.1,
                        "stop": 1.0,
                        "target": 1.2,
                        "accepted": True,
                        "status": "ACCEPTED",
                        "message": "Request executed",
                        "ticket": 123,
                        "dynamic_exit_policy": "ATR_TRAILING_STOP",
                        "dynamic_exit_action": "TRAIL_BY_ATR",
                        "dynamic_exit_reason": "Tendencia forte permite trailing por ATR.",
                        "dynamic_exit_confidence": 0.65,
                        "dynamic_exit_market_state": "TREND_RUNNER",
                        "dynamic_exit_r_multiple": 1.25,
                        "dynamic_exit_candidate_stop": 1.122,
                        "dynamic_exit_allowed_to_execute_demo": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            class AuditDashboardService(DashboardService):
                def _read_mt5_demo_execution_jsonl(self):
                    return [
                        json.loads(line)
                        for line in log_path.read_text(encoding="utf-8").splitlines()
                    ]

                def _load_mt5_trade_history(self):
                    return (
                        {
                            123: {
                                "ticket": 123,
                                "source": "POSITION",
                                "symbol": "EURUSD",
                                "side": "BUY",
                                "volume": 0.1,
                                "price": 1.1,
                                "profit": 12.34,
                                "commission": -1.25,
                                "swap": -0.40,
                                "fee": -0.05,
                                "open_cost": -1.70,
                                "projected_open_cost": -0.75,
                                "time": "2026-07-01T00:00:00+00:00",
                            }
                        },
                        "CONNECTED",
                        "Historico MT5 carregado.",
                    )

            report = AuditDashboardService().get_mt5_trade_audit_report()

        self.assertEqual(report.total_local_records, 1)
        self.assertEqual(report.total_accepted_local, 1)
        self.assertEqual(report.total_matched, 1)
        self.assertEqual(report.rows[0].audit_status, "CONFERE")
        self.assertTrue(report.rows[0].mt5_found)
        self.assertEqual(report.rows[0].mt5_source, "POSITION")
        self.assertEqual(report.rows[0].operation_status, "ABERTA")
        self.assertAlmostEqual(report.rows[0].projected_profit, 1000.0)
        self.assertAlmostEqual(report.rows[0].projected_loss, -1000.0)
        self.assertAlmostEqual(report.rows[0].mt5_realized_profit, 12.34)
        self.assertAlmostEqual(report.rows[0].mt5_commission, -1.25)
        self.assertAlmostEqual(report.rows[0].mt5_swap, -0.40)
        self.assertAlmostEqual(report.rows[0].mt5_fee, -0.05)
        self.assertAlmostEqual(report.rows[0].mt5_open_cost, -1.70)
        self.assertAlmostEqual(report.rows[0].mt5_projected_open_cost, -0.75)
        self.assertEqual(report.rows[0].dynamic_exit_policy, "ATR_TRAILING_STOP")
        self.assertEqual(report.rows[0].dynamic_exit_action, "TRAIL_BY_ATR")
        self.assertEqual(report.rows[0].dynamic_exit_market_state, "TREND_RUNNER")
        self.assertAlmostEqual(report.rows[0].dynamic_exit_confidence, 0.65)
        self.assertAlmostEqual(report.rows[0].dynamic_exit_r_multiple, 1.25)
        self.assertAlmostEqual(report.rows[0].dynamic_exit_candidate_stop or 0.0, 1.122)
        self.assertEqual(report.rows[0].dynamic_exit_executed_action, "NONE")
        self.assertEqual(report.rows[0].dynamic_exit_final_result, "POSICAO_ABERTA")
        self.assertIs(report.rows[0].dynamic_exit_allowed_to_execute_demo, False)

    def test_relatorio_mt5_sinaliza_operacao_fechada_ou_historica(self) -> None:
        class HistoricalAuditDashboardService(DashboardService):
            def _read_mt5_demo_execution_jsonl(self):
                return [
                    {
                        "timestamp": "2026-06-30T21:00:00-03:00",
                        "symbol": "USDJPY",
                        "side": "SELL",
                        "quantity": 0.1,
                        "entry_price": 161.0,
                        "target": 160.0,
                        "accepted": True,
                        "status": "ACCEPTED",
                        "ticket": 456,
                    }
                ]

            def _load_mt5_trade_history(self):
                return (
                    {
                        456: {
                            "ticket": 456,
                            "source": "DEAL",
                            "symbol": "USDJPY",
                            "side": "SELL",
                            "volume": 0.1,
                            "price": 161.0,
                        }
                    },
                    "CONNECTED",
                    "Historico MT5 carregado.",
                )

        report = HistoricalAuditDashboardService().get_mt5_trade_audit_report()

        self.assertEqual(report.rows[0].mt5_source, "DEAL")
        self.assertEqual(report.rows[0].operation_status, "FECHADA/HISTORICO")

    def test_risco_aberto_usa_stop_atual_do_mt5(self) -> None:
        class CurrentStopAuditDashboardService(DashboardService):
            def _read_mt5_demo_execution_jsonl(self):
                return [
                    {
                        "timestamp": "2026-07-10T02:49:00-03:00",
                        "symbol": "EURUSD",
                        "side": "BUY",
                        "quantity": 0.1,
                        "entry_price": 1.1000,
                        "target": 1.1300,
                        "stop": 1.0900,
                        "accepted": True,
                        "status": "ACCEPTED",
                        "ticket": 7001,
                    }
                ]

            def _load_mt5_trade_history(self):
                return (
                    {
                        7001: {
                            "ticket": 7001,
                            "source": "POSITION",
                            "symbol": "EURUSD",
                            "side": "BUY",
                            "volume": 0.1,
                            "price": 1.1000,
                            "stop": 1.0980,
                            "profit": 0.0,
                            "time": "2026-07-10T02:49:00+00:00",
                        }
                    },
                    "CONNECTED",
                    "Historico MT5 carregado.",
                )

        report = CurrentStopAuditDashboardService().get_mt5_trade_audit_report()

        self.assertEqual(report.rows[0].operation_status, "ABERTA")
        self.assertAlmostEqual(report.rows[0].mt5_stop or 0.0, 1.0980)
        self.assertAlmostEqual(report.rows[0].projected_loss, -20.0)

    def test_relatorio_mt5_inclui_posicao_aberta_sem_ticket_local_casado(self) -> None:
        class OpenPositionAuditDashboardService(DashboardService):
            def _read_mt5_demo_execution_jsonl(self):
                return [
                    {
                        "timestamp": "2026-07-10T02:49:00-03:00",
                        "symbol": "NZDUSD",
                        "side": "BUY",
                        "quantity": 0.1,
                        "entry_price": 0.56863,
                        "target": 0.57030,
                        "stop": 0.56804,
                        "accepted": True,
                        "status": "ACCEPTED",
                        "ticket": 3387305,
                    }
                ]

            def _load_mt5_trade_history(self):
                return (
                    {
                        3387305: {
                            "ticket": 3387305,
                            "source": "POSITION",
                            "symbol": "NZDUSD",
                            "side": "BUY",
                            "volume": 0.1,
                            "price": 0.56863,
                            "profit": 19.20,
                            "time": "2026-07-10T02:49:00+00:00",
                        },
                        3379365: {
                            "ticket": 3379365,
                            "source": "POSITION",
                            "symbol": "AUDUSD",
                            "side": "BUY",
                            "volume": 0.1,
                            "price": 0.65720,
                            "profit": -1.40,
                            "time": "2026-07-09T05:56:00+00:00",
                        },
                    },
                    "CONNECTED",
                    "Historico MT5 carregado.",
                )

        report = OpenPositionAuditDashboardService().get_mt5_trade_audit_report()

        mt5_only = [row for row in report.rows if row.audit_status == "MT5_ONLY"]
        self.assertEqual(len(mt5_only), 1)
        self.assertEqual(mt5_only[0].symbol, "AUDUSD")
        self.assertEqual(mt5_only[0].operation_status, "ABERTA")
        self.assertEqual(mt5_only[0].local_ticket, None)
        self.assertAlmostEqual(mt5_only[0].mt5_realized_profit, -1.40)
        self.assertEqual(report.total_audited, 2)

    def test_relatorio_mt5_registra_motivo_saida_do_position_manager(self) -> None:
        class PositionManagerAuditDashboardService(DashboardService):
            def _read_mt5_demo_execution_jsonl(self):
                return [
                    {
                        "timestamp": "2026-07-08T17:00:00-03:00",
                        "symbol": "GBPUSD",
                        "side": "SELL",
                        "quantity": 0.1,
                        "entry_price": 1.33962,
                        "target": 1.33565,
                        "accepted": True,
                        "status": "ACCEPTED",
                        "ticket": 337770472,
                    }
                ]

            def _load_mt5_trade_history(self):
                return (
                    {
                        337770472: {
                            "ticket": 337770472,
                            "source": "DEAL",
                            "symbol": "GBPUSD",
                            "side": "SELL",
                            "volume": 0.1,
                            "price": 1.33944,
                            "profit": 1.2,
                            "time": "2026-07-08T17:28:00-03:00",
                        }
                    },
                    "CONNECTED",
                    "Historico MT5 carregado.",
                )

            def _read_position_manager_audit_index(self):
                return {
                    "ticket:337770472": {
                        "symbol": "GBPUSD",
                        "ticket": 337770472,
                        "action": "FULL_EXIT",
                        "status": "POSITION_CLOSED",
                        "final_exit_reason": "EARLY_EXIT_MOMENTUM_LOSS",
                        "message": "Saida antecipada confirmada dinamicamente.",
                    }
                }

        report = PositionManagerAuditDashboardService().get_mt5_trade_audit_report()

        self.assertEqual(report.rows[0].operation_status, "FECHADA/HISTORICO")
        self.assertIn("EARLY_EXIT_MOMENTUM_LOSS", report.rows[0].final_exit_reason)
        self.assertIn("FULL_EXIT", report.rows[0].final_exit_reason)
        self.assertIn(
            "Saida antecipada confirmada",
            report.rows[0].final_exit_reason,
        )

    def test_relatorio_mt5_converte_projecao_jpy_para_formato_monetario_mt5(
        self,
    ) -> None:
        service = DashboardService()
        record = {
            "symbol": "USDJPY",
            "side": "SELL",
            "quantity": 0.1,
            "entry_price": 160.0,
            "target": 159.0,
            "stop": 160.5,
        }

        profit = service._projected_profit_from_local_record(record)
        loss = service._projected_loss_from_local_record(record)

        self.assertAlmostEqual(profit, 62.5)
        self.assertAlmostEqual(loss, -31.15264797507788)

    def test_relatorio_mt5_agrega_lucro_realizado_por_position_id(self) -> None:
        class FakeMT5:
            def history_deals_get(self, start, end):
                return [
                    SimpleNamespace(
                        ticket=1001,
                        order=332514031,
                        time=1782872047,
                        type=1,
                        entry=0,
                        position_id=332514031,
                        volume=0.1,
                        price=1.14191,
                        profit=0.0,
                        symbol="EURUSD",
                    ),
                    SimpleNamespace(
                        ticket=1002,
                        order=332515293,
                        time=1782872354,
                        type=0,
                        entry=1,
                        position_id=332514031,
                        volume=0.1,
                        price=1.14190,
                        profit=0.1,
                        symbol="EURUSD",
                    ),
                ]

        history: dict[int, dict[str, object]] = {}
        service = DashboardService()

        service._merge_mt5_history_deals(
            FakeMT5(),
            datetime(2026, 6, 30),
            datetime(2026, 7, 1),
            history,
        )

        self.assertIn(332514031, history)
        self.assertEqual(history[332514031]["source"], "DEAL")
        self.assertEqual(history[332514031]["side"], "SELL")
        self.assertAlmostEqual(float(history[332514031]["profit"]), 0.1)

    def test_relatorio_mt5_mantem_historico_cacheado_quando_abertos_nao_mudam(
        self,
    ) -> None:
        service = DashboardService()
        object.__setattr__(service, "mt5_trade_open_ticket_cache", {10, 20})

        refresh = service._should_refresh_mt5_trade_history(
            accepted_tickets={10, 20, 30},
            current_tickets={10, 20},
            cached_history={30: {"ticket": 30, "source": "DEAL"}},
        )

        self.assertFalse(refresh)

    def test_relatorio_mt5_atualiza_historico_quando_operacao_sai_de_aberta(
        self,
    ) -> None:
        service = DashboardService()
        object.__setattr__(service, "mt5_trade_open_ticket_cache", {10, 20})

        refresh = service._should_refresh_mt5_trade_history(
            accepted_tickets={10, 20},
            current_tickets={10},
            cached_history={30: {"ticket": 30, "source": "DEAL"}},
        )

        self.assertTrue(refresh)

    def test_relatorio_mt5_atualiza_historico_quando_ticket_nao_esta_resolvido(
        self,
    ) -> None:
        service = DashboardService()
        object.__setattr__(service, "mt5_trade_open_ticket_cache", {10})

        refresh = service._should_refresh_mt5_trade_history(
            accepted_tickets={10, 40},
            current_tickets={10},
            cached_history={30: {"ticket": 30, "source": "DEAL"}},
        )

        self.assertTrue(refresh)

    def test_relatorio_mt5_consulta_historico_com_margem_de_horario_do_servidor(
        self,
    ) -> None:
        service = DashboardService()

        start, end = service._mt5_trade_history_query_window()

        self.assertEqual(start, datetime(2000, 1, 1))
        self.assertGreaterEqual(end, datetime.now())
        self.assertGreater((end - datetime.now()).total_seconds(), 23 * 60 * 60)

    def test_relatorio_mt5_ordena_negociacoes_mais_recentes_primeiro(self) -> None:
        class OrderedAuditDashboardService(DashboardService):
            def _read_mt5_demo_execution_jsonl(self):
                return [
                    {
                        "timestamp": "2026-06-30T10:00:00-03:00",
                        "symbol": "EURUSD",
                        "side": "BUY",
                        "quantity": 0.1,
                        "entry_price": 1.1,
                        "target": 1.2,
                        "accepted": True,
                        "status": "ACCEPTED",
                        "ticket": 1,
                    },
                    {
                        "timestamp": "2026-06-30T11:00:00-03:00",
                        "symbol": "GBPUSD",
                        "side": "SELL",
                        "quantity": 0.1,
                        "entry_price": 1.3,
                        "target": 1.2,
                        "accepted": True,
                        "status": "ACCEPTED",
                        "ticket": 2,
                    },
                ]

            def _load_mt5_trade_history(self):
                return (
                    {
                        1: {
                            "ticket": 1,
                            "source": "DEAL",
                            "symbol": "EURUSD",
                            "side": "BUY",
                            "volume": 0.1,
                            "price": 1.1,
                        },
                        2: {
                            "ticket": 2,
                            "source": "DEAL",
                            "symbol": "GBPUSD",
                            "side": "SELL",
                            "volume": 0.1,
                            "price": 1.3,
                        },
                    },
                    "CONNECTED",
                    "Historico MT5 carregado.",
                )

        report = OrderedAuditDashboardService().get_mt5_trade_audit_report()

        self.assertEqual([row.local_ticket for row in report.rows], [2, 1])

    def test_dashboard_service_recarrega_ultimo_historico_mt5_persistido(self) -> None:
        """Historico MT5 nao deve voltar para zero apos recriar o service."""
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / "mt5_research_snapshot.json"

            class SnapshotDashboardService(DashboardService):
                def _mt5_research_snapshot_path(self) -> Path:
                    return snapshot_path

            saved = DashboardMT5HeuristicResearchViewModel(
                rows=[
                    DashboardMT5HeuristicResearchRowViewModel(
                        pair="EURUSD",
                        timeframe="M1",
                        recommended_heuristic="TREND_MOMENTUM",
                        decision="BUY",
                        score=0.88,
                        confidence=0.77,
                        status="APROVADO",
                    )
                ],
                scenario_ranking=[
                    DashboardMT5ScenarioViewModel(
                        pair="EURUSD",
                        timeframe="M1",
                        model="TREND_MOMENTUM",
                        parameters={"rr": "2.0"},
                        score=0.88,
                        lab_confidence=0.77,
                        lab_confidence_sample_size=150,
                        lab_confidence_source="SCENARIO_ALPHA_BACKTEST_SAMPLE",
                        status="APROVADO",
                        decision="BUY",
                    )
                ],
                best_scenarios_by_market=[
                    DashboardMT5ScenarioViewModel(
                        pair="EURUSD",
                        timeframe="M1",
                        model="TREND_MOMENTUM",
                        parameters={"rr": "2.0"},
                        score=0.88,
                        lab_confidence=0.77,
                        lab_confidence_sample_size=150,
                        lab_confidence_source="SCENARIO_ALPHA_BACKTEST_SAMPLE",
                        status="APROVADO",
                        decision="BUY",
                    )
                ],
                best_scenario=DashboardMT5ScenarioViewModel(
                    pair="EURUSD",
                    timeframe="M1",
                    model="TREND_MOMENTUM",
                    parameters={"rr": "2.0"},
                    score=0.88,
                    lab_confidence=0.77,
                    lab_confidence_sample_size=150,
                    lab_confidence_source="SCENARIO_ALPHA_BACKTEST_SAMPLE",
                    status="APROVADO",
                    decision="BUY",
                ),
                best_pair="EURUSD",
                best_heuristic="TREND_MOMENTUM",
                best_score=0.88,
                best_decision="BUY",
                best_confidence=0.77,
                status="RESEARCH_ONLY",
                last_update="2026-06-30T21:00:00+00:00",
                candles_loaded=40000,
                timeframe="M1",
                source="MT5_RESEARCH_SNAPSHOT_5000",
            )
            writer = SnapshotDashboardService()
            writer._save_mt5_research_snapshot(saved)

            reader = SnapshotDashboardService()

            self.assertEqual(reader.mt5_research_constants.candles_loaded, 40000)
            self.assertEqual(reader.mt5_research_constants.best_pair, "EURUSD")
            self.assertEqual(reader.mt5_research_constants.rows[0].pair, "EURUSD")
            self.assertEqual(
                reader.mt5_research_constants.best_scenario.model,
                "TREND_MOMENTUM",
            )
            self.assertEqual(
                reader.mt5_research_constants.scenario_ranking[0].parameters["rr"],
                "2.0",
            )

    def test_snapshot_rows_leve_nao_bloqueia_relatorio_completo_do_lab(self) -> None:
        """Resumo leve de rows nao deve impedir ranking/sugestoes do Lab."""
        with tempfile.TemporaryDirectory() as directory:
            snapshot_path = Path(directory) / "mt5_research_snapshot.json"

            class SnapshotDashboardService(DashboardService):
                def _should_preload_mt5_research_snapshot(self) -> bool:
                    return False

                def _mt5_research_snapshot_path(self) -> Path:
                    return snapshot_path

            saved = DashboardMT5HeuristicResearchViewModel(
                rows=[
                    DashboardMT5HeuristicResearchRowViewModel(
                        pair="EURUSD",
                        timeframe="M1",
                        recommended_heuristic="TREND_MOMENTUM",
                        decision="BUY",
                        score=0.88,
                        confidence=0.77,
                        status="APROVADO",
                    )
                ],
                scenario_ranking=[
                    DashboardMT5ScenarioViewModel(
                        alpha_id="ALPHA002",
                        pair="EURUSD",
                        timeframe="M1",
                        model="TREND_MOMENTUM",
                        parameters={"rr": "2.0"},
                        score=0.88,
                        lab_confidence=0.77,
                        lab_confidence_sample_size=150,
                        lab_confidence_source="SCENARIO_ALPHA_BACKTEST_SAMPLE",
                        status="APROVADO",
                        decision="BUY",
                    )
                ],
                best_pair="EURUSD",
                best_heuristic="TREND_MOMENTUM",
                best_score=0.88,
                best_decision="BUY",
                best_confidence=0.77,
                status="RESEARCH_ONLY",
                last_update="2026-07-06T20:58:38+00:00",
                candles_loaded=40000,
                timeframe="M1",
                source="MT5_RESEARCH_ALPHA_LIBRARY_SEARCH_SPACE_5000",
            )
            writer = SnapshotDashboardService()
            writer._save_mt5_research_snapshot(saved)

            reader = SnapshotDashboardService()
            lightweight = reader.get_mt5_research_constants()
            ranking = reader.get_mt5_alpha_research_ranking()

            self.assertEqual(lightweight.source, "MT5_RESEARCH_RUNTIME_INDEX")
            self.assertEqual(lightweight.rows[0].pair, "EURUSD")
            self.assertEqual(ranking[0].alpha_id, "ALPHA002")
            self.assertEqual(ranking[0].best_confidence, 0.77)

    def test_dashboard_app_consumindo_view_model_pela_fachada(self) -> None:
        source = read_source(Path("dashboard_app.py"))

        self.assertIn("get_dashboard_view_model_or_stop(service)", source)
        self.assertIn("exibir_dashboard_layout(service, data)", source)
        self.assertIn("exibir_mt5_market_data(service, data)", source)
        self.assertIn("exibir_mt5_forex_dashboard(service, data)", source)
        self.assertIn("get_dashboard_view_model", source)
        self.assertNotIn("infrastructure", source)

    def test_format_dashboard_timestamp_converte_utc_para_brasil(self) -> None:
        formatted = format_dashboard_timestamp("2026-06-29T21:00:00+00:00")

        self.assertEqual(formatted, "29/06/2026 18:00")

    def test_format_dashboard_timestamp_converte_texto_mt5_para_brasil(self) -> None:
        formatted = format_dashboard_timestamp("29/06/2026 18:00")

        self.assertEqual(formatted, "29/06/2026 15:00")

    def test_dashboard_app_possui_fallback_para_view_model_ausente(self) -> None:
        source = read_source(Path("dashboard_app.py"))

        self.assertIn("get_dashboard_view_model_or_stop(service)", source)
        self.assertIn("Erro arquitetural", source)
        self.assertIn("st.stop()", source)

    def test_live_tab_nao_usa_compatibility_data_ou_dto_legado(self) -> None:
        source = read_source(Path("dashboard_app.py"))
        live_start = source.index("def exibir_live_research_read_only")
        live_end = source.index("def _format_percent")
        live_source = source[live_start:live_end]

        self.assertIn("live_research_status", live_source)
        self.assertIn("live_session_summary", live_source)
        self.assertIn("live_signal_quality", live_source)
        self.assertIn("live_history", live_source)
        self.assertIn("safety_status", live_source)
        self.assertNotIn("compatibility_data", live_source)
        self.assertNotIn("live_research_data", live_source)
        self.assertNotIn("live_experiment_signals", live_source)
        self.assertNotIn("live_experiment_summary", live_source)

    def test_dashboard_app_nao_acessa_operacao_proibida(self) -> None:
        source = read_source(Path("dashboard_app.py"))
        forbidden_fragments = (
            "infrastructure",
            "Broker",
            "order_send",
            "positions_get",
            "orders_get",
            "open_positions",
            "ordens_abertas",
        )

        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)

    def test_mt5_forex_aplica_modelo_ativo_trend_momentum(self) -> None:
        service = DashboardService()
        row = self._forex_row(
            trend="ALTA",
            momentum=0.01,
            rsi=75.0,
            short_average=1.2,
            long_average=1.1,
        )

        view_row = service._to_view_model_mt5_forex_signal_row(
            row,
            "TREND_MOMENTUM",
        )

        self.assertEqual(view_row.active_model, "TREND_MOMENTUM")
        self.assertEqual(view_row.decision, "WAIT")
        self.assertEqual(view_row.theoretical_entry_status, "FORA_DA_ZONA_DE_INTERESSE")
        self.assertIn("Tendencia=", view_row.active_model_indicators[0])

    def test_mt5_forex_aplica_modelo_ativo_ma_rsi_filter(self) -> None:
        service = DashboardService()
        row = self._forex_row(
            trend="ALTA",
            momentum=0.01,
            rsi=55.0,
            short_average=1.2,
            long_average=1.1,
        )

        view_row = service._to_view_model_mt5_forex_signal_row(
            row,
            "MA_RSI_FILTER",
        )

        self.assertEqual(view_row.active_model, "MA_RSI_FILTER")
        self.assertEqual(view_row.decision, "SELL")
        self.assertIn("RSI=", " ".join(view_row.active_model_indicators))

    def test_mt5_forex_aplica_modelo_ativo_rsi_reversal(self) -> None:
        service = DashboardService()
        row = self._forex_row(
            pair="UNITTEST",
            trend="ALTA",
            momentum=0.01,
            rsi=25.0,
            short_average=1.2,
            long_average=1.1,
        )

        view_row = service._to_view_model_mt5_forex_signal_row(
            row,
            "RSI_REVERSAL",
        )

        self.assertEqual(view_row.active_model, "RSI_REVERSAL")
        self.assertEqual(view_row.decision, "BUY")
        self.assertEqual(view_row.theoretical_entry_status, "SEM_DADOS")
        self.assertTrue(view_row.active_model_indicators[0].startswith("RSI="))

    def test_mt5_forex_usa_modelo_recomendado_por_par_e_timeframe(
        self,
    ) -> None:
        service = DashboardService()
        research = DashboardMT5HeuristicResearchViewModel(
            rows=[
                DashboardMT5HeuristicResearchRowViewModel(
                    pair="EURUSD",
                    timeframe="H1",
                    recommended_heuristic="TREND_MOMENTUM",
                ),
                DashboardMT5HeuristicResearchRowViewModel(
                    pair="NZDUSD",
                    timeframe="H1",
                    recommended_heuristic="TREND_PULLBACK",
                    ideal_timeframe="H1",
                    final_configuration={
                        "alpha": "ALPHA002",
                        "modelo": "TREND_PULLBACK",
                        "timeframe": "H1",
                        "ema_curta": "20",
                        "ema_longa": "50",
                        "rsi_sobrevenda": "35.0",
                        "rsi_sobrecompra": "65.0",
                        "atr_stop_factor": "2.0",
                        "rr": "3.0",
                    },
                    reason="Cruzamento de medias com RSI em zona operacional.",
                ),
            ],
            best_pair="EURUSD",
            best_heuristic="TREND_MOMENTUM",
        )
        active_models = service._active_mt5_research_models_by_market(research)
        active_rows = service._active_mt5_research_rows_by_market(research)
        nzdusd = self._forex_row(
            pair="NZDUSD",
            timeframe="H1",
            trend="ALTA",
            momentum=-0.01,
            rsi=56.0,
            short_average=0.565,
            long_average=0.564,
        )

        active_model = service._active_mt5_research_model_for_row(
            nzdusd,
            active_models,
            research,
        )
        view_row = service._to_view_model_mt5_forex_signal_row(
            nzdusd,
            active_model,
            service._active_mt5_research_row_for_source_row(nzdusd, active_rows),
        )

        self.assertEqual(active_model, "TREND_PULLBACK")
        self.assertEqual(view_row.active_model, "TREND_PULLBACK")
        self.assertEqual(view_row.lab_alpha_id, "ALPHA002")
        self.assertEqual(view_row.lab_timeframe, "H1")
        self.assertEqual(view_row.lab_configuration_source, "RESEARCH_LAB")
        self.assertEqual(view_row.lab_parameters["ema_curta"], "20")
        self.assertEqual(view_row.lab_parameters["rr"], "3.0")
        self.assertIn("TREND_PULLBACK", view_row.reason)
        self.assertIn("ema_curta=20", " ".join(view_row.active_model_indicators))

    def test_mt5_forex_usa_timeframe_do_lab_sem_pesquisa_pesada(self) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._flat_then_breakout_candles()
        )
        row = self._forex_row(
            pair="EURUSD",
            timeframe="M1",
            trend="BAIXA",
            momentum=-0.01,
            rsi=45.0,
            short_average=1.0,
            long_average=1.1,
            last_candle_time="2026-06-29T10:00:00+00:00",
        )

        view_row = service._to_view_model_mt5_forex_signal_row(
            row,
            "TREND_MOMENTUM",
            DashboardMT5HeuristicResearchRowViewModel(
                pair="EURUSD",
                timeframe="H1",
                ideal_timeframe="H1",
                recommended_heuristic="TREND_MOMENTUM",
                confidence=0.61,
                ict_score=82.0,
                ict_grade="A",
                ict_status="CERTIFICADA_A",
                ict_usage="Operacao automatica Demo liberada.",
                ict_demo_allowed=True,
                status="APROVADO",
                final_configuration={
                    "alpha": "ALPHA001",
                    "modelo": "TREND_MOMENTUM",
                    "timeframe": "H1",
                    "ema_curta": "20",
                    "ema_longa": "50",
                    "atr_stop_factor": "2.0",
                    "rr": "2.0",
                    "stop_management": "ATR_TRAILING_STOP",
                    "atr_trailing_factor": "2.0",
                    "atr_trailing_activation_rr": "1.0",
                    "momentum_threshold": "0.0",
                    "volatility_threshold": "0.0001",
                },
            ),
        )

        self.assertEqual(view_row.lab_timeframe, "H1")
        self.assertEqual(view_row.timeframe, "H1")
        self.assertEqual(view_row.decision, "BUY")
        self.assertEqual(view_row.lab_confidence, 0.61)
        self.assertEqual(view_row.theoretical_entry_status, "FORA_DA_ZONA_DE_INTERESSE")
        self.assertEqual(view_row.research_plan_status, "SEM_GATILHO_VALIDO")

    def test_refresh_forex_usa_mapa_de_timeframes_do_lab(self) -> None:
        service = DashboardService()
        object.__setattr__(
            service,
            "mt5_research_constants",
            DashboardMT5HeuristicResearchViewModel(
                rows=[
                    DashboardMT5HeuristicResearchRowViewModel(
                        pair="EURUSD",
                        timeframe="M15",
                        ideal_timeframe="M15",
                    ),
                    DashboardMT5HeuristicResearchRowViewModel(
                        pair="USDJPY",
                        timeframe="H1",
                        ideal_timeframe="H1",
                    ),
                ]
            ),
        )
        calls: list[tuple[dict[str, str], str]] = []

        def load_by_map(timeframes_by_pair, fallback_timeframe="M1"):
            calls.append((dict(timeframes_by_pair), fallback_timeframe))
            return MT5ForexSignalDashboard(timeframe=fallback_timeframe, pairs=[])

        service.mt5_market_data_service.load_forex_signal_dashboard_for_timeframes = (
            load_by_map
        )

        service.load_mt5_forex_signals(timeframe="M1")

        self.assertEqual(
            calls,
            [({"EURUSD": "M15", "USDJPY": "H1"}, "M1")],
        )

    def test_lab_multi_timeframe_nao_forca_tudo_em_m1(self) -> None:
        service = DashboardService()
        configuration = service.configuration_service.get_configuration_data()

        timeframes = service._mt5_research_timeframes(configuration, "MULTI")

        self.assertIn("M1", timeframes)
        self.assertIn("M5", timeframes)
        self.assertIn("M15", timeframes)
        self.assertIn("M30", timeframes)
        self.assertIn("H1", timeframes)
        self.assertGreater(len(set(timeframes)), 1)

    def test_mt5_forex_marca_entrada_teorica_em_zona_de_interesse(
        self,
    ) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._flat_then_breakout_candles()
        )
        row = self._forex_row(
            trend="ALTA",
            momentum=0.01,
            rsi=55.0,
            short_average=1.02,
            long_average=1.01,
        )

        view_row = service._to_view_model_mt5_forex_signal_row(
            row,
            "TREND_MOMENTUM",
            DashboardMT5HeuristicResearchRowViewModel(
                pair="EURUSD",
                timeframe="H1",
                recommended_heuristic="TREND_MOMENTUM",
                decision="BUY",
                score=0.80,
                confidence=0.72,
                ict_score=82.0,
                ict_grade="A",
                ict_status="CERTIFICADA_A",
                ict_usage="Operacao automatica Demo liberada.",
                ict_demo_allowed=True,
                status="APROVADO",
                final_configuration={
                    "alpha": "ALPHA001",
                    "modelo": "TREND_MOMENTUM",
                    "timeframe": "H1",
                    "ema_curta": "20",
                    "ema_longa": "50",
                    "rsi_sobrevenda": "30.0",
                    "rsi_sobrecompra": "70.0",
                    "atr_stop_factor": "2.0",
                    "rr": "2.0",
                    "stop_management": "ATR_TRAILING_STOP",
                    "atr_trailing_factor": "2.0",
                    "atr_trailing_activation_rr": "1.0",
                    "momentum_threshold": "0.0",
                    "volatility_threshold": "0.0001",
                },
            ),
        )

        self.assertNotEqual(view_row.last_candle_time, "N/D")
        self.assertEqual(view_row.research_plan_source, "RESEARCH_LAB")
        if view_row.theoretical_entry_status == "SINAL_TEORICO":
            self.assertIn(view_row.theoretical_entry_direction, {"BUY", "SELL"})
            self.assertNotEqual(view_row.theoretical_entry_candle, "N/D")
            self.assertIsNotNone(view_row.theoretical_entry_price)
            self.assertEqual(view_row.research_plan_status, "PLANO_VALIDO")
            self.assertEqual(
                view_row.research_plan_exit_model,
                "INITIAL_RISK_PLAN",
            )
            self.assertEqual(view_row.research_plan_exit_score, 0.0)
            self.assertIsNotNone(view_row.research_plan_stop)
            self.assertIsNotNone(view_row.research_plan_target)
        else:
            self.assertEqual(
                view_row.theoretical_entry_status,
                "FORA_DA_ZONA_DE_INTERESSE",
            )
            self.assertEqual(view_row.theoretical_entry_direction, "WAIT")
            self.assertEqual(view_row.theoretical_entry_candle, "N/D")
            self.assertIsNone(view_row.theoretical_entry_price)
            self.assertIn("zona de interesse", view_row.theoretical_entry_reason)
            self.assertEqual(view_row.research_plan_status, "SEM_GATILHO_VALIDO")
            self.assertEqual(view_row.research_plan_exit_model, "NONE")
            self.assertEqual(view_row.research_plan_exit_score, 0.0)
            self.assertIsNone(view_row.research_plan_stop)
            self.assertIsNone(view_row.research_plan_target)
            self.assertEqual(view_row.research_plan_risk_pips, 0.0)
            self.assertEqual(view_row.research_plan_reward_pips, 0.0)
            self.assertEqual(view_row.research_plan_risk_percent, 0.0)
            self.assertEqual(view_row.research_plan_reward_percent, 0.0)
            self.assertIn("Stop ausente", view_row.research_plan_stop_reason)
            self.assertIn("Alvo ausente", view_row.research_plan_target_reason)
        self.assertEqual(view_row.research_plan_stop_management, "ATR_TRAILING_STOP")
        self.assertEqual(
            view_row.research_plan_stop_management_parameters,
            {
                "atr_trailing_factor": "2.0",
                "atr_trailing_activation_rr": "1.0",
            },
        )

    def test_mt5_forex_mantem_entrada_quando_regime_continua_autorizado(
        self,
    ) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._uptrend_candles()
        )
        row = self._forex_row(
            trend="ALTA",
            momentum=0.01,
            rsi=55.0,
            short_average=1.02,
            long_average=1.01,
        )

        view_row = service._to_view_model_mt5_forex_signal_row(
            row,
            "TREND_MOMENTUM",
        )

        self.assertEqual(view_row.theoretical_entry_status, "SINAL_TEORICO")
        self.assertEqual(view_row.theoretical_entry_direction, "BUY")

    def test_research_lab_cenario_recebe_contexto_temporal_favoravel(self) -> None:
        service = DashboardService()
        row = self._forex_row(
            pair="EURUSD",
            timeframe="M15",
            trend="ALTA",
            momentum=0.001,
            rsi=55.0,
            short_average=1.02,
            long_average=1.01,
            last_candle_time="2026-07-01T14:30:00+00:00",
        )

        scenario = service._mt5_scenario_for_parameters(
            row,
            "TREND_MOMENTUM",
            {
                "alpha": "ALPHA001",
                "modelo": "TREND_MOMENTUM",
                "ema_curta": 20,
                "ema_longa": 50,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 2.0,
                "rr": 3.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
            },
        )

        self.assertEqual(scenario.temporal_session, "LONDON_NEW_YORK_OVERLAP")
        self.assertEqual(scenario.temporal_status, "SESSAO_FAVORAVEL")
        self.assertFalse(scenario.temporal_blocked)
        self.assertGreater(scenario.temporal_score_adjustment, 0.0)
        self.assertEqual(scenario.temporal_window_brt, "11:00-12:00")
        self.assertIn("Tempo:", scenario.reason)

    def test_research_lab_cenario_bloqueia_rollover(self) -> None:
        service = DashboardService()
        service.update_configuration(forex_session_filter_enabled=True)
        row = self._forex_row(
            pair="EURUSD",
            timeframe="M15",
            trend="ALTA",
            momentum=0.001,
            rsi=55.0,
            short_average=1.02,
            long_average=1.01,
            last_candle_time="2026-07-01T21:30:00+00:00",
        )

        scenario = service._mt5_scenario_for_parameters(
            row,
            "TREND_MOMENTUM",
            {
                "alpha": "ALPHA001",
                "modelo": "TREND_MOMENTUM",
                "ema_curta": 20,
                "ema_longa": 50,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 2.0,
                "rr": 3.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
            },
        )

        self.assertEqual(scenario.temporal_status, "ROLLOVER_BLOQUEADO")
        self.assertTrue(scenario.temporal_blocked)
        self.assertEqual(scenario.status, "REJEITADO")
        self.assertEqual(scenario.decision, "WAIT")
        self.assertEqual(scenario.score, 0.0)

    def test_research_lab_cenario_ignora_rollover_quando_filtro_desligado(
        self,
    ) -> None:
        service = DashboardService()
        service.update_configuration(forex_session_filter_enabled=False)
        row = self._forex_row(
            pair="EURUSD",
            timeframe="M15",
            trend="ALTA",
            momentum=0.001,
            rsi=55.0,
            short_average=1.02,
            long_average=1.01,
            last_candle_time="2026-07-01T21:30:00+00:00",
        )

        scenario = service._mt5_scenario_for_parameters(
            row,
            "TREND_MOMENTUM",
            {
                "alpha": "ALPHA001",
                "modelo": "TREND_MOMENTUM",
                "ema_curta": 20,
                "ema_longa": 50,
                "rsi_sobrevenda": 30.0,
                "rsi_sobrecompra": 70.0,
                "atr_stop_factor": 2.0,
                "rr": 3.0,
                "momentum_threshold": 0.0,
                "volatility_threshold": 0.0001,
            },
        )

        self.assertEqual(scenario.temporal_status, "ROLLOVER_BLOQUEADO")
        self.assertFalse(scenario.temporal_blocked)
        self.assertEqual(scenario.decision, "BUY")
        self.assertGreater(scenario.score, 0.0)
        self.assertIn("Filtro de sessao ignorado", scenario.reason)
        self.assertEqual(scenario.temporal_score_adjustment, 0.0)

    def test_research_lab_prioriza_evento_pos_rollover_antes_das_alphas(
        self,
    ) -> None:
        class PostRolloverDashboardService(DashboardService):
            def _mt5_server_timestamp(self, symbol: str = "EURUSD") -> str:
                return "2026-07-09T00:12:00+00:00"

        service = PostRolloverDashboardService()
        row = self._forex_row(
            pair="EURUSD",
            timeframe="M1",
            trend="ALTA",
            momentum=0.001,
            rsi=55.0,
            short_average=1.02,
            long_average=1.01,
            last_candle_time="2026-07-09T00:12:00+00:00",
        )
        row.atr = 0.0008
        row.volatility = 0.0004
        row.spread = 0.0001
        row.spread_average = 0.0001
        row.last_price = 1.1000
        row.theoretical_entry_price = 1.1000
        row.tick_volume = 80

        scenarios = service._mt5_research_scenario_ranking(
            [row],
            service.configuration_service.get_configuration_data(),
        )

        self.assertEqual(scenarios[0].alpha_id, "EVENT_POST_ROLLOVER_DAILY_OPEN")
        self.assertEqual(scenarios[0].model, "POST_ROLLOVER_DAILY_OPEN")
        self.assertEqual(scenarios[0].status, "APROVADO")
        self.assertEqual(scenarios[0].decision, "BUY")
        self.assertEqual(
            scenarios[0].parameters["event_mode"],
            "POST_ROLLOVER_TRADE_READY",
        )

    def test_dashboard_service_entrega_filtro_de_sessao_ignorado_ao_robo(
        self,
    ) -> None:
        service = DashboardService()
        service.update_configuration(forex_session_filter_enabled=False)
        time_context = service.forex_time_layer.classify(
            "EURUSD",
            "2026-07-01T21:30:00+00:00",
        )

        signal = service._mt5_demo_signal_from_view_row(
            DashboardMT5ForexSignalRowViewModel(
                pair="EURUSD",
                timeframe="H1",
                last_price=1.1,
                trend="ALTA",
                momentum=0.001,
                short_average=1.101,
                long_average=1.099,
                decision="BUY",
                confidence=0.72,
            ),
            candle_time="2026-07-01T21:30:00+00:00",
            time_context=time_context,
        )

        self.assertFalse(signal.session_filter_enabled)
        self.assertEqual(signal.session_filter_result, "IGNORED")
        self.assertFalse(signal.temporal_blocked)
        self.assertIn("Rollover", signal.forex_session)
        self.assertTrue(signal.is_rollover)

    def test_trade_plan_usa_parametros_do_cenario_vencedor_do_lab(self) -> None:
        service = DashboardService()

        plan = service._mt5_research_trade_plan_for_view_row(
            DashboardMT5ForexSignalRowViewModel(
                pair="EURUSD",
                timeframe="H1",
                lab_timeframe="H1",
                active_model="TREND_MOMENTUM",
                decision="BUY",
                theoretical_entry_status="SINAL_TEORICO",
                theoretical_entry_price=1.1000,
                theoretical_entry_reason="gatilho teorico",
                atr=0.0010,
                lab_parameters={
                    "atr_stop_factor": "2.5",
                    "rr": "3.0",
                },
            )
        )

        self.assertEqual(plan.status, "PLANO_VALIDO")
        self.assertEqual(plan.stop_multiplier, 2.5)
        self.assertEqual(plan.risk_reward, 3.0)
        self.assertAlmostEqual(plan.stop or 0.0, 1.0975)
        self.assertAlmostEqual(plan.target or 0.0, 1.1075)

    def test_trade_plan_modelo1_deriva_beta_saida_do_lab(self) -> None:
        service = DashboardService()

        plan = service._mt5_research_trade_plan_for_view_row(
            DashboardMT5ForexSignalRowViewModel(
                pair="EURUSD",
                timeframe="M1",
                lab_timeframe="M1",
                active_model="TREND_MOMENTUM",
                decision="BUY",
                theoretical_entry_status="SINAL_TEORICO",
                theoretical_entry_price=1.1000,
                theoretical_entry_reason="gatilho teorico",
                atr=0.0010,
                beta_id="BETA002",
                beta_version="M1_EMA14_MOMENTUM_VOLATILITY",
                beta_mode="ADAPTIVE_FULL_EXIT",
                lab_parameters={
                    "atr_stop_factor": "2.0",
                    "rr": "2.0",
                    "stop_management": "ATR_TRAILING_STOP",
                    "beta_id": "BETA002",
                    "beta_version": "M1_EMA14_MOMENTUM_VOLATILITY",
                    "beta_mode": "ADAPTIVE_FULL_EXIT",
                },
            )
        )

        self.assertEqual(plan.beta_id, "BETA005")
        self.assertEqual(plan.beta_version, "ATR_TRAILING_STOP_MANAGER")
        self.assertEqual(plan.beta_mode, "ATR_TRAILING_ONLY")

    def test_exportador_visual_mt5_gera_json_read_only(self) -> None:
        exporter = MT5VisualSignalExporter()
        exporter._open_positions_by_symbol = lambda: {}
        forex = DashboardMT5ForexSignalViewModel(
            timeframe="H1",
            pairs=[
                DashboardMT5ForexSignalRowViewModel(
                    pair="EURUSD",
                    timeframe="H1",
                    last_candle_time="29/06/2026 18:00",
                    decision="BUY",
                    confidence=0.91,
                    active_model="TREND_MOMENTUM",
                    active_model_score=87.0,
                    active_model_indicators=("EMA20>EMA50", "ADX>25"),
                    lab_alpha_id="ALPHA001",
                    lab_timeframe="M15",
                    lab_configuration_source="RESEARCH_LAB",
                    lab_parameters={
                        "alpha": "ALPHA001",
                        "modelo": "TREND_MOMENTUM",
                        "timeframe": "M15",
                        "ema_curta": "20",
                        "ema_longa": "50",
                        "rsi_sobrevenda": "30.0",
                        "rsi_sobrecompra": "70.0",
                        "atr_stop_factor": "2.0",
                        "rr": "3.0",
                        "stop_management": "ATR_TRAILING_STOP",
                        "atr_trailing_factor": "2.0",
                        "atr_trailing_activation_rr": "1.0",
                        "momentum_threshold": "0.0005",
                        "volatility_threshold": "0.0003",
                    },
                    trend="ALTA",
                    momentum=0.001,
                    volatility=0.0004,
                    rsi=58.0,
                    short_average=1.1410,
                    long_average=1.1390,
                    adx=28.0,
                    atr=0.0012,
                    tick_volume=120,
                    theoretical_entry_status="SINAL_TEORICO",
                    theoretical_entry_candle="29/06/2026 18:00",
                    theoretical_entry_price=1.1422,
                    theoretical_entry_direction="BUY",
                    research_plan_status="PLANO_VALIDO",
                    research_plan_entry_price=1.1422,
                    research_plan_stop=1.1402,
                    research_plan_target=1.1482,
                    research_plan_risk_reward=3.0,
                    research_plan_risk_pips=20.0,
                    research_plan_reward_pips=60.0,
                    research_plan_risk_percent=0.1751,
                    research_plan_reward_percent=0.5253,
                    research_plan_exit_model="ATR_RR_RESEARCH_SELECTION",
                    research_plan_stop_reason="Stop por ATR.",
                    research_plan_target_reason="Alvo por RR.",
                    research_plan_stop_management="ATR_TRAILING_STOP",
                    research_plan_stop_management_parameters={
                        "atr_trailing_factor": "2.0",
                        "atr_trailing_activation_rr": "1.0",
                    },
                    research_plan_stop_management_reason="Gestao pelo Lab.",
                    research_plan_reason="Plano visual pronto.",
                    research_plan_diagnostics=("RR_VALIDO",),
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "traderia_signals.json"
            result = exporter.export(forex, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        signal = payload["signals"][0]
        self.assertEqual(result.total_signals, 1)
        self.assertEqual(payload["mode"], "VISUAL_ONLY")
        self.assertTrue(payload["read_only"])
        self.assertEqual(signal["symbol"], "EURUSD")
        self.assertEqual(signal["timeframe"], "M15")
        self.assertEqual(signal["mt5_source_timeframe"], "H1")
        self.assertEqual(signal["decision"], "BUY")
        self.assertEqual(signal["entry"], 1.1422)
        self.assertEqual(signal["stop"], 1.1402)
        self.assertEqual(signal["target"], 1.1482)
        self.assertEqual(signal["rr"], 3.0)
        self.assertEqual(signal["risk_pips"], 20.0)
        self.assertEqual(signal["reward_pips"], 60.0)
        self.assertEqual(signal["risk_percent"], 0.1751)
        self.assertEqual(signal["reward_percent"], 0.5253)
        self.assertEqual(signal["stop_reason"], "Stop por ATR.")
        self.assertEqual(signal["target_reason"], "Alvo por RR.")
        self.assertEqual(signal["stop_management"], "ATR_TRAILING_STOP")
        self.assertEqual(
            signal["stop_management_parameters"]["atr_trailing_factor"],
            "2.0",
        )
        self.assertEqual(signal["stop_management_reason"], "Gestao pelo Lab.")
        expected_plan_text = "\n".join(
            (
                "ALPHA001",
                "",
                "Entrada",
                "--------",
                "Modelo:",
                "TREND_MOMENTUM",
                "",
                "Gatilho:",
                "29/06/2026 18:00",
                "",
                "Stop Inicial:",
                "2.0 ATR",
                "",
                "Saida:",
                "RR 3.0",
                "",
                "Gestao:",
                "ATR_TRAILING_STOP",
                "",
                "Parametros:",
                "atr_trailing_factor=2.0 | atr_trailing_activation_rr=1.0",
                "",
                "Confidence:",
                "91%",
                "",
                "Score:",
                "87",
                "",
                "Reason:",
                "Plano visual pronto.",
            )
        )
        self.assertEqual(signal["operational_plan_text"], "")
        self.assertEqual(signal["score"], 87.0)
        self.assertEqual(signal["confidence"], 0.91)
        self.assertEqual(signal["lab_alpha_id"], "ALPHA001")
        self.assertEqual(signal["lab_timeframe"], "M15")
        self.assertEqual(signal["lab_configuration_source"], "RESEARCH_LAB")
        self.assertEqual(signal["lab_configuration"]["model"], "TREND_MOMENTUM")
        self.assertEqual(signal["lab_configuration"]["timeframe"], "M15")
        self.assertEqual(signal["lab_configuration"]["parameters"]["ema_curta"], "20")
        self.assertEqual(signal["lab_configuration"]["parameters"]["rr"], "3.0")
        self.assertEqual(signal["market_indicators"]["trend"], "ALTA")
        self.assertEqual(signal["market_indicators"]["rsi"], 58.0)
        self.assertEqual(signal["market_indicators"]["adx"], 28.0)
        self.assertIn("EMA20>EMA50", signal["active_indicators"])
        self.assertEqual(signal["robot_status"], "PLANO_VALIDADO")
        self.assertIn("EMA20>EMA50", signal["reason_codes"])
        self.assertIn("RR_VALIDO", signal["reason_codes"])
        self.assertTrue(signal["visual_only"])
        self.assertEqual(payload["signal_history"], [])

    def test_exportador_visual_mt5_preserva_historico_de_sinais(self) -> None:
        exporter = MT5VisualSignalExporter()
        exporter._open_positions_by_symbol = lambda: {}
        forex = DashboardMT5ForexSignalViewModel(
            timeframe="H1",
            pairs=[
                DashboardMT5ForexSignalRowViewModel(
                    pair="EURUSD",
                    timeframe="H1",
                    last_candle_time="29/06/2026 19:00",
                    decision="SELL",
                    active_model="RSI_REVERSAL",
                    theoretical_entry_status="SINAL_TEORICO",
                    theoretical_entry_candle="29/06/2026 19:00",
                    theoretical_entry_price=1.1400,
                    theoretical_entry_direction="SELL",
                    research_plan_status="PLANO_VALIDO",
                    research_plan_entry_price=1.1400,
                    research_plan_stop=1.1420,
                    research_plan_target=1.1340,
                    research_plan_risk_reward=3.0,
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "traderia_signals.json"
            output_path.write_text(
                json.dumps(
                    {
                        "signal_history": [
                            {
                                "symbol": "EURUSD",
                                "timeframe": "H1",
                                "timestamp": "29/06/2026 18:00",
                                "decision": "BUY",
                                "entry": 1.1422,
                                "stop": 1.1402,
                                "target": 1.1482,
                                "visual_only": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            exporter.export(forex, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(len(payload["signals"]), 1)
        self.assertEqual(payload["signal_history"], [])

    def test_exportador_visual_mt5_bloco_operacional_usa_fallback_na(self) -> None:
        exporter = MT5VisualSignalExporter()
        exporter._open_positions_by_symbol = lambda: {}
        forex = DashboardMT5ForexSignalViewModel(
            pairs=[DashboardMT5ForexSignalRowViewModel(pair="EURUSD")]
        )

        payload = exporter.build_payload(forex)
        text = payload["signals"][0]["operational_plan_text"]

        self.assertEqual(text, "")

    def test_exportador_visual_mt5_remove_historico_de_pares_nao_rastreados(self) -> None:
        exporter = MT5VisualSignalExporter()
        exporter._open_positions_by_symbol = lambda: {}
        forex = DashboardMT5ForexSignalViewModel(
            timeframe="M1",
            pairs=[
                DashboardMT5ForexSignalRowViewModel(
                    pair="EURUSD",
                    timeframe="M1",
                    last_candle_time="30/06/2026 03:10",
                    decision="SELL",
                    active_model="MA_RSI_FILTER",
                    research_plan_status="SEM_GATILHO_VALIDO",
                )
            ],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "traderia_signals.json"
            output_path.write_text(
                json.dumps(
                    {
                        "signal_history": [
                            {
                                "symbol": "EURJPY",
                                "timeframe": "M1",
                                "timestamp": "30/06/2026 03:08",
                                "decision": "BUY",
                                "entry": 184.9,
                                "visual_only": True,
                            },
                            {
                                "symbol": "EURUSD",
                                "timeframe": "M1",
                                "timestamp": "30/06/2026 03:09",
                                "decision": "SELL",
                                "entry": 1.1406,
                                "visual_only": True,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            exporter.export(forex, output_path)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["signal_history"], [])

    def test_dashboard_service_exporta_sinais_visuais_mt5(self) -> None:
        service = DashboardService()

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "traderia_signals.json"
            result = service.export_mt5_visual_signals(output_path)

            self.assertTrue(result.output_path.exists())
            payload = json.loads(result.output_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["schema_version"], "traderia.mt5.visual_signals.v1")
        self.assertEqual(payload["order_execution"], "NOT_ALLOWED_BY_INDICATOR")

    def test_dashboard_service_exporta_visual_mt5_automaticamente_ao_atualizar(
        self,
    ) -> None:
        service = DashboardService()
        calls: list[str] = []
        object.__setattr__(
            service,
            "mt5_market_data_service",
            SimpleNamespace(
                load_forex_signal_dashboard=lambda timeframe: f"loaded:{timeframe}"
            ),
        )
        object.__setattr__(
            service,
            "_auto_export_mt5_visual_signals",
            lambda: calls.append("export"),
        )

        result = service.load_mt5_forex_signals("M1")

        self.assertEqual(result, "loaded:M1")
        self.assertEqual(calls, ["export"])

    def test_dashboard_service_detecta_mql5_files_para_export_visual(
        self,
    ) -> None:
        service = DashboardService()
        original_appdata = os.environ.get("APPDATA")
        original_configured = os.environ.get("TRADERIA_MT5_VISUAL_SIGNALS_PATH")

        with tempfile.TemporaryDirectory() as temp_dir:
            terminal_files = (
                Path(temp_dir)
                / "MetaQuotes"
                / "Terminal"
                / "ABC"
                / "MQL5"
                / "Files"
            )
            terminal_files.mkdir(parents=True)
            expected_path = terminal_files / "traderia_visual_signals.json"
            expected_path.write_text("{}", encoding="utf-8")
            os.environ["APPDATA"] = temp_dir
            os.environ.pop("TRADERIA_MT5_VISUAL_SIGNALS_PATH", None)

            detected = service._mt5_visual_signals_output_path(None)

        if original_appdata is None:
            os.environ.pop("APPDATA", None)
        else:
            os.environ["APPDATA"] = original_appdata
        if original_configured is None:
            os.environ.pop("TRADERIA_MT5_VISUAL_SIGNALS_PATH", None)
        else:
            os.environ["TRADERIA_MT5_VISUAL_SIGNALS_PATH"] = original_configured

        self.assertEqual(detected, expected_path)

    def test_dashboard_service_registra_ordem_demo_no_historico_visual(
        self,
    ) -> None:
        service = DashboardService()
        robot = service._demo_robot_view_model(
            row=DashboardMT5ForexSignalRowViewModel(
                pair="USDJPY",
                timeframe="M1",
                decision="BUY",
                active_model="TREND_MOMENTUM",
            ),
            status="EXECUTED",
            message="Ordem demo enviada.",
            result_status="ACCEPTED",
            result_message="Solicitacao executada.",
            entry_price=162.165,
            stop=162.009,
            target=162.658,
            provider="MT5_DEMO",
            mt5_order_send_enabled=True,
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "traderia_signals.json"
            output_path.write_text(
                json.dumps(
                    {
                        "schema_version": "traderia.mt5.visual_signals.v1",
                        "signals": [],
                        "signal_history": [],
                        "read_only": True,
                    }
                ),
                encoding="utf-8",
            )
            original = service._mt5_visual_signals_output_path
            object.__setattr__(
                service,
                "_mt5_visual_signals_output_path",
                lambda output: output_path if output is None else Path(output),
            )

            service._append_demo_robot_visual_signal(robot)
            payload = json.loads(output_path.read_text(encoding="utf-8"))

            object.__setattr__(service, "_mt5_visual_signals_output_path", original)

        signal = payload["signal_history"][0]
        self.assertEqual(signal["symbol"], "USDJPY")
        self.assertEqual(signal["decision"], "BUY")
        self.assertEqual(signal["entry"], 162.165)
        self.assertEqual(signal["stop"], 162.009)
        self.assertEqual(signal["target"], 162.658)
        self.assertEqual(signal["plan_status"], "PLANO_VALIDO")
        self.assertEqual(signal["robot_status"], "ORDEM_ENVIADA_DEMO")
        self.assertEqual(payload["order_execution"], "NOT_ALLOWED_BY_INDICATOR")

    def test_indicador_visual_mt5_nao_possui_funcoes_de_ordem(self) -> None:
        source = Path("mt5/indicators/TraderIAVisualSignals.mq5").read_text(
            encoding="utf-8"
        )

        for fragment in ("OrderSend", "OrderCheck", "CTrade", "PositionOpen"):
            with self.subTest(fragment=fragment):
                self.assertNotIn(fragment, source)
        self.assertIn("FileOpen", source)
        self.assertIn("OBJ_ARROW", source)
        self.assertIn("OBJ_TREND", source)
        self.assertIn("OBJ_LABEL", source)
        self.assertIn("plan_status", source)
        self.assertIn("signal_history", source)
        self.assertIn("robot_status", source)
        self.assertIn("operational_plan_text", source)
        self.assertIn('"Tempo: "', source)
        self.assertIn('"Entrada Alpha: "', source)
        self.assertIn('"Saida Beta: "', source)
        self.assertIn('ExtractJsonString(block, "alpha_id")', source)
        self.assertIn('ExtractJsonString(block, "beta_id")', source)
        self.assertIn("DrawOperationalPlanLabel", source)
        self.assertIn("OPERATIONAL_PLAN_LABEL_", source)
        self.assertIn("DecodeJsonText", source)

    def test_indicador_visual_mt5_filtra_por_symbol_e_timeframe(self) -> None:
        source = Path("mt5/indicators/TraderIAVisualSignals.mq5").read_text(
            encoding="utf-8"
        )

        self.assertIn('ExtractJsonString(block, "symbol")', source)
        self.assertIn('ExtractJsonString(block, "timeframe")', source)
        self.assertIn("ChartTimeframeLabel()", source)
        self.assertIn("signal_timeframe == chart_timeframe", source)
        self.assertIn("DrawTimeframeMismatchLabel", source)
        self.assertIn("Sinal disponivel em", source)
        self.assertIn("FindLatestDrawableSymbolBlock", source)
        self.assertIn("POSICAO_ABERTA_MT5", source)
        self.assertIn("ORDEM_ENVIADA_DEMO", source)

    def test_template_visual_mt5_abre_em_m1(self) -> None:
        source = Path("mt5/templates/TraderIAVisualSignals.tpl").read_text(
            encoding="utf-8"
        )

        self.assertIn("period_type=0", source)
        self.assertIn("period_size=1", source)

    def _forex_row(
        self,
        *,
        trend: str,
        momentum: float,
        rsi: float,
        short_average: float,
        long_average: float,
        pair: str = "EURUSD",
        timeframe: str = "H1",
        last_candle_time: str = "2026-06-29T10:00:00+00:00",
    ) -> SimpleNamespace:
        return SimpleNamespace(
            pair=pair,
            status="OK",
            last_price=1.2,
            last_candle_time=last_candle_time,
            trend=trend,
            momentum=momentum,
            volatility=0.001,
            rsi=rsi,
            short_average=short_average,
            long_average=long_average,
            candles_loaded=1000,
            sample_size=0,
            win_rate=0.0,
            avg_return=0.0,
            profit_factor=0.0,
            max_drawdown=0.0,
            matched_context_count=0,
            rejected_reason="",
            volatility_bucket="UNKNOWN",
            rsi_bucket="UNKNOWN",
            momentum_sign="ZERO",
            ma_distance_bucket="FLAT",
            confidence_penalties=(),
            confidence_drivers=(),
            timeframe=timeframe,
            configured_candles=1000,
            requested_candles=1000,
            received_candles=1000,
            research_candles_used=0,
            last_update="2026-06-29T10:01:00+00:00",
            diagnostics_status="OK",
            diagnostics_log="OK",
        )

    def _flat_then_breakout_candles(self) -> list[Candle]:
        candles = [
            Candle(
                data=f"2026-06-29T{index:02d}:00:00+00:00",
                abertura=1.0,
                maxima=1.001,
                minima=0.999,
                fechamento=1.0,
                volume=1000,
            )
            for index in range(60)
        ]
        candles.append(
            Candle(
                data="2026-06-29T21:00:00+00:00",
                abertura=1.0,
                maxima=1.101,
                minima=0.999,
                fechamento=1.10,
                volume=1200,
            )
        )
        return candles

    def _uptrend_candles(self) -> list[Candle]:
        return [
            Candle(
                data=f"2026-06-29T{index:02d}:00:00+00:00",
                abertura=1.0 + index * 0.001,
                maxima=1.001 + index * 0.001,
                minima=0.999 + index * 0.001,
                fechamento=1.0 + index * 0.001,
                volume=1000 + index,
            )
            for index in range(61)
        ]


if __name__ == "__main__":
    unittest.main()
