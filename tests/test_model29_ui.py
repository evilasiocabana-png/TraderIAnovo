from types import SimpleNamespace

from streamlit.testing.v1 import AppTest
import dashboard_app as app


def test_m29_off_by_default_can_be_selected_without_m23(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    test = AppTest.from_string(
        "import dashboard_app as app\napp._render_mt5_operational_model_selector()"
    ).run(timeout=20)
    assert not test.exception
    boxes = {c.label:c for c in test.checkbox}
    assert "M29" in boxes
    assert not boxes["M29"].value
    for label, box in boxes.items():
        if label.startswith("M") or label == "Todos":
            box.set_value(label == "M29")
    next(b for b in test.button if b.label == "Aplicar modelos").click()
    test.run(timeout=20)
    assert not test.exception
    assert app._load_persisted_mt5_operational_selections() == (app.MT5_OPERATIONAL_MODEL_29,)
    assert any(m.value == "LIGADAS" and m.label == "Novas entradas M29" for m in test.metric)
    assert 29 in app.MT5_ACTIVE_REPORT_MODEL_NUMBERS
    assert app._mt5_equity_row_model_key(SimpleNamespace(
        operational_model=app.MT5_OPERATIONAL_MODEL_29 + "_SOURCE_M7")) == "MODELO29"
