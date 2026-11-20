from types import SimpleNamespace as NS
import pytest
import dashboard_app as app


def test_original_m23_m7_and_column_position():
    row = NS(symbol="XAUUSD", operational_model=app.MT5_OPERATIONAL_MODEL_23+"_SOURCE_M7",
        entry_setup="TREND_MOMENTUM", plan_snapshot={"stop_management_parameters":{"source_model_label":"M7"}})
    rendered = app._mt5_open_trade_compact_row(row)
    assert rendered["Modelo"] == "Modelo 23 (Fonte: M7)"
    assert rendered["Setup de entrada"] == "M23 <- M7 | TREND_MOMENTUM"
    columns = list(rendered)
    assert columns[columns.index("Risco atual")+1] == "Setup de entrada"


@pytest.mark.parametrize("mode", ["NORMAL", "ESPELHADO"])
def test_copy_preserves_original_source_and_mode(mode):
    row=NS(plan_snapshot={"entry_setup":"REENTRY","stop_management_parameters":{
        "m23_m29_origin_source":"M18","m23_m29_mode":mode}})
    assert app._mt5_open_trade_entry_setup(row)==f"M23 <- M29 (M18) | {mode} | REENTRY"


def test_missing_evidence_does_not_guess_from_executor(monkeypatch):
    monkeypatch.setattr(app,"_mt5_recorded_entry_origin",lambda row: "")
    assert app._mt5_open_trade_entry_setup(NS(operational_model=app.MT5_OPERATIONAL_MODEL_23)).startswith("N/D")


def test_recorded_order_fallback(monkeypatch):
    monkeypatch.setattr(app,"_mt5_recorded_entry_origin",lambda row:"M23 <- M5 | TREND_PULLBACK")
    assert app._mt5_open_trade_entry_setup(NS(mt5_ticket=123,symbol="EURUSD"))=="M23 <- M5 | TREND_PULLBACK"


def test_non_demo_does_not_use_demo_log(monkeypatch):
    monkeypatch.setattr(app,"_mt5_recorded_entry_origin",lambda row:pytest.fail("cross-account lookup"))
    assert app._mt5_open_trade_entry_setup(NS(execution_account_mode="REAL")).startswith("N/D")


@pytest.mark.parametrize("mode", ["NORMAL", "ESPELHADO"])
def test_open_copy_label_uses_immediate_source(mode):
    row = NS(operational_model=app.MT5_OPERATIONAL_MODEL_23+"_SOURCE_M29",
        plan_snapshot={"stop_management_parameters":{
            "source_model_label":"M29", "m23_m29_origin_source":"M7", "m23_m29_mode":mode}})
    assert app._mt5_open_trade_model_label(row) == "Modelo 23 (Fonte: M29)"
    assert f"M29 (M7) | {mode}" in app._mt5_open_trade_entry_setup(row)


@pytest.mark.parametrize("source", ["M1", "M5", "M7", "M8", "M10", "M18", "M20"])
def test_open_original_label_all_sources(source):
    row = NS(operational_model=app.MT5_OPERATIONAL_MODEL_23+"_SOURCE_"+source)
    assert app._mt5_open_trade_model_label(row) == f"Modelo 23 (Fonte: {source})"


def test_open_label_uses_recorded_metadata_without_guessing(monkeypatch):
    monkeypatch.setattr(app,"_mt5_recorded_entry_origin",lambda row: "")
    assert app._mt5_open_trade_model_label(NS(operational_model=app.MT5_OPERATIONAL_MODEL_23)) == "Modelo 23"
    row = NS(operational_model=app.MT5_OPERATIONAL_MODEL_29,
        plan_snapshot={"stop_management_parameters":{"source_operational_model":app.MT5_OPERATIONAL_MODEL_7}})
    assert app._mt5_open_trade_model_label(row) == "Modelo 29 (Fonte: M7)"
