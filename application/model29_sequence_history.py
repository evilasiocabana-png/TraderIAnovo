"""Account-isolated sequence state based on fully reconciled MT5 positions."""

from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
import re
import threading
import time

from application.model29_m7_sequence import M7SequenceState

_LOCK = threading.RLock()


def closed_m7_positions(snapshot: dict) -> list[dict]:
    groups: dict[int, list[dict]] = defaultdict(list)
    opened = {int(p.get("identifier") or p.get("ticket") or 0)
              for p in snapshot.get("open_positions", [])}
    for deal in snapshot.get("rows", []):
        position = int(deal.get("position_id") or 0)
        if position and int(deal.get("type", -1)) in (0, 1):
            groups[position].append(deal)
    results = []
    for position, deals in groups.items():
        if position in opened or any(int(d.get("entry", -1)) == 2 for d in deals):
            continue
        entries = [d for d in deals if int(d.get("entry", -1)) == 0]
        exits = [d for d in deals if int(d.get("entry", -1)) in (1, 3)]
        if not entries or not exits:
            continue
        models = set()
        for d in entries:
            match = re.search(r"\bM(23|29)\s+S7\b", str(d.get("comment", "")).upper())
            if match:
                models.add(int(match.group(1)))
        if len(models) != 1:
            continue
        vin = sum(float(d.get("volume") or 0) for d in entries)
        vout = sum(float(d.get("volume") or 0) for d in exits)
        if vin <= 0 or not math.isclose(vin, vout, abs_tol=1e-8):
            continue
        net = sum(float(d.get(k) or 0) for d in deals for k in ("profit", "swap", "commission", "fee"))
        if not math.isfinite(net):
            raise ValueError("Resultado M7 nao finito")
        results.append(dict(
            position=str(position), model=models.pop(), symbol=str(entries[0]["symbol"]).upper(),
            net=net, closed=max(int(d.get("time_msc") or int(d["time"]) * 1000) for d in exits),
        ))
    return sorted(results, key=lambda r: (r["closed"], int(r["position"])))


def sequence_mode(provider, symbol: str, root: Path = Path(".traderia/model29_sequences")) -> str:
    """Rebuild mode from closed M23/M7 results continuously, isolated per asset/account."""
    with _LOCK:
        # Broker snapshot owns the account identity, not a caller-supplied label.
        payload = provider._external_mt5_read("m29_sequence", portable=os.getenv("MT5_PORTABLE", "0") == "1")
        if not payload.get("ok"):
            raise RuntimeError("M29 aguarda historico MT5 conciliado")
        account = payload.get("account") or {}
        if not account.get("login") or not account.get("server"):
            raise RuntimeError("Conta M29 nao identificada")
        identity = str(account["server"]) + ":" + str(account["login"])
        key = hashlib.sha256(identity.encode()).hexdigest()
        path = root / (key + ".json")
        if path.exists():
            document = json.loads(path.read_text(encoding="utf-8"))
            if document.get("account") != identity:
                raise RuntimeError("Estado M29 pertence a outra conta")
        else:
            document = {"account": identity, "symbols": {}}
        closed = closed_m7_positions(payload)
        symbol = symbol.upper()
        state_doc = document["symbols"].get(symbol)
        if state_doc is None:
            if any(r["model"] == 29 and r["symbol"] == symbol for r in closed):
                raise RuntimeError("M29 possui resultados mas perdeu seu estado inicial; restaurar estado antes de enviar")
            seed = [r["net"] for r in closed if r["model"] == 23 and r["symbol"] == symbol]
            state_doc = {"seed": seed, "created_at": time.time()}
            document["symbols"][symbol] = state_doc
        source_rows = [row for row in closed if row["model"] == 23 and row["symbol"] == symbol]
        source_ids = [row["position"] for row in source_rows]
        if not source_rows and state_doc.get("seed"):
            raise RuntimeError("M29 aguarda historico M23 completo para definir modo")
        if not set(state_doc.get("reference_positions", [])).issubset(source_ids):
            raise RuntimeError("M29 recebeu historico M23 incompleto")
        state = M7SequenceState(four_result_trigger=symbol == "XAUUSD")
        for row in source_rows:
            state.record(row["position"], row["net"])
        state_doc.update(
            mode=state.mode, outcomes=state.outcomes,
            positions=sum(row["model"] == 29 and row["symbol"] == symbol for row in closed),
            reference_model=23, reference_positions=source_ids,
            reference_last_close=source_rows[-1]["closed"] if source_rows else None,
        )
        root.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(document, ensure_ascii=True, indent=2), encoding="utf-8")
        temporary.replace(path)
        return state.mode
