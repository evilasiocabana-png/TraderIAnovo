"""Historical M7 sequence policy, without operational equity channels."""
from application.model29_m7_sequence import M7SequenceState

POLICY = "M23_M7_HISTORICAL_SEQUENCE_20260916"


def historical_mode_state(rows):
    state = M7SequenceState(four_result_trigger=True, historical_alternations=True)
    for row in rows:
        state.record(str(row["position"]), float(row["net"]))
    return {"mode": state.mode, "mode_policy": POLICY}
