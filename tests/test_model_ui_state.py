from application.learning_store import LearningStore
from application.model30_configuration import enabled, set_enabled
from application.model_ui_state import model_ui_state, sync_persisted_widget, REPORT_MODEL_NUMBERS
from streamlit.testing.v1 import AppTest


def test_all_consumers_read_same_persisted_permission(tmp_path):
    from application.model30_learning import enabled as execution_enabled
    store = LearningStore(tmp_path / "ui.sqlite3")
    assert not enabled(store)
    set_enabled(True, store)
    assert execution_enabled(store)
    state = model_ui_state(["MODELO_23_BASKET_ACCUMULATOR"], store=store)
    assert state.summary == "M23 + M30"
    set_enabled(False, store)
    assert not execution_enabled(store)
    assert model_ui_state(["MODELO_23_BASKET_ACCUMULATOR"], store=store).summary == "M23"


def test_widget_refreshes_other_tab_without_discarding_unsaved_edits():
    session = {}
    sync_persisted_widget(session, "mt5", True)
    sync_persisted_widget(session, "learning", True)
    session["mt5"] = False
    sync_persisted_widget(session, "mt5", True)
    assert session["mt5"] is False
    sync_persisted_widget(session, "learning", False)
    assert session["learning"] is False
    sync_persisted_widget(session, "mt5", False)
    assert session["mt5"] is False
    sync_persisted_widget(session, "mt5", True)
    assert session["mt5"] is True


def test_report_catalog_preserves_retirement_and_includes_m30():
    assert {7, 23, 29, 30} <= set(REPORT_MODEL_NUMBERS)
    assert not {3, 4, 6, 24, 25} & set(REPORT_MODEL_NUMBERS)


def test_learning_toggle_does_not_reenable_after_change_in_mt5():
    app = AppTest.from_string("""
import streamlit as st
from application.learning_dashboard import render_model30_panel
class Service:
    def get_learning_dashboard(self, **kwargs):
        return dict(rows=[],pairs=[],comparison=[],m30_enabled=st.session_state['backend'])
    def set_model30_enabled(self, value):
        st.session_state['writes'].append(value)
        st.session_state['backend'] = value
render_model30_panel(Service())
""")
    app.session_state['backend'] = True
    app.session_state['writes'] = []
    app.run(timeout=20)
    assert not app.exception
    assert app.toggle[0].value is True
    app.session_state['backend'] = False
    app.run(timeout=20)
    assert not app.exception
    assert app.toggle[0].value is False
    assert app.session_state['writes'] == []
    app.toggle[0].set_value(True).run(timeout=20)
    assert not app.exception
    assert app.session_state['backend'] is True
    assert app.session_state['writes'] == [True]
