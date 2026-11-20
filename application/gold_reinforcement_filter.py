"""User-selected exploratory gold reinforcement contexts; not statistical validation."""
import math

VERSION = "GOLD_SOURCE_SIX_PLUS_M7_UPTREND_V4"
MIRROR_CONTEXTS = frozenset()
CONTEXTS = frozenset({
    (8, "Alta", "Perto do piso"),
    (8, "Transicao", "Abaixo do piso"),
    (10, "Transicao", "Abaixo do piso"),
    (18, "Baixa", "Meio"),
    (18, "Baixa", "Acima do teto"),
    (20, "Alta", "Abaixo do piso"),
})


def location(equity, operation, channel):
    if not channel:
        return "Sem canal", None
    lower = channel["slope"] * operation + channel["lower"]
    upper = channel["slope"] * operation + channel["upper"]
    if not all(math.isfinite(float(v)) for v in (equity, lower, upper)) or upper <= lower:
        raise ValueError("Canal invalido para calcular faixa")
    relative = (equity - lower) / (upper - lower)
    zone = ("Abaixo do piso" if relative < 0 else "Perto do piso" if relative < 1/3
            else "Meio" if relative < 2/3 else "Perto do teto" if relative <= 1
            else "Acima do teto")
    return zone, relative


def apply_filter(state, source, symbol):
    if str(symbol).upper() != "XAUUSD":
        return {**state, "blocked": True, "mode": "NORMAL", "filter_version": VERSION,
                "reason": "Reforcos autorizados somente no ouro (XAUUSD)"}
    key = (int(source), state["state"], state.get("zone", "Sem canal"))
    mirrored = key in MIRROR_CONTEXTS
    m7_uptrend = int(source) == 7 and state["state"] == "Alta" and (state.get("channel") or {}).get("trend") == "Alta"
    allowed = key in CONTEXTS or mirrored or m7_uptrend
    return {**state, "blocked": not allowed, "filter_version": VERSION, "mode": "ESPELHADO" if mirrored else "NORMAL",
            "reason": f"M{source}/XAUUSD: {state['state']} / {state.get('zone', 'Sem canal')} — "
                      + ("recorte autorizado" if allowed else "fora dos recortes autorizados")}
