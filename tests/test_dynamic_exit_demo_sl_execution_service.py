"""Testes da execucao assistida de SL demo para saida dinamica."""

import unittest

from application.dynamic_exit_demo_sl_execution_service import (
    DynamicExitDemoSLExecutionService,
)
from domain.contracts.dynamic_exit_demo_sl import DynamicExitDemoSLExecutionResult
from domain.contracts.dynamic_exit_simulation import DynamicExitSimulationDecision


class DynamicExitDemoSLExecutionServiceTest(unittest.TestCase):
    def test_default_desligado_nao_chama_provider(self) -> None:
        provider = _Provider()
        result = DynamicExitDemoSLExecutionService().execute_assisted(
            decision=self._decision(),
            executor=provider,
            current_price=1.1030,
        )

        self.assertFalse(result.allowed)
        self.assertFalse(result.submitted)
        self.assertEqual(provider.calls, 0)

    def test_conta_nao_demo_rejeita_antes_do_provider(self) -> None:
        provider = _Provider()
        result = DynamicExitDemoSLExecutionService().execute_assisted(
            decision=self._decision(),
            executor=provider,
            enabled=True,
            user_confirmed=True,
            robot_armed=True,
            demo_account_confirmed=False,
            current_price=1.1030,
        )

        self.assertFalse(result.allowed)
        self.assertIn("Conta demo", " ".join(result.rejection_reasons))
        self.assertEqual(provider.calls, 0)

    def test_buy_nao_permite_sl_menor_que_stop_atual(self) -> None:
        result = self._execute(self._decision(approved_stop=1.0970))

        self.assertFalse(result.success)
        self.assertIn("BUY nao permite", " ".join(result.rejection_reasons))

    def test_sell_nao_permite_sl_maior_que_stop_atual(self) -> None:
        result = self._execute(
            self._decision(side="SELL", current_stop=1.1030, approved_stop=1.1040),
            current_price=1.0970,
        )

        self.assertFalse(result.success)
        self.assertIn("SELL nao permite", " ".join(result.rejection_reasons))

    def test_candidato_que_cruza_preco_atual_rejeita(self) -> None:
        result = self._execute(self._decision(approved_stop=1.1040), current_price=1.1030)

        self.assertFalse(result.success)
        self.assertIn("preco atual", " ".join(result.rejection_reasons))

    def test_candidato_irrelevante_rejeita(self) -> None:
        result = self._execute(self._decision(approved_stop=1.098000001))

        self.assertFalse(result.success)
        self.assertIn("irrelevante", " ".join(result.rejection_reasons))

    def test_nao_chama_abertura_ou_fechamento_de_ordem(self) -> None:
        provider = _Provider()
        result = self._execute(self._decision(), provider=provider)

        self.assertTrue(result.success)
        self.assertEqual(provider.submit_order_calls, 0)
        self.assertEqual(provider.close_position_calls, 0)

    def test_confirmacao_assistida_chama_apenas_modificacao_de_sl(self) -> None:
        provider = _Provider()
        result = self._execute(self._decision(), provider=provider)

        self.assertTrue(result.success)
        self.assertEqual(provider.calls, 1)
        self.assertEqual(provider.last_requested_stop, 1.1000)

    def test_falha_da_api_fica_registrada_em_auditoria(self) -> None:
        service = DynamicExitDemoSLExecutionService()
        result = self._execute(self._decision(), service=service, provider=_Provider(success=False))

        self.assertFalse(result.success)
        self.assertEqual(service.list_audit_log()[-1].message, "api failed")

    def test_chamada_repetida_na_mesma_vela_rejeita(self) -> None:
        service = DynamicExitDemoSLExecutionService()
        first = self._execute(self._decision(), service=service)
        second = self._execute(self._decision(), service=service)

        self.assertTrue(first.success)
        self.assertFalse(second.success)
        self.assertIn("ja registrada", " ".join(second.rejection_reasons))

    def test_decisao_simulada_rejeitada_nao_executa(self) -> None:
        provider = _Provider()
        decision = self._decision(allowed=False)
        result = self._execute(decision, provider=provider)

        self.assertFalse(result.allowed)
        self.assertEqual(provider.calls, 0)

    def _execute(
        self,
        decision: DynamicExitSimulationDecision,
        *,
        service: DynamicExitDemoSLExecutionService | None = None,
        provider: "_Provider | None" = None,
        current_price: float = 1.1030,
    ) -> DynamicExitDemoSLExecutionResult:
        service = service or DynamicExitDemoSLExecutionService()
        provider = provider or _Provider()
        return service.execute_assisted(
            decision=decision,
            executor=provider,
            enabled=True,
            user_confirmed=True,
            robot_armed=True,
            demo_account_confirmed=True,
            current_price=current_price,
        )

    def _decision(
        self,
        *,
        side: str = "BUY",
        current_stop: float = 1.0980,
        approved_stop: float = 1.1000,
        allowed: bool = True,
    ) -> DynamicExitSimulationDecision:
        return DynamicExitSimulationDecision(
            symbol="EURUSD",
            ticket=123,
            side=side,
            current_stop=current_stop,
            approved_stop=approved_stop,
            allowed_to_simulate=allowed,
            candle_key="2026-07-07T19:00:00",
        )


class _Provider:
    def __init__(self, success: bool = True) -> None:
        self.success = success
        self.calls = 0
        self.submit_order_calls = 0
        self.close_position_calls = 0
        self.last_requested_stop = None

    def modify_demo_position_stop_loss(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        requested_stop: float,
        decision_key: str = "N/D",
    ) -> DynamicExitDemoSLExecutionResult:
        self.calls += 1
        self.last_requested_stop = requested_stop
        return DynamicExitDemoSLExecutionResult(
            symbol=symbol,
            ticket=ticket,
            side=side,
            requested_stop=requested_stop,
            previous_stop=1.0980,
            new_stop=requested_stop if self.success else None,
            allowed=True,
            submitted=True,
            success=self.success,
            retcode="DONE" if self.success else "10030",
            message="done" if self.success else "api failed",
        )


if __name__ == "__main__":
    unittest.main()
