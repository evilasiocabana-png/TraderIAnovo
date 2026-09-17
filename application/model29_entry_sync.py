"""Cycle-local confirmations for M29 gold/M7 entries paired with M23."""

import math
import re


def is_gold_m7(plan):
    return (str(plan.symbol).upper() == "XAUUSD"
            and (plan.stop_management_parameters or {}).get("source_operational_model")
            == "MODELO_7_LAB_XAU_BTC")


def _key(plan, candle):
    if not is_gold_m7(plan) or str(candle).strip().upper() in {"", "N/D", "NONE"}:
        return None
    parameters = dict(plan.stop_management_parameters or {})
    try:
        prices = tuple(float(v) for v in (
            plan.entry_price, parameters["source_initial_stop"], parameters["source_target"],
        ))
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(v) and v > 0 for v in prices):
        return None
    direction = parameters.get("m29_original_direction", plan.direction)
    return (str(plan.symbol).upper(), str(plan.timeframe).upper(), str(candle).strip(),
            parameters.get("source_operational_model"), parameters.get("source_entry_setup"),
            direction, *prices)


class GoldM7EntrySync:
    """Never reuse historical confirmations or share them across account cycles."""

    def __init__(self):
        self._confirmed = {}

    def record(self, model, plan, candle, result):
        if not str(model).startswith("MODELO_23_"):
            return
        key = _key(plan, candle)
        execution = getattr(result, "execution_result", None)
        ticket = getattr(execution, "ticket", None)
        if (key is not None and result.status == "EXECUTED"
                and getattr(execution, "accepted", False) and ticket):
            self._confirmed[key] = (ticket, plan.stop)

    def claim(self, plan, candle):
        confirmation = self._confirmed.pop(_key(plan, candle), None)
        if confirmation is None:
            return None
        ticket, source_stop = confirmation
        if (plan.stop_management_parameters or {}).get("m29_mirrored"):
            if not math.isclose(float(plan.target), float(source_stop), rel_tol=0, abs_tol=1e-8):
                return None
        return ticket


def same_source_plan(left, left_candle, right, right_candle):
    key = _key(left, left_candle)
    return key is not None and key == _key(right, right_candle)


def pair_has_open_position(positions):
    if positions is None:
        raise RuntimeError("Posicoes do par M23/M29 indisponiveis")
    return any(
        str(getattr(p, "symbol", "")).upper() == "XAUUSD"
        and re.search(r"\bM(?:23|29)\s+S7\b", str(getattr(p, "comment", "")).upper())
        for p in positions
    )


def original_plan_for_copy(plan):
    """Normalize lineage only for matching, never change the submitted copy."""
    from dataclasses import replace
    p = dict(plan.stop_management_parameters or {})
    if p.get("m23_m29_origin_source") != "M7":
        return plan
    p["source_operational_model"] = "MODELO_7_LAB_XAU_BTC"
    return replace(plan, stop_management_parameters=p)

def pair_has_open_copy(positions):
    """Identify copies from broker comments and legacy execution lineage."""
    from pathlib import Path
    import json
    if positions is None:
        raise RuntimeError("Posicoes da dupla indisponiveis")
    if pair_has_open_position(positions):
        return True
    copies = [p for p in positions if str(getattr(p,"symbol","")).upper()=="XAUUSD"
        and re.search(r"\bM23\s+S29\b",str(getattr(p,"comment","")))]
    if not copies:return False
    if any(re.search(r"\bM7\b",str(getattr(p,"comment",""))) for p in copies):return True
    ids={str(getattr(p,"identifier",None) or getattr(p,"ticket",0)) for p in copies}
    found={}
    path=Path(".traderia/mt5_demo_execution.jsonl")
    if path.exists():
        for line in path.open(encoding="utf-8"):
            try: row=json.loads(line)
            except ValueError:continue
            if str(row.get("ticket")) in ids and row.get("accepted") and row.get("operational_model")=="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29":
                found[str(row["ticket"])]=((row.get("plan_snapshot") or {}).get("stop_management_parameters") or {}).get("m23_m29_origin_source")
    # Unknown legacy copy cannot safely be declared unrelated to the pair.
    return any(found.get(i) in (None,"M7") for i in ids)


class RejectedGoldCopyRetry:
    """Persist only explicit rejected admissions; consume before retry (fail closed).

    Broker identity and open original are rechecked. Accepted/uncertain attempts
    never survive as retry permissions, including across process restarts.
    """
    def __init__(self, root=None):
        from pathlib import Path
        self.root = Path(root or ".traderia/m23_m29_rejected_pairs")

    @staticmethod
    def fingerprint(plan, candle):
        p = plan.stop_management_parameters or {}
        if p.get("m23_m29_origin_source") != "M7" or plan.status != "PLANO_VALIDO":
            return None
        key = _key(original_plan_for_copy(plan), candle)
        if key is None:
            return None
        return list(key) + [plan.direction, plan.stop, plan.target,
                           p.get("m23_m29_mode"), p.get("execution_volume")]

    def snapshot(self, provider):
        import os, hashlib
        payload = provider._external_mt5_read("m29_sequence", portable=os.getenv("MT5_PORTABLE", "0") == "1")
        account = payload.get("account") or {}
        if not payload.get("ok") or not account.get("login") or not account.get("server") or "open_positions" not in payload:
            raise RuntimeError("Retomada aguarda conta e posicoes confirmadas")
        identity = str(account["server"]) + ":" + str(account["login"])
        return payload, identity, self.root / (hashlib.sha256(identity.encode()).hexdigest() + ".json")

    @staticmethod
    def original_open(payload, ticket):
        return any(str(ticket) in {str(p.get("identifier")), str(p.get("ticket"))}
                   and str(p.get("symbol", "")).upper() == "XAUUSD"
                   and re.search(r"\bM23\s+S7\b", str(p.get("comment", "")))
                   for p in payload["open_positions"])

    @staticmethod
    def copy_open(payload):
        # Legacy copies without lineage cannot safely be retried either.
        return any(str(p.get("symbol", "")).upper() == "XAUUSD"
                   and re.search(r"\bM23\s+S29\b", str(p.get("comment", "")))
                   for p in payload["open_positions"])

    def remember(self, provider, plan, candle, result):
        import json
        p = plan.stop_management_parameters or {}
        ticket = p.get("m23_m29_pair_original_ticket")
        execution = getattr(result, "execution_result", None)
        fingerprint = self.fingerprint(plan, candle)
        if (not ticket or fingerprint is None or result.status != "REJECTED"
                or execution is None or getattr(execution, "accepted", None) is not False
                or getattr(execution, "status", "") != "REJECTED"
                or getattr(execution, "error_code", None) in (10012, 10031)):
            return
        payload, identity, path = self.snapshot(provider)
        if not self.original_open(payload, ticket) or self.copy_open(payload):
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(dict(account=identity, original=str(ticket), fingerprint=fingerprint)), encoding="utf-8")
        tmp.replace(path)

    def claim(self, provider, plan, candle):
        import json
        if not self.root.exists() or not any(self.root.glob("*.json")):
            return None
        fingerprint = self.fingerprint(plan, candle)
        if fingerprint is None:
            return None
        payload, identity, path = self.snapshot(provider)
        if not path.exists():
            return None
        row = json.loads(path.read_text(encoding="utf-8"))
        # Remove before dispatch: a crash or uncertain response cannot duplicate a leg.
        path.unlink()
        if (row.get("account") != identity or row.get("fingerprint") != fingerprint
                or not self.original_open(payload, row.get("original")) or self.copy_open(payload)):
            return None
        return row["original"]
