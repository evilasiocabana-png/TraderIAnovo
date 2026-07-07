"""Streamlit app do TraderIA Nuvem."""

from application.dashboard_service import DashboardService


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="TraderIA Nuvem", layout="wide")
    st.title("TraderIA Nuvem")

    service = DashboardService()
    view_model = service.get_dashboard_view_model()

    with st.sidebar:
        st.caption("Origem: GitHub / TraderIAnovo")
        if st.button("Atualizar agora", use_container_width=True):
            st.rerun()
        st.caption("MT5 em modo leitura. Nenhuma ordem e enviada por este app.")

    forex_tab, lab_tab, report_tab = st.tabs(["Forex MT5", "Lab", "Relatório"])

    with forex_tab:
        forex = view_model["forex_mt5"]
        st.subheader("Forex MT5")
        st.caption("Leitura MT5 read-only com fallback limpo quando o terminal estiver offline.")

        cols = st.columns(5)
        cols[0].metric("Status MT5", forex["status"])
        cols[1].metric("Servidor", forex["server"])
        cols[2].metric("Conta", forex["account"])
        cols[3].metric("Timeframe", forex["timeframe"])
        cols[4].metric("Pares", len(forex["signals"]))

        if forex.get("connected"):
            st.success(forex.get("message", "MT5 online."))
        else:
            st.warning(forex.get("message", "MT5 offline."))

        st.dataframe(forex["signals"], hide_index=True, use_container_width=True)

        with st.expander("Payload visual MT5"):
            st.json(service.get_mt5_visual_signal_payload())

    with lab_tab:
        lab = view_model["lab"]
        st.subheader("Lab")
        st.caption("O Lab decide setup, timeframe, entrada teorica, zona e saida.")

        cols = st.columns(5)
        cols[0].metric("Setup", lab["setup"])
        cols[1].metric("Timeframe", lab["timeframe"])
        cols[2].metric("Entrada", lab["theoretical_entry"])
        cols[3].metric("Zona", lab["interest_zone"])
        cols[4].metric("Saida", lab["stop_management"])
        st.json(lab["parameters"])

    with report_tab:
        report = view_model["report"]
        audit = report["audit"]
        summary = report["summary"]

        st.subheader("Relatório")
        st.caption("Consolidação read-only de Forex MT5, Lab e posições abertas.")

        cols = st.columns(5)
        cols[0].metric("Auditoria", audit["status"])
        cols[1].metric("Linhas", audit["total_rows"])
        cols[2].metric("Posições abertas", audit.get("total_open_positions", 0))
        cols[3].metric("Lucro aberto", f"{float(audit.get('open_profit', 0.0) or 0.0):.2f}")
        cols[4].metric("Saida Lab", summary["lab_stop_management"])

        st.info(audit["message"])
        st.dataframe(audit["rows"], hide_index=True, use_container_width=True)

        with st.expander("Resumo técnico"):
            st.json(summary)


if __name__ == "__main__":
    main()
