import json

from streamlit.testing.v1 import AppTest
from application.learning_dashboard import model30_theoretical_rows


def pair(time, **snapshot):
    return dict(created_at=time, source="M29", symbol="XAUUSD", status="ACCEPTED",
                filter_version="BASELINE", reason="accepted", snapshot=json.dumps(snapshot))


def test_m30_uses_clone_contract_and_latest_route_not_m23_history():
    snapshot = dict(direction="SELL", entry_price=10, initial_stop=12, target=8,
                    stop_management_parameters=dict(m23_m29_origin_source="M8", m30_execution_volume=.1))
    state = dict(rows=[dict(entry_price=999)], pairs=[pair("2026-09-25", **snapshot), pair("2026-09-26", **snapshot)])
    rows = model30_theoretical_rows(state)
    assert len(rows) == 1
    assert rows[0]["Registro"] == "2026-09-26"
    assert rows[0]["Fonte"] == "M8"
    assert rows[0]["Entrada teorica"] == 10
    assert rows[0]["Lote"] == .1
    assert rows[0]["Status"] == "ACCEPTED"


def test_missing_prices_are_not_fabricated():
    row = model30_theoretical_rows(dict(pairs=[pair("2026-09-25")]))[0]
    assert row["Entrada teorica"] is None
    assert row["Stop"] is None
    assert row["Lote"] is None


def test_empty_surface_does_not_send_or_change_configuration():
    app = AppTest.from_string('''
from application.learning_dashboard import render_model30_theoretical
class Service:
    def get_learning_dashboard(self, **kwargs):
        return dict(pairs=[])
render_model30_theoretical(Service())
''').run(timeout=20)
    assert not app.exception
    assert "Modelo 30" in app.subheader[0].value
    assert "sem plano registrado" in app.info[0].value
    assert not app.toggle
