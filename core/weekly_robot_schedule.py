"""Deterministic weekly operating window for the TraderIA Demo robot."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


BRAZIL_TIMEZONE = ZoneInfo("America/Sao_Paulo")
FRIDAY_CLOSE = time(17, 30)
SUNDAY_OPEN = time(23, 30)


@dataclass(frozen=True)
class WeeklyRobotScheduleDecision:
    operating: bool
    status: str
    reason: str
    evaluated_at_brt: str
    next_transition_brt: str


def weekly_robot_schedule_decision(
    now: datetime | None = None,
) -> WeeklyRobotScheduleDecision:
    """Return the fixed Sunday 23:30 to Friday 17:30 BRT window."""
    local = _as_brazil_time(now or datetime.now(tz=BRAZIL_TIMEZONE))
    weekday = local.weekday()
    clock = local.time().replace(tzinfo=None)
    operating = (
        weekday in {0, 1, 2, 3}
        or (weekday == 4 and clock < FRIDAY_CLOSE)
        or (weekday == 6 and clock >= SUNDAY_OPEN)
    )
    if operating:
        status = "WEEKLY_WINDOW_OPEN"
        reason = (
            "Robo deve permanecer ligado de domingo 23:30 ate sexta 17:30 "
            "no horario de Brasilia."
        )
        transition = _next_friday_close(local)
    else:
        status = "WEEKLY_WINDOW_CLOSED"
        reason = (
            "Robo deve permanecer desligado e sem posicoes entre sexta 17:30 "
            "e domingo 23:30 no horario de Brasilia."
        )
        transition = _next_sunday_open(local)
    return WeeklyRobotScheduleDecision(
        operating=operating,
        status=status,
        reason=reason,
        evaluated_at_brt=local.isoformat(),
        next_transition_brt=transition.isoformat(),
    )


def _as_brazil_time(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=BRAZIL_TIMEZONE)
    return value.astimezone(BRAZIL_TIMEZONE)


def _next_friday_close(local: datetime) -> datetime:
    days = (4 - local.weekday()) % 7
    candidate = datetime.combine(
        (local + timedelta(days=days)).date(),
        FRIDAY_CLOSE,
        tzinfo=BRAZIL_TIMEZONE,
    )
    if candidate <= local:
        candidate += timedelta(days=7)
    return candidate


def _next_sunday_open(local: datetime) -> datetime:
    days = (6 - local.weekday()) % 7
    candidate = datetime.combine(
        (local + timedelta(days=days)).date(),
        SUNDAY_OPEN,
        tzinfo=BRAZIL_TIMEZONE,
    )
    if candidate <= local:
        candidate += timedelta(days=7)
    return candidate
