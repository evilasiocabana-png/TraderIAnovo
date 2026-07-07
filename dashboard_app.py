"""Streamlit app inicial do traderiaianovo."""

from application.dashboard_service import DashboardService


def main() -> None:
    import streamlit as st

    service = DashboardService()
    view_model = service.get_dashboard_view_model()

    st.set_page_config(page_title="traderiaianovo", layout="wide")
    st.title("traderiaianovo")

    forex_tab, lab_tab, report_tab = st.tabs(["Forex MT5", "Lab", "Relatório"])

    with forex_tab:
        forex = view_model["forex_mt5"]
        st.subheader("Forex MT5")
        st.caption("Leitura MT5 read-only. Nenhuma ordem real e enviada.")
        cols = st.columns(4)
        cols[0].metric("Status MT5", forex["status"])
        cols[1].metric("Servidor", forex["server"])
        cols[2].metric("Conta", forex["account"])
        cols[3].metric("Timeframe", forex["timeframe"])
        st.dataframe(forex["signals"], hide_index=True, use_container_width=True)

    with lab_tab:
        lab = view_model["lab"]
        st.subheader("Lab")
        st.caption("O Lab decide parametros teoricos para o ciclo Forex MT5.")
        st.json(lab)

    with report_tab:
        report = view_model["report"]
        st.subheader("Relatorio")
        st.caption("Consolidacao read-only de Forex MT5 e Lab.")
        st.dataframe(report["rows"], hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
