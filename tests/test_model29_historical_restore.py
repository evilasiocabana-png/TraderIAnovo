import pytest
from application.model29_historical_mode import historical_mode_state
from application.model29_entry_sync import is_gold_channel_source
from application.model23_m29_copy import copy_m29_signal
from application.model29_basket_accumulator import MODEL_29_ID
from tests.test_model23_context_integration import setup_service


@pytest.mark.parametrize("outcomes,mode", [("PPPP","ESPELHADO"),("PPPPGGGG","NORMAL"),
    ("GPGPPP","ESPELHADO"),("PGPGPP","ESPELHADO"),
    ("PPPPGPGPGG","NORMAL"),("PPPPPGPGGG","NORMAL")])
def test_historical_sequences(outcomes, mode):
    rows = [{"position": str(i), "net": 1 if v == "G" else -1} for i,v in enumerate(outcomes)]
    assert historical_mode_state(rows)["mode"] == mode


@pytest.mark.parametrize("source", ["M8","M10","M18","M20"])
def test_normal_sources_do_not_consult_channels(tmp_path, monkeypatch, source):
    service, row, plan = setup_service(tmp_path, monkeypatch)
    def forbidden(*args, **kwargs):
        raise AssertionError("No channel or sequence lookup for normal sources")
    monkeypatch.setattr("application.model29_sequence_history.sequence_mode", forbidden)
    actual_row, actual_plan = service._apply_model29_m7_mode(row, plan, source)
    assert actual_plan is plan
    copied = copy_m29_signal(MODEL_29_ID + "_SOURCE_" + source, actual_row, actual_plan)
    assert copied[2].stop_management_parameters["m23_m29_mode"] == "NORMAL"
    assert copied[2].stop_management_parameters["execution_volume"] == 0.1
