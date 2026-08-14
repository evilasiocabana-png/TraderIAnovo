from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

import dashboard_app
from application.mt5_position_profit_peak_store import MT5PositionProfitPeakStore
from application.dashboard_service import DashboardService
from application.dashboard_view_model import (
    DashboardMT5TradeAuditRowViewModel,
    DashboardMT5TradeAuditViewModel,
)


class MT5PositionProfitPeakStoreTest(unittest.TestCase):
    def test_peak_only_moves_up_and_survives_position_close(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MT5PositionProfitPeakStore(Path(directory) / "peaks.sqlite3")
            position = SimpleNamespace(ticket=101, symbol="EURUSD", profit=-4.0)

            first = store.observe_positions([position], observed_at="2026-08-13T10:00:00Z")
            position.profit = 12.5
            second = store.observe_positions([position], observed_at="2026-08-13T10:01:00Z")
            position.profit = 3.0
            third = store.observe_positions([position], observed_at="2026-08-13T10:02:00Z")

            self.assertEqual(first[101].peak_profit, -4.0)
            self.assertEqual(second[101].peak_profit, 12.5)
            self.assertEqual(third[101].peak_profit, 12.5)
            self.assertEqual(third[101].peak_at, "2026-08-13T10:01:00Z")
            self.assertEqual(store.get_many([101])[101].peak_profit, 12.5)

    def test_tickets_are_tracked_independently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MT5PositionProfitPeakStore(Path(directory) / "peaks.sqlite3")
            peaks = store.observe_positions(
                [
                    SimpleNamespace(ticket=201, symbol="XAUUSD", profit=8.0),
                    SimpleNamespace(ticket=202, symbol="XAUUSD", profit=15.0),
                ]
            )

            self.assertEqual(peaks[201].peak_profit, 8.0)
            self.assertEqual(peaks[202].peak_profit, 15.0)

    def test_close_raises_tracked_peak_but_does_not_backfill_old_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MT5PositionProfitPeakStore(Path(directory) / "peaks.sqlite3")
            store.observe_positions(
                [SimpleNamespace(ticket=250, symbol="XAUUSD", profit=19.0)],
                observed_at="2026-08-13T10:00:00Z",
            )

            raised = store.raise_existing_peaks(
                [
                    (250, "XAUUSD", 32.1, "2026-08-13T10:00:08Z"),
                    (999, "EURUSD", 5.0, "2026-08-13T10:00:08Z"),
                ]
            )

            self.assertEqual(raised[250].peak_profit, 32.1)
            self.assertEqual(raised[250].peak_at, "2026-08-13T10:00:08Z")
            self.assertNotIn(999, store.get_many([999]))

    def test_closed_report_row_keeps_peak_by_ticket(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = MT5PositionProfitPeakStore(Path(directory) / "peaks.sqlite3")
            store.observe_positions(
                [SimpleNamespace(ticket=301, symbol="GBPUSD", profit=21.75)],
                observed_at="2026-08-13T11:00:00Z",
            )
            service = object.__new__(DashboardService)
            object.__setattr__(service, "mt5_position_profit_peak_store", store)
            report = DashboardMT5TradeAuditViewModel(
                rows=[
                    DashboardMT5TradeAuditRowViewModel(
                        mt5_ticket=301,
                        operation_status="FECHADA/HISTORICO",
                        mt5_realized_profit=-2.0,
                    )
                ]
            )

            merged = service._with_mt5_position_profit_peaks(report)

            self.assertEqual(merged.rows[0].mt5_peak_open_profit, 21.75)
            self.assertEqual(
                merged.rows[0].mt5_peak_open_profit_at,
                "2026-08-13T11:00:00Z",
            )

            visible = dashboard_app._mt5_trade_audit_compact_row(merged.rows[0])
            exported = dashboard_app._mt5_trade_audit_csv_row(merged.rows[0], {})
            self.assertEqual(visible["Pico lucro aberto"], "21.75")
            self.assertEqual(exported["Pico lucro aberto"], "21.75")
            self.assertEqual(
                exported["Horario pico lucro"],
                "2026-08-13T11:00:00Z",
            )


if __name__ == "__main__":
    unittest.main()
