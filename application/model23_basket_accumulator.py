"""Modelo 23: acumulador de sinais com gestao financeira global da cesta."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import threading
import time
from typing import Any, Protocol
from uuid import uuid4

MODEL_23_ID = "MODELO_23_BASKET_ACCUMULATOR"
MODEL_23_ALPHA_ID = "ALPHA023_ACTIVE_MODEL_ACCUMULATOR"
MODEL_23_ALPHA_VERSION = "M23_ENTRY_V1"
MODEL_23_BETA_ID = "BETA023_FULL_EXIT_1000"
MODEL_23_BETA_VERSION = "M23_EXIT_V2"
MODEL_23_ENTRY_SOURCE = "MODEL_23_ACTIVE_SOURCE_SIGNAL"
MODEL_23_EXIT_POLICY = "M23_FULL_EXIT_1000_ONLY"
MODEL_23_FULL_EXIT_USD = 1000.0
MODEL_23_CLOSE_CONFIRMATION_SECONDS = 15.0
MODEL_23_STATE_PATH = Path(".traderia") / "model23_basket_state.json"
MODEL_23_ADDITIONAL_SOURCE_NUMBERS = (26,)

_MODEL23_LOCK = threading.Lock()


class Model23ExecutionPort(Protocol):
    def list_open_positions(self) -> list[object]: ...

    def close_position(
        self,
        *,
        symbol: str,
        ticket: int,
        side: str,
        volume: float,
        reason: str,
    ) -> object: ...


def operational_model_number(value: object) -> int | None:
    normalized = str(value or "").upper()
    match = re.search(r"(?:MODELO[_ ]?|(?:^|[\s|])M)(\d{1,2})(?:_|\b|$)", normalized)
    return int(match.group(1)) if match is not None else None


def is_model23(value: object) -> bool:
    return str(value or "").upper().startswith(MODEL_23_ID)


def model23_source_model_id(value: object) -> str:
    normalized = str(value or "").upper()
    match = re.search(r"_SOURCE_M(\d{1,2})(?:_|\b|$)", normalized)
    return f"M{int(match.group(1))}" if match is not None else "N/D"


def model23_variant_id(source_operational_model: object) -> str:
    number = operational_model_number(source_operational_model)
    if number is None or (
        number >= 23 and number not in MODEL_23_ADDITIONAL_SOURCE_NUMBERS
    ):
        raise ValueError("M23 exige uma fonte operacional autorizada.")
    return f"{MODEL_23_ID}_SOURCE_M{number}"


def model23_order_comment(value: object) -> str:
    source = model23_source_model_id(value)
    return "TraderIA M23" if source == "N/D" else f"TraderIA M23 S{source[1:]}"


def model23_position_matches(position: object) -> bool:
    comment = str(getattr(position, "comment", "") or "").upper()
    return bool(re.search(r"\bM23\b", comment))


def model23_position_source(position: object) -> str:
    comment = str(getattr(position, "comment", "") or "").upper()
    match = re.search(r"\bS(\d{1,2})\b", comment)
    return f"M{int(match.group(1))}" if match is not None else "N/D"


def model23_entry_type(
    parameters: dict[str, Any] | None = None,
    *,
    entry_setup: object = "",
    alpha_id: object = "",
) -> str:
    """Resolve o tipo operacional real herdado pela copia M23."""
    payload = dict(parameters or {})
    candidates = (
        payload.get("m23_entry_type"),
        payload.get("m24_entry_role"),
        payload.get("m25_entry_role"),
        payload.get("source_entry_role"),
        payload.get("entry_role"),
        payload.get("active_signal_kind"),
        payload.get("source_signal_kind"),
        payload.get("signal_kind"),
    )
    aliases = {
        "INITIAL": "INITIAL",
        "INITIAL_ENTRY": "INITIAL",
        "ENTRADA_INICIAL": "INITIAL",
        "REENTRY": "REENTRY",
        "STRUCTURAL_REENTRY": "REENTRY",
        "REENTRADA": "REENTRY",
        "REENTRY_AFTER_RSI_EXTREME_EXIT": "REENTRY",
        "CONTINUATION": "CONTINUATION",
        "CONTINUACAO": "CONTINUATION",
        "LATERALIZATION": "LATERALIZATION",
        "LATERALIZACAO": "LATERALIZATION",
        "EXHAUSTION": "EXHAUSTION",
        "EXAUSTAO": "EXHAUSTION",
    }
    for candidate in candidates:
        normalized = str(candidate or "").strip().upper()
        if normalized in aliases:
            return aliases[normalized]

    order_type = str(payload.get("active_entry_order_type") or "").upper()
    if order_type in {"BUY_STOP", "SELL_STOP", "BUY_LIMIT", "SELL_LIMIT"}:
        return "REENTRY"

    setup = str(
        payload.get("source_entry_setup")
        or payload.get("entry_setup")
        or entry_setup
        or ""
    ).strip().upper()
    if setup:
        parts = [part.strip() for part in setup.split("|") if part.strip()]
        for part in reversed(parts):
            if part not in {"N/D", "NONE", "WAIT"} and not part.startswith("M23 <-"):
                return re.sub(r"[^A-Z0-9_]+", "_", part).strip("_")

    alpha = str(payload.get("source_alpha_id") or alpha_id or "").strip().upper()
    if alpha and alpha not in {"N/D", "NONE"}:
        return re.sub(r"[^A-Z0-9_]+", "_", alpha).strip("_")
    return ""


def model23_entry_type_token(entry_type: object) -> str:
    """Gera token curto e estavel para persistir a chave no comentario MT5."""
    normalized = str(entry_type or "").strip().upper()
    if not normalized:
        return ""
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8].upper()
    return f"T{digest}"


def model23_position_entry_type_token(position: object) -> str:
    comment = str(getattr(position, "comment", "") or "").upper()
    match = re.search(r"\bT[0-9A-F]{8}\b", comment)
    return match.group(0) if match is not None else ""


def model23_position_net(position: object) -> float:
    """Resultado executavel disponivel no positions_get, incluindo custos expostos."""
    return sum(
        float(getattr(position, name, 0.0) or 0.0)
        for name in ("profit", "swap", "commission", "fee")
    )


def model23_entry_gate(
    candle_time: object,
    state_path: Path = MODEL_23_STATE_PATH,
) -> tuple[bool, str]:
    """Permite reentrada nova e bloqueia apenas zeragem ou sinal antigo."""
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return True, "M23_SEM_RODADA_ANTERIOR"
    status = str(payload.get("status", "") or "").upper()
    if status in {"CLOSING", "EXIT_SUBMITTED", "EXIT_PARTIAL"}:
        return False, f"M23_AGUARDA_ZERAGEM_COMPLETA_{status}"
    accept_after = _parse_utc(payload.get("accept_signals_after"))
    if accept_after is None:
        return True, "M23_RODADA_LIBERADA"
    signal_time = _parse_utc(candle_time)
    if signal_time is None:
        return False, "M23_AGUARDA_NOVO_CANDLE_APOS_ZERAGEM"
    if signal_time <= accept_after:
        return False, "M23_SINAL_ANTIGO_DA_RODADA_ANTERIOR"
    return True, "M23_NOVO_SINAL_LIBERADO"


def _parse_utc(value: object) -> datetime | None:
    normalized = str(value or "").strip()
    if not normalized or normalized.upper() in {"N/D", "NONE"}:
        return None
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        try:
            # The dashboard exposes theoretical candle timestamps in Brasilia
            # time. M23 must accept that same contract when checking a new round.
            parsed = datetime.strptime(normalized, "%d/%m/%Y %H:%M").replace(
                tzinfo=timezone(timedelta(hours=-3), name="BRT")
            )
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class Model23BasketSnapshot:
    status: str = "WAITING_NEW_ROUND"
    round_id: str = ""
    round_started_at: str = ""
    positions: int = 0
    net_result_usd: float = 0.0
    peak_result_usd: float = 0.0
    trailing_armed: bool = False
    trailing_floor_usd: float = 0.0
    exit_reason: str = ""
    closed: int = 0
    rejected: int = 0
    accept_signals_after: str = ""
    updated_at: str = ""


@dataclass
class Model23BasketManager:
    """Fecha a cesta M23 somente no alvo financeiro global de US$1.000."""

    execution_service: Model23ExecutionPort
    state_path: Path = field(
        default_factory=lambda: MODEL_23_STATE_PATH
    )
    audit_path: Path = field(
        default_factory=lambda: Path(".traderia") / "model23_basket_audit.jsonl"
    )
    full_exit_usd: float = MODEL_23_FULL_EXIT_USD
    close_confirmation_seconds: float = MODEL_23_CLOSE_CONFIRMATION_SECONDS

    def evaluate_once(self) -> Model23BasketSnapshot:
        """Avalia e, quando necessario, encerra todos os tickets M23 Demo."""
        with _MODEL23_LOCK:
            positions = sorted(
                (
                    position
                    for position in self.execution_service.list_open_positions()
                    if model23_position_matches(position)
                ),
                key=model23_position_net,
                reverse=True,
            )
            state = self._load_state()
            now = datetime.now(timezone.utc).isoformat()
            if not positions:
                accept_after = state.accept_signals_after
                if state.status in {"CLOSING", "EXIT_SUBMITTED", "EXIT_PARTIAL"}:
                    accept_after = now
                elif state.round_id or state.positions > 0:
                    # Uma cesta que desapareceu fora do fluxo automatico foi
                    # zerada manualmente. Exigir candle posterior impede que os
                    # mesmos sinais da rodada encerrada sejam reutilizados.
                    accept_after = now
                snapshot = Model23BasketSnapshot(
                    status="WAITING_NEW_ROUND",
                    accept_signals_after=accept_after,
                    updated_at=now,
                )
                if state.status != snapshot.status or state.round_id:
                    self._audit("ROUND_CLEARED", snapshot, {})
                self._write_state(snapshot)
                return snapshot

            round_id = state.round_id or self._new_round_id()
            started_at = state.round_started_at or now
            net_result = round(sum(model23_position_net(item) for item in positions), 2)
            # Campos antigos permanecem no snapshot apenas para ler estados
            # persistidos sem quebrar compatibilidade. Nao participam da decisao.
            peak = round(max(state.peak_result_usd, net_result), 2)
            trailing_armed = False
            trailing_floor = 0.0
            pending_exit = (
                state.status in {"CLOSING", "EXIT_SUBMITTED", "EXIT_PARTIAL"}
                and state.exit_reason == "M23_FULL_EXIT_PLUS_1000_USD"
            )
            if pending_exit and self._awaiting_close_confirmation(state, now):
                snapshot = Model23BasketSnapshot(
                    status=state.status,
                    round_id=round_id,
                    round_started_at=started_at,
                    positions=len(positions),
                    net_result_usd=net_result,
                    peak_result_usd=peak,
                    trailing_armed=trailing_armed,
                    trailing_floor_usd=trailing_floor,
                    exit_reason=state.exit_reason,
                    closed=state.closed,
                    rejected=state.rejected,
                    accept_signals_after=state.accept_signals_after,
                    updated_at=state.updated_at,
                )
                self._write_state(snapshot)
                return snapshot
            exit_reason = (
                state.exit_reason
                if pending_exit and state.exit_reason
                else self._exit_reason(net_result)
            )
            if not exit_reason:
                snapshot = Model23BasketSnapshot(
                    status="ACCUMULATING",
                    round_id=round_id,
                    round_started_at=started_at,
                    positions=len(positions),
                    net_result_usd=net_result,
                    peak_result_usd=peak,
                    trailing_armed=trailing_armed,
                    trailing_floor_usd=trailing_floor,
                    accept_signals_after=state.accept_signals_after,
                    updated_at=now,
                )
                self._write_state(snapshot)
                return snapshot

            closing = Model23BasketSnapshot(
                status="CLOSING",
                round_id=round_id,
                round_started_at=started_at,
                positions=len(positions),
                net_result_usd=net_result,
                peak_result_usd=peak,
                trailing_armed=trailing_armed,
                trailing_floor_usd=trailing_floor,
                exit_reason=exit_reason,
                accept_signals_after=state.accept_signals_after,
                updated_at=now,
            )
            self._write_state(closing)
            results: list[dict[str, Any]] = []
            for position in positions:
                side = "BUY" if int(getattr(position, "type", -1) or 0) == 0 else "SELL"
                result = self.execution_service.close_position(
                    symbol=str(getattr(position, "symbol", "") or "").upper(),
                    ticket=int(getattr(position, "ticket", 0) or 0),
                    side=side,
                    volume=float(getattr(position, "volume", 0.0) or 0.0),
                    reason=exit_reason,
                )
                results.append(
                    {
                        "ticket": int(getattr(position, "ticket", 0) or 0),
                        "symbol": str(getattr(position, "symbol", "") or "").upper(),
                        "source_model": model23_position_source(position),
                        "profit_before_close": model23_position_net(position),
                        "accepted": bool(getattr(result, "accepted", False)),
                        "status": str(getattr(result, "status", "N/D") or "N/D"),
                        "message": str(getattr(result, "message", "") or ""),
                    }
                )
            closed = sum(bool(item["accepted"]) for item in results)
            rejected = len(results) - closed
            snapshot = Model23BasketSnapshot(
                status="EXIT_SUBMITTED" if rejected == 0 else "EXIT_PARTIAL",
                round_id=round_id,
                round_started_at=started_at,
                positions=len(positions),
                net_result_usd=net_result,
                peak_result_usd=peak,
                trailing_armed=trailing_armed,
                trailing_floor_usd=trailing_floor,
                exit_reason=exit_reason,
                closed=closed,
                rejected=rejected,
                accept_signals_after=state.accept_signals_after,
                updated_at=datetime.now(timezone.utc).isoformat(),
            )
            self._audit("FULL_EXIT", snapshot, {"results": results})
            self._write_state(snapshot)
            return snapshot

    def _exit_reason(self, net_result: float) -> str:
        if net_result >= self.full_exit_usd:
            return "M23_FULL_EXIT_PLUS_1000_USD"
        return ""

    def _awaiting_close_confirmation(
        self,
        state: Model23BasketSnapshot,
        now: str,
    ) -> bool:
        if state.status not in {"CLOSING", "EXIT_SUBMITTED", "EXIT_PARTIAL"}:
            return False
        previous = _parse_utc(state.updated_at)
        current = _parse_utc(now)
        if previous is None or current is None:
            return False
        return (current - previous).total_seconds() < self.close_confirmation_seconds

    def _load_state(self) -> Model23BasketSnapshot:
        try:
            payload = json.loads(self.state_path.read_text(encoding="utf-8"))
            allowed = Model23BasketSnapshot.__dataclass_fields__
            return Model23BasketSnapshot(
                **{key: value for key, value in payload.items() if key in allowed}
            )
        except (OSError, ValueError, TypeError):
            return Model23BasketSnapshot()

    def _write_state(self, snapshot: Model23BasketSnapshot) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(f".{uuid4().hex}.tmp")
        payload = json.dumps(asdict(snapshot), ensure_ascii=True, indent=2)
        try:
            temporary.write_text(payload, encoding="utf-8")
            for attempt in range(5):
                try:
                    temporary.replace(self.state_path)
                    return
                except PermissionError:
                    if attempt < 4:
                        time.sleep(0.05 * (attempt + 1))
            # O OneDrive pode bloquear momentaneamente a troca atomica. A
            # gravacao direta preserva o ciclo; a proxima avaliacao reconcilia
            # o estado com as posicoes reais do MT5.
            for attempt in range(3):
                try:
                    self.state_path.write_text(payload, encoding="utf-8")
                    return
                except PermissionError:
                    if attempt < 2:
                        time.sleep(0.1 * (attempt + 1))
        finally:
            temporary.unlink(missing_ok=True)

    def _audit(
        self,
        event: str,
        snapshot: Model23BasketSnapshot,
        extra: dict[str, Any],
    ) -> None:
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"event": event, **asdict(snapshot), **extra}
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(payload, ensure_ascii=True) + "\n")

    @staticmethod
    def _new_round_id() -> str:
        return "M23-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
