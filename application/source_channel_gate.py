"""New-entry reinforcement gate from original M23 results, isolated by source/asset."""
import json
import math
import os
import re
from collections import defaultdict
from application.learning_store import LearningStore, digest, encoded
from application.realized_equity_structure import analyze_equity_structure
from application.realized_equity_pivot_channels import analyze_pivot_channels

POLICY = "M23_SOURCE_CHANNEL_DOWN_BLOCK_V1"
SOURCES = frozenset({1, 2, 5, 7, 8, 10, 18, 20})


def reconciled_results(payload, source, symbol):
    if source not in SOURCES:
        raise ValueError("Fonte nao autorizada no filtro de canal")
    groups = defaultdict(list)
    seen = set()
    opened = {int(p.get("identifier") or p.get("ticket")) for p in payload.get("open_positions", [])}
    for d in payload.get("rows", []):
        ticket = int(d["ticket"])
        if ticket in seen:
            continue
        seen.add(ticket)
        if d.get("type") in (0, 1) and d.get("position_id"):
            groups[int(d["position_id"])].append(d)
    results = []
    for position, deals in groups.items():
        entries = [d for d in deals if d.get("entry") == 0]
        relevant = [d for d in entries if re.search(rf"\bM23 S{source}\b", d.get("comment", "")) and d.get("symbol") == symbol.upper()]
        if not relevant or position in opened:
            continue
        if len(relevant) != len(entries) or any(d.get("entry") == 2 for d in deals):
            raise ValueError("Posicao de referencia com origem ambigua")
        exits = [d for d in deals if d.get("entry") in (1, 3)]
        vin = sum(float(d["volume"]) for d in entries)
        vout = sum(float(d["volume"]) for d in exits)
        if not exits or vin <= 0 or not math.isclose(vin, vout, abs_tol=1e-8):
            raise ValueError("Historico M23 incompleto para posicao encerrada")
        if any(not all(k in d for k in ("profit", "commission", "swap", "fee")) for d in deals):
            raise ValueError("Referencia M23 sem custos completos")
        net = sum(float(d[k]) for d in deals for k in ("profit", "commission", "swap", "fee"))
        if not math.isfinite(net):
            raise ValueError("Resultado de referencia invalido")
        results.append(dict(id=str(position), net=round(net, 2), time=max((d.get("time_msc") or d["time"]*1000) for d in exits)))
    return sorted(results, key=lambda r: (r["time"], r["id"]))


def channel_state(results):
    structure = analyze_equity_structure(results, sensitivity=1.0)
    channels = analyze_pivot_channels(results, confirmations=1, sensitivity=1.0)
    # Mixed/broken structure is transition, not a confirmed falling channel.
    blocked = structure["state"] == "Baixa" and channels["trend"] == "Baixa"
    return dict(policy=POLICY, mode="NORMAL", blocked=blocked,
                state=structure["state"], channel=channels["segments"][-1] if channels["segments"] else None,
                reference=digest(results), closed=len(results))


def reference_state(provider, symbol, source, store=None):
    if str(getattr(provider.execution_account, "mode", "")) != "DEMO":
        raise ValueError("Filtro de reforco autorizado somente na Demo")
    payload = provider._external_mt5_read("m29_sequence", portable=os.getenv("MT5_PORTABLE", "0") == "1")
    account = payload.get("account") or {}
    if (not payload.get("ok") or not account.get("login") or not account.get("server")
            or account.get("trade_mode") != provider.mt5.ACCOUNT_TRADE_MODE_DEMO
            or account.get("margin_mode") != provider.mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING):
        raise ValueError("Aguardando historico confirmado da conta Demo hedging")
    live = provider.mt5.account_info()
    if live is not None and (live.login != account["login"] or live.server != account["server"]):
        raise ValueError("Referencia e execucao pertencem a contas diferentes")
    rows = reconciled_results(payload, int(source), symbol)
    ids = {r["id"] for r in rows}
    store = store or LearningStore()
    key = "reinforcement_reference:" + digest([account["login"], account["server"], source, symbol, POLICY])
    with store.connect() as db:
        old = db.execute("SELECT value FROM metadata WHERE key=?", (key,)).fetchone()
        if old and not set(json.loads(old[0])).issubset(ids):
            raise ValueError("Historico de referencia regrediu; aguardando conciliacao")
        db.execute("INSERT OR REPLACE INTO metadata VALUES (?,?)", (key, encoded(sorted(ids))))
    return channel_state(rows)


def parameters(state, source, direction):
    return dict(reinforcement_policy=POLICY, reinforcement_source=int(source),
                reinforcement_reference=state["reference"], reinforcement_state=state["state"],
                reinforcement_original_direction=direction)


def entry_volume(parameters, symbol, default):
    """Current gold reinforcements use 0.20; legacy and other assets unchanged."""
    if parameters.get("reinforcement_policy") == POLICY and str(symbol).upper() == "XAUUSD":
        return 0.20
    return float(default)


def order_error(provider, order):
    model = str(order.operational_model)
    p = (order.plan_snapshot or {}).get("stop_management_parameters") or {}
    if not (model.startswith("MODELO_29_") or model.startswith("MODELO_30_")
            or model.startswith("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29")):
        return None
    try:
        if p.get("reinforcement_policy") != POLICY:
            return "Plano anterior ao filtro atual de canal; aguarde nova avaliacao"
        source = int(p["reinforcement_source"])
        from domain.operational_model_policy import operational_model_number
        origin = (int(str(p.get("m23_m29_origin_source", "M0"))[1:])
                  if model.startswith("MODELO_23_") else operational_model_number(p.get("source_operational_model")))
        if source not in SOURCES or source != origin or p.get("reinforcement_original_direction") != order.side:
            return "Reforco exige fonte e direcao original confirmadas"
        if p.get("m29_mirrored") or p.get("m30_mode", "NORMAL") != "NORMAL" or p.get("m23_m29_mode", "NORMAL") != "NORMAL":
            return "Espelhamento desativado na politica atual de reforco"
        if str(order.symbol).upper() == "XAUUSD" and not math.isclose(float(order.quantity), 0.20, abs_tol=1e-8):
            return "Reforco no ouro exige lote 0.20; aguarde plano atualizado"
        state = reference_state(provider, order.symbol, source)
        if state["blocked"]:
            return f"M{source}/{order.symbol}: canal de baixa no M23 suspende reforcos"
        if state["reference"] != p.get("reinforcement_reference"):
            return "Referencia M23 mudou; aguarde plano atualizado"
        return None
    except Exception as exc:
        return "Filtro de canal indisponivel: " + str(exc)[:180]


def current_reinforcement(order):
    model=str(getattr(order,"operational_model",""))
    p=(getattr(order,"plan_snapshot",None) or {}).get("stop_management_parameters") or {}
    return p.get("reinforcement_policy")==POLICY and (model.startswith("MODELO_29_") or model.startswith("MODELO_30_") or model=="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29")


def loss_limit(order):
    return 400.0 if (current_reinforcement(order) and str(order.symbol).upper()=="XAUUSD"
                     and math.isclose(float(order.quantity),.20,abs_tol=1e-8)) else 200.0
