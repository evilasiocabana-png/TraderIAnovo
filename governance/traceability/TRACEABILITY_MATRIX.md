# TraderIA Novo - Matriz de Rastreabilidade

`M24_CONTRACT=M24_SETUP_V3_20260819; SHA256=4caa2af5fb100fbf7631fbaf2655b0ab9006f4afbc55ebcf7543590d176eb60b`

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
| Contrato M24 | `Model24SetupContract` | versao e fingerprint | `application/model24_setup_contract.py` |
| Plano M24 | `stop_management_parameters` | `m24_setup_contract_version`, `m24_setup_contract_fingerprint` | `DashboardService` |
| Estado M24 | JSON local nao versionado | `setup_contract_version`, `setup_contract_fingerprint` | `model24_xau_basket.py` |
| Tela M24 | tabela de setup | campos derivados do contrato | `model24_public_setup_fields()` |
| CONTINUATION M24 | watch persistido + historico MT5 | TP da REENTRY, lado, RSI extremo, papel e volume 0,40 | `model24_xau_basket.py` + `MT5DemoExecutionProvider` |
| Contrato M25 | constantes + fingerprint | XAUUSD/M5, M8/M10/M18-M22, lotes e Full Exit | `model25_multi_asset_rsi50_basket.py` |
| Plano M25 | `stop_management_parameters` | fonte, versao/fingerprint, papel, entrada, SL e TP copiados | `DashboardService` |
| Ordem M25 | variante + comentario MT5 | `SOURCE_M<n>` e `TraderIA M25 S<n>` | `MT5DemoExecutionProvider` |
| Saida M25 | plano persistido + cesta | saida tecnica da fonte e Full Exit +US$1.000 | `PositionManagerService` + `Model25BasketManager` |

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
| Regra M24 diverge entre motor, tela e docs | validar fingerprint e `tests/test_model24_setup_contract.py` |
| M25 volta a operar outro simbolo ou setup proprio | validar fontes, copia literal e dupla rejeicao XAUUSD em `tests/test_model25_multi_asset_rsi50_basket.py` e provider |

## Documentos relacionados

- `docs/SYSTEM_FLOW.md`
- `docs/APP_TABS_FLOW.md`
- `docs/ALPHA_TRACEABILITY.md`
- `docs/SETUP_LOGIC_TRACEABILITY.md`
- `docs/LAB_FOREX_MT5_CONTRACT.md`
- `docs/MT5_VISUAL_SIGNAL_CONTRACT.md`
- `docs/OPERATIONAL_GUARDRAILS.md`
