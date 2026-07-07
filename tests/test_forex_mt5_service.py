import unittest

from application.forex_mt5_service import ForexMT5Service


class ForexMT5ServiceTest(unittest.TestCase):
    def test_returns_readonly_status_and_mock_signals(self) -> None:
        service = ForexMT5Service()

        status = service.get_status()
        signals = service.get_signals()

        self.assertEqual(status.status, "READ_ONLY_MOCK")
        self.assertGreaterEqual(len(signals), 1)
        self.assertTrue(all(signal.decision == "WAIT" for signal in signals))
