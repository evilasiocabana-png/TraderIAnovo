"""USD200 broker-priced initial defense for direct M23 entries.

M29 copies retain their independently configured defense. No position updates.
"""
from math import ceil, floor, isfinite
from application.model23_basket_accumulator import is_model23, model23_source_model_id

LIMIT_USD = 200.0


def protected_request(order, request, mt5):
    model = getattr(order, "operational_model", "")
    if not is_model23(model) or model23_source_model_id(model) == "M29":
        return request
    if str(getattr(mt5.account_info(), "currency", "")).upper() != "USD":
        raise ValueError("Defesa M23 exige conta USD")
    info = mt5.symbol_info(order.symbol)
    tick = float(getattr(info, "trade_tick_size", 0) or 0)
    entry, structural, volume = (float(request[k]) for k in ("price", "sl", "volume"))
    side = str(order.side).upper()
    if (side not in {"BUY", "SELL"}
            or not all(isfinite(v) and v > 0 for v in (tick, entry, structural, volume))
            or (structural >= entry if side == "BUY" else structural <= entry)):
        raise ValueError("Dados invalidos para defesa M23")
    kind = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL

    def loss(price):
        result = mt5.order_calc_profit(kind, order.symbol, volume, entry, price)
        if result is None or not isfinite(float(result)):
            raise ValueError("Corretora nao calculou a perda M23")
        return -float(result)

    if abs(loss(entry)) > 1e-6:
        raise ValueError("Calculo financeiro M23 inconsistente")
    structural_loss = loss(structural)
    if structural_loss <= 0:
        raise ValueError("Perda estrutural M23 invalida")
    if structural_loss <= LIMIT_USD:
        return request
    safe, unsafe = entry, structural
    for _ in range(64):
        midpoint = (safe + unsafe) / 2
        calculated = loss(midpoint)
        if calculated < 0:
            raise ValueError("Calculo financeiro M23 inconsistente")
        if calculated <= LIMIT_USD:
            safe = midpoint
        else:
            unsafe = midpoint
    units = ceil(safe / tick) if side == "BUY" else floor(safe / tick)
    stop = round(units * tick, int(getattr(info, "digits", 8)))
    if not min(entry, structural) < stop < max(entry, structural):
        raise ValueError("Stop financeiro M23 nao representavel")
    final_loss = loss(stop)
    if not 0 < final_loss <= LIMIT_USD:
        raise ValueError("Stop financeiro M23 excede limite")
    return dict(request, sl=stop)
