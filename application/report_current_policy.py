"""Read-only report scopes: exclude legacy or unidentifiable policy results."""
from application.model30_independent import POLICY as M30_POLICY
from application.source_channel_gate import POLICY as REINFORCEMENT_POLICY
from domain.operational_model_policy import operational_model_number


def current_policy_rows(rows, model, *, m7_only=False):
    if model not in ("M29", "M30"):
        return list(rows)
    result = []
    for row in rows:
        snapshot = getattr(row, "plan_snapshot", None)
        if not isinstance(snapshot, dict):
            continue
        parameters = snapshot.get("stop_management_parameters") or {}
        if not isinstance(parameters, dict):
            continue
        if model == "M30":
            if (parameters.get("m30_policy") == M30_POLICY
                    and (not m7_only or operational_model_number(parameters.get("m30_baseline_model")) == 7)):
                result.append(row)
        elif (parameters.get("reinforcement_policy") == REINFORCEMENT_POLICY
              and parameters.get("m23_m29_mode") == "NORMAL"
              and (not m7_only or parameters.get("m23_m29_origin_source") == "M7")):
            result.append(row)
    return result
