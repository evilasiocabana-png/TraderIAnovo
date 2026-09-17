"""UI tests never launch workers or connect to MetaTrader."""

import os
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

SOURCE = '''
from dashboard.mt5_account_controls import render_mt5_account_controls
render_mt5_account_controls()
'''


def test_real_opt_in_is_independent_and_explicit():
    with patch("dashboard.mt5_account_controls.read_json", return_value={}), \
         patch("dashboard.mt5_account_controls.set_real_enabled") as save, \
         patch("dashboard.mt5_account_controls.ensure_real_worker") as start:
        before = dict(os.environ)
        app = AppTest.from_string(SOURCE).run()
        assert not app.exception
        assert not app.radio
        assert not app.checkbox[0].disabled
        assert not app.checkbox[0].value
        save.assert_not_called()
        app.checkbox[0].check().run()
        save.assert_not_called()
        app.button[0].click().run()
        assert not app.exception
        save.assert_called_once_with(True)
        start.assert_called_once()
        assert os.environ.get("TRADERIA_EXECUTION_ACCOUNT_MODE") == before.get("TRADERIA_EXECUTION_ACCOUNT_MODE")
        assert os.environ.get("TRADERIA_DEMO_EXECUTION_ENABLED") == before.get("TRADERIA_DEMO_EXECUTION_ENABLED")


def test_disable_real_does_not_change_demo():
    with patch("dashboard.mt5_account_controls.read_json", return_value={"enabled": True}), \
         patch("dashboard.mt5_account_controls.set_real_enabled") as save, \
         patch("dashboard.mt5_account_controls.ensure_real_worker"):
        app = AppTest.from_string(SOURCE).run()
        app.checkbox[0].uncheck()
        app.button[0].click().run()
        assert not app.exception
        save.assert_called_once_with(False)
