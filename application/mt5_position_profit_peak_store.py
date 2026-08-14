"""Persistencia leve do maior lucro flutuante observado por ticket MT5."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path
import sqlite3
from typing import Iterable


DEFAULT_MT5_POSITION_PROFIT_PEAK_PATH = (
    Path(".traderia") / "runtime" / "mt5_position_profit_peaks.sqlite3"
)


@dataclass(frozen=True)
class MT5PositionProfitPeak:
    ticket: int
    symbol: str
    peak_profit: float
    peak_at: str


class MT5PositionProfitPeakStore:
    """Mantem somente maximos; uma leitura posterior nunca reduz o pico."""

    def __init__(self, path: Path | str = DEFAULT_MT5_POSITION_PROFIT_PEAK_PATH) -> None:
        self.path = Path(path)

    def observe_positions(
        self,
        positions: Iterable[object],
        *,
        observed_at: str | None = None,
    ) -> dict[int, MT5PositionProfitPeak]:
        timestamp = observed_at or datetime.now(timezone.utc).isoformat()
        samples: list[tuple[int, str, float, str]] = []
        for position in positions:
            try:
                ticket = int(getattr(position, "ticket", 0) or 0)
                profit = float(getattr(position, "profit", 0.0) or 0.0)
            except (TypeError, ValueError):
                continue
            if ticket <= 0 or not math.isfinite(profit):
                continue
            samples.append(
                (
                    ticket,
                    str(getattr(position, "symbol", "N/D") or "N/D").upper(),
                    profit,
                    timestamp,
                )
            )
        if not samples:
            return {}

        try:
            with closing(self._connect()) as connection:
                connection.executemany(
                    """
                    INSERT INTO mt5_position_profit_peak (
                        ticket, symbol, peak_profit, peak_at
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(ticket) DO UPDATE SET
                        symbol = excluded.symbol,
                        peak_profit = excluded.peak_profit,
                        peak_at = excluded.peak_at
                    WHERE excluded.peak_profit > mt5_position_profit_peak.peak_profit
                    """,
                    samples,
                )
                connection.commit()
                return self._get_many_with_connection(
                    connection,
                    [sample[0] for sample in samples],
                )
        except (OSError, sqlite3.Error):
            return {}

    def get_many(self, tickets: Iterable[int | None]) -> dict[int, MT5PositionProfitPeak]:
        normalized = sorted(
            {
                int(ticket)
                for ticket in tickets
                if ticket is not None and int(ticket) > 0
            }
        )
        if not normalized or not self.path.exists():
            return {}
        try:
            with closing(self._connect()) as connection:
                return self._get_many_with_connection(connection, normalized)
        except (OSError, sqlite3.Error):
            return {}

    def raise_existing_peaks(
        self,
        samples: Iterable[tuple[int, str, float, str]],
    ) -> dict[int, MT5PositionProfitPeak]:
        """Eleva apenas tickets ja observados; nao inventa pico historico."""
        normalized: list[tuple[str, float, str, int, float]] = []
        for ticket, symbol, profit, observed_at in samples:
            try:
                normalized_ticket = int(ticket)
                normalized_profit = float(profit)
            except (TypeError, ValueError):
                continue
            if normalized_ticket <= 0 or not math.isfinite(normalized_profit):
                continue
            normalized.append(
                (
                    str(symbol or "N/D").upper(),
                    normalized_profit,
                    str(observed_at or datetime.now(timezone.utc).isoformat()),
                    normalized_ticket,
                    normalized_profit,
                )
            )
        if not normalized or not self.path.exists():
            return {}
        try:
            with closing(self._connect()) as connection:
                connection.executemany(
                    """
                    UPDATE mt5_position_profit_peak
                    SET symbol = ?, peak_profit = ?, peak_at = ?
                    WHERE ticket = ? AND ? > peak_profit
                    """,
                    normalized,
                )
                connection.commit()
                return self._get_many_with_connection(
                    connection,
                    [sample[3] for sample in normalized],
                )
        except (OSError, sqlite3.Error):
            return {}

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=0.25)
        connection.execute("PRAGMA busy_timeout = 250")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS mt5_position_profit_peak (
                ticket INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                peak_profit REAL NOT NULL,
                peak_at TEXT NOT NULL
            )
            """
        )
        return connection

    @staticmethod
    def _get_many_with_connection(
        connection: sqlite3.Connection,
        tickets: list[int],
    ) -> dict[int, MT5PositionProfitPeak]:
        if not tickets:
            return {}
        placeholders = ",".join("?" for _ in tickets)
        rows = connection.execute(
            "SELECT ticket, symbol, peak_profit, peak_at "
            f"FROM mt5_position_profit_peak WHERE ticket IN ({placeholders})",
            tickets,
        ).fetchall()
        return {
            int(ticket): MT5PositionProfitPeak(
                ticket=int(ticket),
                symbol=str(symbol),
                peak_profit=float(peak_profit),
                peak_at=str(peak_at),
            )
            for ticket, symbol, peak_profit, peak_at in rows
        }
