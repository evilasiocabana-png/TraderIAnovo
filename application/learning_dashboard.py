"""Read-only learning view. Trading never depends on this renderer."""

import json
import streamlit as st
from application.model_ui_state import M30_DESCRIPTION, m30_permission_text, sync_persisted_widget


@st.fragment(run_every="15s")
def render_learning_dashboard(service):
    st.subheader("Aprendizado")
    state = service.get_learning_dashboard()
    render_learning_summary(state)
    st.info(M30_DESCRIPTION)
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
    st.write(m30_permission_text(state["m30_enabled"]))
    st.caption("Revisao automatica diaria; no maximo um novo candidato por semana. A coleta e a revisao "
               "dependem do aplicativo em execucao. Evidencia insuficiente mantem a base anterior.")
    for event in state["journal"][:10]:
        st.write(f"{event['created_at'][:16]} | {event['state']} | {event['message']}")
        with st.expander("Evidencia " + event["id"][:8]):
            st.json(json.loads(event["evidence"]))
    st.subheader("M30 e M23: historico legado de entradas pareadas")
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
    if "comparison_groups" in state:
        st.caption("Cada grafico separa modelo de origem, setup, ativo e conta. M23 e M30 sao os executores comparados, nao a origem do aprendizado.")
        groups = state["comparison_groups"]
        if not groups:
            st.info("Aguardando pares M23/M30 identificados por origem.")
        for source, rows in groups.items():
            st.subheader(source)
            candidate = dict(state.get("candidate_comparison", {}).get("scoped", {}).get(source, {"state": "NONE", "rows": []}))
            learned = candidate
            candidate = state.get('manual_candidates', {}).get(source, candidate)
            render_single_comparison({"comparison": rows, "candidate_comparison": candidate})
            if candidate.get('manual') and learned.get('version'):
                with st.expander('Candidato estatistico independente - ' + learned['version'][:12]):
                    render_single_comparison({'comparison': rows, 'candidate_comparison': learned})
        return
    render_single_comparison(state)


def render_single_comparison(state):
    candidate = state.get("candidate_comparison", {"state": "NONE", "rows": []})
    if candidate["state"] == "NONE":
        st.info("Nenhum candidato em teste")
    elif candidate["state"] == "BASE_CHANGED":
        st.info("Candidato de outra base: aguardando revisao. Curva nao exibida.")
    else:
        st.caption(f"Candidato em teste: {candidate['version']} | Inicio: {candidate['start']}")
        if candidate.get('manual'):
            st.caption('Hipotese manual de canais do resultado acumulado liquido M23 desta origem. Somente simulacao; nao altera ordens nem participa da promocao automatica.')
            st.caption('Estado: ' + candidate.get('pending', ''))
        if not candidate["rows"]:
            st.info("Aguardando resultados prospectivos pareados do candidato")
        else:
            import altair as alt
            import pandas as pd
            data = pd.DataFrame(candidate["rows"]).melt("Par", var_name="Serie", value_name="Liquido")
            chart = alt.Chart(data).mark_line(point=True).encode(
                x=alt.X("Par:Q", title="Par prospectivo"),
                y=alt.Y("Liquido:Q", title="Resultado liquido acumulado"),
                color=alt.Color("Serie:N", scale=alt.Scale(
                    domain=["M23", "M30", "Candidato em teste"],
                    range=["#2563eb", "#16a34a", "#dc2626"]), title="Serie"),
                tooltip=["Par:Q", "Serie:N", "Liquido:Q"],
            )
            st.altair_chart(chart, width="stretch")
            if candidate.get('manual'):
                st.caption('Simulacao causal NORMAL/ESPELHADO por ticks bid/ask, RR 1:1 e mesmo lote. Custos espelhados estimados pelas comissoes/taxas nativas da referencia; swap sem evidencia permanece pendente. Janela comum, sem pular operacoes nao resolvidas; nao e lucro executado.')
                return
            st.caption("Candidato: simulacao do filtro congelado sobre oportunidades M23 registradas apos o inicio do teste. "
                       "Usa resultado liquido conciliado, incluindo custos; operacoes descartadas contam zero. "
                       "As tres curvas usam os mesmos pares e comecam em zero nesta janela. "
                       "Nao simula novos preenchimentos nem mudancas de sequencia causadas pelo filtro.")
            return
    if state.get("comparison"):
        chart = st.scatter_chart if len(state["comparison"]) == 1 else st.line_chart
        chart(state["comparison"], x="Par", y=["M23 liquido", "M30 liquido"])
        st.caption("Historico legado de copias: pares encerrados e conciliados, ordenados pela entrada. Sinais filtrados no M30 contam zero execucao; "
                   "pares ainda abertos e resultados desconhecidos ficam fora.")
    else:
        st.info("Aguardando pares M23/M30 encerrados e conciliados para o grafico de resultados reais.")


