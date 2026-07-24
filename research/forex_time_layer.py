"""Camada Tempo para pesquisa Forex."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


BRASILIA_OFFSET = timezone(timedelta(hours=-3))


@dataclass(frozen=True)
class ForexTimeContext:
    """Contexto temporal read-only de um candle Forex."""

    pair: str
    source_timestamp: str
    timestamp_utc: str
    timestamp_brt: str
    hour_utc: int | None
    hour_brt: int | None
    weekday: str
    session: str
    forex_session: str
    session_label: str
    brt_window: str
    is_london_session: bool
    is_new_york_session: bool
    is_asia_session: bool
    is_london_new_york_overlap: bool
    is_london_ny_overlap: bool
    is_rollover_window: bool
    is_rollover: bool
    is_friday_late: bool
    is_sunday_open: bool
    is_off_hours: bool
    temporal_status: str
    temporal_blocked: bool
    temporal_score_adjustment: float
    temporal_reason: str
    preferred_sessions: tuple[str, ...]
    financial_centers: tuple[str, ...]
    quality_note: str
    server_timestamp: str = "N/D"
    server_day: str = "N/D"
    minutes_to_server_rollover: float | None = None
    minutes_from_server_rollover: float | None = None


class ForexTimeLayer:
    """Classifica o contexto temporal sem acessar MT5, UI ou arquivos."""

    WEEKDAYS = (
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
        "SATURDAY",
        "SUNDAY",
    )

    PREFERRED_SESSIONS_BY_PAIR: dict[str, tuple[str, ...]] = {
        "EURUSD": ("LONDON", "LONDON_NEW_YORK_OVERLAP"),
        "GBPUSD": ("LONDON", "LONDON_NEW_YORK_OVERLAP"),
        "USDCHF": ("LONDON", "LONDON_NEW_YORK_OVERLAP", "NEW_YORK"),
        "USDJPY": ("ASIA", "NEW_YORK", "LONDON_NEW_YORK_OVERLAP"),
        "EURJPY": ("ASIA", "LONDON"),
        "AUDUSD": ("ASIA", "NEW_YORK"),
        "NZDUSD": ("ASIA", "NEW_YORK"),
        "USDCAD": ("NEW_YORK", "LONDON_NEW_YORK_OVERLAP"),
    }

    FINANCIAL_CENTERS_BY_PAIR: dict[str, tuple[str, ...]] = {
        "EURUSD": ("Frankfurt", "Londres", "Nova York"),
        "GBPUSD": ("Londres", "Nova York"),
        "USDCHF": ("Zurique", "Londres", "Nova York"),
        "USDJPY": ("Toquio", "Nova York", "Londres"),
        "EURJPY": ("Toquio", "Frankfurt", "Londres"),
        "AUDUSD": ("Sydney", "Toquio", "Nova York"),
        "NZDUSD": ("Wellington", "Sydney", "Toquio", "Nova York"),
        "USDCAD": ("Toronto", "Nova York", "Londres"),
    }

    def classify(
        self,
        pair: str,
        timestamp: object,
        *,
        server_timestamp: object | None = None,
        rollover_guard_minutes: int = 5,
    ) -> ForexTimeContext:
        """Retorna a classificacao temporal do candle informado."""
        source = str(timestamp or "").strip()
        parsed = self._parse_timestamp(source)
        server_source = str(server_timestamp or "").strip()
        server_dt = self._parse_timestamp(server_source)
        normalized_pair = str(pair or "").upper()
        if parsed is None:
            return ForexTimeContext(
                pair=normalized_pair,
                source_timestamp=source or "N/D",
                timestamp_utc="N/D",
                timestamp_brt="N/D",
                hour_utc=None,
                hour_brt=None,
                weekday="UNKNOWN",
                session="OFF_HOURS",
                forex_session="OFF_HOURS",
                session_label="Sem horario valido",
                brt_window="N/D",
                is_london_session=False,
                is_new_york_session=False,
                is_asia_session=False,
                is_london_new_york_overlap=False,
                is_london_ny_overlap=False,
                is_rollover_window=False,
                is_rollover=False,
                is_friday_late=False,
                is_sunday_open=False,
                is_off_hours=True,
                temporal_status="FORA_DA_JANELA",
                temporal_blocked=True,
                temporal_score_adjustment=0.0,
                temporal_reason="Timestamp invalido; cenario temporalmente inelegivel.",
                preferred_sessions=self._preferred_sessions(normalized_pair),
                financial_centers=self._financial_centers(normalized_pair),
                quality_note="Timestamp ausente ou invalido para Camada Tempo.",
                server_timestamp=server_source or "N/D",
            )

        utc_dt = parsed.astimezone(timezone.utc)
        brt_dt = utc_dt.astimezone(BRASILIA_OFFSET)
        server_rollover = self._server_rollover_context(
            server_dt,
            guard_minutes=rollover_guard_minutes,
        )
        session = (
            "ROLLOVER"
            if bool(server_rollover["is_rollover_window"])
            else self._session(utc_dt.hour)
        )
        preferred_sessions = self._preferred_sessions(normalized_pair)
        status, blocked, adjustment, reason = self._temporal_decision(
            session,
            utc_dt,
            preferred_sessions,
            server_rollover=server_rollover,
        )
        return ForexTimeContext(
            pair=normalized_pair,
            source_timestamp=source,
            timestamp_utc=utc_dt.isoformat(),
            timestamp_brt=brt_dt.isoformat(),
            hour_utc=utc_dt.hour,
            hour_brt=brt_dt.hour,
            weekday=self.WEEKDAYS[utc_dt.weekday()],
            session=session,
            forex_session=session,
            session_label=self._session_label(session),
            brt_window=self._brt_window(brt_dt.hour),
            is_london_session=session == "LONDON",
            is_new_york_session=session == "NEW_YORK",
            is_asia_session=session == "ASIA",
            is_london_new_york_overlap=session == "LONDON_NEW_YORK_OVERLAP",
            is_london_ny_overlap=session == "LONDON_NEW_YORK_OVERLAP",
            is_rollover_window=bool(
                server_rollover["is_rollover_window"]
                or self._is_rollover_window(utc_dt.hour)
            ),
            is_rollover=bool(
                server_rollover["is_rollover_window"]
                or self._is_rollover_window(utc_dt.hour)
            ),
            is_friday_late=self._is_friday_late(utc_dt),
            is_sunday_open=self._is_sunday_open(utc_dt),
            is_off_hours=session == "OFF_HOURS",
            temporal_status=status,
            temporal_blocked=blocked,
            temporal_score_adjustment=adjustment,
            temporal_reason=reason,
            preferred_sessions=preferred_sessions,
            financial_centers=self._financial_centers(normalized_pair),
            quality_note=reason,
            server_timestamp=str(server_rollover["server_timestamp"]),
            server_day=str(server_rollover["server_day"]),
            minutes_to_server_rollover=server_rollover["minutes_to_rollover"],
            minutes_from_server_rollover=server_rollover["minutes_from_rollover"],
        )

    def _parse_timestamp(self, value: str) -> datetime | None:
        if not value or value.upper() in {"N/D", "NONE", "NULL"}:
            return None
        candidates = [value, value.replace("Z", "+00:00")]
        for candidate in candidates:
            try:
                parsed = datetime.fromisoformat(candidate)
            except ValueError:
                continue
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        for pattern in ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, pattern).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    def _session(self, hour_utc: int) -> str:
        if self._is_rollover_window(hour_utc):
            return "ROLLOVER"
        if 13 <= hour_utc < 17:
            return "LONDON_NEW_YORK_OVERLAP"
        if 7 <= hour_utc < 13:
            return "LONDON"
        if 17 <= hour_utc < 22:
            return "NEW_YORK"
        if 0 <= hour_utc < 7:
            return "ASIA"
        return "OFF_HOURS"

    def _session_label(self, session: str) -> str:
        labels = {
            "ASIA": "Asia / Toquio",
            "LONDON": "Londres",
            "NEW_YORK": "Nova York",
            "LONDON_NEW_YORK_OVERLAP": "Overlap Londres/Nova York",
            "ROLLOVER": "Rollover diario",
            "OFF_HOURS": "Fora da janela",
        }
        return labels.get(session, session)

    def _is_rollover_window(self, hour_utc: int) -> bool:
        return 21 <= hour_utc < 22

    def _server_rollover_context(
        self,
        server_timestamp: datetime | None,
        *,
        guard_minutes: int,
    ) -> dict[str, object]:
        if server_timestamp is None:
            return {
                "is_rollover_window": False,
                "server_timestamp": "N/D",
                "server_day": "N/D",
                "minutes_to_rollover": None,
                "minutes_from_rollover": None,
                "reason": "",
            }
        server_dt = server_timestamp
        midnight = server_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if server_dt < midnight:
            midnight = midnight - timedelta(days=1)
        next_midnight = midnight + timedelta(days=1)
        minutes_from = (server_dt - midnight).total_seconds() / 60.0
        minutes_to = (next_midnight - server_dt).total_seconds() / 60.0
        is_guard = minutes_from <= guard_minutes or minutes_to <= guard_minutes
        reason = ""
        if is_guard:
            reason = (
                "Rollover do servidor MT5: janela de protecao "
                f"{guard_minutes} min antes/depois da virada do dia do servidor."
            )
        return {
            "is_rollover_window": is_guard,
            "server_timestamp": server_dt.isoformat(),
            "server_day": server_dt.date().isoformat(),
            "minutes_to_rollover": round(minutes_to, 2),
            "minutes_from_rollover": round(minutes_from, 2),
            "reason": reason,
        }

    def _is_friday_late(self, timestamp_utc: datetime) -> bool:
        return timestamp_utc.weekday() == 4 and timestamp_utc.hour >= 20

    def _is_sunday_open(self, timestamp_utc: datetime) -> bool:
        return timestamp_utc.weekday() == 6 and 21 <= timestamp_utc.hour < 24

    def _temporal_decision(
        self,
        session: str,
        timestamp_utc: datetime,
        preferred_sessions: tuple[str, ...],
        *,
        server_rollover: dict[str, object] | None = None,
    ) -> tuple[str, bool, float, str]:
        if server_rollover and bool(server_rollover.get("is_rollover_window")):
            return (
                "ROLLOVER_SERVIDOR_MT5_BLOQUEADO",
                True,
                0.0,
                str(server_rollover.get("reason") or "Rollover do servidor MT5."),
            )
        if timestamp_utc.weekday() == 5 or (
            timestamp_utc.weekday() == 6 and not self._is_sunday_open(timestamp_utc)
        ):
            return (
                "FIM_DE_SEMANA_BLOQUEADO",
                True,
                0.0,
                "Mercado Forex fechado no fim de semana.",
            )
        if self._is_sunday_open(timestamp_utc):
            return (
                "DOMINGO_ABERTURA_BLOQUEADO",
                True,
                0.0,
                "Abertura de domingo: liquidez reduzida e spread instavel.",
            )
        if self._is_friday_late(timestamp_utc):
            return (
                "SEXTA_FINAL_BLOQUEADO",
                True,
                0.0,
                "Final de sexta-feira: risco de baixa liquidez e gap.",
            )
        if self._is_rollover_window(timestamp_utc.hour):
            return (
                "ROLLOVER_BLOQUEADO",
                True,
                0.0,
                "Rollover diario: janela bloqueada por spread/liquidez.",
            )
        if session == "OFF_HOURS":
            return (
                "FORA_DA_JANELA",
                True,
                0.0,
                "Horario fora das sessoes Forex institucionais.",
            )
        if session in preferred_sessions:
            return (
                "SESSAO_FAVORAVEL",
                False,
                0.03,
                "Sessao favoravel para o par; aplica bonus leve no Score Tecnico.",
            )
        if session == "LONDON_NEW_YORK_OVERLAP":
            return (
                "SESSAO_NEUTRA",
                False,
                0.0,
                "Janela de alta liquidez, mas nao e preferencial primaria do par.",
            )
        return (
            "SESSAO_DESFAVORAVEL",
            False,
            -0.03,
            "Sessao desfavoravel para o par; aplica penalidade leve no Score Tecnico.",
        )

    def _brt_window(self, hour_brt: int) -> str:
        return f"{hour_brt:02d}:00-{(hour_brt + 1) % 24:02d}:00"

    def _preferred_sessions(self, pair: str) -> tuple[str, ...]:
        return self.PREFERRED_SESSIONS_BY_PAIR.get(str(pair).upper(), ())

    def _financial_centers(self, pair: str) -> tuple[str, ...]:
        return self.FINANCIAL_CENTERS_BY_PAIR.get(str(pair).upper(), ())
