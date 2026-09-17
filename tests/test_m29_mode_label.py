from types import SimpleNamespace
import pytest
import dashboard_app as app

@pytest.mark.parametrize("mode,label", [("ESPELHADO","Espelhado"),("NORMAL","Normal"),("","Modo nao registrado")])
def test_m29_mode_comes_from_entry_snapshot(mode,label):
    row=SimpleNamespace(operational_model=app.MT5_OPERATIONAL_MODEL_29+"_SOURCE_M7",plan_snapshot={"stop_management_parameters":{"m29_m7_mode":mode}})
    assert app._mt5_sender_model_label(row)==f"MODELO 29 - {label} (fonte M7)"

def test_other_source_does_not_inherit_mirror_label():
    row=SimpleNamespace(operational_model=app.MT5_OPERATIONAL_MODEL_29+"_SOURCE_M1",plan_snapshot={"stop_management_parameters":{"m29_m7_mode":"ESPELHADO"}})
    assert app._mt5_sender_model_label(row)=="MODELO 29"
