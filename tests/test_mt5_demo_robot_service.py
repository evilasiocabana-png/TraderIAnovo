"""Testes do robo temporal MT5 Demo."""

import unittest

from application.demo_execution_service import DemoExecutionService
from application.mt5_demo_robot_service import (
    MT5DemoRobotService,
    MT5DemoRobotSignal,
    MT5DemoTradePlan,
)
from domain.contracts.execution_order import ExecutionOrder
from domain.contracts.execution_result import ExecutionResult


class MT5DemoRobotServiceTest(unittest.TestCase):
    """Valida separacao entre execucao manual e robo temporal."""

    def test_kill_switch_bloqueia_execucao(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=False,
        )

        result = service.evaluate_once(self._signal("BUY"), self._plan("BUY"))

        self.assertEqual(result.status, "DISABLED")
        self.assertFalse(result.executed)
        self.assertEqual(provider.orders, [])

    def test_executa_buy_atual_com_plano_research_valido(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )
        plan = self._plan("BUY")

        result = service.evaluate_once(self._signal("BUY"), plan)

        self.assertEqual(result.status, "EXECUTED")
        self.assertTrue(result.executed)
        self.assertEqual(len(provider.orders), 1)
        order = provider.orders[0]
        self.assertEqual(order.quantity, 0.1)
        self.assertEqual(order.entry_price, plan.entry_price)
        self.assertEqual(order.stop, plan.stop)
        self.assertEqual(order.target, plan.target)
        self.assertEqual(order.beta_id, "LEGACY_CURRENT_EXIT")
        self.assertEqual(order.beta_mode, "PROTECT_ONLY")
        audit = service.execution_service.list_audit_log()[0]
        self.assertEqual(audit.alpha_id, "ALPHA007")
        self.assertEqual(audit.alpha_version, "v1.6")
        self.assertEqual(audit.beta_id, "LEGACY_CURRENT_EXIT")
        self.assertEqual(audit.beta_mode, "PROTECT_ONLY")
        self.assertEqual(audit.session_policy_version, "v2.1")
        self.assertEqual(audit.execution_pipeline_version, "v3.4")
        self.assertEqual(audit.lab_configuration_version, "v8")
        self.assertEqual(audit.trade_plan_version, "TP v5")
        self.assertEqual(audit.execution_engine_version, "ExecutionEngine v1")
        self.assertEqual(audit.indicator_bundle_version, "Indicators v9")
        self.assertEqual(audit.microstructure_version, "Micro v2")
        self.assertEqual(audit.validation_pipeline_version, "VAL v4")
        self.assertEqual(audit.strategy_definition_version, "STRAT v3")
        self.assertAlmostEqual(audit.technical_score, 0.70)
        self.assertAlmostEqual(audit.historical_confirmation, 0.68)
        self.assertEqual(audit.entry_price, plan.entry_price)
        self.assertEqual(audit.stop, plan.stop)
        self.assertEqual(audit.target, plan.target)
        self.assertEqual(audit.risk_reward, plan.risk_reward)
        self.assertEqual(audit.candle_time, "2026-06-29T10:00:00+00:00")

    def test_nao_reopera_mesmo_candle(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )
        signal = self._signal("BUY")
        plan = self._plan("BUY")

        first = service.evaluate_once(signal, plan)
        second = service.evaluate_once(signal, plan)

        self.assertEqual(first.status, "EXECUTED")
        self.assertEqual(second.status, "NO_NEW_CANDLE")
        self.assertEqual(len(provider.orders), 1)

    def test_rejeicao_transitoria_nao_consumir_candle(self) -> None:
        provider = _RejectingProvider(
            ExecutionResult(
                False,
                "REJECTED",
                "Plano MT5 Demo stale: preco atual tornou SL/TP invalidos.",
            )
        )
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )
        signal = self._signal("BUY")
        plan = self._plan("BUY")

        first = service.evaluate_once(signal, plan)
        second = service.evaluate_once(signal, plan)

        self.assertEqual(first.status, "REJECTED")
        self.assertEqual(second.status, "REJECTED")
        self.assertEqual(provider.calls, 2)
        self.assertEqual(service.last_candle_by_market, {})

    def test_autotrading_desligado_nao_consumir_candle(self) -> None:
        provider = _RejectingProvider(
            ExecutionResult(
                False,
                "REJECTED",
                "AutoTrading disabled by client",
            )
        )
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )
        signal = self._signal("SELL")
        plan = self._plan("SELL")

        first = service.evaluate_once(signal, plan)
        second = service.evaluate_once(signal, plan)

        self.assertEqual(first.status, "REJECTED")
        self.assertEqual(second.status, "REJECTED")
        self.assertEqual(provider.calls, 2)
        self.assertEqual(service.last_candle_by_market, {})

    def test_autoriza_novo_candle_quando_sinal_continua_valido(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )

        first = service.evaluate_once(
            self._signal("BUY", candle_time="2026-06-29T10:00:00+00:00"),
            self._plan("BUY"),
        )
        second = service.evaluate_once(
            self._signal("BUY", candle_time="2026-06-29T11:00:00+00:00"),
            self._plan("BUY"),
        )

        self.assertEqual(first.status, "EXECUTED")
        self.assertEqual(second.status, "EXECUTED")
        self.assertEqual(len(provider.orders), 2)

    def test_bloqueia_regime_indefinido(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )

        result = service.evaluate_once(
            MT5DemoRobotSignal(
                symbol="EURUSD",
                timeframe="H1",
                candle_time="2026-06-29T10:00:00+00:00",
                decision="BUY",
                confidence=0.70,
                active_model="TREND_MOMENTUM",
                reason="Sem estrutura.",
                trend="INDEFINIDA",
            ),
            self._plan("BUY"),
        )

        self.assertEqual(result.status, "REGIME_INDEFINIDO")
        self.assertFalse(result.executed)
        self.assertEqual(provider.orders, [])

    def test_wait_atualiza_estado_e_permite_proximo_gatilho(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )

        wait = service.evaluate_once(
            self._signal("WAIT", candle_time="2026-06-29T10:00:00+00:00"),
            self._plan("BUY"),
        )
        buy = service.evaluate_once(
            self._signal("BUY", candle_time="2026-06-29T11:00:00+00:00"),
            self._plan("BUY"),
        )

        self.assertEqual(wait.status, "NO_SIGNAL")
        self.assertEqual(buy.status, "EXECUTED")
        self.assertEqual(len(provider.orders), 1)

    def test_rejeita_plano_que_nao_veio_do_research_lab(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )
        plan = MT5DemoTradePlan(
            symbol="EURUSD",
            timeframe="H1",
            entry_price=1.1,
            stop=1.09,
            target=1.12,
            risk_reward=2.0,
            source="DASHBOARD",
        )

        result = service.evaluate_once(self._signal("BUY"), plan)

        self.assertEqual(result.status, "NO_TRADE_PLAN")
        self.assertEqual(provider.orders, [])

    def test_bloqueia_sinal_com_bloqueio_temporal(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )

        result = service.evaluate_once(
            self._signal(
                "BUY",
                temporal_blocked=True,
                temporal_status="ROLLOVER_BLOQUEADO",
            ),
            self._plan("BUY"),
        )

        self.assertEqual(result.status, "TEMPORAL_BLOCKED")
        self.assertEqual(provider.orders, [])

    def test_ignora_bloqueio_temporal_quando_filtro_de_sessao_desligado(self) -> None:
        provider = _AcceptingProvider()
        service = MT5DemoRobotService(
            execution_service=DemoExecutionService(provider=provider),
            enabled=True,
        )

        result = service.evaluate_once(
            self._signal(
                "BUY",
                temporal_blocked=True,
                temporal_status="ROLLOVER_BLOQUEADO",
                session_filter_enabled=False,
                session_filter_result="IGNORED",
            ),
            self._plan("BUY"),
        )

        self.assertEqual(result.status, "EXECUTED")
        self.assertEqual(len(provider.orders), 1)
        audit = service.execution_service.list_audit_log()[0]
        self.assertFalse(audit.session_filter_enabled)
        self.assertEqual(audit.session_filter_result, "IGNORED")
        self.assertEqual(audit.forex_session, "ROLLOVER")
        self.assertFalse(audit.forex_session_open)
        self.assertTrue(audit.is_rollover)

    def _signal(
        self,
        decision: str,
        candle_time: str = "2026-06-29T10:00:00+00:00",
        temporal_blocked: bool = False,
        temporal_status: str = "SESSAO_FAVORAVEL",
        session_filter_enabled: bool = True,
        session_filter_result: str = "ALLOWED",
    ) -> MT5DemoRobotSignal:
        return MT5DemoRobotSignal(
            symbol="EURUSD",
            timeframe="H1",
            candle_time=candle_time,
            decision=decision,
            confidence=0.70,
            active_model="TREND_MOMENTUM",
            reason="Transicao temporal valida.",
            alpha_id="ALPHA007",
            alpha_version="v1.6",
            technical_score=0.70,
            historical_confirmation=0.68,
            temporal_blocked=temporal_blocked,
            temporal_status=temporal_status,
            temporal_reason=temporal_status,
            session_filter_enabled=session_filter_enabled,
            session_filter_result=session_filter_result,
            session_filter_reason=(
                "Session Filter Disabled"
                if not session_filter_enabled
                else temporal_status
            ),
            forex_session=(
                "ROLLOVER" if temporal_status == "ROLLOVER_BLOQUEADO" else "LONDON"
            ),
            forex_session_open=not temporal_blocked,
            timestamp_utc=candle_time,
            timestamp_brt="2026-06-29T07:00:00-03:00",
            weekday="MONDAY",
            is_rollover=temporal_status == "ROLLOVER_BLOQUEADO",
            is_london_ny_overlap=False,
            is_sunday_open=False,
            is_friday_late=False,
            last_price=1.1,
            trend="BAIXA" if decision == "SELL" else "ALTA",
            momentum=-0.001 if decision == "SELL" else 0.001,
            rsi=45.0 if decision == "SELL" else 55.0,
            short_average=1.099 if decision != "SELL" else 1.101,
            long_average=1.095 if decision != "SELL" else 1.105,
            ema_fast=1.099 if decision != "SELL" else 1.101,
            ema_mid=1.098 if decision != "SELL" else 1.102,
            ema_slow=1.095 if decision != "SELL" else 1.105,
            atr=0.002,
        )

    def _plan(self, decision: str) -> MT5DemoTradePlan:
        if decision == "SELL":
            return MT5DemoTradePlan(
                symbol="EURUSD",
                timeframe="H1",
                entry_price=1.1,
                stop=1.11,
                target=1.08,
                risk_reward=2.0,
            )
        return MT5DemoTradePlan(
            symbol="EURUSD",
            timeframe="H1",
            entry_price=1.1,
            stop=1.09,
            target=1.12,
            risk_reward=2.0,
        )


class _AcceptingProvider:
    def __init__(self) -> None:
        self.orders: list[ExecutionOrder] = []

    def has_open_position(self, symbol: str) -> bool:
        return False

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        self.orders.append(order)
        return ExecutionResult(True, "ACCEPTED", "demo", ticket=1)


class _RejectingProvider(_AcceptingProvider):
    def __init__(self, result: ExecutionResult) -> None:
        super().__init__()
        self.result = result
        self.calls = 0

    def submit_order(self, order: ExecutionOrder) -> ExecutionResult:
        self.calls += 1
        return self.result


if __name__ == "__main__":
    unittest.main()
