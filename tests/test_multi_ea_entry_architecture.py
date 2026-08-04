from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from research.multi_ea_entry_architecture import MultiEAEntryArchitectureEngine
from research.multi_ea_trading_lab import MultiEATradePosition


UTC = timezone.utc


def _position(
    row: int,
    symbol: str,
    direction: str,
    when: datetime,
    price: float,
    volume: float = 0.01,
) -> MultiEATradePosition:
    return MultiEATradePosition(
        source_symbol=symbol,
        symbol=symbol,
        direction=direction,
        volume=volume,
        open_time=when,
        open_price=price,
        close_time=when + timedelta(days=1),
        close_price=price + 99.0,
        commission=-99.0,
        swap=-99.0,
        profit=-999.0,
        source_row=row,
        position_id=f"P{row}",
    )


class MultiEAEntryArchitectureEngineTest(unittest.TestCase):
    def test_detects_split_hedge_grid_pyramiding_and_basket(self) -> None:
        start = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
        positions = [
            _position(1, "EURUSD", "BUY", start, 1.10000),
            _position(2, "EURUSD", "BUY", start + timedelta(seconds=5), 1.10001),
            _position(3, "EURUSD", "SELL", start + timedelta(seconds=8), 1.10002),
            _position(4, "GBPUSD", "SELL", start + timedelta(seconds=20), 1.25000),
            _position(5, "EURUSD", "SELL", start + timedelta(minutes=30), 1.10100),
            _position(6, "EURUSD", "SELL", start + timedelta(minutes=60), 1.09900),
        ]

        report = MultiEAEntryArchitectureEngine().analyze(positions)

        mechanics = [row["primary_mechanic"] for row in report["entry_records"]]
        self.assertEqual(
            mechanics,
            [
                "SEED",
                "SPLIT_TICKET",
                "HEDGE_PAIR",
                "SEED",
                "GRID_AVERAGING",
                "PYRAMIDING",
            ],
        )
        self.assertEqual(
            report["observed_architecture"]["account_mode"],
            "HEDGING_COMPATIBLE",
        )
        self.assertEqual(report["evidence"]["cross_asset_basket_followers"], 1)
        self.assertFalse(report["uses_exit_data"])
        self.assertFalse(report["uses_profit_data"])

    def test_result_is_invariant_to_close_and_profit_fields(self) -> None:
        start = datetime(2026, 2, 1, 8, 0, tzinfo=UTC)
        positions = [
            _position(1, "XAUUSD", "SELL", start, 4100.0),
            _position(2, "XAUUSD", "SELL", start + timedelta(minutes=20), 4104.0),
        ]
        changed = [
            replace(
                item,
                close_time=item.close_time + timedelta(days=50),
                close_price=item.close_price * 10,
                commission=123.0,
                swap=456.0,
                profit=789.0,
            )
            for item in positions
        ]

        engine = MultiEAEntryArchitectureEngine()
        self.assertEqual(engine.analyze(positions), engine.analyze(changed))

    def test_empty_report_and_base_lot_mode_are_deterministic(self) -> None:
        engine = MultiEAEntryArchitectureEngine()
        self.assertEqual(engine.analyze([])["status"], "SEM_ENTRADAS")

        start = datetime(2026, 3, 1, tzinfo=UTC)
        report = engine.analyze(
            [
                _position(1, "AUDUSD", "BUY", start, 0.7, 0.02),
                _position(2, "AUDUSD", "BUY", start + timedelta(days=1), 0.71, 0.01),
                _position(3, "AUDUSD", "BUY", start + timedelta(days=2), 0.72, 0.01),
            ]
        )
        self.assertEqual(report["observed_architecture"]["base_lot"], 0.01)
        self.assertEqual(
            report["observed_architecture"]["base_lot_share_percent"],
            66.666667,
        )


if __name__ == "__main__":
    unittest.main()