def model30_theoretical_rows(state):
    """Show recorded clone contracts, never infer a new order from M23 history."""
    rows = []
    seen = set()
    for pair in sorted([*state.get("independent", []), *state.get("pairs", [])], key=lambda p: p["created_at"], reverse=True):
        try:
            snap = json.loads(pair.get("snapshot") or "{}")
        except (ValueError, TypeError):
            continue
        if not isinstance(snap, dict):
            continue
        params = snap.get("stop_management_parameters") or {}
        source = params.get("m23_m29_origin_source") or params.get("source_operational_model") or pair.get("source")
        route = (source, pair.get("symbol"), snap.get("entry_setup"))
        if route in seen:
            continue
        seen.add(route)
        rows.append({
            "Modelo ativo": "M30", "Fonte": source or "N/D",
            "Politica": "Independente" if params.get("m30_policy") else "Copia anterior",
            "Modo": params.get("m30_mode", "Legado"),
            "Par": pair.get("symbol"), "Registro": pair["created_at"],
            "Direcao": snap.get("direction"), "Entrada teorica": snap.get("entry_price"),
            "Stop": snap.get("initial_stop"), "Alvo": snap.get("target"),
            "Lote": params.get("m30_execution_volume"),
            "Status": pair.get("status"), "Filtro": pair.get("filter_version"),
            "Motivo": pair.get("reason"),
        })
    return rows


def render_model30_theoretical(service, table_renderer=None):
    st.subheader("Entrada Teorica MT5 - Modelo 30")
    state = service.get_learning_dashboard(executor="M23")
    st.caption("Ultimo plano M30 registrado por origem, ativo e setup. Aceite nao confirma preenchimento; "
               "estes registros nao indicam uma nova entrada liberada agora.")
    rows = model30_theoretical_rows(state)
    if not rows:
        st.info("M30 sem plano registrado. Aguardando sinais originais das fontes habilitadas.")
    elif table_renderer:
        table_renderer(rows, model_column="Modelo ativo", decision_column="Direcao", color_status_cells=True)
    else:
        st.dataframe(rows, hide_index=True, width="stretch")


def render_model30_panel(service, report=False):
    with st.expander("M30 | Aprendizado sobre a base M23", expanded=False):
        state = service.get_learning_dashboard(executor="M23")
        st.write(m30_permission_text(state["m30_enabled"]))
        if not report:
            sync_persisted_widget(st.session_state, "m30_demo_enabled", state["m30_enabled"])
            active = st.toggle("Executar M30 na mesma Demo do M23", key="m30_demo_enabled")
            if active != state["m30_enabled"]:
                service.set_model30_enabled(active)
                st.rerun()
        st.caption(M30_DESCRIPTION + " A conta Real nao participa.")
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


def render_learning_summary(state):
    st.subheader("Como está o aprendizado")
    if state.get('manual_candidates'):
        st.write(f"Hipoteses manuais de canais: {len(state['manual_candidates'])}. Separadas dos candidatos estatisticos; somente teste teorico prospectivo.")
    summary = state.get("summary")
    if not summary or not summary.get("available"):
        st.info("Resumo dos filtros indisponível nesta leitura. Isso não significa que existam zero filtros.")
        return
    columns = st.columns(4)
    columns[0].metric("Candidatos criados", summary["candidates"])
    columns[1].metric("Em teste", summary["testing"])
    columns[2].metric("Filtros aplicados agora", summary["applied"])
    columns[3].metric("Rejeitados ou revertidos", summary["rejected"] + summary["reverted"])
    if summary["applied"]:
        stage = "Filtro aplicado — acompanhando os resultados no M30 Demo."
    elif summary["testing"]:
        stage = "Candidato em teste — aguardando novos resultados para validar."
    else:
        stage = "Coleta e análise — nenhum filtro novo aplicado nesta base."
    st.info(stage)
    st.caption("Candidatos criados é o total histórico; em teste e aplicados mostram o estado atual. "
               "Um candidato em teste ainda não altera entradas. O M23 continua como referência.")
    st.write(m30_permission_text(state.get("m30_enabled", False)))
    latest = summary.get("latest")
    if latest:
        st.write("Última atualização: " + latest["message"])
        from datetime import datetime
        from zoneinfo import ZoneInfo
        timestamp = datetime.fromisoformat(latest["created_at"]).astimezone(ZoneInfo("America/Sao_Paulo"))
        st.caption("Registro em " + timestamp.strftime("%d/%m/%Y às %H:%M") + " (Brasília)")
    with st.expander("O que falta para avançar?"):
        from application.learning_policy import POLICY
        st.write(f"Para procurar um candidato: pelo menos {POLICY['discovery_groups'] + POLICY['calibration_groups']} grupos elegíveis e {POLICY['training_days']} dias distintos.")
        st.write(f"Depois, o candidato precisa de resultados futuros: pelo menos {POLICY['future_groups']} grupos, {POLICY['context_groups']} no contexto e {POLICY['future_days']} dias, além dos critérios estatísticos.")
        st.caption("Não é um prazo prometido. Sinais coletados não equivalem a operações encerradas e elegíveis. Os gráficos abaixo comparam resultados; não são filtros aplicados.")
