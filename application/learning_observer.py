"""Bounded, fail-isolated observation of the existing strategy baseline."""

from __future__ import annotations

from collections import OrderedDict
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
from queue import Empty, Full, Queue
import re
import threading
import time

from application.learning_store import LearningStore, ROOT, digest, encoded, now

QUEUE_LIMIT = 512
ITEM_BYTES = 16384
RECENT_LIMIT = 2048
FEATURES = ("last_price", "trend", "momentum", "volatility", "rsi", "adx", "atr",
            "short_average", "long_average", "support", "resistance", "spread",
            "forex_session", "theoretical_entry_status", "theoretical_entry_reason",
            "entry_filter_status", "entry_filter_reason")
BASELINE_FILES = ("config/m29_pattern_filter.json",
                  ".traderia/research/m23_pattern_filter/report.json",
                  "application/model23_pattern_filter.py",
                  "application/model23_m29_copy.py",
                  "application/model29_m7_sequence.py")


def model(value) -> str:
    found = re.search(r"(?:MODELO_|M)(\d+)", str(value).upper())
    return "M" + found[1] if found else str(value or "UNKNOWN")


def compact(parameters: dict) -> dict:
    return {str(k): v if isinstance(v, (int, float, bool, type(None))) else str(v)[:256]
            for k, v in sorted(parameters.items())[:100]}


def item_from_snapshot(snapshot: dict, *, provenance: str, stage: str,
                       executor: str = "", source: str = "", status: str = "", reason: str = "") -> dict:
    params = snapshot.get("stop_management_parameters") or {}
    executor = model(executor or snapshot.get("operational_model"))
    source = model(params.get("m23_m29_origin_source") or params.get("m29_source_operational_model")
                   or source or params.get("source_operational_model") or executor)
    setup = str(params.get("source_entry_setup") or snapshot.get("source_setup")
                or snapshot.get("setup_id") or snapshot.get("entry_setup") or "UNKNOWN")
    mode = str(params.get("m23_m29_mode") or params.get("m29_mode")
               or (params.get("m29_sequence_mode") or params.get("m29_m7_mode") if source == "M7" else None)
               or "NORMAL").upper()
    candle = str(snapshot.get("candle_time") or "UNKNOWN")
    return {"source": source, "executor": executor, "symbol": snapshot.get("symbol", "UNKNOWN"),
            "route": "M29_COPY" if params.get("m23_m29_origin_source") else "DIRECT",
            "timeframe": snapshot.get("timeframe", "UNKNOWN"), "candle": candle,
            "setup": setup, "direction": snapshot.get("direction", "WAIT"), "mode": mode,
            "provenance": provenance, "stage": stage, "status": status or snapshot.get("status", "OBSERVED"),
            "reason": str(reason)[:1000], "snapshot": snapshot, "observed_at": now()}


def capture(row, plan, *, stage: str, executor: str = "", source: str = "", fallback=None) -> dict | None:
    if getattr(plan, "direction", "WAIT") not in ("BUY", "SELL"):
        if fallback is None or getattr(fallback, "direction", "WAIT") not in ("BUY", "SELL"):
            return None
        geometry = fallback
    else:
        geometry = plan
    params = dict(getattr(geometry, "stop_management_parameters", {}) or {})
    candle = getattr(row, "theoretical_entry_candle", None)
    if not candle or candle == "N/D":
        candle = getattr(row, "last_candle_time", "N/D")
    if candle in (None, "", "N/D"):
        return None  # No stable causal identity: never manufacture a new signal each poll.
    snapshot = {"symbol": geometry.symbol, "timeframe": geometry.timeframe,
                "direction": geometry.direction, "entry_price": geometry.entry_price,
                "initial_stop": geometry.stop, "target": geometry.target,
                "risk_reward": geometry.risk_reward, "candle_time": str(candle),
                "entry_setup": str(getattr(row, "active_model", "")),
                "alpha_id": geometry.alpha_id, "beta_id": geometry.beta_id,
                "stop_management_parameters": compact(params),
                "features": {k: getattr(row, k, None) for k in FEATURES}}
    return item_from_snapshot(snapshot, provenance="PROSPECTIVE", stage=stage, executor=executor,
                              source=source, status=plan.status,
                              reason=getattr(plan, "invalid_reason", "") or getattr(plan, "reason", ""))


