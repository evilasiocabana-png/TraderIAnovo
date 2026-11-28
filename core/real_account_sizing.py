"""Account-scoped sizing; never changes Demo or existing position volumes."""
import os
import math

def real_mode():
    return os.getenv("TRADERIA_EXECUTION_ACCOUNT_MODE", "DEMO").upper() == "REAL"

def real_entry_volume(model):
    model = str(model)
    return 0.02 if model.startswith("MODELO_29_") or model.startswith("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29") else 0.01

def basket_target(default=1000.0):
    return 100.0 if real_mode() else float(default)

def volume_error(order, mode):
    if mode == "REAL" and not math.isclose(float(order.quantity), real_entry_volume(order.operational_model), rel_tol=0, abs_tol=1e-9):
        return "Lote Real diverge da politica autorizada: normal 0.01, reforco M29 0.02."
    return None
