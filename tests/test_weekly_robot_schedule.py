from __future__ import annotations

import unittest
from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

from application.dashboard_service import DashboardService
from core.weekly_robot_schedule import weekly_robot_schedule_decision


BRT = ZoneInfo("America/Sao_Paulo")


class WeeklyRobotScheduleTest(unittest.TestCase):
    def test_friday_before_1730_is_operating(self) -> None:
        decision = weekly_robot_schedule_decision(
            datetime(2026, 7, 31, 17, 29, 59, tzinfo=BRT)
        )
        self.assertTrue(decision.operating)
        self.assertEqual(decision.status, "WEEKLY_WINDOW_OPEN")

    def test_friday_at_1730_is_closed(self) -> None:
        decision = weekly_robot_schedule_decision(
            datetime(2026, 7, 31, 17, 30, tzinfo=BRT)
        )
        self.assertFalse(decision.operating)
        self.assertIn("2026-08-02T18:01:00", decision.next_transition_brt)

    def test_sunday_before_1801_is_closed(self) -> None:
        decision = weekly_robot_schedule_decision(
            datetime(2026, 8, 2, 18, 0, 59, tzinfo=BRT)
        )
        self.assertFalse(decision.operating)

    def test_sunday_at_1801_is_operating(self) -> None:
        decision = weekly_robot_schedule_decision(
            datetime(2026, 8, 2, 18, 1, tzinfo=BRT)
        )
        self.assertTrue(decision.operating)
        self.assertIn("2026-08-07T17:30:00", decision.next_transition_brt)

    def test_starting_late_on_sunday_keeps_window_operating(self) -> None:
        decision = weekly_robot_schedule_decision(
            datetime(2026, 8, 2, 22, 45, tzinfo=BRT)
        )
        self.assertTrue(decision.operating)
        self.assertEqual(decision.status, "WEEKLY_WINDOW_OPEN")

    def test_close_all_demo_positions_closes_each_ticket(self) -> None:
        execution = _FakeExecutionService()
        service = DashboardService.__new__(DashboardService)
        object.__setattr__(service, "demo_robot_execution_service", execution)
        object.__setattr__(service, "_mt5_demo_execution_enabled", lambda: True)
        object.__setattr__(service, "_enable_mt5_demo_provider", lambda: None)

        result = service.close_all_demo_positions("WEEKLY_TEST")

        self.assertEqual(result["status"], "CLOSED")
        self.assertEqual(result["closed"], 2)
        self.assertEqual(result["remaining"], 0)
        self.assertEqual(execution.reasons, ["WEEKLY_TEST", "WEEKLY_TEST"])


class _FakeExecutionService:
    def __init__(self) -> None:
        self.positions = [
            SimpleNamespace(ticket=101, symbol="EURUSD", volume=0.1, type=0),
            SimpleNamespace(ticket=102, symbol="GBPUSD", volume=0.2, type=1),
        ]
        self.reasons: list[str] = []

    def list_open_positions(self) -> list[object]:
        return list(self.positions)

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> object:
        self.reasons.append(reason)
        self.positions = [
            item for item in self.positions if int(item.ticket) != int(ticket)
        ]
        return SimpleNamespace(
            accepted=True,
            status="ACCEPTED",
            message=f"{symbol}/{side}/{volume}",
        )


if __name__ == "__main__":
    unittest.main()
