"""Additional Real control; rendering never switches the Demo executor."""

from datetime import datetime, timedelta, timezone
from html import escape
import os

import streamlit as st

from core.dual_mt5 import CONTROL, STATUS, PROJECT, REAL_LOGIN, REAL_SERVER, read_json, set_real_enabled, ensure_real_worker
from core.mt5_permissions import permissions_label, permissions_allowed
from core.mt5_terminal_status import read_demo_terminal_status


STATUS_MAX_AGE_SECONDS = 90


def _timestamp(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return result if result.tzinfo is not None else None
    except (TypeError, ValueError):
        return None


def _fresh(value, now):
    stamp = _timestamp(value)
    return stamp is not None and 0 <= (now - stamp).total_seconds() <= STATUS_MAX_AGE_SECONDS


def _market_stamp(forex):
    value = getattr(forex, "last_mt5_read", None) or getattr(forex, "last_update", None)
    stamp = _timestamp(value)
    if stamp is not None:
        return stamp.isoformat()
    # DashboardService has already converted these display timestamps to BRT.
    try:
        return datetime.strptime(str(value), "%d/%m/%Y %H:%M").replace(
            tzinfo=timezone(timedelta(hours=-3))
        ).isoformat()
    except ValueError:
        return None


def _time_label(value):
    stamp = _timestamp(value)
    return stamp.astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M:%S BRT") if stamp else "N/D"


def real_status_view(control, state, *, now=None):
    now = now or datetime.now(timezone.utc)
    recent = _fresh(state.get("updated_at"), now)
    authorized = (control.get("authorized") is True and str(control.get("login")) == REAL_LOGIN
                  and control.get("server") == REAL_SERVER)
    enabled = authorized and control.get("enabled") is True
    permissions = state.get("permissions") if recent else {}
    permissions = permissions if isinstance(permissions, dict) else {}
    identity_ok = str(state.get("login")) == REAL_LOGIN and state.get("server") == REAL_SERVER
    status = str(state.get("status") or "SEM LEITURA") if recent else "SEM STATUS RECENTE"
    if recent and state.get("login") and not identity_ok:
        status = "CONTA DIVERGENTE"
        permissions = {}
    elif not enabled:
        status = "NOVAS ENTRADAS DESLIGADAS"
    elif recent and not identity_ok:
        status = "CONTA NAO CONFIRMADA"
        permissions = {}
    elif recent and not permissions_allowed(permissions):
        blocked = permissions.get("python_api_disabled") is True or any(
            permissions.get(key) is False
            for key in ("connected", "algotrading", "account_trade_allowed", "account_trade_expert")
        )
        status = "PERMISSOES BLOQUEADAS" if blocked else "PERMISSOES NAO CONFIRMADAS"
    return {
        "environment": "REAL", "expected_account": REAL_LOGIN, "expected_server": REAL_SERVER,
        "account": str(state.get("login") or "N/D") if recent else "N/D",
        "server": str(state.get("server") or "N/D") if recent else "N/D",
        "requested": enabled, "status": status, "recent": recent and identity_ok,
        "updated": _time_label(state.get("updated_at")),
        "message": str(state.get("message") or "") if recent else "Processo sem leitura recente; conexao e permissoes atuais nao confirmadas.",
        "permissions": permissions,
    }


def demo_status_view(forex, online, background, *, configured, now=None, terminal=None):
    now = now or datetime.now(timezone.utc)
    login = os.getenv("TRADERIA_DEMO_ACCOUNT_LOGIN") or "61551556"
    server = os.getenv("TRADERIA_DEMO_ACCOUNT_SERVER") or "Pepperstone-Demo"
    stamp = _market_stamp(forex)
    recent = _fresh(stamp, now)
    cycle_recent = _fresh(background.get("updated_at"), now)
    account = str(getattr(forex, "account", "") or "N/D")
    observed_server = str(getattr(forex, "server", "") or "N/D")
    identity_ok = account == login and observed_server == server
    enabled = configured and online.get("online") is True
    connection = str(getattr(forex, "connection_status", "")).upper()
    status = "CICLO ATIVO" if enabled and cycle_recent else "SEM CICLO RECENTE"
    if not enabled:
        status = "NOVAS ENTRADAS DESLIGADAS"
    elif not recent:
        status = "SEM LEITURA RECENTE"
    elif account != "N/D" and not identity_ok:
        status = "FONTE DE DADOS DIVERGENTE"
    elif not identity_ok:
        status = "CONTA NAO CONFIRMADA"
    elif connection != "CONNECTED":
        status = "CONEXAO NAO CONFIRMADA"
    elif cycle_recent:
        status = str(background.get("status") or "CICLO ATIVO")
    # The market snapshot does not prove executor/Algotrading permissions.
    view = {
        "environment": "DEMO", "expected_account": login, "expected_server": server,
        "account": account if recent and identity_ok else "N/D",
        "server": observed_server if recent and identity_ok else "N/D",
        "requested": enabled, "status": status, "recent": recent and cycle_recent and identity_ok,
        "updated": _time_label(background.get("updated_at")),
        "message": str(background.get("message") or "") if cycle_recent else "Sem ciclo recente confirmado.",
        "permissions": {"connected": connection == "CONNECTED"} if recent and identity_ok else {},
    }
    terminal = terminal or {}
    if (_fresh(terminal.get("updated_at"), now)
            and str(terminal.get("login")) == login and terminal.get("server") == server):
        view["permissions"] = terminal.get("permissions") or {}
        view["account"] = login
        view["server"] = server
        view["terminal_updated"] = _time_label(terminal.get("updated_at"))
    return view


def render_mt5_accounts_status(forex, *, configured):
    online = read_json(PROJECT / ".traderia/mt5_demo_robot_online_state.json")
    background = read_json(PROJECT / ".traderia/mt5_demo_robot_background_state.json")
    control, state = read_json(CONTROL), read_json(STATUS)
    views = [demo_status_view(forex, online, background, configured=configured,
                             terminal=read_demo_terminal_status()), real_status_view(control, state)]
    selected = [v["environment"] for v in views if v["requested"]]
    st.subheader("Contas MT5")
    st.caption("Solicitacao de novas entradas: " + (" + ".join(selected) if selected else "DESLIGADA"))
    cards = []
    for view in views:
        fields = [
            ("Conta configurada", view["expected_account"]), ("Servidor configurado", view["expected_server"]),
            ("Novas entradas solicitadas", "SIM" if view["requested"] else "NAO"),
            ("Estado observado", view["status"]),
            ("Conta confirmada na leitura recente", view["account"]),
            ("Ultimo ciclo registrado", view["updated"]),
            ("Conexao do terminal", "CONECTADA" if view["permissions"].get("connected") is True else "DESCONECTADA" if view["permissions"].get("connected") is False else "NAO CONFIRMADA"),
            ("Algotrading", "LIGADO" if view["permissions"].get("algotrading") is True else "DESLIGADO" if view["permissions"].get("algotrading") is False else "NAO CONFIRMADO"),
            ("Leitura das permissoes", view.get("terminal_updated", view["updated"]) if view["permissions"].get("algotrading") is not None else "N/D"),
        ]
        rows = "".join(f'<div><dt>{escape(label)}</dt><dd>{escape(str(value))}</dd></div>' for label, value in fields)
        message = view["message"]
        if not view["recent"]:
            message = "Estado atual nao confirmado. " + message
        cards.append(f'<section class="mt5-account-status"><h4>{view["environment"]}</h4><dl>{rows}</dl>'
                     f'<p>{escape(permissions_label(view["permissions"]))}</p><p>{escape(message)}</p></section>')
    st.markdown("""<style>
      .mt5-accounts-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,290px),1fr));gap:12px;}
      .mt5-account-status {border:1px solid #b7c1c8;border-radius:6px;padding:14px;min-width:0;}
      .mt5-account-status h4 {font-size:18px;margin:0 0 12px;letter-spacing:0;}
      .mt5-account-status dl {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:0;}
      .mt5-account-status dt {font-size:12px;font-weight:400;}
      .mt5-account-status dd {font-size:14px;font-weight:600;margin:3px 0 0;overflow-wrap:anywhere;}
      .mt5-account-status p {font-size:12px;margin:12px 0 0;overflow-wrap:anywhere;}
      </style><div class="mt5-accounts-grid">""" + "".join(cards) + "</div>", unsafe_allow_html=True)
    source_account = getattr(forex, "account", "N/D")
    source_server = getattr(forex, "server", "N/D")
    st.caption(f"Fonte da analise de mercado: conta {source_account} | {source_server} | TF {getattr(forex, 'timeframe', 'N/D')}. Ultima leitura: {_time_label(_market_stamp(forex))}.")
    if views[0]["status"] == "FONTE DE DADOS DIVERGENTE":
        st.error("A leitura de mercado nao corresponde a conta Demo configurada. Conexao de outra conta nao comprova execucao Demo.")


def render_mt5_account_controls() -> None:
    current = read_json(CONTROL)
    with st.form("mt5_additional_real_form"):
        enabled = st.checkbox(
            "Operar tambem na conta Real",
            value=current.get("enabled") is True, key="mt5_additional_real_enabled",
            help="Autoriza dinheiro real na conta 51517136, sem desligar a Demo. Desmarcar bloqueia novos envios; ordens pendentes existentes continuam vigentes e posicoes abertas seguem sob gestao.",
        )
        st.caption("Conta Real: 51517136 | PepperstoneBS-MT5-Live01")
        submitted = st.form_submit_button("Aplicar", type="primary")
    if submitted:
        try:
            set_real_enabled(enabled)
            ensure_real_worker()
            st.success("Configuracao Real salva. Demo permanece independente.")
        except (OSError, ValueError) as exc:
            st.error(f"Nao foi possivel concluir a ativacao Real: {exc}")
    view = real_status_view(read_json(CONTROL), read_json(STATUS))
    st.caption(f"Real: {view['status']} | {view['message']}")
    st.caption(permissions_label(view["permissions"]))
    st.caption(f"Ultima leitura Real: {view['updated']}")
