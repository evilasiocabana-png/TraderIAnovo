from __future__ import annotations

from types import SimpleNamespace
import unittest

from research.forex_time_layer import ForexTimeLayer
from research.post_rollover_analyzer import (
    POST_ROLLOVER_ALPHA_ID,
    POST_ROLLOVER_EVENT,
    PostRolloverAnalyzer,
)


class PostRolloverAnalyzerTest(unittest.TestCase):
    def test_bloqueia_enquanto_guard_rollover_esta_ativo(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-09T00:02:00+00:00",
            server_timestamp="2026-07-09T00:02:00+00:00",
        )

        decision = PostRolloverAnalyzer().analyze(self._row(), context)

        self.assertEqual(decision.alpha_id, POST_ROLLOVER_ALPHA_ID)
        self.assertEqual(decision.event_type, POST_ROLLOVER_EVENT)
        self.assertEqual(decision.decision, "WAIT")
        self.assertEqual(decision.skip_reason, "ROLLOVER_GUARD_ACTIVE")

    def test_aprova_continuacao_quando_liquidez_normaliza_e_momentum_volta(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-09T00:12:00+00:00",
            server_timestamp="2026-07-09T00:12:00+00:00",
        )

        decision = PostRolloverAnalyzer().analyze(self._row(), context)

        self.assertEqual(decision.status, "POST_ROLLOVER_TRADE_READY")
        self.assertEqual(decision.context, "CONTINUATION_CANDIDATE")
        self.assertEqual(decision.decision, "BUY")
        self.assertIsNotNone(decision.stop)
        self.assertIsNotNone(decision.target)
        self.assertEqual(decision.risk_reward, 3.0)

    def test_skip_quando_spread_pos_rollover_ainda_alto(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-09T00:12:00+00:00",
            server_timestamp="2026-07-09T00:12:00+00:00",
        )
        row = self._row(spread=0.0005, spread_average=0.0001)

        decision = PostRolloverAnalyzer().analyze(row, context)

        self.assertEqual(decision.context, "SPREAD_TOO_HIGH_SKIP")
        self.assertEqual(decision.decision, "WAIT")

    def test_fora_da_janela_segue_fluxo_normal(self) -> None:
        context = ForexTimeLayer().classify(
            "EURUSD",
            "2026-07-09T03:00:00+00:00",
            server_timestamp="2026-07-09T03:00:00+00:00",
        )

        decision = PostRolloverAnalyzer().analyze(self._row(), context)

        self.assertEqual(decision.mode, "NORMAL_LAB_FLOW")
        self.assertEqual(decision.decision, "WAIT")

    def _row(self, **overrides: object) -> SimpleNamespace:
        data = {
            "pair": "EURUSD",
            "timeframe": "M1",
            "trend": "ALTA",
            "momentum": 0.001,
            "atr": 0.0008,
            "volatility": 0.0004,
            "spread": 0.0001,
            "spread_average": 0.0001,
            "tick_volume": 80,
            "last_price": 1.1000,
            "theoretical_entry_price": 1.1000,
        }
        data.update(overrides)
        return SimpleNamespace(**data)


if __name__ == "__main__":
    unittest.main()
