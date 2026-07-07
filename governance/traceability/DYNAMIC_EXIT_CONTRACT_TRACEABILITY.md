# Dynamic Exit Contract Traceability

Missao: `MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY`

Data: 2026-07-07

## Cadeia Implementada

```text
Research plan / Lab parameters
  -> DashboardMT5ForexSignalRowViewModel.dynamic_exit_*
  -> MT5 visual JSON dynamic_exit_*
  -> ReportRow / TradeAuditRow dynamic_exit_*
  -> auditoria read-only
```

## Campos

| Campo | Lab/TradePlan | Forex | MT5 JSON | Relatorio |
| --- | --- | --- | --- | --- |
| `dynamic_exit_policy` | derivado da politica base | sim | sim | sim |
| `dynamic_exit_action` | derivado read-only | sim | sim | sim |
| `dynamic_exit_reason` | justificativa | sim | sim | auditoria |
| `dynamic_exit_confidence` | informativo | sim | sim | futuro |
| `dynamic_exit_market_state` | leitura leve | sim | sim | futuro |
| `dynamic_exit_r_multiple` | reservado | sim | sim | futuro |
| `dynamic_exit_candidate_stop` | candidato read-only | sim | sim | futuro |
| `dynamic_exit_allowed_to_execute_demo` | sempre false | sim | sim | sim |
| `dynamic_exit_source` | origem | sim | sim | futuro |

## Fonte por Camada

| Camada | Arquivo | Responsabilidade |
| --- | --- | --- |
| Contrato | `domain/contracts/dynamic_exit.py` | Define recomendacao read-only. |
| Forex row | `application/dashboard_view_model.py` | Carrega campos para UI/exportacao. |
| Builder | `application/dashboard_service.py` | Calcula recomendacao read-only minima. |
| JSON MT5 | `application/mt5_visual_signal_exporter.py` | Exporta campos opcionais. |
| Relatorio simples | `application/report_service.py` | Inclui campos no resumo. |
| Auditoria | `application/mt5_trade_audit_service.py` | Preserva campos por sinal. |

## Nao Implementado Nesta Missao

- Execucao real de novas politicas.
- Alteracao no provider demo MT5.
- Alteracao em MQL5.
- Recalculo pesado de Lab no ciclo leve.
- Mudanca de entrada, stop ou alvo operacional.

## Anti-regressao

- `dynamic_exit_allowed_to_execute_demo` deve permanecer `false`.
- `stop_management` original nao pode ser substituido.
- Falta de campos dinamicos nao pode quebrar payloads antigos.
- Relatorio audita; nao decide saida.

## Proxima Missao

`MISSION_TIA-007_EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_RELATORIO`
