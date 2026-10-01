from types import SimpleNamespace as NS
import pytest
import dashboard_app as app
from application.report_entry_channel import entry_channel_columns

@pytest.mark.parametrize("model,source,channel", [
    ("MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29",8,"Transicao"),
    ("MODELO_30_ADAPTIVE_M23_SOURCE_M20",20,"Alta"),
    ("MODELO_29_BASKET_ACCUMULATOR_SOURCE_M7",7,"Baixa"),
])
def test_open_closed_and_export_preserve_entry_evidence(model,source,channel):
    row=NS(operational_model=model, symbol="XAUUSD", entry_setup="REENTRY",
        plan_snapshot={"stop_management_parameters":{
            "reinforcement_source":source,"reinforcement_state":channel}})
    expected=entry_channel_columns(row)
    for render in (app._mt5_open_trade_compact_row,app._mt5_trade_audit_compact_row,app._mt5_trade_audit_row):
        displayed=render(row)
        assert {key:displayed[key] for key in expected}==expected
    assert expected["Fonte original"]==f"M{source}"
    assert expected["Canal na entrada"]=={"Transicao":"Transição"}.get(channel,channel)
    assert app._mt5_trade_audit_csv_row(row,{})["Canal na entrada"]==expected["Canal na entrada"]

@pytest.mark.parametrize("snapshot", [None,[],{"stop_management_parameters":None},
    {"stop_management_parameters":[]}])
def test_legacy_unknown_is_not_current_channel(snapshot):
    row=NS(operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M29",plan_snapshot=snapshot)
    assert entry_channel_columns(row)=={"Fonte original":"Não registrada","Canal na entrada":"Não registrado"}

def test_original_m23_source_without_recorded_channel():
    row=NS(operational_model="MODELO_23_BASKET_ACCUMULATOR_SOURCE_M18")
    assert entry_channel_columns(row)=={"Fonte original":"M18","Canal na entrada":"Não registrado"}


def test_current_channel_is_per_source_not_entry_snapshot():
    from application.report_entry_channel import current_channel_labels
    from tests.test_reinforcement_chart_status import payload
    data=payload([-100,100,-200,100,-200,100])
    states=current_channel_labels(data,[("M7","XAUUSD"),("M18","XAUUSD")])
    assert states[("M7","XAUUSD")]=="Baixa"
    assert states[("M18","XAUUSD")]=="Formação"
    data["account"]["trade_mode"]=2
    assert current_channel_labels(data,[("M7","XAUUSD")])=={}


def test_current_channel_reader_requires_expected_demo_identity(monkeypatch):
    from infrastructure.execution.mt5_demo_execution_provider import MT5DemoExecutionProvider
    app._report_current_entry_channels.clear()
    monkeypatch.setattr(MT5DemoExecutionProvider,"_external_mt5_read",lambda *a,**k:{
        "ok":True,"account":{"trade_mode":0,"login":123,"server":"other"}})
    assert app._report_current_entry_channels((("M7","XAUUSD"),),"demo.exe","123","expected")=={}
    assert app._report_current_entry_channels((("M7","XAUUSD"),),"","","")=={}
