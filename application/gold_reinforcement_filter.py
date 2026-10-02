"""User-selected exploratory gold reinforcement contexts; not statistical validation."""
import math

VERSION = "GOLD_SOURCE_CHANNEL_SIX_CONTEXTS_V1"
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
        return state
    allowed = (int(source), state["state"], state.get("zone", "Sem canal")) in CONTEXTS
    return {**state, "blocked": not allowed, "filter_version": VERSION,
            "reason": f"M{source}/XAUUSD: {state['state']} / {state.get('zone', 'Sem canal')} — "
                      + ("recorte autorizado" if allowed else "fora dos seis recortes autorizados")}
