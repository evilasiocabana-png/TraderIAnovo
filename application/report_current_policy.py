"""Read-only report scopes: exclude legacy or unidentifiable policy results."""
from application.model30_independent import POLICY as M30_POLICY


def current_policy_rows(rows, model):
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
            if parameters.get("m30_policy") == M30_POLICY:
                result.append(row)
        elif (parameters.get("m23_m29_origin_source") == "M7"
              and parameters.get("m29_sequence_mode") == "ESPELHADO"
              and "m29_channel_mode" not in parameters):
            result.append(row)
    return result
