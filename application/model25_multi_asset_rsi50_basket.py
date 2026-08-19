"""Modelo 25: replica a logica M24 em M5 para os 19 ativos canonicos."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Iterable, Protocol
from uuid import uuid4

from application.model24_xau_basket import (
    Model24EntryDecision,
    Model24ReentryGateDecision,
    evaluate_model24_pending_reentry,
    evaluate_model24_rsi50_market_entry,
    model24_position_net,
)
from domain.market_universe import MT5_RESEARCH_MARKETS


MODEL_25_ID = "MODELO_25_MULTI_ASSET_RSI50_BASKET"
MODEL_25_ALPHA_ID = "ALPHA025_MULTI_ASSET_RSI50"
MODEL_25_ALPHA_VERSION = "M25_ENTRY_V1"
MODEL_25_BETA_ID = "BETA025_BASKET_FULL_EXIT_1000"
MODEL_25_BETA_VERSION = "M25_EXIT_V1"
MODEL_25_ENTRY_SOURCE = "MODEL_25_MULTI_ASSET_SIGNAL"
MODEL_25_EXIT_POLICY = "M25_RSI_EXIT_PLUS_BASKET_1000"
MODEL_25_FULL_EXIT_USD = 1000.0
MODEL_25_INITIAL_VOLUME = 0.20
MODEL_25_REENTRY_VOLUME = 0.10
MODEL_25_DISTANCE_ATR_MIN = 0.25
MODEL_25_TIMEFRAME = "M5"
MODEL_25_SYMBOLS = tuple(MT5_RESEARCH_MARKETS)
MODEL_25_STATE_PATH = Path(".traderia") / "model25_basket_state.json"
MODEL_25_RUNTIME_STATE_PATH = Path(".traderia") / "model25_runtime_state.json"
MODEL_25_AUDIT_PATH = Path(".traderia") / "model25_basket_audit.jsonl"

_LOCK = threading.RLock()


class Model25ExecutionPort(Protocol):
    def list_open_positions(self) -> list[object]: ...

    def close_position(
        self, *, symbol: str, ticket: int, side: str, volume: float, reason: str
    ) -> object: ...


def is_model25(value: object) -> bool:
    return str(value or "").upper().startswith(MODEL_25_ID)


def model25_order_comment(_: object = None) -> str:
    return "TraderIA M25"


def model25_position_matches(position: object) -> bool:
    return bool(re.search(r"\bM25\b", str(getattr(position, "comment", "") or "").upper()))


def model25_symbol_pip_size(symbol: object) -> float:
    normalized = str(symbol or "").upper()
    if normalized in {"XAUUSD", "BTCUSD"} or normalized.endswith("JPY"):
        return 0.01
    return 0.0001


def _m25_decision(decision: Model24EntryDecision) -> Model24EntryDecision:
    return replace(
        decision,
        status=str(decision.status or "").replace("M24", "M25"),
        reason=str(decision.reason or "").replace("M24", "M25"),
    )


def evaluate_model25_rsi50_market_entry(
    candles: Iterable[object],
    *,
    symbol: object = "XAUUSD",
) -> Model24EntryDecision:
    return _m25_decision(
        evaluate_model24_rsi50_market_entry(
            candles,
            entry_role="INITIAL",
            pip_size=model25_symbol_pip_size(symbol),
            require_rsi_cross=True,
            initial_stop_from_micro_pivot=True,
        )
    )


def evaluate_model25_pending_reentry(
    candles: Iterable[object],
    *,
    symbol: object,
) -> Model24EntryDecision:
    return _m25_decision(
        evaluate_model24_pending_reentry(
            candles,
            pip_size=model25_symbol_pip_size(symbol),
        )
    )


def model25_market_entry_role(symbol: object, trend_side: object) -> str:
    key = str(symbol or "").upper()
    side = str(trend_side or "").upper()
    with _LOCK:
        state = dict(dict(_load_runtime_state().get("symbols") or {}).get(key) or {})
    return "INITIAL" if str(state.get("last_initial_side") or "").upper() != side else "REENTRY"


def mark_model25_market_entry_accepted(
    symbol: object,
    trend_side: object,
    candle_time: object,
) -> None:
    key = str(symbol or "").upper()
    side = str(trend_side or "").upper()
    with _LOCK:
        payload = _load_runtime_state()
        symbols = dict(payload.get("symbols") or {})
        state = dict(symbols.get(key) or {})
        previous_side = str(state.get("last_initial_side") or "").upper()
        if previous_side and previous_side != side:
            for field_name in (
                "skip_first_reentry_after_extreme",
                "blocked_reentry_opportunity_key",
                "blocked_reentry_at",
                "released_reentry_opportunity_key",
            ):
                state.pop(field_name, None)
        state.update(
            {
                "last_initial_side": side,
                "last_entry_candle": str(candle_time or "N/D"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        symbols[key] = state
        payload.update({"symbols": symbols, "updated_at": datetime.now(timezone.utc).isoformat()})
        _atomic_json_write(MODEL_25_RUNTIME_STATE_PATH, payload)


def mark_model25_extreme_full_exit(
    symbol: object,
    trend_side: object,
    exit_status: object,
    candle_time: object,
) -> None:
    key = str(symbol or "").upper()
    side = str(trend_side or "").upper()
    event_key = f"{side}|{str(exit_status or '').upper()}|{candle_time or 'N/D'}"
    with _LOCK:
        payload = _load_runtime_state()
        symbols = dict(payload.get("symbols") or {})
        state = dict(symbols.get(key) or {})
        if str(state.get("last_extreme_exit_event_key") or "") == event_key:
            return
        state.update(
            {
                "last_initial_side": side,
                "skip_first_reentry_after_extreme": True,
                "blocked_reentry_opportunity_key": "",
                "last_extreme_exit_event_key": event_key,
                "last_extreme_exit_status": str(exit_status or "").upper(),
                "last_extreme_exit_candle": str(candle_time or "N/D"),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        symbols[key] = state
        payload["symbols"] = symbols
        _atomic_json_write(MODEL_25_RUNTIME_STATE_PATH, payload)


def evaluate_model25_reentry_opportunity(
    symbol: object,
    trend_side: object,
    opportunity_key: object,
) -> Model24ReentryGateDecision:
    key = str(symbol or "").upper()
    side = str(trend_side or "").upper()
    opportunity = str(opportunity_key or "").strip()
    with _LOCK:
        payload = _load_runtime_state()
        symbols = dict(payload.get("symbols") or {})
        state = dict(symbols.get(key) or {})
        if not bool(state.get("skip_first_reentry_after_extreme")):
            return Model24ReentryGateDecision(True, "M25_REENTRY_SEM_DESCARTE_PENDENTE", "Nao existe Full Exit extremo com descarte pendente.")
        if str(state.get("last_initial_side") or "").upper() != side:
            return Model24ReentryGateDecision(True, "M25_REENTRY_NOVA_DIRECAO_LIBERADA", "A trava pertence a outra direcao.")
        if not opportunity:
            return Model24ReentryGateDecision(False, "M25_REENTRY_AGUARDA_IDENTIFICAR_OPORTUNIDADE", "A reentrada aguarda candle M5 fechado identificavel.")
        blocked = str(state.get("blocked_reentry_opportunity_key") or "")
        if not blocked:
            blocked = opportunity
            state.update({"blocked_reentry_opportunity_key": blocked, "blocked_reentry_at": datetime.now(timezone.utc).isoformat()})
            symbols[key] = state
            payload["symbols"] = symbols
            _atomic_json_write(MODEL_25_RUNTIME_STATE_PATH, payload)
        if blocked == opportunity:
            return Model24ReentryGateDecision(False, "M25_REENTRY_PRIMEIRA_OPORTUNIDADE_IGNORADA", "Primeira oportunidade apos Full Exit extremo ignorada.", blocked)
        state.update({"skip_first_reentry_after_extreme": False, "released_reentry_opportunity_key": opportunity, "updated_at": datetime.now(timezone.utc).isoformat()})
        symbols[key] = state
        payload["symbols"] = symbols
        _atomic_json_write(MODEL_25_RUNTIME_STATE_PATH, payload)
        return Model24ReentryGateDecision(True, "M25_REENTRY_SEGUNDA_OPORTUNIDADE_LIBERADA", "Segunda oportunidade valida liberada.", blocked)


def _load_runtime_state() -> dict[str, Any]:
    try:
        payload = json.loads(MODEL_25_RUNTIME_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


@dataclass(frozen=True)
class Model25BasketSnapshot:
    status: str = "WAITING_NEW_ROUND"
    round_id: str = ""
    positions: int = 0
    net_result_usd: float = 0.0
    exit_reason: str = ""
    closed: int = 0
    rejected: int = 0
    updated_at: str = ""


@dataclass
class Model25BasketManager:
    execution_service: Model25ExecutionPort
    state_path: Path = field(default_factory=lambda: MODEL_25_STATE_PATH)
    audit_path: Path = field(default_factory=lambda: MODEL_25_AUDIT_PATH)
    full_exit_usd: float = MODEL_25_FULL_EXIT_USD

    def evaluate_once(self) -> Model25BasketSnapshot:
        with _LOCK:
            positions = [
                position
                for position in list(self.execution_service.list_open_positions() or [])
                if model25_position_matches(position)
            ]
            now = datetime.now(timezone.utc).isoformat()
            if not positions:
                snapshot = Model25BasketSnapshot(updated_at=now)
                self._write_state(asdict(snapshot))
                return snapshot
            net = round(sum(model24_position_net(position) for position in positions), 2)
            if net < self.full_exit_usd:
                snapshot = Model25BasketSnapshot(
                    status="ACCUMULATING",
                    round_id=self._round_id(),
                    positions=len(positions),
                    net_result_usd=net,
                    updated_at=now,
                )
                self._write_state(asdict(snapshot))
                return snapshot
            round_id = "M25-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
            results: list[dict[str, Any]] = []
            for position in positions:
                position_type = int(getattr(position, "type", -1) or 0)
                result = self.execution_service.close_position(
                    symbol=str(getattr(position, "symbol", "") or "").upper(),
                    ticket=int(getattr(position, "ticket", 0) or 0),
                    side="BUY" if position_type == 0 else "SELL",
                    volume=float(getattr(position, "volume", 0.0) or 0.0),
                    reason="M25_FULL_EXIT_PLUS_1000_USD",
                )
                results.append({"ticket": int(getattr(position, "ticket", 0) or 0), "accepted": bool(getattr(result, "accepted", False)), "message": str(getattr(result, "message", ""))})
            closed = sum(bool(row["accepted"]) for row in results)
            snapshot = Model25BasketSnapshot(
                status="EXIT_SUBMITTED" if closed == len(results) else "EXIT_PARTIAL",
                round_id=round_id,
                positions=len(positions),
                net_result_usd=net,
                exit_reason="M25_FULL_EXIT_PLUS_1000_USD",
                closed=closed,
                rejected=len(results) - closed,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._write_state(asdict(snapshot))
            self._append_audit({**asdict(snapshot), "results": results})
            return snapshot

    def _read_state(self) -> dict[str, Any]:
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return {}
        return dict(value) if isinstance(value, dict) else {}

    def _write_state(self, payload: dict[str, Any]) -> None:
        _atomic_json_write(self.state_path, payload)

    def _round_id(self) -> str:
        existing = str(self._read_state().get("round_id") or "")
        return existing or (
            "M25-"
            + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            + "-"
            + uuid4().hex[:8]
        )

    def _append_audit(self, payload: dict[str, Any]) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
    """Escrita atomica tolerante a bloqueios curtos do Windows/OneDrive."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{uuid4().hex}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    try:
        for attempt in range(6):
            try:
                os.replace(temporary, path)
                return
            except PermissionError:
                if attempt >= 5:
                    raise
                time.sleep(0.05 * (attempt + 1))
    finally:
        temporary.unlink(missing_ok=True)
