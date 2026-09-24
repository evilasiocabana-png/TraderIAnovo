"""Read-only learning view. Trading never depends on this renderer."""

import json
import streamlit as st


@st.fragment(run_every="15s")
def render_learning_dashboard(service):
    st.subheader("Aprendizado")
    state = service.get_learning_dashboard()
    health = state["health"]
    st.write("Coletando dados" if health["running"] else "Coleta aguardando inicializacao")
    st.caption("Base atual: Replay, setups e filtros existentes. Melhorias avaliadas separadamente para o M30 Demo.")
    source = st.selectbox("Origem", ["Todas", *state["sources"]], key="learning_source")
    page = st.number_input("Pagina", min_value=1, value=1, step=1, key="learning_page")
    if source != "Todas" or page != 1:
        state = service.get_learning_dashboard(page=page-1, source="" if source == "Todas" else source)
    a, b, c = st.columns(3)
    a.metric("Sinais por origem", state["groups"])
    b.metric("Variantes observadas", state["total"])
    c.metric("Banco local (MiB)", f"{state['bytes']/1048576:.2f}")
    if health["dropped"] or health["errors"] or health["last_error"]:
        st.warning(f"Coleta com lacunas: {health['dropped']} descartes, {health['errors']} falhas. {health['last_error']}")
    st.caption("Cobertura: sinais efetivamente avaliados pelo aplicativo. Fontes nao avaliadas nao sao simuladas. "
               "Sem evidencia de encerramento, resultado e custos permanecem pendentes.")
    executions = {}
    for execution in state["executions"]:
        executions.setdefault(execution["signal_id"], []).append(execution)
    rows = []
    for row in state["rows"]:
        actual = executions.get(row["id"], [])
        from application.learning_observer import item_from_snapshot
        display_mode = item_from_snapshot(json.loads(row["snapshot"]), provenance=row["provenance"], stage="VIEW",
                                          executor=row["executor"], source=row["source"])["mode"]
        rows.append({"Observado": row["first_seen"], "Origem": row["source"], "Executor": row["executor"],
                     "Ativo": row["symbol"], "TF": row["timeframe"], "Direcao": row["direction"],
                     "Modo": display_mode, "Estado sinal": row["status"],
                     "Execucao": ", ".join(x["status"] for x in actual) or "SEM_EXECUCAO_CONFIRMADA",
                     "Liquido confirmado": sum(x["net"] for x in actual if x["net"] is not None)
                     if any(x["net"] is not None for x in actual) else None,
                     "Evidencia": row["provenance"], "Grupo": row["group_id"][:12],
                     "Motivo": row["reason"]})
    st.dataframe(rows, width="stretch", hide_index=True)
    if state["rows"]:
        selected = st.selectbox("Detalhe do sinal", range(len(state["rows"])),
                                format_func=lambda i: f"{state['rows'][i]['source']} | {state['rows'][i]['symbol']} | {state['rows'][i]['candle']}")
        detail = state["rows"][selected]
        with st.expander("Contexto inicial e referencia"):
            st.json({"baseline": detail["baseline"], "grupo": detail["group_id"],
                     "contexto": json.loads(detail["snapshot"])})
    st.subheader("Evidencia prospectiva")
    st.write("M30 Demo habilitado" if state["m30_enabled"] else "M30 Demo ainda nao habilitado")
    st.caption("Revisao automatica diaria; no maximo um novo candidato por semana. A coleta e a revisao "
               "dependem do aplicativo em execucao. Evidencia insuficiente mantem a base anterior.")
    for event in state["journal"][:10]:
        st.write(f"{event['created_at'][:16]} | {event['state']} | {event['message']}")
        with st.expander("Evidencia " + event["id"][:8]):
            st.json(json.loads(event["evidence"]))
    st.subheader("M30 e M23: entradas pareadas")
    st.dataframe([{k: r[k] for k in ("created_at", "original_ticket", "source", "symbol", "status", "clone_ticket", "filter_version", "reason")}
                  for r in state["pairs"]], hide_index=True, width="stretch")
    render_comparison(state)
    if rows:
        counts = {}
        for row in state["rows"]:
            key = row["first_seen"][:10]
            counts[key] = counts.get(key, 0) + 1
        st.bar_chart([{"Data": k, "Observacoes nesta pagina": v} for k, v in sorted(counts.items())],
                     x="Data", y="Observacoes nesta pagina")
    with st.expander("Persistencia e versoes"):
        st.code(health["path"])
        st.write(f"Fila: {health['queue']} / {health['queue_limit']}. Ultima gravacao: {health['last_write'] or 'pendente'}.")
        st.caption("SQLite separado do banco operacional; sem exclusao automatica. Nao armazena imagens ou ticks completos.")
        st.json(state["baselines"])


def render_comparison(state):
    if state.get("comparison"):
        st.line_chart(state["comparison"], x="Par", y=["M23 liquido", "M30 liquido"])
        st.caption("Pares encerrados e conciliados, ordenados pela entrada. Sinais filtrados no M30 contam zero execucao; "
                   "pares ainda abertos e resultados desconhecidos ficam fora.")
    else:
        st.info("Aguardando pares M23/M30 encerrados e conciliados para o grafico de resultados reais.")


def render_model30_panel(service, report=False):
    with st.expander("M30 | Aprendizado sobre a base M23", expanded=False):
        state = service.get_learning_dashboard(executor="M23")
        st.write("DEMO HABILITADA" if state["m30_enabled"] else "DEMO DESABILITADA")
        if not report:
            active = st.toggle("Executar M30 na mesma Demo do M23", value=state["m30_enabled"], key="m30_demo_enabled")
            if active != state["m30_enabled"]:
                service.set_model30_enabled(active)
                st.rerun()
        st.caption("Novas ordens pareadas apos aceite M23. A conta Real nao participa.")
        theoretical = []
        for row in state["rows"]:
            if row["executor"] != "M23":
                continue
            snap = json.loads(row["snapshot"])
            theoretical.append({"Origem": row["source"], "Ativo": row["symbol"], "Candle": row["candle"],
                "Direcao": row["direction"], "Entrada teorica": snap.get("entry_price"),
                "Stop planejado": snap.get("initial_stop"), "Alvo": snap.get("target"), "Estado M23": row["status"]})
        st.dataframe(theoretical, hide_index=True, width="stretch")
        if report:
            render_comparison(state)
        st.dataframe([{k: r[k] for k in ("created_at", "original_ticket", "clone_ticket", "status", "reason")}
                      for r in state["pairs"]], hide_index=True, width="stretch")
