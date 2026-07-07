# Dynamic Exit Report Traceability

## Missao

`MISSION_TIA-011_REGISTRAR_SAIDA_DINAMICA_NO_RELATORIO`

## Fluxo

```text
Lab policy
->
DynamicExitRecommendation
->
Forex signal / local execution record
->
MT5TradeAuditService / DashboardService
->
DashboardMT5TradeAuditRowViewModel
->
dashboard_app._mt5_trade_audit_row
->
Aba Relatorio
```

## Contrato

| Campo | Origem | Uso no Relatorio |
| --- | --- | --- |
| `dynamic_exit_policy` | politica base do Lab | politica original |
| `dynamic_exit_action` | recomendacao dinamica | recomendacao observada |
| `dynamic_exit_reason` | motor dinamico | motivo auditavel |
| `dynamic_exit_confidence` | motor dinamico | confianca auditavel |
| `dynamic_exit_market_state` | leitura de mercado | contexto atual |
| `dynamic_exit_r_multiple` | leitura de posicao | R atual |
| `dynamic_exit_candidate_stop` | motor dinamico | stop candidato |
| `dynamic_exit_executed_action` | execucao observada | acao executada ou `NONE` |
| `dynamic_exit_final_result` | auditoria MT5 | resultado final observado |
| `dynamic_exit_allowed_to_execute_demo` | guardrail | sempre falso nesta fase |

## Guardrail

O Relatorio nao decide. Ele apenas apresenta a trilha que veio do Lab, Runtime,
Forex e MT5.
