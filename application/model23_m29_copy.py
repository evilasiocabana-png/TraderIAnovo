"""One-way validated M29 signals into M23, independent of M29 own orders."""
from dataclasses import replace
import re
from application.model23_basket_accumulator import (
    MODEL_23_ID, MODEL_23_ALPHA_ID, MODEL_23_ALPHA_VERSION, MODEL_23_BETA_ID,
    MODEL_23_BETA_VERSION, MODEL_23_ENTRY_SOURCE, MODEL_23_EXIT_POLICY,
)
from application.model29_basket_accumulator import is_model29, model29_source_model_id

COPY_ID = MODEL_23_ID + "_SOURCE_M29"

def copy_confirmed_m29(model, row, plan, result):
    execution = getattr(result, "execution_result", None)
    ticket = getattr(execution, "ticket", None)
    if (not is_model29(model) or str(plan.symbol).upper() != "XAUUSD"
            or result.status != "EXECUTED" or not getattr(execution, "accepted", False) or not ticket):
        return None
    return copy_m29_signal(model, row, plan, parent_ticket=ticket)

def copy_m29_signal(model, row, plan, *, parent_ticket=None):
    if (not is_model29(model) or str(plan.symbol).upper() != "XAUUSD"
            or plan.status != "PLANO_VALIDO" or plan.direction not in {"BUY", "SELL"}):
        return None
    parameters = dict(plan.stop_management_parameters or {})
    origin = model29_source_model_id(model)
    if origin != "M7":
        return None
    mode = str(parameters.get("m29_m7_mode", "NORMAL")).upper() if origin == "M7" else "NORMAL"
    if mode not in {"NORMAL", "ESPELHADO"}:
        return None
    entry_type = re.sub(r"[^A-Z0-9_]+", "_", str(parameters.get("m29_entry_type") or plan.alpha_id).upper())
    parameters.update(
        source_operational_model="MODELO_29_BASKET_ACCUMULATOR",
        source_model_label="M29", m23_entry_type=origin + "_" + entry_type,
        m23_m29_original_signal_kind=parameters.get("active_signal_kind"),
        active_signal_kind="M29_" + origin + "_" + entry_type,
        m23_m29_origin_source=origin, m23_m29_origin_ticket=str(parent_ticket) if parent_ticket else None,
        m23_m29_admission="VALIDATED_SIGNAL",
        m23_m29_mode=mode, execution_volume=0.2 if mode == "ESPELHADO" else 0.1,
    )
    copied_plan = replace(plan, source=MODEL_23_ENTRY_SOURCE,
        alpha_id=MODEL_23_ALPHA_ID, alpha_version=MODEL_23_ALPHA_VERSION,
        beta_id=MODEL_23_BETA_ID, beta_version=MODEL_23_BETA_VERSION,
        beta_mode="FULL_EXIT_1000_ONLY", exit_model=MODEL_23_BETA_VERSION,
        stop_management=MODEL_23_EXIT_POLICY, stop_management_parameters=parameters,
        reason="M23 recebeu setup validado do M29. " + plan.reason)
    copied_row = replace(row, active_model="M23 <- M29 | " + row.active_model,
        lab_alpha_id=MODEL_23_ALPHA_ID, lab_alpha_version=MODEL_23_ALPHA_VERSION,
        beta_id=MODEL_23_BETA_ID, beta_version=MODEL_23_BETA_VERSION,
        beta_mode="FULL_EXIT_1000_ONLY", lab_parameters=parameters,
        lab_configuration_source=MODEL_23_ENTRY_SOURCE, research_plan_source=MODEL_23_ENTRY_SOURCE)
    return COPY_ID, copied_row, copied_plan

def copy_order_error(order):
    if str(getattr(order, "operational_model", "")) != COPY_ID:
        return None
    p = dict((getattr(order, "plan_snapshot", None) or {}).get("stop_management_parameters") or {})
    mode = p.get("m23_m29_mode")
    if str(order.symbol).upper() != "XAUUSD" or mode not in {"NORMAL", "ESPELHADO"} or not (p.get("m23_m29_origin_ticket") or p.get("m23_m29_admission") == "VALIDATED_SIGNAL"):
        return "M23 fonte M29 sem contrato de origem valido."
    if p.get("m23_m29_origin_source") != "M7":
        return "M23 fonte M29: somente a origem M7 esta autorizada."
    if abs(float(order.quantity) - (0.2 if mode == "ESPELHADO" else 0.1)) > 1e-8:
        return "M23 fonte M29 com lote diferente do modo autorizado."
    return None
