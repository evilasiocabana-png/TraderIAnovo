# TraderIA Novo - Matriz de Rastreabilidade

Matriz ponta a ponta para revisar melhorias no GitHub.

## Fluxo Alpha -> Relatorio

| Etapa | Artefato | Campo principal | Fonte |
| --- | --- | --- | --- |
| Alpha | `DashboardMT5ScenarioViewModel` | `alpha_id` | `application/dashboard_service.py` |
| Setup | `DashboardMT5ScenarioViewModel` | `model`, `parameters` | `_mt5_scenario_for_parameters()` |
| Entrada | candidato da Alpha | `decision`, `reason` | `_mt5_parameterized_candidate()` |
| Timeframe | row/scenario | `timeframe` | historico MT5 + Lab |
| Saida | parametros expandidos | `stop_management` | `_mt5_exit_management_variants()` |
| TradePlan | `MT5ResearchTradePlan` | `stop`, `target`, `risk_reward` | `research/mt5_research_trade_plan.py` |
| Forex | `DashboardMT5ForexSignalRowViewModel` | `lab_alpha_id`, `lab_timeframe`, `research_plan_*` | `DashboardService` |
| MT5 JSON | `signals[]` | `stop_management`, `lab_configuration` | `MT5VisualSignalExporter` |
| MT5 Indicador | MQL5 | visual entry/stop/target | `TraderIAVisualSignals.mq5` |
| Relatorio | `DashboardMT5TradeAuditViewModel` | auditoria local x MT5 | `get_mt5_trade_audit_report()` |

## Perguntas obrigatorias para qualquer melhoria

1. Qual Alpha ou setup muda?
2. Qual campo de entrada muda?
3. Qual campo de saida/stop muda?
4. Qual timeframe deve ser preservado?
5. Qual aba consome a mudanca?
6. O JSON MT5 muda?
7. O Relatorio precisa enxergar essa mudanca?
8. Qual teste prova que a cadeia nao quebrou?

## Anti-regressoes

| Risco | Como detectar |
| --- | --- |
| Tudo volta para M1 | validar `lab_timeframe` e ranking multi-TF |
| Stop vira fixo para todos | validar `stop_management` no Lab, TradePlan e JSON |
| Forex recalcula Lab pesado | revisar chamadas no ciclo leve |
| Grafico MT5 poluido | validar filtro `is_positioned`/visual |
| Relatorio decide setup | revisar dependencia do Relatorio |
| Runtime versionado | checar `.traderia`, logs e bancos fora do Git |

## Documentos relacionados

- `docs/SYSTEM_FLOW.md`
- `docs/APP_TABS_FLOW.md`
- `docs/ALPHA_TRACEABILITY.md`
- `docs/SETUP_LOGIC_TRACEABILITY.md`
- `docs/LAB_FOREX_MT5_CONTRACT.md`
- `docs/MT5_VISUAL_SIGNAL_CONTRACT.md`
- `docs/OPERATIONAL_GUARDRAILS.md`
