"""Testes do fluxo de execucao demo separado do dashboard visual."""

import os
import unittest
from unittest.mock import patch

from application.demo_execution_service import (
    DemoExecutionPolicy,
    DemoExecutionService,
)
from application.dashboard_service import DashboardService
from application.dashboard_view_model import (
    DashboardMT5ForexSignalRowViewModel,
    DashboardMT5HeuristicResearchRowViewModel,
    DashboardMT5HeuristicResearchViewModel,
)
from application.mt5_market_data_service import (
    MT5ForexSignalDashboard,
    MT5ForexSignalRow,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult
from domain.contracts.market_snapshot import MarketSnapshot
from domain.contracts.risk_decision import RiskDecision
from domain.contracts.strategy_signal import StrategySignal
from domain.candle import Candle
from research.mt5_research_trade_plan import MT5ResearchTradePlan


class DemoExecutionServiceTest(unittest.TestCase):
    """Valida travas obrigatorias antes do provider demo."""

    def test_prepara_ordem_depois_de_decision_pipeline_e_risco(self) -> None:
        service = DemoExecutionService(provider=_AcceptingProvider())

        context, order = service.prepare_order(
            self._signal("BUY"),
            self._snapshot(),
            RiskDecision(True, "Risco aprovado", 2, 1.0),
            entry_price=100.0,
            stop_points=10.0,
            target_points=20.0,
        )

        self.assertTrue(context.approved)
        self.assertIsNotNone(order)
        self.assertEqual(order.symbol, "WDO")
        self.assertEqual(order.quantity, 2)
        self.assertEqual(order.stop, 90.0)
        self.assertEqual(order.target, 120.0)

    def test_bloqueia_sem_paper_validation(self) -> None:
        service = DemoExecutionService(provider=_AcceptingProvider())
        context, order = self._prepared(service)

        result = service.submit_demo_order(context, order, paper_validated=False)

        self.assertFalse(result.accepted)
        self.assertIn("Paper Validation", result.message)
        self.assertEqual(len(service.list_audit_log()), 1)

    def test_bloqueia_posicao_aberta_no_mesmo_simbolo(self) -> None:
        service = DemoExecutionService(provider=_PositionOpenProvider())
        context, order = self._prepared(service)

        result = service.submit_demo_order(context, order, paper_validated=True)

        self.assertFalse(result.accepted)
        self.assertIn("posicao aberta", result.message)

    def test_bloqueia_limite_de_operacoes_por_dia(self) -> None:
        service = DemoExecutionService(
            provider=_AcceptingProvider(),
            policy=DemoExecutionPolicy(max_daily_operations=1),
            daily_operations=1,
        )
        context, order = self._prepared(service)

        result = service.submit_demo_order(context, order, paper_validated=True)

        self.assertFalse(result.accepted)
        self.assertIn("Limite de operacoes", result.message)

    def test_max_daily_operations_zero_remove_limite_diario(self) -> None:
        service = DemoExecutionService(
            provider=_AcceptingProvider(),
            policy=DemoExecutionPolicy(max_daily_operations=0),
            daily_operations=999,
        )
        context, order = self._prepared(service)

        result = service.submit_demo_order(context, order, paper_validated=True)

        self.assertTrue(result.accepted)
        self.assertEqual(result.status, "ACCEPTED")

    def test_bloqueia_limite_de_perda_diaria(self) -> None:
        service = DemoExecutionService(
            provider=_AcceptingProvider(),
            policy=DemoExecutionPolicy(max_daily_loss=100.0),
            daily_result=-100.0,
        )
        context, order = self._prepared(service)

        result = service.submit_demo_order(context, order, paper_validated=True)

        self.assertFalse(result.accepted)
        self.assertIn("perda diaria", result.message)

    def test_bloqueia_ordem_sem_stop_target_validos(self) -> None:
        service = DemoExecutionService(provider=_AcceptingProvider())
        context, order = self._prepared(service)
        invalid_order = ExecutionOrder(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            entry_price=order.entry_price,
            stop=110.0,
            target=120.0,
        )

        result = service.submit_demo_order(context, invalid_order, paper_validated=True)

        self.assertFalse(result.accepted)
        self.assertIn("Stop Loss", result.message)

    def test_bloqueia_fora_do_horario_permitido(self) -> None:
        service = DemoExecutionService(provider=_AcceptingProvider())
        context, order = service.prepare_order(
            self._signal("BUY"),
            self._snapshot(datetime_text="2026-06-29 20:00:00"),
            RiskDecision(True, "Risco aprovado", 1, 1.0),
            entry_price=100.0,
            stop_points=10.0,
            target_points=20.0,
        )

        result = service.submit_demo_order(context, order, paper_validated=True)

        self.assertFalse(result.accepted)
        self.assertIn("Horario fora", result.message)

    def test_envia_para_provider_quando_todas_as_travas_passam(self) -> None:
        provider = _AcceptingProvider()
        service = DemoExecutionService(provider=provider)
        context, order = self._prepared(service)

        result = service.submit_demo_order(context, order, paper_validated=True)

        self.assertTrue(result.accepted)
        self.assertEqual(service.daily_operations, 1)
        self.assertEqual(provider.orders, [order])

    def test_close_position_delega_para_provider_demo(self) -> None:
        provider = _AcceptingProvider()
        service = DemoExecutionService(provider=provider)

        result = service.close_position(
            symbol="EURUSD",
            ticket=123,
            side="BUY",
            volume=0.1,
            reason="EARLY_EXIT_MOMENTUM_LOSS",
        )

        self.assertTrue(result.accepted)
        self.assertEqual(provider.close_requests[0]["symbol"], "EURUSD")
        self.assertEqual(provider.close_requests[0]["reason"], "EARLY_EXIT_MOMENTUM_LOSS")

    def test_dashboard_service_expoe_fluxo_sem_provider_externo_por_padrao(self) -> None:
        service = DashboardService()
        context, order = service.prepare_demo_execution_order(
            self._signal("BUY"),
            self._snapshot(),
            RiskDecision(True, "Risco aprovado", 1, 1.0),
            entry_price=100.0,
            stop_points=10.0,
            target_points=20.0,
        )

        result = service.submit_demo_execution_order(context, order, True)

        self.assertFalse(result.accepted)
        self.assertEqual(result.status, "PROVIDER_DISABLED")
        self.assertEqual(len(service.list_demo_execution_audit_log()), 1)

    def test_dashboard_service_robo_demo_bloqueia_sem_env_explicita(self) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_signal_dashboard = (
            self._forex_dashboard()
        )
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._flat_then_trigger_candles("BUY")
        )
        os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        result = service.run_demo_robot_once("EURUSD", "H1")

        self.assertEqual(result.status, "DISABLED")
        self.assertEqual(result.result_status, "DISABLED")
        self.assertEqual(result.provider, "MT5_DEMO_DISABLED")
        self.assertFalse(result.mt5_order_send_enabled)
        self.assertEqual(len(result.audit_log), 0)

    def test_dashboard_service_robo_demo_usa_provider_mt5_quando_env_ativa(
        self,
    ) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_signal_dashboard = (
            self._forex_dashboard()
        )
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._flat_then_trigger_candles("BUY")
        )
        self._install_certified_research_constants(service, ("EURUSD",))
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        object.__setattr__(
            service,
            "_enable_mt5_demo_provider",
            lambda: object.__setattr__(
                service,
                "demo_robot_execution_service",
                DemoExecutionService(provider=_AcceptingProvider()),
            ),
        )

        try:
            result = service.run_demo_robot_once("EURUSD", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(result.status, "EXECUTED")
        self.assertEqual(result.result_status, "ACCEPTED")
        self.assertEqual(result.selected_pair, "EURUSD")
        self.assertEqual(result.decision, "BUY")
        self.assertFalse(result.real_order_enabled)
        self.assertTrue(result.mt5_order_send_enabled)
        self.assertEqual(len(result.audit_log), 1)
        self.assertAlmostEqual(result.entry_price or 0.0, 1.2)
        self.assertAlmostEqual(result.stop or 0.0, 1.198)
        self.assertAlmostEqual(result.target or 0.0, 1.204)
        rejection_stages = {step.stage: step for step in result.rejection_tree}
        self.assertEqual(rejection_stages["Kill switch demo"].status, "APROVADO")
        self.assertEqual(rejection_stages["Research Constants"].status, "APROVADO")
        self.assertEqual(rejection_stages["Trade Plan"].status, "APROVADO")
        self.assertEqual(
            rejection_stages["Decision/Risk/Execution"].status,
            "APROVADO",
        )

    def test_dashboard_service_provider_mt5_demo_padrao_forex_24h(
        self,
    ) -> None:
        service = DashboardService()
        os.environ.pop("TRADERIA_DEMO_ALLOWED_START", None)
        os.environ.pop("TRADERIA_DEMO_ALLOWED_END", None)

        class _Module:
            MT5DemoExecutionProvider = _AcceptingProvider

        with patch("application.dashboard_service.importlib.import_module") as importer:
            importer.return_value = _Module
            service._enable_mt5_demo_provider()

        policy = service.demo_robot_execution_service.policy

        self.assertEqual(policy.allowed_start, "00:00")
        self.assertEqual(policy.allowed_end, "23:59")

    def test_dashboard_service_atualiza_politica_de_provider_mt5_ja_existente(
        self,
    ) -> None:
        service = DashboardService()

        class MT5DemoExecutionProvider(_AcceptingProvider):
            pass

        object.__setattr__(
            service,
            "demo_robot_execution_service",
            DemoExecutionService(
                provider=MT5DemoExecutionProvider(),
                policy=DemoExecutionPolicy(
                    allowed_start="09:00",
                    allowed_end="18:00",
                ),
                daily_operations=2,
                daily_result=-10.0,
            ),
        )
        os.environ.pop("TRADERIA_DEMO_ALLOWED_START", None)
        os.environ.pop("TRADERIA_DEMO_ALLOWED_END", None)

        service._enable_mt5_demo_provider()

        policy = service.demo_robot_execution_service.policy

        self.assertEqual(policy.allowed_start, "00:00")
        self.assertEqual(policy.allowed_end, "23:59")
        self.assertEqual(service.demo_robot_execution_service.daily_operations, 2)
        self.assertEqual(service.demo_robot_execution_service.daily_result, -10.0)

    def test_dashboard_service_robo_demo_executa_todos_ativos_habilitados(
        self,
    ) -> None:
        service = DashboardService()
        dashboard = self._forex_dashboard(include_multiple_pairs=True)
        object.__setattr__(dashboard, "pairs", dashboard.pairs[:2])
        service.mt5_market_data_service.latest_forex_signal_dashboard = dashboard
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._flat_then_trigger_candles("BUY")
        )
        service.mt5_market_data_service.latest_forex_candles[("GBPUSD", "H1")] = (
            self._flat_then_trigger_candles("SELL")
        )
        self._install_certified_research_constants(service, ("EURUSD", "GBPUSD"))
        valid_rows = {
            "EURUSD": DashboardMT5ForexSignalRowViewModel(
                pair="EURUSD",
                status="OK",
                timeframe="H1",
                lab_timeframe="H1",
                last_price=1.1000,
                last_candle_time="2026-06-29T14:00:00+00:00",
                trend="ALTA",
                momentum=0.001,
                volatility=0.001,
                short_average=1.0995,
                long_average=1.0980,
                ema_fast=1.0995,
                atr=0.001,
                decision="BUY",
                theoretical_entry_direction="BUY",
                theoretical_entry_status="SINAL_TEORICO",
                theoretical_entry_price=1.1000,
                active_model="TREND_MOMENTUM",
                confidence=0.80,
                lab_confidence=0.75,
                reason="Plano valido fixture.",
                research_plan_status="PLANO_VALIDO",
                research_plan_entry_price=1.1000,
                research_plan_stop=1.0950,
                research_plan_target=1.1100,
                research_plan_risk_reward=2.0,
            ),
            "GBPUSD": DashboardMT5ForexSignalRowViewModel(
                pair="GBPUSD",
                status="OK",
                timeframe="H1",
                lab_timeframe="H1",
                last_price=1.3000,
                last_candle_time="2026-06-29T14:00:00+00:00",
                trend="BAIXA",
                momentum=-0.001,
                volatility=0.001,
                short_average=1.2995,
                long_average=1.3020,
                ema_fast=1.2995,
                atr=0.001,
                decision="SELL",
                theoretical_entry_direction="SELL",
                theoretical_entry_status="SINAL_TEORICO",
                theoretical_entry_price=1.3000,
                active_model="TREND_MOMENTUM",
                confidence=0.80,
                lab_confidence=0.75,
                reason="Plano valido fixture.",
                research_plan_status="PLANO_VALIDO",
                research_plan_entry_price=1.3000,
                research_plan_stop=1.3050,
                research_plan_target=1.2900,
                research_plan_risk_reward=2.0,
            ),
        }
        valid_plans = {
            "EURUSD": MT5ResearchTradePlan(
                symbol="EURUSD",
                timeframe="H1",
                direction="BUY",
                entry_price=1.1000,
                stop=1.0950,
                target=1.1100,
                risk_reward=2.0,
                stop_multiplier=2.0,
                exit_model="FIXED_STOP",
                exit_score=1.0,
                exit_candidates=1,
                status="PLANO_VALIDO",
                risk_pips=0.005,
                reward_pips=0.010,
                source="RESEARCH_LAB",
            ),
            "GBPUSD": MT5ResearchTradePlan(
                symbol="GBPUSD",
                timeframe="H1",
                direction="SELL",
                entry_price=1.3000,
                stop=1.3050,
                target=1.2900,
                risk_reward=2.0,
                stop_multiplier=2.0,
                exit_model="FIXED_STOP",
                exit_score=1.0,
                exit_candidates=1,
                status="PLANO_VALIDO",
                risk_pips=0.005,
                reward_pips=0.010,
                source="RESEARCH_LAB",
            ),
        }
        object.__setattr__(
            service,
            "_to_view_model_mt5_forex_signal_row",
            lambda source_row, *_args, **_kwargs: valid_rows[source_row.pair],
        )
        object.__setattr__(
            service,
            "_mt5_research_trade_plan_for_view_row",
            lambda row, *_args, **_kwargs: valid_plans[row.pair],
        )
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        object.__setattr__(
            service,
            "_enable_mt5_demo_provider",
            lambda: None
            if service.demo_robot_execution_service.provider is provider
            else object.__setattr__(
                service,
                "demo_robot_execution_service",
                DemoExecutionService(provider=provider),
            ),
        )

        try:
            result = service.run_demo_robot_for_all(
                ["EURUSD", "GBPUSD", "USDJPY"],
                "H1",
            )
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(result.status, "BATCH_COMPLETED")
        self.assertEqual(result.selected_pair, "TODOS")
        self.assertEqual(result.provider, "MT5_DEMO")
        self.assertTrue(result.mt5_order_send_enabled)
        self.assertIn("2 aceita", result.message)
        self.assertIn("1 sem ordem", result.message)
        self.assertEqual(len(result.audit_log), 2)
        self.assertTrue(all(row.quantity == 0.1 for row in result.audit_log))

    def test_dashboard_service_robo_demo_nao_executa_sem_plano_research(self) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_signal_dashboard = (
            self._forex_dashboard()
        )
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        object.__setattr__(
            service,
            "_enable_mt5_demo_provider",
            lambda: object.__setattr__(
                service,
                "demo_robot_execution_service",
                DemoExecutionService(provider=provider),
            ),
        )

        try:
            result = service.run_demo_robot_once("EURUSD", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(result.status, "AGUARDANDO_PLANO")
        self.assertEqual(result.result_status, "SEM_GATILHO_VALIDO")
        self.assertEqual(provider.orders, [])
        rejection_stages = {step.stage: step for step in result.rejection_tree}
        self.assertEqual(
            rejection_stages["Research Constants"].status,
            "APROVADO",
        )
        self.assertEqual(rejection_stages["ICT informativo"].status, "APROVADO")
        self.assertIn(
            "nao bloqueia Demo",
            rejection_stages["ICT informativo"].reason,
        )
        self.assertEqual(
            rejection_stages["Regime de Mercado"].status,
            "BLOQUEADO",
        )
        self.assertEqual(rejection_stages["Trade Plan"].status, "BLOQUEADO")
        self.assertIn("SEM_GATILHO_VALIDO", rejection_stages["Trade Plan"].reason)

    def test_robo_temporal_armado_executa_no_maximo_um_gatilho_por_avaliacao(
        self,
    ) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_signal_dashboard = (
            self._forex_dashboard(include_multiple_pairs=True)
        )
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._flat_then_trigger_candles("BUY")
        )
        service.mt5_market_data_service.latest_forex_candles[("GBPUSD", "H1")] = (
            self._flat_then_trigger_candles("SELL")
        )
        self._install_certified_research_constants(service, ("EURUSD", "GBPUSD"))
        valid_rows = {
            "EURUSD": DashboardMT5ForexSignalRowViewModel(
                pair="EURUSD",
                status="OK",
                timeframe="H1",
                lab_timeframe="H1",
                last_price=1.1000,
                last_candle_time="2026-06-29T14:00:00+00:00",
                trend="ALTA",
                momentum=0.001,
                volatility=0.001,
                short_average=1.0995,
                long_average=1.0980,
                ema_fast=1.0995,
                atr=0.001,
                decision="BUY",
                theoretical_entry_direction="BUY",
                theoretical_entry_status="SINAL_TEORICO",
                theoretical_entry_price=1.1000,
                active_model="TREND_MOMENTUM",
                confidence=0.80,
                lab_confidence=0.75,
                reason="Plano valido fixture.",
                research_plan_status="PLANO_VALIDO",
                research_plan_entry_price=1.1000,
                research_plan_stop=1.0950,
                research_plan_target=1.1100,
                research_plan_risk_reward=2.0,
            ),
            "GBPUSD": DashboardMT5ForexSignalRowViewModel(
                pair="GBPUSD",
                status="OK",
                timeframe="H1",
                lab_timeframe="H1",
                last_price=1.3000,
                last_candle_time="2026-06-29T14:00:00+00:00",
                trend="BAIXA",
                momentum=-0.001,
                volatility=0.001,
                short_average=1.2995,
                long_average=1.3020,
                ema_fast=1.2995,
                atr=0.001,
                decision="SELL",
                theoretical_entry_direction="SELL",
                theoretical_entry_status="SINAL_TEORICO",
                theoretical_entry_price=1.3000,
                active_model="TREND_MOMENTUM",
                confidence=0.80,
                lab_confidence=0.75,
                reason="Plano valido fixture.",
                research_plan_status="PLANO_VALIDO",
                research_plan_entry_price=1.3000,
                research_plan_stop=1.3050,
                research_plan_target=1.2900,
                research_plan_risk_reward=2.0,
            ),
        }
        valid_plans = {
            "EURUSD": MT5ResearchTradePlan(
                symbol="EURUSD",
                timeframe="H1",
                direction="BUY",
                entry_price=1.1000,
                stop=1.0950,
                target=1.1100,
                risk_reward=2.0,
                stop_multiplier=2.0,
                exit_model="FIXED_STOP",
                exit_score=1.0,
                exit_candidates=1,
                status="PLANO_VALIDO",
                risk_pips=0.005,
                reward_pips=0.010,
                source="RESEARCH_LAB",
            ),
            "GBPUSD": MT5ResearchTradePlan(
                symbol="GBPUSD",
                timeframe="H1",
                direction="SELL",
                entry_price=1.3000,
                stop=1.3050,
                target=1.2900,
                risk_reward=2.0,
                stop_multiplier=2.0,
                exit_model="FIXED_STOP",
                exit_score=1.0,
                exit_candidates=1,
                status="PLANO_VALIDO",
                risk_pips=0.005,
                reward_pips=0.010,
                source="RESEARCH_LAB",
            ),
        }
        object.__setattr__(
            service,
            "_to_view_model_mt5_forex_signal_row",
            lambda source_row, *_args, **_kwargs: valid_rows[source_row.pair],
        )
        object.__setattr__(
            service,
            "_mt5_research_trade_plan_for_view_row",
            lambda row, *_args, **_kwargs: valid_plans[row.pair],
        )
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        object.__setattr__(
            service,
            "_enable_mt5_demo_provider",
            lambda: object.__setattr__(
                service,
                "demo_robot_execution_service",
                DemoExecutionService(provider=provider),
            ),
        )

        try:
            armed = service.arm_demo_robot("TODOS", "H1")
            result = service.evaluate_armed_demo_robot_once("TODOS", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(armed.status, "ARMED")
        self.assertIn(result.status, {"EXECUTED", "REJECTED"})
        self.assertEqual(len(provider.orders), 1)
        self.assertEqual(provider.orders[0].symbol, "EURUSD")

    def test_robo_temporal_precisa_ser_armado_antes_de_avaliar(self) -> None:
        service = DashboardService()

        result = service.evaluate_armed_demo_robot_once("TODOS", "H1")

        self.assertEqual(result.status, "NOT_ARMED")
        self.assertFalse(result.mt5_order_send_enabled)

    def test_robo_temporal_nao_consumir_candle_sem_plano_research(self) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_signal_dashboard = (
            self._forex_dashboard()
        )
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        object.__setattr__(
            service,
            "_enable_mt5_demo_provider",
            lambda: object.__setattr__(
                service,
                "demo_robot_execution_service",
                DemoExecutionService(provider=provider),
            ),
        )

        try:
            service.arm_demo_robot("TODOS", "H1")
            result = service.evaluate_armed_demo_robot_once("TODOS", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(result.status, "AGUARDANDO_PLANO")
        self.assertEqual(result.result_status, "SEM_GATILHO_VALIDO")
        self.assertIsNone(result.stop)
        self.assertIsNone(result.target)
        self.assertEqual(provider.orders, [])
        self.assertEqual(service.mt5_demo_robot_service.last_candle_by_market, {})

    def test_robo_temporal_sem_plano_nao_exibe_preco_parcial_como_trade(self) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_signal_dashboard = (
            self._forex_dashboard()
        )
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        object.__setattr__(
            service,
            "_enable_mt5_demo_provider",
            lambda: object.__setattr__(
                service,
                "demo_robot_execution_service",
                DemoExecutionService(provider=provider),
            ),
        )

        try:
            service.arm_demo_robot("TODOS", "H1")
            result = service.evaluate_armed_demo_robot_once("TODOS", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(result.status, "AGUARDANDO_PLANO")
        self.assertEqual(result.result_status, "SEM_GATILHO_VALIDO")
        self.assertIsNone(result.entry_price)
        self.assertIsNone(result.stop)
        self.assertIsNone(result.target)
        self.assertEqual(provider.orders, [])

    def test_robo_online_atualiza_mt5_antes_de_avaliar(self) -> None:
        service = DashboardService()
        service.mt5_market_data_service.latest_forex_signal_dashboard = (
            self._forex_dashboard()
        )
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._flat_then_trigger_candles("BUY")
        )
        self._install_certified_research_constants(service, ("EURUSD",))
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        calls: list[str] = []

        def load_forex(timeframe: str = "H1"):
            calls.append(timeframe)
            return service.mt5_market_data_service.latest_forex_signal_dashboard

        object.__setattr__(service, "load_mt5_forex_signals", load_forex)
        object.__setattr__(
            service,
            "_enable_mt5_demo_provider",
            lambda: object.__setattr__(
                service,
                "demo_robot_execution_service",
                DemoExecutionService(provider=provider),
            ),
        )

        try:
            service.arm_demo_robot("TODOS", "H1")
            result = service.run_online_demo_robot_cycle("TODOS", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(calls, ["H1"])
        self.assertEqual(result.status, "BATCH_COMPLETED")
        self.assertEqual(len(provider.orders), 1)

    def test_robo_online_todos_executa_todos_os_candidatos_prontos(self) -> None:
        service = DashboardService()
        dashboard = self._forex_dashboard(include_multiple_pairs=True)
        object.__setattr__(dashboard, "pairs", dashboard.pairs[:2])
        service.mt5_market_data_service.latest_forex_signal_dashboard = dashboard
        service.mt5_market_data_service.latest_forex_candles[("EURUSD", "H1")] = (
            self._flat_then_trigger_candles("BUY")
        )
        service.mt5_market_data_service.latest_forex_candles[("GBPUSD", "H1")] = (
            self._flat_then_trigger_candles("SELL")
        )
        self._install_certified_research_constants(service, ("EURUSD", "GBPUSD"))
        valid_rows = {
            "EURUSD": DashboardMT5ForexSignalRowViewModel(
                pair="EURUSD",
                status="OK",
                timeframe="H1",
                lab_timeframe="H1",
                last_price=1.1000,
                last_candle_time="2026-06-29T14:00:00+00:00",
                trend="ALTA",
                momentum=0.001,
                volatility=0.001,
                short_average=1.0995,
                long_average=1.0980,
                ema_fast=1.0995,
                atr=0.001,
                decision="BUY",
                theoretical_entry_direction="BUY",
                theoretical_entry_status="SINAL_TEORICO",
                theoretical_entry_price=1.1000,
                active_model="TREND_MOMENTUM",
                confidence=0.80,
                lab_confidence=0.75,
                reason="Plano valido fixture.",
                research_plan_status="PLANO_VALIDO",
                research_plan_entry_price=1.1000,
                research_plan_stop=1.0950,
                research_plan_target=1.1100,
                research_plan_risk_reward=2.0,
            ),
            "GBPUSD": DashboardMT5ForexSignalRowViewModel(
                pair="GBPUSD",
                status="OK",
                timeframe="H1",
                lab_timeframe="H1",
                last_price=1.3000,
                last_candle_time="2026-06-29T14:00:00+00:00",
                trend="BAIXA",
                momentum=-0.001,
                volatility=0.001,
                short_average=1.2995,
                long_average=1.3020,
                ema_fast=1.2995,
                atr=0.001,
                decision="SELL",
                theoretical_entry_direction="SELL",
                theoretical_entry_status="SINAL_TEORICO",
                theoretical_entry_price=1.3000,
                active_model="TREND_MOMENTUM",
                confidence=0.80,
                lab_confidence=0.75,
                reason="Plano valido fixture.",
                research_plan_status="PLANO_VALIDO",
                research_plan_entry_price=1.3000,
                research_plan_stop=1.3050,
                research_plan_target=1.2900,
                research_plan_risk_reward=2.0,
            ),
        }
        valid_plans = {
            "EURUSD": MT5ResearchTradePlan(
                symbol="EURUSD",
                timeframe="H1",
                direction="BUY",
                entry_price=1.1000,
                stop=1.0950,
                target=1.1100,
                risk_reward=2.0,
                stop_multiplier=2.0,
                exit_model="FIXED_STOP",
                exit_score=1.0,
                exit_candidates=1,
                status="PLANO_VALIDO",
                risk_pips=0.005,
                reward_pips=0.010,
                source="RESEARCH_LAB",
            ),
            "GBPUSD": MT5ResearchTradePlan(
                symbol="GBPUSD",
                timeframe="H1",
                direction="SELL",
                entry_price=1.3000,
                stop=1.3050,
                target=1.2900,
                risk_reward=2.0,
                stop_multiplier=2.0,
                exit_model="FIXED_STOP",
                exit_score=1.0,
                exit_candidates=1,
                status="PLANO_VALIDO",
                risk_pips=0.005,
                reward_pips=0.010,
                source="RESEARCH_LAB",
            ),
        }
        object.__setattr__(
            service,
            "_to_view_model_mt5_forex_signal_row",
            lambda source_row, *_args, **_kwargs: valid_rows[source_row.pair],
        )
        object.__setattr__(
            service,
            "_mt5_research_trade_plan_for_view_row",
            lambda row, *_args, **_kwargs: valid_plans[row.pair],
        )
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        object.__setattr__(
            service,
            "demo_robot_execution_service",
            DemoExecutionService(provider=provider),
        )

        def load_forex(timeframe: str = "H1"):
            return service.mt5_market_data_service.latest_forex_signal_dashboard

        object.__setattr__(service, "load_mt5_forex_signals", load_forex)
        object.__setattr__(service, "_enable_mt5_demo_provider", lambda: None)

        try:
            service.arm_demo_robot("TODOS", "H1")
            result = service.run_online_demo_robot_cycle("TODOS", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(result.status, "BATCH_COMPLETED")
        self.assertIn("2 aceita", result.message)
        self.assertEqual([order.symbol for order in provider.orders], ["EURUSD", "GBPUSD"])

    def test_todos_modelos_executa_modelos_1_2_e_4_no_mesmo_ciclo(self) -> None:
        service = DashboardService()
        service.set_mt5_operational_model("TODOS_MODELOS")
        dashboard = self._forex_dashboard()
        service.mt5_market_data_service.latest_forex_signal_dashboard = dashboard
        valid_row = DashboardMT5ForexSignalRowViewModel(
            pair="EURUSD",
            status="OK",
            timeframe="H1",
            lab_timeframe="H1",
            last_price=1.1000,
            last_candle_time="2026-06-29T14:00:00+00:00",
            trend="ALTA",
            momentum=0.001,
            volatility=0.001,
            short_average=1.0995,
            long_average=1.0980,
            ema_fast=1.0995,
            atr=0.001,
            decision="BUY",
            theoretical_entry_direction="BUY",
            theoretical_entry_status="SINAL_TEORICO",
            theoretical_entry_price=1.1000,
            active_model="TREND_MOMENTUM",
            confidence=0.80,
            lab_confidence=0.75,
            adx=19.5,
            reason="Plano valido fixture.",
            lab_ict_demo_allowed=True,
            lab_ict_status="APROVADO",
            research_plan_status="PLANO_VALIDO",
            research_plan_entry_price=1.1000,
            research_plan_stop=1.0950,
            research_plan_target=1.1100,
            research_plan_risk_reward=2.0,
        )
        valid_plan = MT5ResearchTradePlan(
            symbol="EURUSD",
            timeframe="H1",
            direction="BUY",
            entry_price=1.1000,
            stop=1.0950,
            target=1.1100,
            risk_reward=2.0,
            stop_multiplier=2.0,
            exit_model="FIXED_STOP",
            exit_score=1.0,
            exit_candidates=1,
            status="PLANO_VALIDO",
            risk_pips=0.005,
            reward_pips=0.010,
            alpha_id="ALPHA001",
            beta_id="BETA001",
            beta_version="FIXED_STOP",
            source="RESEARCH_LAB",
            reason="Plano valido fixture.",
        )
        object.__setattr__(
            service,
            "_to_view_model_mt5_forex_signal_row",
            lambda *_args, **_kwargs: valid_row,
        )
        object.__setattr__(
            service,
            "_mt5_research_trade_plan_for_view_row",
            lambda *_args, **_kwargs: valid_plan,
        )
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        object.__setattr__(
            service,
            "demo_robot_execution_service",
            DemoExecutionService(provider=provider),
        )

        def load_forex(timeframe: str = "H1"):
            return service.mt5_market_data_service.latest_forex_signal_dashboard

        object.__setattr__(service, "load_mt5_forex_signals", load_forex)
        object.__setattr__(service, "_enable_mt5_demo_provider", lambda: None)

        try:
            service.arm_demo_robot("TODOS", "H1")
            result = service.run_online_demo_robot_cycle("TODOS", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertEqual(result.status, "BATCH_COMPLETED")
        self.assertEqual(len(provider.orders), 3)
        self.assertEqual(
            [order.operational_model for order in provider.orders],
            [
                "MODELO_1_ALPHA_ATUAL",
                "MODELO_2_ESPELHO_BETA2_RR1",
                "MODELO_4_ESPELHO_M1",
            ],
        )
        self.assertIn(provider.orders[0].side, {"BUY", "SELL"})
        self.assertIn(provider.orders[1].side, {"BUY", "SELL"})
        self.assertIn(provider.orders[2].side, {"BUY", "SELL"})
        self.assertNotEqual(provider.orders[0].side, provider.orders[1].side)
        self.assertNotEqual(provider.orders[0].side, provider.orders[2].side)
        self.assertEqual(provider.orders[2].target, valid_plan.stop)
        self.assertEqual(provider.orders[2].stop, valid_plan.target)

    def test_robo_temporal_continua_apos_par_sem_plano_research(self) -> None:
        service = DashboardService()
        dashboard = self._forex_dashboard(include_multiple_pairs=True)
        service.mt5_market_data_service.latest_forex_signal_dashboard = dashboard
        service.mt5_market_data_service.latest_forex_candles[("GBPUSD", "H1")] = (
            self._flat_then_trigger_candles("SELL")
        )
        self._install_certified_research_constants(service, ("GBPUSD",))
        os.environ["TRADERIA_DEMO_EXECUTION_ENABLED"] = "1"
        provider = _AcceptingProvider()
        object.__setattr__(
            service,
            "_enable_mt5_demo_provider",
            lambda: object.__setattr__(
                service,
                "demo_robot_execution_service",
                DemoExecutionService(provider=provider),
            ),
        )

        try:
            service.arm_demo_robot("TODOS", "H1")
            result = service.evaluate_armed_demo_robot_once("TODOS", "H1")
        finally:
            os.environ.pop("TRADERIA_DEMO_EXECUTION_ENABLED", None)

        self.assertIn(result.status, {"EXECUTED", "REJECTED"})
        self.assertEqual(len(provider.orders), 1)
        self.assertEqual(provider.orders[0].symbol, "GBPUSD")

    def _forex_dashboard(
        self,
        include_multiple_pairs: bool = False,
    ) -> MT5ForexSignalDashboard:
        pairs = [
            MT5ForexSignalRow(
                pair="EURUSD",
                status="OK",
                last_price=1.1000,
                last_candle_time="2026-06-29T14:00:00+00:00",
                trend="ALTA",
                momentum=0.001,
                volatility=0.001,
                rsi=56.0,
                short_average=1.1010,
                long_average=1.0990,
                decision="BUY",
                confidence=0.70,
                reason="Sinal fake.",
                atr=0.001,
                tick_volume=1000,
                timeframe="H1",
            )
        ]
        if include_multiple_pairs:
            pairs.extend(
                [
                    MT5ForexSignalRow(
                        pair="GBPUSD",
                        status="OK",
                        last_price=1.3000,
                        last_candle_time="2026-06-29T14:00:00+00:00",
                        trend="BAIXA",
                        momentum=-0.001,
                        volatility=0.001,
                        rsi=44.0,
                        short_average=1.2990,
                        long_average=1.3010,
                        decision="SELL",
                        confidence=0.72,
                        reason="Sinal fake.",
                        atr=0.001,
                        tick_volume=1000,
                        timeframe="H1",
                    ),
                    MT5ForexSignalRow(
                        pair="USDJPY",
                        status="OK",
                        last_price=160.0,
                        last_candle_time="2026-06-29T14:00:00+00:00",
                        trend="INDEFINIDA",
                        momentum=0.0,
                        volatility=0.001,
                        rsi=50.0,
                        short_average=160.0,
                        long_average=160.0,
                        decision="WAIT",
                        confidence=0.30,
                        reason="Sinal fake.",
                        atr=0.001,
                        tick_volume=1000,
                        timeframe="H1",
                    ),
                ]
            )
        return MT5ForexSignalDashboard(
            connection_status="CONNECTED",
            timeframe="H1",
            pairs=pairs,
        )

    def _install_certified_research_constants(
        self,
        service: DashboardService,
        pairs: tuple[str, ...],
    ) -> None:
        rows = [
            DashboardMT5HeuristicResearchRowViewModel(
                pair=pair,
                timeframe="H1",
                recommended_heuristic="TREND_MOMENTUM",
                decision="BUY" if pair == "EURUSD" else "SELL",
                score=0.82,
                confidence=0.72,
                ict_score=82.0,
                ict_grade="A",
                ict_status="CERTIFICADA_A",
                ict_usage="Operacao automatica Demo liberada.",
                ict_demo_allowed=True,
                status="APROVADO",
                ideal_timeframe="H1",
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
                    "momentum_threshold": "0.0",
                    "volatility_threshold": "0.0001",
                },
            )
            for pair in pairs
        ]
        object.__setattr__(
            service,
            "mt5_research_constants",
            DashboardMT5HeuristicResearchViewModel(
                rows=rows,
                status="RESEARCH_ONLY",
                timeframe="H1",
                source="TEST_CERTIFIED_RESEARCH",
            ),
        )
        object.__setattr__(
            service,
            "_mt5_research_source_for_reports",
            lambda: service.mt5_research_constants,
        )
        object.__setattr__(
            service,
            "_load_mt5_model3_rr3_snapshot",
            lambda: {},
        )

    def _flat_then_trigger_candles(self, direction: str) -> list[Candle]:
        base = 1.198 if direction == "BUY" else 1.202
        final = 1.2 if direction == "BUY" else 1.2
        candles = [
            Candle(
                data=f"2026-06-29T{index:02d}:00:00+00:00",
                abertura=base,
                maxima=base + 0.001,
                minima=base - 0.001,
                fechamento=base,
                volume=1000,
            )
            for index in range(60)
        ]
        candles.append(
            Candle(
                data="2026-06-29T14:00:00+00:00",
                abertura=base,
                maxima=max(base, final) + 0.001,
                minima=min(base, final) - 0.001,
                fechamento=final,
                volume=1200,
            )
        )
        return candles

    def _prepared(
        self,
        service: DemoExecutionService,
    ):
        return service.prepare_order(
            self._signal("BUY"),
            self._snapshot(),
            RiskDecision(True, "Risco aprovado", 1, 1.0),
            entry_price=100.0,
            stop_points=10.0,
            target_points=20.0,
        )

    def _signal(self, decision: str) -> StrategySignal:
        return StrategySignal(decision, score=90, confidence=0.9, reasons=["ok"])

    def _snapshot(self, datetime_text: str = "2026-06-29 10:00:00") -> MarketSnapshot:
        return MarketSnapshot(
            symbol="WDO",
            datetime=datetime_text,
            regime="TREND",
            volatility=1.0,
            liquidity=1.0,
            trend_strength=1.0,
            market_dna_score=100.0,
        )


class _AcceptingProvider:
    def __init__(self) -> None:
        self.orders: list[ExecutionOrder] = []
        self.close_requests: list[dict[str, object]] = []

    def has_open_position(self, symbol: str) -> bool:
        return False

    def get_open_position(self, symbol: str) -> object | None:
        return None

    def get_current_price(self, symbol: str) -> float | None:
        return None

    def get_recent_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> list[object]:
        return []

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
    ) -> ExecutionResult:
        return ExecutionResult(True, "ACCEPTED", "sl")

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> ExecutionResult:
        self.close_requests.append(
            {
                "symbol": symbol,
                "ticket": ticket,
                "side": side,
                "volume": volume,
                "reason": reason,
            }
        )
        return ExecutionResult(True, "ACCEPTED", "closed", ticket=ticket)

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        self.orders.append(order)
        return ExecutionResult(True, "ACCEPTED", "demo", ticket=123)


class _PositionOpenProvider(_AcceptingProvider):
    def has_open_position(self, symbol: str) -> bool:
        return True


if __name__ == "__main__":
    unittest.main()
