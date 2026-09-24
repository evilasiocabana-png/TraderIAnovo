"""Durable observational ledger. No strategy decisions or execution commands."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATH = ROOT / ".traderia" / "learning" / "signals.sqlite3"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encoded(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, default=str)


def digest(value: object) -> str:
    return hashlib.sha256(encoded(value).encode()).hexdigest()


class LearningStore:
    def __init__(self, path: Path = DEFAULT_PATH):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=2)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA cache_size=-2048")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS baselines (
                    id TEXT PRIMARY KEY, captured_at TEXT NOT NULL, manifest TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS signals (
                    id TEXT PRIMARY KEY, group_id TEXT NOT NULL, source TEXT NOT NULL,
                    executor TEXT NOT NULL, symbol TEXT NOT NULL, timeframe TEXT NOT NULL,
                    candle TEXT NOT NULL, direction TEXT NOT NULL, setup TEXT NOT NULL,
                    mode TEXT NOT NULL, provenance TEXT NOT NULL, baseline TEXT,
                    first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, status TEXT NOT NULL,
                    reason TEXT NOT NULL, snapshot TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS signals_recent ON signals(first_seen DESC, id);
                CREATE INDEX IF NOT EXISTS signals_source ON signals(source, first_seen DESC);
                CREATE INDEX IF NOT EXISTS signals_group ON signals(group_id);
                CREATE TABLE IF NOT EXISTS observations (
                    id TEXT PRIMARY KEY, signal_id TEXT NOT NULL, observed_at TEXT NOT NULL,
                    stage TEXT NOT NULL, status TEXT NOT NULL, reason TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS executions (
                    id TEXT PRIMARY KEY, signal_id TEXT NOT NULL, ticket INTEGER,
                    account_mode TEXT NOT NULL, account TEXT NOT NULL,
                    recorded_at TEXT NOT NULL, status TEXT NOT NULL, actual_price REAL,
                    volume REAL, position_id INTEGER, net REAL, evidence TEXT NOT NULL,
                    last_checked TEXT NOT NULL DEFAULT '', snapshot TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS execution_pending ON executions(status, last_checked);
                CREATE INDEX IF NOT EXISTS execution_signal ON executions(signal_id);
                CREATE TABLE IF NOT EXISTS deals (
                    account TEXT NOT NULL, ticket INTEGER NOT NULL, position_id INTEGER,
                    snapshot TEXT NOT NULL, PRIMARY KEY(account,ticket));
            """)
            yield db
            db.commit()
        finally:
            db.close()

    def register(self, db, item: dict) -> str:
        identity = [item[k] for k in ("source", "symbol", "timeframe", "candle", "setup")]
        group = digest(identity)
        key = digest([group, item["executor"], item["mode"], item["direction"], item.get("route", "DIRECT")])
        if item["source"] == "M7" and item["executor"] == "M29" and item["mode"] == "ESPELHADO":
            legacy = digest([group, "M29", "NORMAL", item["direction"], item.get("route", "DIRECT")])
            old = db.execute("SELECT snapshot FROM signals WHERE id=?", (legacy,)).fetchone()
            if old and json.loads(old[0]).get("stop_management_parameters", {}).get("m29_mirrored"):
                if not db.execute("SELECT 1 FROM signals WHERE id=?", (key,)).fetchone():
                    db.execute("UPDATE signals SET id=?,mode='ESPELHADO' WHERE id=?", (key, legacy))
                    db.execute("UPDATE observations SET signal_id=? WHERE signal_id=?", (key, legacy))
                    db.execute("UPDATE executions SET signal_id=? WHERE signal_id=?", (key, legacy))
        timestamp = item.get("observed_at") or now()
        values = [key, group] + [item[k] for k in (
            "source", "executor", "symbol", "timeframe", "candle", "direction", "setup",
            "mode", "provenance")] + [item.get("baseline"), timestamp, timestamp,
            item["status"], item.get("reason", ""), encoded(item["snapshot"])]
        db.execute("""INSERT INTO signals VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(id) DO UPDATE SET last_seen=excluded.last_seen,
            status=excluded.status, reason=excluded.reason""", values)
        event = [key, item.get("stage", "SOURCE"), item["status"], item.get("reason", "")]
        db.execute("INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?)",
                   [digest(event), key, timestamp, *event[1:]])
        return key

    def baseline(self, db, manifest: dict) -> str:
        key = digest(manifest)
        db.execute("INSERT OR IGNORE INTO baselines VALUES (?,?,?)", (key, now(), encoded(manifest)))
        return key

    def reconcile(self, db, execution_id: str, evidence: dict):
        """Only native, complete entry/exit deals may produce a realized net value."""
        row = db.execute("SELECT * FROM executions WHERE id=?", (execution_id,)).fetchone()
        if not row:
            return
        status, net = "ACCEPTED_UNRECONCILED", None
        if evidence.get("cancelled"):
            status = "CANCELLED_UNFILLED"
        account = str(evidence.get("account", ""))
        deals = evidence.get("deals", [])
        position = evidence.get("position_id")
        if evidence.get("ok") and account and position:
            for deal in deals:
                db.execute("INSERT OR REPLACE INTO deals VALUES (?,?,?,?)",
                           (account, int(deal["ticket"]), position, encoded(deal)))
            # Each native ticket appears once even after repeated reconciliation.
            deals = list({int(d["ticket"]): d for d in deals}.values())
            entries = sum(float(d.get("volume", 0)) for d in deals if d.get("entry") == 0)
            exits = sum(float(d.get("volume", 0)) for d in deals if d.get("entry") in (1, 3))
            ambiguous = any(d.get("entry") == 2 for d in deals)
            complete = entries > 0 and abs(entries-exits) < 1e-8 and not ambiguous
            if evidence.get("open") is True:
                status = "OPEN"
            elif complete and evidence.get("open") is False:
                if all(all(k in d for k in ("profit", "commission", "swap", "fee")) for d in deals):
                    status = "CLOSED"
                    net = sum(sum(float(d[k]) for k in ("profit", "commission", "swap", "fee")) for d in deals)
                else:
                    status = "CLOSED_COSTS_UNKNOWN"
        db.execute("""UPDATE executions SET status=?,net=?,position_id=?,evidence=?,
            last_checked=? WHERE id=?""", (status, net, position, encoded(evidence), now(), execution_id))

    def page(self, page: int = 0, source: str = "", limit: int = 50, executor: str = "") -> dict:
        limit = max(1, min(int(limit), 100))
        if not self.path.exists():
            return {"rows": [], "total": 0, "groups": 0, "executions": [], "baselines": [], "sources": [], "bytes": 0}
        with self.connect() as db:
            filters = [(name, value) for name, value in (("source", source), ("executor", executor)) if value]
            where = "WHERE " + " AND ".join(name + "=?" for name, _ in filters) if filters else ""
            args = [value for _, value in filters]
            rows = db.execute(f"SELECT * FROM signals {where} ORDER BY first_seen DESC,id LIMIT ? OFFSET ?",
                              [*args, limit, max(0, int(page))*limit]).fetchall()
            total = db.execute(f"SELECT COUNT(*) FROM signals {where}", args).fetchone()[0]
            groups = db.execute(f"SELECT COUNT(DISTINCT group_id) FROM signals {where}", args).fetchone()[0]
            executions = []
            for row in rows:
                executions.extend(dict(x) for x in db.execute("SELECT * FROM executions WHERE signal_id=?", (row["id"],)))
            return {"rows": [dict(r) for r in rows], "total": total, "groups": groups,
                    "executions": executions,
                    "sources": [r[0] for r in db.execute("SELECT DISTINCT source FROM signals ORDER BY source")],
                    "baselines": [dict(r) for r in db.execute("SELECT * FROM baselines ORDER BY captured_at DESC LIMIT 10")],
                    "bytes": sum(p.stat().st_size for p in self.path.parent.glob(self.path.name+"*") if p.is_file())}
