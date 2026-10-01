"""Entry evidence for open and closed report rows; never uses live channels."""
import re


def entry_channel_columns(row):
    snapshot = getattr(row, "plan_snapshot", None)
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    parameters = snapshot.get("stop_management_parameters")
    parameters = parameters if isinstance(parameters, dict) else {}
    source = ""
    for candidate in (parameters.get("reinforcement_source"),
                      parameters.get("m23_m29_origin_source"),
                      parameters.get("source_model_label")):
        match = re.fullmatch(r"M?([0-9]+)", str(candidate or "").upper())
        if match and 1 <= int(match.group(1)) <= 30:
            source = "M" + match.group(1)
            break
    if not source:
        model = str(snapshot.get("operational_model") or getattr(row, "operational_model", ""))
        match = re.search(r"_SOURCE_(M[0-9]+)$", model)
        if match:
            source = match.group(1)
        else:
            origin = str(parameters.get("source_operational_model") or model)
            match = re.match(r"MODELO_([0-9]+)(?:_|$)", origin)
            if match and int(match.group(1)) not in (23, 29, 30):
                source = "M" + match.group(1)
    # An intermediary is not evidence of the original source.
    if source in ("M23", "M29", "M30"):
        source = ""
    state = str(parameters.get("reinforcement_state") or "").strip().casefold()
    channels = {"alta": "Alta", "baixa": "Baixa", "lateral": "Lateral",
                "transicao": "Transição", "transição": "Transição",
                "formacao": "Formação", "formação": "Formação"}
    return {"Fonte original": source or "Não registrada",
            "Canal na entrada": channels.get(state, "Não registrado")}
