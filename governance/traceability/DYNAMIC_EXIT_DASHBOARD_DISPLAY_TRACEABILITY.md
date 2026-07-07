# Dynamic Exit Dashboard Display Traceability

## Missao

`MISSION_TIA-009_EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_DASHBOARD`

## Fluxo

```text
Lab policy
↓
DynamicExitMarketReading
↓
DynamicExitRecommendation
↓
DashboardMT5ForexSignalRowViewModel
↓
dashboard_app._forex_signal_row
↓
Tabela Forex MT5
```

## Garantia

A tela somente exibe. Ela nao decide, nao executa e nao move stop.

## Campos de Auditoria

| Campo UI | Origem |
| --- | --- |
| `Politica Saida Lab` | `dynamic_exit_policy` |
| `Estado Mercado Saida` | `dynamic_exit_market_state` |
| `Recomendacao Saida` | `dynamic_exit_action` |
| `Motivo Saida Dinamica` | `dynamic_exit_reason` |
| `Confianca Saida Dinamica` | `dynamic_exit_confidence` |
| `R Atual Saida` | `dynamic_exit_r_multiple` |
| `Stop Candidato` | `dynamic_exit_candidate_stop` |
| `Execucao Saida Permitida` | `dynamic_exit_allowed_to_execute_demo` |
