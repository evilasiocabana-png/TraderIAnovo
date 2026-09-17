"""Real-mode transport tests using only the in-memory MT5 fake."""

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from core.mt5_execution_account import MT5ExecutionAccount
from tests.test_mt5_demo_execution_provider import MT5DemoExecutionProviderTest, _FakeMT5


class MT5RealAccountTest(unittest.TestCase):
    def provider(self, mt5):
        fixture = MT5DemoExecutionProviderTest()
        return fixture._provider(mt5), fixture._order()

    def real(self):
        mt5 = _FakeMT5(trade_mode=2)
        mt5.ACCOUNT_TRADE_MODE_REAL = 2
        mt5.account_info = lambda: SimpleNamespace(
            trade_mode=2, login=123, server="Test-Live", trade_allowed=True, trade_expert=True,
            balance=15000,
        )
        provider, order = self.provider(mt5)
        provider.execution_account = MT5ExecutionAccount("REAL", "123", "Test-Live", True)
        return mt5, provider, order

    def test_same_order_geometry_and_volume_in_real_and_demo(self):
        demo = _FakeMT5()
        dp, order = self.provider(demo)
        dp.execution_account = MT5ExecutionAccount()
        real, rp, _ = self.real()
        self.assertTrue(dp.submit_order(order).accepted)
        self.assertTrue(rp.submit_order(order).accepted)
        self.assertEqual(demo.last_request, real.last_request)

    def test_real_requires_explicit_enable_and_identity(self):
        for policy in (MT5ExecutionAccount(), MT5ExecutionAccount("REAL"),
                       MT5ExecutionAccount("REAL", "999", "Test-Live", True),
                       MT5ExecutionAccount("REAL", "123", "Wrong", True)):
            mt5, provider, order = self.real()
            provider.execution_account = policy
            self.assertFalse(provider.submit_order(order).accepted)
            self.assertIsNone(mt5.last_request)

    def test_account_switch_during_order_check_is_blocked(self):
        mt5, provider, order = self.real()
        def check(request):
            mt5.account_info = lambda: SimpleNamespace(trade_mode=0)
            return SimpleNamespace(retcode=0)
        mt5.order_check = check
        self.assertFalse(provider.submit_order(order).accepted)
        self.assertIsNone(mt5.last_request)

    def test_failed_external_checks_never_send(self):
        for method in ("account_info", "positions_get", "orders_get", "order_check"):
            mt5, provider, order = self.real()
            with patch.object(mt5, method, return_value=None):
                self.assertFalse(provider.submit_order(order).accepted, method)
            self.assertIsNone(mt5.last_request, method)

    def test_unknown_account_mode_fails_closed(self):
        mt5, provider, order = self.real()
        provider.execution_account = MT5ExecutionAccount("AUTO", "123", "Test-Live", True)
        self.assertFalse(provider.submit_order(order).accepted)
        self.assertIsNone(mt5.last_request)

    def test_book_exception_never_sends(self):
        for method in ("positions_get", "orders_get"):
            mt5, provider, order = self.real()
            with patch.object(mt5, method, side_effect=RuntimeError("offline")):
                self.assertFalse(provider.submit_order(order).accepted)
            self.assertIsNone(mt5.last_request)

    def test_real_duplicate_history_ignores_demo(self):
        import json
        mt5, provider, order = self.real()
        provider.log_path.parent.mkdir(parents=True, exist_ok=True)
        provider.log_path.write_text(json.dumps({"accepted": True, "ticket": 1234}) + "\n")
        self.assertEqual(provider._read_execution_log_records(), [])

    def test_previous_executor_is_revoked_after_ui_selection(self):
        import os
        mt5, provider, order = self.real()
        with patch.dict(os.environ, {"TRADERIA_EXECUTION_ACCOUNT_REVISION": "new-selection"}):
            result = provider.submit_order(order)
        self.assertFalse(result.accepted)
        self.assertIn("executor anterior", result.message)
        self.assertIsNone(mt5.last_request)

    def test_explicit_missing_terminal_never_falls_back(self):
        from dataclasses import replace
        mt5, provider, order = self.real()
        provider.execution_account = replace(
            provider.execution_account,
            terminal_path=str(provider.log_path.parent / "missing-terminal.exe"),
        )
        result = provider.submit_order(order)
        self.assertFalse(result.accepted)
        self.assertIn("descoberta automatica bloqueada", result.message)
        self.assertIsNone(mt5.last_request)

    def test_wrong_connected_terminal_is_rejected(self):
        from dataclasses import replace
        mt5, provider, _ = self.real()
        provider.execution_account = replace(
            provider.execution_account, terminal_path=r"C:\expected\terminal64.exe",
        )
        mt5.terminal_info = lambda: SimpleNamespace(path=r"C:\other", connected=True)
        result = provider._demo_account_check()
        self.assertIsNotNone(result)
        self.assertIn("diverge do caminho", result.message)
        self.assertIsNone(mt5.last_request)


if __name__ == "__main__":
    unittest.main()
