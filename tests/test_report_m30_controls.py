from unittest.mock import MagicMock
from types import SimpleNamespace


def test_companions_follow_gold_before_bitcoin(monkeypatch):
    import dashboard_app as app
    fake = MagicMock()
    monkeypatch.setattr(app, "st", fake)
    monkeypatch.setattr(app, "_m7_operational_chart_results", lambda *a: [])
    seen = []
    fake.markdown.side_effect = seen.append
    app._render_m23_source_structure("M7", [], after_gold=lambda: seen.extend(["M29", "M30"]))
    assert "Ouro" in seen[0]
    assert seen[1:3] == ["M29", "M30"]
    assert "Bitcoin" in seen[3]


def test_apply_models_updates_existing_m30_gate(monkeypatch):
    import dashboard_app as app
    service = MagicMock()
    old_selection = MagicMock()
    monkeypatch.setattr(app, "DashboardService", lambda: service)
    monkeypatch.setattr(app, "_persist_mt5_operational_model_form_selection", old_selection)
    monkeypatch.setattr(app, "st", SimpleNamespace(session_state={"mt5_m30_send_enabled": True}))
    app._persist_mt5_models_with_m30()
    service.set_model30_enabled.assert_called_once_with(True)
    old_selection.assert_called_once()
    app.st.session_state["mt5_m30_send_enabled"] = False
    app._persist_mt5_models_with_m30()
    assert service.set_model30_enabled.call_args.args == (False,)


def test_m30_report_keeps_own_execution_history():
    import dashboard_app as app
    row = SimpleNamespace(operational_model="MODELO_30_ADAPTIVE_M23_SOURCE_M7", symbol="XAUUSD")
    assert app._mt5_rows_for_equity_model_filter([row], "MODELO 30") == [row]
    assert app._mt5_rows_for_equity_model_filter([row], "MODELO 23") == []
