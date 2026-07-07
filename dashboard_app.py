"""Streamlit app do TraderIA Nuvem."""

from application.dashboard_service import DashboardService


AUTO_REFRESH_SECONDS = 10


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="TraderIA Nuvem", layout="wide")
    st.title("TraderIA Nuvem")

    fragment = getattr(st, "fragment", None)

    def every_cycle(func):
        if callable(fragment):
            return fragment(run_every=AUTO_REFRESH_SECONDS)(func)
        return func

    def service() -> DashboardService:
        return DashboardService()

    with st.sidebar:
        st.caption("Origem: GitHub / TraderIAnovo")
        st.caption(f"Ciclo visual: {AUTO_REFRESH_SECONDS}s")
        if st.button("Atualizar agora", use_container_width=True):
            st.rerun()
        st.caption("MT5 em modo leitura. Nenhuma ordem e enviada por este app.")

    forex_tab, lab_tab, report_tab = st.tabs(["Forex MT5", "Lab", "Relatorio"])

    @every_cycle
    def render_forex_tab() -> None:
        data = service().get_dashboard_view_model()
        forex = data["forex_mt5"]
        visual = data["visual_export"]

        st.subheader("Forex MT5")
        st.caption("Leitura MT5 read-only, atualizada no ciclo operacional.")

        cols = st.columns(6)
        cols[0].metric("Status MT5", forex["status"])
        cols[1].metric("Servidor", forex["server"])
        cols[2].metric("Conta", forex["account"])
        cols[3].metric("Timeframe", forex["timeframe"])
        cols[4].metric("Pares", len(forex["signals"]))
        cols[5].metric("Visual MT5", visual["status"])

        if forex.get("connected"):
            st.success(forex.get("message", "MT5 online."))
        else:
            st.warning(forex.get("message", "MT5 offline."))

        signal_rows = _forex_rows(forex["signals"])
        st.dataframe(signal_rows, hide_index=True, width="stretch")

        with st.expander("Exportacao visual MT5"):
            st.write(visual["message"])
            st.code(str(visual["output_path"]))

    @every_cycle
    def render_lab_tab() -> None:
        data = service().get_dashboard_view_model()
        lab = data["lab"]
        forex = data["forex_mt5"]

        st.subheader("Lab")
        st.caption("Parametros que comandam o ciclo leve Forex MT5.")

        cols = st.columns(5)
        cols[0].metric("Setup", lab["setup"])
        cols[1].metric("Timeframe decisor", lab["timeframe"])
        cols[2].metric("Entrada teorica", lab["theoretical_entry"])
        cols[3].metric("Zona", lab["interest_zone"])
        cols[4].metric("Saida", lab["stop_management"])

        st.dataframe(
            [
                {
                    "Par": row["pair"],
                    "TF MT5": row["timeframe"],
                    "TF Lab": lab["timeframe"],
                    "Setup": lab["setup"],
                    "Entrada": lab["theoretical_entry"],
                    "Saida": lab["stop_management"],
                    "Posicionado": "SIM" if row.get("is_positioned") else "NAO",
                    "Motivo": row["reason"],
                }
                for row in forex["signals"]
            ],
            hide_index=True,
            width="stretch",
        )

        with st.expander("Parametros do Lab"):
            st.json(lab["parameters"])

    @every_cycle
    def render_report_tab() -> None:
        data = service().get_dashboard_view_model()
        report = data["report"]
        audit = report["audit"]
        summary = report["summary"]

        st.subheader("Relatorio")
        st.caption("Acompanhamento read-only de negociacao aberta e parametros do Lab.")

        cols = st.columns(6)
        cols[0].metric("Auditoria", audit["status"])
        cols[1].metric("Linhas", audit["total_rows"])
        cols[2].metric("Posicoes abertas", audit.get("total_open_positions", 0))
        cols[3].metric("Lucro aberto", f"{float(audit.get('open_profit', 0.0) or 0.0):.2f}")
        cols[4].metric("Entrada Lab", summary["lab_entry"])
        cols[5].metric("Saida Lab", summary["lab_stop_management"])

        st.info(audit["message"])
        st.dataframe(
            _audit_rows(audit["rows"]),
            hide_index=True,
            width="stretch",
        )

        with st.expander("Resumo tecnico"):
            st.json(summary)

    with forex_tab:
        render_forex_tab()

    with lab_tab:
        render_lab_tab()

    with report_tab:
        render_report_tab()


def _forex_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "Par": row["pair"],
            "Status": "POSICIONADO" if row.get("is_positioned") else "OK",
            "Decisao": row["decision"],
            "TF": row["timeframe"],
            "Preco": _price(row.get("price")),
            "Bid": _price(row.get("bid")),
            "Ask": _price(row.get("ask")),
            "Spread": _price(row.get("spread")),
            "Lado": row.get("position_side", "N/D"),
            "Volume": row.get("position_volume", 0.0),
            "Lucro": _money(row.get("position_profit")),
            "Atualizado": row.get("last_update", "N/D"),
            "Motivo": row["reason"],
        }
        for row in rows
    ]


def _audit_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        {
            "Par": row["symbol"],
            "Status": row["mt5_position_status"],
            "Lado": row.get("side", "N/D"),
            "Volume": row.get("volume", 0.0),
            "Entrada": _price(row.get("entry_price")),
            "Preco atual": _price(row.get("current_price")),
            "Lucro": _money(row.get("profit")),
            "Decisao Lab": row["lab_decision"],
            "Mensagem": row["message"],
        }
        for row in rows
    ]


def _price(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "N/D"
    if number <= 0.0:
        return "N/D"
    return f"{number:.5f}"


def _money(value: object) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


if __name__ == "__main__":
    main()