def observe_plans(stage: str, executor: str = ""):
    """Observe returned plans without mutating return values or catching strategy failures."""
    def decorate(fn):
        @wraps(fn)
        def wrapped(self, row, plan, *args, **kwargs):
            result = fn(self, row, plan, *args, **kwargs)
            try:
                if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TRADERIA_LEARNING_DISABLED") == "1":
                    return result
                pairs = result if isinstance(result, (list, tuple)) and (not result or isinstance(result[0], tuple)) else [result]
                for out_row, out_plan in pairs:
                    item = capture(out_row, out_plan, stage=stage,
                                   executor=executor or kwargs.get("operational_model", ""),
                                   source=kwargs.get("source_operational_model", ""),
                                   fallback=plan if stage != "SOURCE" else None)
                    if item:
                        observer().submit(item)
            except Exception:
                # Collection never changes the trading decision, even during disk failure.
                if _INSTANCE is not None:
                    _INSTANCE.errors += 1
            return result
        return wrapped
    return decorate


class LearningObserver:
    def __init__(self, store=None, root=ROOT):
        self.store = store or LearningStore()
        self.root = Path(root)
        self.queue = Queue(maxsize=QUEUE_LIMIT)
        self.recent = OrderedDict()
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.dropped = self.errors = 0
        self.last_write = ""
        self.last_error = ""
        self.baseline_id = None
        self.baseline_signature = None
        self.thread = None
        self.started_at = now()
        self.last_native = 0.0
        self.pending = []

    def start(self):
        if self.thread is None:
            self.thread = threading.Thread(target=self.run, name="TraderIA-observer", daemon=True)
            self.thread.start()
        return self

    def submit(self, item):
        # Store a detached bounded string, never retain mutable strategy objects.
        item = dict(item, baseline=self.baseline_id)
        payload = encoded(item)
        if len(payload.encode()) > ITEM_BYTES:
            self.dropped += 1
            self.last_error = "Observation exceeds 16 KiB"
            return False
        signature = digest({k: v for k, v in item.items() if k not in ("observed_at", "snapshot")})
        with self.lock:
            if signature in self.recent:
                return True
            try:
                self.queue.put_nowait(payload)
            except Full:
                self.dropped += 1
                self.last_error = "Observation queue full"
                return False
            self.recent[signature] = True
            if len(self.recent) > RECENT_LIMIT:
                self.recent.popitem(last=False)
        return True

    def refresh_baseline(self, db):
        signature = []
        names = set(BASELINE_FILES)
        names.update(str(p.relative_to(self.root)).replace("\\", "/") for p in (self.root / "application").glob("model*.py")
                     if not p.name.startswith("model30_"))
        names.update(str(p.relative_to(self.root)).replace("\\", "/") for p in (self.root / "config").glob("*.json"))
        names.add(".traderia/mt5_operational_model.json")
        for name in sorted(names):
            path = self.root / name
            stat = path.stat() if path.exists() else None
            signature.append((name, stat.st_mtime_ns if stat else None, stat.st_size if stat else None))
        if signature == self.baseline_signature:
            return
        manifest = {"kind": "EXISTING_REPLAY_AND_SETUP", "files": {}, "training": "NOT_RUN"}
        for name, _, _ in signature:
            path = self.root / name
            if not path.exists():
                manifest["files"][name] = {"state": "MISSING"}
                continue
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(65536), b""):
                    h.update(chunk)
            manifest["files"][name] = {"sha256": h.hexdigest()}
        self.baseline_id = self.store.baseline(db, manifest)
        self.baseline_signature = signature

    def drain(self, db, limit=100):
        if not self.pending:
            for _ in range(limit):
                try:
                    self.pending.append(self.queue.get_nowait())
                except Empty:
                    break
        for payload in self.pending:
            item = json.loads(payload)
            self.store.register(db, item)
            self.last_write = now()

    def ingest_log(self, db, limit=100):
        path = self.root / ".traderia" / "mt5_demo_execution.jsonl"
        if not path.exists():
            return
        meta = db.execute("SELECT value FROM metadata WHERE key='execution_offset'").fetchone()
        offset = int(meta[0]) if meta else 0
        if meta is None:
            # Bounded historical context only; all subsequent bytes are followed durably.
            offset = max(0, path.stat().st_size - 2*1024*1024)
            if offset:
                with path.open("rb") as initial:
                    initial.seek(offset)
                    initial.readline()
                    offset = initial.tell()
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('execution_bootstrap',?)",
                       (encoded({"kind": "LEGACY_LOG_TAIL", "max_bytes": 2*1024*1024, "started_at": self.started_at}),))
        if offset > path.stat().st_size:
            offset = 0
        with path.open("rb") as stream:
            stream.seek(offset)
            for _ in range(limit):
                line = stream.readline(131073)
                if not line:
                    break
                if len(line) > 131072:
                    raise ValueError("Execution line exceeds import budget")
                if not line.endswith(b"\n"):
                    break
                offset = stream.tell()
                try:
                    record = json.loads(line)
                except (ValueError, TypeError):
                    self.errors += 1
                    self.last_error = "Invalid execution log line skipped"
                    continue
                snapshot = record.get("plan_snapshot") or {}
                if snapshot.get("direction") not in ("BUY", "SELL"):
                    continue
                # Import is explicit even when a native log was written seconds ago.
                item = item_from_snapshot(snapshot, provenance="EXECUTION_LOG_IMPORT", stage="EXECUTION",
                                          status="ACCEPTED_UNRECONCILED" if record.get("accepted") else "REJECTED",
                                          reason=record.get("message", ""))
                item["observed_at"] = str(record.get("timestamp") or now())
                signal_id = self.store.register(db, item)
                login = record.get("observed_account_login") or record.get("execution_account_login")
                server = record.get("observed_account_server") or record.get("execution_account_server")
                account = f"{login}@{server}" if login and server else ""
                key = digest([record.get("timestamp"), record.get("ticket"), record.get("plan_identity"), record.get("accepted")])
                db.execute("""INSERT OR IGNORE INTO executions
                    (id,signal_id,ticket,account_mode,account,recorded_at,status,actual_price,volume,evidence,snapshot)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (key, signal_id, record.get("ticket"),
                    str(record.get("execution_account_mode", "UNKNOWN")), account,
                    item["observed_at"], item["status"], record.get("executed_price"), record.get("quantity"),
                    "Native outcomes pending; log acceptance is not a fill", encoded(snapshot)))
            db.execute("INSERT OR REPLACE INTO metadata VALUES ('execution_offset',?)", (str(offset),))

    def run(self):
        while not self.stop_event.is_set():
            try:
                with self.store.connect() as db:
                    self.refresh_baseline(db)
                    self.drain(db)
                    self.ingest_log(db)
                for _ in self.pending:
                    self.queue.task_done()
                self.pending.clear()
                if time.monotonic() - self.last_native >= 60:
                    self.last_native = time.monotonic()
                    self.reconcile_pending()
                    from application.learning_policy import cycle
                    cycle(self.store)
            except Exception as exc:
                self.errors += 1
                self.last_error = str(exc)[:300]
            self.stop_event.wait(5)

    def reconcile_pending(self):
        from application.learning_native_read import reconcile_batch
        with self.store.connect() as db:
            db.execute("UPDATE executions SET status='ACCOUNT_UNCONFIRMED' WHERE status='ACCEPTED_UNRECONCILED' AND account=''")
            items = [dict(r) for r in db.execute("""SELECT id,ticket,account FROM executions
                WHERE account_mode='DEMO' AND ticket>0
                AND status IN ('ACCEPTED_UNRECONCILED','OPEN','CLOSED_COSTS_UNKNOWN')
                ORDER BY CASE WHEN recorded_at>=date('now','-1 day') THEN 0 ELSE 1 END,
                last_checked,recorded_at DESC LIMIT 10""")]
        evidence = reconcile_batch(items)
        with self.store.connect() as db:
            # Advance even unavailable tickets to avoid starving subsequent positions.
            for item in items:
                db.execute("UPDATE executions SET last_checked=? WHERE id=?", (now(), item["id"]))
            for result in evidence.get("results", []):
                self.store.reconcile(db, result["id"], result)
        if not evidence.get("ok"):
            self.last_error = evidence.get("reason", "native_read_unavailable")

    def health(self):
        return {"queue": self.queue.qsize(), "queue_limit": QUEUE_LIMIT,
                "dropped": self.dropped, "errors": self.errors, "last_error": self.last_error,
                "last_write": self.last_write, "started_at": self.started_at,
                "running": bool(self.thread and self.thread.is_alive()), "path": str(self.store.path)}


_INSTANCE = None
_LOCK = threading.Lock()


def observer():
    global _INSTANCE
    with _LOCK:
        if _INSTANCE is None:
            _INSTANCE = LearningObserver().start()
        return _INSTANCE


def observe_execution(fn):
    @wraps(fn)
    def wrapped(self, signal, trade_plan):
        result = fn(self, signal, trade_plan)
        if os.getenv("PYTEST_CURRENT_TEST") or os.getenv("TRADERIA_LEARNING_DISABLED") == "1":
            return result
        try:
            if signal.decision in ("BUY", "SELL"):
                snapshot = self._trade_plan_snapshot(signal, trade_plan, signal.decision)
                observer().submit(item_from_snapshot(snapshot, provenance="PROSPECTIVE", stage="EXECUTOR",
                                                     status=result.status, reason=result.message))
        except Exception:
            if _INSTANCE:
                _INSTANCE.errors += 1
        return result
    return wrapped
