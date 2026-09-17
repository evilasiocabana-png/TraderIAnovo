"""Permission regressions: all transport calls use an in-memory MT5 fake."""

from types import SimpleNamespace
from unittest.mock import patch
import unittest

from core.mt5_permissions import read_permissions, permissions_allowed
from tests import test_mt5_real_execution_account as fixtures


class MT5PermissionsTest(unittest.TestCase):
    def make(self, real=False):
        fixture = fixtures.MT5RealAccountTest()
        if real:
            return fixture.real()
        mt5 = fixtures._FakeMT5()
        provider, order = fixture.provider(mt5)
        return mt5, provider, order

    def test_each_permission_blocks_both_modes(self):
        for real in (False, True):
            for method, field, value in (
                ("terminal_info", "connected", False),
                ("terminal_info", "trade_allowed", False),
                ("terminal_info", "tradeapi_disabled", True),
                ("account_info", "trade_allowed", False),
                ("account_info", "trade_expert", False),
            ):
                with self.subTest(real=real, field=field):
                    mt5, provider, order = self.make(real)
                    info = getattr(mt5, method)()
                    setattr(info, field, value)
                    with patch.object(mt5, method, return_value=info):
                        result = provider.submit_order(order)
                    self.assertFalse(result.accepted)
                    self.assertIsNone(mt5.last_request)
                    self.assertIn("Algotrading:", result.message)

    def test_unknown_or_unreadable_permissions_fail_closed(self):
        mt5, provider, _ = self.make()
        for info in (None, SimpleNamespace(connected=True)):
            with patch.object(mt5, "terminal_info", return_value=info):
                self.assertFalse(permissions_allowed(read_permissions(mt5)))
                result = provider._result_from_response(provider._order_send({}))
                self.assertIn("INDISPONIVEL", result.message)
        with patch.object(mt5, "terminal_info", side_effect=RuntimeError("offline")):
            self.assertFalse(permissions_allowed(read_permissions(mt5)))
        self.assertIsNone(mt5.last_request)

    def test_permission_change_during_preflight_blocks_all_actions(self):
        for action in (5, 6, 7, 8):
            with self.subTest(action=action):
                mt5, provider, _ = self.make()
                terminal = mt5.terminal_info()
                mt5.terminal_info = lambda: terminal
                def check(request):
                    terminal.trade_allowed = False
                    return SimpleNamespace(retcode=0)
                mt5.order_check = check
                result = provider._result_from_response(provider._order_send({"action": action}))
                self.assertFalse(result.accepted)
                self.assertIn("Algotrading: DESLIGADO", result.message)
                self.assertIsNone(mt5.last_request)

    def test_broker_rejection_and_empty_response_include_current_status(self):
        mt5, provider, _ = self.make()
        for response in (None, SimpleNamespace(retcode=10027, comment="Client disables autotrading")):
            result = provider._result_from_response(response)
            self.assertFalse(result.accepted)
            self.assertIn("Algotrading: LIGADO", result.message)
            self.assertIn("API Python: PERMITIDA", result.message)

    def test_rejection_log_contains_permission_snapshot(self):
        import json
        mt5, provider, order = self.make()
        terminal = mt5.terminal_info()
        terminal.trade_allowed = False
        mt5.terminal_info = lambda: terminal
        provider.submit_order(order)
        record = json.loads(provider.log_path.read_text().splitlines()[-1])
        self.assertFalse(record["mt5_permissions_at_log"]["algotrading"])
