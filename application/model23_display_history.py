"""Read-only realized M7 lineage within M23, separate original and M29-derived."""
from collections import defaultdict
import json, math, re
from pathlib import Path
from application.model23_m29_copy import COPY_ID
from application.model23_basket_accumulator import model23_entry_type_token

def closed_m29_m7_copies(snapshot, audit_path=Path(".traderia/mt5_demo_execution.jsonl")):
    account = snapshot.get("account") or {}
    origins = set()
    legacy_tokens = {}
    with audit_path.open(encoding="utf-8") as stream:
        for line in stream:
            try: row = json.loads(line)
            except ValueError: continue
            if not row.get("accepted") or row.get("operational_model") != COPY_ID: continue
            if row.get("execution_account_login") and str(row["execution_account_login"]) != str(account.get("login")): continue
            if row.get("execution_account_server") and row["execution_account_server"] != account.get("server"): continue
            parameters = (row.get("plan_snapshot") or {}).get("stop_management_parameters") or {}
            if parameters.get("m23_m29_origin_source") == "M7":
                if row.get("execution_account_login") and row.get("execution_account_server"):
                    origins.add(str(row.get("ticket")))
                elif parameters.get("m23_entry_type"):
                    legacy_tokens[str(row.get("ticket"))] = model23_entry_type_token(parameters["m23_entry_type"])
    groups=defaultdict(list)
    for deal in snapshot.get("rows",[]):
        if int(deal.get("type",-1)) in (0,1): groups[str(deal.get("position_id"))].append(deal)
    opened={str(p.get("identifier") or p.get("ticket")) for p in snapshot.get("open_positions",[])}
    result=[]
    for position, deals in groups.items():
        if position in opened or any(d.get("entry")==2 for d in deals):continue
        ins=[d for d in deals if d.get("entry")==0]
        outs=[d for d in deals if d.get("entry") in (1,3)]
        if not ins or not outs:continue
        known = position in origins or any(str(d.get("order")) in origins for d in ins)
        marked = all(re.search(r"\bM23\s+S29\s+M7\b",str(d.get("comment",""))) for d in ins)
        legacy = any(legacy_tokens.get(position) and legacy_tokens[position] in str(d.get("comment","")) for d in ins)
        if not (known or marked or legacy):continue
        if not all(re.search(r"\bM23\s+S29\b",str(d.get("comment",""))) for d in ins):continue
        if not math.isclose(sum(d.get("volume",0) for d in ins),sum(d.get("volume",0) for d in outs),abs_tol=1e-8):continue
        net=sum(float(d.get(k) or 0) for d in deals for k in ("profit","swap","commission","fee"))
        if not math.isfinite(net):continue
        result.append(dict(position=position,symbol=ins[0]["symbol"],net=net,
            opened=min(int(d.get("time_msc") or d["time"]*1000) for d in ins),
            closed=max(int(d.get("time_msc") or d["time"]*1000) for d in outs)))
    return sorted(result,key=lambda row:(row["closed"],int(row["position"])))


def m29_display_continuation(own_rows, copy_rows, symbol="XAUUSD", limit=7):
    """Seed display with old own M29 closures; live copies take precedence.

    This is presentation only, never the state driving mirroring.
    Own results after the first copied entry are not merged as parallel trades.
    """
    copies = sorted((r for r in copy_rows if r["symbol"] == symbol),
                    key=lambda r: (r["closed"], int(r["position"])))
    cutoff = min((r.get("opened", r["closed"]) for r in copies), default=float("inf"))
    own = sorted((r for r in own_rows if r.get("model") == 29
                  and r["symbol"] == symbol and r["closed"] < cutoff),
                 key=lambda r: (r["closed"], int(r["position"])))
    recent = [{**r, "display_origin": "M23 via M29"} for r in copies[-limit:]]
    missing = max(0, limit - len(recent))
    seed = [{**r, "display_origin": "Historico proprio M29"} for r in own[-missing:]] if missing else []
    return seed + recent
