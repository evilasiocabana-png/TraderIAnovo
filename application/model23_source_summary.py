"""Read-only realized results by source within the M23 basket."""
import math
import re
from application.model23_basket_accumulator import model23_source_model_id, operational_model_number


def collect_m23_source_results(rows, active_sources=None):
    """Input: confirmed closed M23 rows already filtered to the report period."""
    allowed = set(active_sources) if active_sources is not None else None
    groups = {source: [] for source in (allowed or ())}
    seen = set()
    for row in rows:
        if not getattr(row, "mt5_found", False) or getattr(row, "operation_status", "").upper() != "FECHADA/HISTORICO":
            continue
        ticket = getattr(row, "mt5_ticket", None) or getattr(row, "local_ticket", None)
        if not ticket or str(ticket) in seen:
            continue
        seen.add(str(ticket))
        snapshot = getattr(row, "plan_snapshot", {}) or {}
        parameters = snapshot.get("stop_management_parameters") or {}
        model = getattr(row, "operational_model", "") or ""
        source = model23_source_model_id(model)
        if source == "N/D":
            source = model23_source_model_id(snapshot.get("operational_model", ""))
        if source == "N/D":
            number = operational_model_number(parameters.get("source_operational_model", ""))
            source = f"M{number}" if number is not None else "Origem nao identificada"
        if allowed is not None and source not in allowed:
            continue
        amounts = [float(getattr(row, key, 0) or 0) for key in
                   ("mt5_realized_profit", "mt5_commission", "mt5_swap", "mt5_fee")]
        if not all(math.isfinite(v) for v in amounts):
            continue
        net = round(sum(amounts), 2)
        groups.setdefault(source, []).append({"net": net, "ticket": str(ticket),
            "time": str(getattr(row, "mt5_time", "") or ""),
            "letter": "G" if net > 0 else "P" if net < 0 else "E"})
    return groups


def summarize_m23_sources(rows, active_sources=None):
    groups = collect_m23_source_results(rows, active_sources)
    def sort_key(source):
        match = re.fullmatch(r"M(\d+)", source)
        return int(match.group(1)) if match else 999
    return [{"Fonte do sinal": source, "Sequencia completa": " ".join(r["letter"] for r in groups[source]) or "Sem encerramentos",
             "Saldo liquido (US$)": round(sum(r["net"] for r in groups[source]), 2)}
            for source in sorted(groups, key=sort_key)]


def collect_realized_results(rows):
    """Chronologically prefiltered confirmed rows, without mixing ownership."""
    results=[]
    seen=set()
    for row in rows:
        if not getattr(row,"mt5_found",False) or getattr(row,"operation_status","").upper()!="FECHADA/HISTORICO":continue
        ticket=getattr(row,"mt5_ticket",None) or getattr(row,"local_ticket",None)
        if not ticket or str(ticket) in seen:continue
        amounts=[float(getattr(row,k,0) or 0) for k in ("mt5_realized_profit","mt5_commission","mt5_swap","mt5_fee")]
        if not all(math.isfinite(v) for v in amounts):continue
        seen.add(str(ticket));net=round(sum(amounts),2)
        results.append(dict(net=net,ticket=str(ticket),time=str(getattr(row,"mt5_time","") or ""),letter="G" if net>0 else "P" if net<0 else "E"))
    return results
