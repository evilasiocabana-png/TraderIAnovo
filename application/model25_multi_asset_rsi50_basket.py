"""Modelo 25: cesta XAUUSD que copia sinais dos modelos-fonte autorizados."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any, Protocol
from uuid import uuid4

from application.model24_xau_basket import (
    model24_position_net,
)
from application.model8_xau_m5_sma_rsi_reentry import MODEL_8_ID, MODEL_8_SYMBOL
from application.xau_m5_sma_rsi_model_family import (
    MODEL_10_ID,
    MODEL_18_ID,
    MODEL_19_ID,
    MODEL_20_ID,
    MODEL_21_ID,
    MODEL_22_ID,
)


MODEL_25_ID = "MODELO_25_MULTI_ASSET_RSI50_BASKET"
MODEL_25_ALPHA_ID = "ALPHA025_XAU_SOURCE_AGGREGATOR"
MODEL_25_ALPHA_VERSION = "M25_ENTRY_V2"
MODEL_25_BETA_ID = "BETA025_BASKET_FULL_EXIT_1000"
MODEL_25_BETA_VERSION = "M25_EXIT_V2"
MODEL_25_ENTRY_SOURCE = "MODEL_25_XAU_SOURCE_SIGNAL"
MODEL_25_EXIT_POLICY = "M25_SOURCE_EXIT_PLUS_BASKET_1000"
MODEL_25_CONTRACT_VERSION = "M25_XAU_SOURCES_V2_20260819"
MODEL_25_FULL_EXIT_USD = 1000.0
MODEL_25_INITIAL_VOLUME = 0.20
MODEL_25_REENTRY_VOLUME = 0.10
MODEL_25_TIMEFRAME = "M5"
MODEL_25_SYMBOLS = (MODEL_8_SYMBOL,)
MODEL_25_SOURCE_MODEL_IDS = (
    MODEL_8_ID,
    MODEL_10_ID,
    MODEL_18_ID,
    MODEL_19_ID,
    MODEL_20_ID,
    MODEL_21_ID,
    MODEL_22_ID,
)
MODEL_25_CONTRACT_FINGERPRINT = hashlib.sha256(
    "|".join(
        (
            MODEL_25_CONTRACT_VERSION,
            MODEL_8_SYMBOL,
            MODEL_25_TIMEFRAME,
            *MODEL_25_SOURCE_MODEL_IDS,
            f"INITIAL={MODEL_25_INITIAL_VOLUME:.2f}",
            f"REENTRY={MODEL_25_REENTRY_VOLUME:.2f}",
            f"FULL_EXIT={MODEL_25_FULL_EXIT_USD:.2f}",
        )
    ).encode("utf-8")
).hexdigest()[:16]
MODEL_25_STATE_PATH = Path(".traderia") / "model25_basket_state.json"
MODEL_25_AUDIT_PATH = Path(".traderia") / "model25_basket_audit.jsonl"

_LOCK = threading.RLock()


class Model25ExecutionPort(Protocol):
    def list_open_positions(self) -> list[object]: ...

    def close_position(
        self, *, symbol: str, ticket: int, side: str, volume: float, reason: str
    ) -> object: ...


def is_model25(value: object) -> bool:
    return str(value or "").upper().startswith(MODEL_25_ID)


def model25_source_model_id(value: object) -> str:
    normalized = str(value or "").upper()
    match = re.search(r"_SOURCE_M(8|10|18|19|20|21|22)(?:_|\b|$)", normalized)
    return f"M{match.group(1)}" if match is not None else "N/D"


def model25_variant_id(source_operational_model: object) -> str:
    normalized = str(source_operational_model or "").upper()
    if normalized not in MODEL_25_SOURCE_MODEL_IDS:
        raise ValueError("M25 exige fonte XAU ativa: M8, M10 ou M18-M22.")
    number = re.search(r"MODELO_(\d{1,2})_", normalized)
    if number is None:
        raise ValueError("M25 recebeu fonte sem numero operacional.")
    return f"{MODEL_25_ID}_SOURCE_M{int(number.group(1))}"


def model25_order_comment(value: object = None) -> str:
    source = model25_source_model_id(value)
    return "TraderIA M25" if source == "N/D" else f"TraderIA M25 S{source[1:]}"


def model25_position_matches(position: object) -> bool:
    return bool(re.search(r"\bM25\b", str(getattr(position, "comment", "") or "").upper()))


def model25_position_source(position: object) -> str:
    comment = str(getattr(position, "comment", "") or "").upper()
    match = re.search(r"\bS(8|10|18|19|20|21|22)\b", comment)
    return f"M{match.group(1)}" if match is not None else "N/D"


def model25_symbol_pip_size(symbol: object) -> float:
    """Compatibilidade da gestao de posicoes M25 V1 ja abertas antes do V2."""
    normalized = str(symbol or "").upper()
    if normalized in {"XAUUSD", "BTCUSD"} or normalized.endswith("JPY"):
        return 0.01
    return 0.0001


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
