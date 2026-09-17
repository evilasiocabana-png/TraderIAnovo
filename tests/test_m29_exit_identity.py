from types import SimpleNamespace
import dashboard_app as app

def test_m29_sender_is_not_replaced_by_m1_source():
    model=app.MT5_OPERATIONAL_MODEL_29 + "_SOURCE_M1"
    row=SimpleNamespace(operational_model=model,entry_setup="M29 <- M1 | ADX_TREND_STRENGTH",exit_setup="M29_FULL_EXIT_1000_ONLY",plan_snapshot={})
    effective=app._mt5_theoretical_exit_effective_model(row,app.MT5_OPERATIONAL_MODEL_1)
    assert effective==model
    assert app._mt5_theoretical_exit_has_recorded_model(row)
    assert app._mt5_sender_model_label(row,effective)=="MODELO 29"
    assert app._mt5_theoretical_exit_selection_status(effective,{app.MT5_OPERATIONAL_MODEL_29})=="ATIVO PARA ENTRADA"
    assert app._mt5_theoretical_exit_entry_model_label(row,{})==row.entry_setup
    assert app._mt5_theoretical_exit_model_label(row,{},effective)==row.exit_setup
