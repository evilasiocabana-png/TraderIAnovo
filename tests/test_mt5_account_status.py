"""Account indicators never initialize MT5 or enable trading."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

from dashboard.mt5_account_controls import demo_status_view, real_status_view
from core.dual_mt5 import REAL_LOGIN, REAL_SERVER


NOW = datetime(2026, 9, 6, 22, tzinfo=timezone.utc)
CONTROL = {"enabled": True, "authorized": True, "login": REAL_LOGIN, "server": REAL_SERVER}
PERMISSIONS = {"connected": True, "algotrading": True, "python_api_disabled": False,
               "account_trade_allowed": True, "account_trade_expert": True}


def real_state(stamp=NOW):
    return {"login": REAL_LOGIN, "server": REAL_SERVER, "updated_at": stamp.isoformat(),
            "status": "ARMED_WAITING", "message": "Aguardando sinal", "permissions": PERMISSIONS}


def forex(account="61551556", server="Pepperstone-Demo", stamp=NOW):
    return SimpleNamespace(account=account, server=server, last_mt5_read=stamp.isoformat(),
                           connection_status="CONNECTED", timeframe="M5")


@pytest.mark.parametrize("stamp", [NOW-timedelta(seconds=91), NOW+timedelta(seconds=1)])
def test_old_or_future_real_status_does_not_claim_connected(stamp):
    result = real_status_view(CONTROL, real_state(stamp), now=NOW)
    assert result["requested"]
    assert not result["recent"]
    assert result["status"] == "SEM STATUS RECENTE"
    assert result["account"] == "N/D"
    assert result["permissions"] == {}


@pytest.mark.parametrize("stamp", [None, "bad", "2026-09-06T22:00:00"])
def test_invalid_real_timestamp_is_unknown(stamp):
    state = real_state()
    state["updated_at"] = stamp
    assert not real_status_view(CONTROL, state, now=NOW)["recent"]


def test_current_real_waiting_and_revocation():
    result = real_status_view(CONTROL, real_state(), now=NOW)
    assert result["requested"] and result["recent"]
    assert result["status"] == "ARMED_WAITING"
    assert result["updated"] == "06/09/2026 19:00:00 BRT"
    result = real_status_view({**CONTROL, "enabled": False}, real_state(), now=NOW)
    assert not result["requested"]
    assert result["status"] == "NOVAS ENTRADAS DESLIGADAS"


def test_enabled_without_authorization_is_not_active():
    assert not real_status_view({"enabled": True}, real_state(), now=NOW)["requested"]


def test_real_quote_does_not_prove_demo_connection():
    result = demo_status_view(forex(REAL_LOGIN, REAL_SERVER), {"online": True},
        {"updated_at": NOW.isoformat(), "status": "ARMED_WAITING"}, configured=True, now=NOW)
    assert result["status"] == "FONTE DE DADOS DIVERGENTE"
    assert not result["recent"]
    assert result["account"] == "N/D"
    assert result["permissions"] == {}


def test_demo_cycle_is_separate_from_permissions():
    result = demo_status_view(forex(), {"online": True},
        {"updated_at": NOW.isoformat(), "status": "ARMED_WAITING"}, configured=True, now=NOW)
    assert result["recent"] and result["requested"]
    assert result["status"] == "ARMED_WAITING"
    assert result["permissions"] == {"connected": True}


def test_demo_accepts_dashboard_brt_timestamp():
    snapshot = forex()
    snapshot.last_mt5_read = "06/09/2026 19:00"
    result = demo_status_view(snapshot, {"online": True},
        {"updated_at": NOW.isoformat(), "status": "ARMED_WAITING"}, configured=True, now=NOW)
    assert result["recent"]
    assert result["account"] == "61551556"
    snapshot.last_mt5_read = "06/09/2026 18:57"
    assert not demo_status_view(snapshot, {"online": True}, {}, configured=True, now=NOW)["recent"]
    assert "algotrading" not in result["permissions"]


def test_demo_missing_cycle_or_disabled():
    result = demo_status_view(forex(), {"online": True}, {}, configured=True, now=NOW)
    assert result["status"] == "SEM CICLO RECENTE"
    assert not result["recent"]
    result = demo_status_view(forex(), {"online": True}, {}, configured=False, now=NOW)
    assert result["status"] == "NOVAS ENTRADAS DESLIGADAS"


@pytest.mark.parametrize("permissions, expected", [({}, "PERMISSOES NAO CONFIRMADAS"),
    ({**PERMISSIONS, "algotrading": False}, "PERMISSOES BLOQUEADAS")])
def test_real_permission_not_inferred_from_armed_label(permissions, expected):
    result = real_status_view(CONTROL, {**real_state(), "permissions": permissions}, now=NOW)
    assert result["status"] == expected


def test_wrong_real_identity_hides_other_accounts_permissions():
    result = real_status_view(CONTROL, {**real_state(), "login": "999"}, now=NOW)
    assert result["status"] == "CONTA DIVERGENTE"
    assert not result["recent"] and result["permissions"] == {}


def test_status_render_is_read_only():
    source = '''
from types import SimpleNamespace
from dashboard.mt5_account_controls import render_mt5_accounts_status
render_mt5_accounts_status(SimpleNamespace(), configured=True)
'''
    with patch("dashboard.mt5_account_controls.read_demo_terminal_status", return_value={}), \
         patch("dashboard.mt5_account_controls.read_json", return_value={}), \
         patch("dashboard.mt5_account_controls.set_real_enabled") as save, \
         patch("dashboard.mt5_account_controls.ensure_real_worker") as worker:
        app = AppTest.from_string(source).run()
        assert not app.exception
        html = " ".join(item.value for item in app.markdown)
        assert "DEMO" in html and "REAL" in html
        assert "SEM STATUS RECENTE" not in html  # Disabled authorization is explicit.
        assert "NOVAS ENTRADAS DESLIGADAS" in html
        save.assert_not_called()
        worker.assert_not_called()


def test_status_render_escapes_external_message():
    source = '''
from types import SimpleNamespace
from dashboard.mt5_account_controls import render_mt5_accounts_status
render_mt5_accounts_status(SimpleNamespace(), configured=False)
'''
    state = {**real_state(datetime.now(timezone.utc)), "message": "<script>alert(1)</script>"}
    def read(path):
        return state if path.name == "status.json" else CONTROL if path.name == "additional_real.json" else {}
    with patch("dashboard.mt5_account_controls.read_demo_terminal_status", return_value={}), \
         patch("dashboard.mt5_account_controls.read_json", side_effect=read):
        app = AppTest.from_string(source).run()
    assert not app.exception
    html = " ".join(item.value for item in app.markdown)
    assert "&lt;script&gt;" in html
    assert "<script>" not in html


def test_guard_restarts_demo_with_dedicated_identity():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "scripts/traderianovo_ram_guard.ps1").read_text(encoding="utf-8")
    assert "TRADERIA_EXECUTION_ACCOUNT_MODE='DEMO'" in source
    assert "TRADERIA_REAL_EXECUTION_ENABLED='0'" in source
    assert "TRADERIA_DEMO_ACCOUNT_LOGIN='61551556'" in source
    assert "TRADERIA_DEMO_ACCOUNT_SERVER='Pepperstone-Demo'" in source
    assert "TraderIANovo\\MT5-Demo\\terminal64.exe" in source
    assert "MT5_PORTABLE='1'" in source
    assert "MT5_PATH='C:\\Program Files\\MetaTrader 5" not in source


@pytest.mark.parametrize("algo", [True, False])
def test_demo_terminal_permissions_are_independent_of_robot_cycle(algo):
    terminal = {"login": 61551556, "server": "Pepperstone-Demo",
                "updated_at": NOW.isoformat(), "permissions": {**PERMISSIONS, "algotrading": algo}}
    result = demo_status_view(forex(), {"online": True},
        {"updated_at": NOW.isoformat(), "status": "ERROR"},
        configured=True, now=NOW, terminal=terminal)
    assert result["status"] == "ERROR"
    assert result["permissions"]["algotrading"] is algo


@pytest.mark.parametrize("changes", [{"login": 51517136},
    {"updated_at": (NOW-timedelta(seconds=91)).isoformat()}])
def test_demo_rejects_stale_or_wrong_terminal_permissions(changes):
    terminal = {"login": 61551556, "server": "Pepperstone-Demo",
                "updated_at": NOW.isoformat(), "permissions": PERMISSIONS, **changes}
    result = demo_status_view(forex(), {}, {}, configured=True, now=NOW, terminal=terminal)
    assert "algotrading" not in result["permissions"]
