"""Broker-priced loss defense for new normal M29 copies only."""
from math import ceil, floor, isfinite

from application.model23_m29_copy import COPY_ID


def protected_request(order, request, mt5):
    parameters = (getattr(order, "plan_snapshot", None) or {}).get("stop_management_parameters") or {}
    if (getattr(order, "operational_model", "") != COPY_ID
            or str(order.symbol).upper() != "XAUUSD"
            or parameters.get("m23_m29_origin_source") not in {"M8", "M10", "M18", "M20"}
            or parameters.get("m23_m29_mode") != "NORMAL"):
        return request
    from application.source_channel_gate import entry_volume
    expected = entry_volume(parameters, order.symbol, 0.1)
    if not isfinite(float(order.quantity)) or abs(float(order.quantity) - expected) > 1e-8:
        raise ValueError("Defesa M29 exige o lote contratado da politica")
    account = mt5.account_info()
    info = mt5.symbol_info(order.symbol)
    if str(getattr(account, "currency", "")).upper() != "USD":
        raise ValueError("Defesa M29 exige conta denominada em USD")
    tick_size = float(getattr(info, "trade_tick_size", 0) or 0)
    entry, structural = float(request["price"]), float(request["sl"])
    side = str(order.side).upper()
    if (side not in {"BUY", "SELL"} or not all(isfinite(v) and v > 0 for v in (tick_size, entry, structural))
            or (side == "BUY" and structural >= entry)
            or (side == "SELL" and structural <= entry)):
        raise ValueError("Precos invalidos para defesa M29")
    kind = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

    def profit(price):
        result = mt5.order_calc_profit(kind, order.symbol, float(order.quantity), entry, price)
        if result is None or not isfinite(float(result)):
            raise ValueError("Corretora nao calculou a defesa M29")
        return float(result)

    if profit(structural) >= -200.0:
        return request
    if abs(profit(entry)) > 1e-6:
        raise ValueError("Calculo financeiro M29 inconsistente")
    # Search toward the existing stop, never widening structural risk.
    safe, unsafe = entry, structural
    for _ in range(64):
        midpoint = (safe + unsafe) / 2
        if profit(midpoint) >= -200.0:
            safe = midpoint
        else:
            unsafe = midpoint
    rounded = (ceil(safe / tick_size) if side == "BUY" else floor(safe / tick_size)) * tick_size
    stop = round(rounded, int(getattr(info, "digits", 8)))
    if (not min(entry, structural) < stop < max(entry, structural)
            or profit(stop) < -200.000001):
        raise ValueError("Stop financeiro M29 nao representavel")
    return dict(request, sl=stop)
