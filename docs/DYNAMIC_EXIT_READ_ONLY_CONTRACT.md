# TraderIA Novo - Dynamic Exit Read-only Contract

Missao: `MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY`

Data: 2026-07-07

## Objetivo

Registrar o contrato implementado para transportar recomendacao de saida
dinamica sem autorizar gestao real de SL/TP no MT5 demo.

## Regra Central

Nesta fase:

```text
dynamic_exit_allowed_to_execute_demo = false
```

Sempre.

Nenhum comportamento operacional de entrada, ordem, stop loss ou take profit foi
alterado.

## Campos do Contrato

| Campo | Tipo esperado | Uso |
| --- | --- | --- |
| `dynamic_exit_policy` | string | Politica recomendada/base da saida dinamica. |
| `dynamic_exit_action` | string | Acao read-only sugerida. |
| `dynamic_exit_reason` | string | Justificativa auditavel. |
| `dynamic_exit_confidence` | float | Confianca informativa da recomendacao. |
| `dynamic_exit_market_state` | string | Estado de mercado/posicao observado. |
| `dynamic_exit_r_multiple` | float | Multiplo de R atual, reservado para fase futura. |
| `dynamic_exit_candidate_stop` | float/null | Stop candidato read-only. |
| `dynamic_exit_allowed_to_execute_demo` | bool | Sempre `false` nesta fase. |
| `dynamic_exit_source` | string | Origem da recomendacao. |

## Acoes Suportadas

```text
KEEP_ORIGINAL_PLAN
PROTECT_TO_BREAK_EVEN
TRAIL_BY_ATR
TRAIL_BY_STRUCTURE
TIGHTEN_BY_MOMENTUM_LOSS
TIME_DECAY_EXIT_WATCH
NO_ACTION_BAD_CONTEXT
```

## Estados Suportados

```text
NO_POSITION
NEW_POSITION
PROTECTED_POSITION
TREND_RUNNER
REVERSAL_RISK
TIME_DECAY
BAD_EXECUTION_CONTEXT
```

## Arquivos Implementados

- `domain/contracts/dynamic_exit.py`
- `domain/contracts/forex_signal.py`
- `domain/contracts/visual_signal.py`
- `domain/contracts/report_row.py`
- `domain/contracts/trade_audit.py`
- `application/dashboard_view_model.py`
- `application/dashboard_service.py`
- `application/forex_mt5_service.py`
- `application/mt5_visual_signal_exporter.py`
- `application/report_service.py`
- `application/mt5_trade_audit_service.py`

## Fluxo

```text
Lab/TradePlan
  -> DashboardMT5ForexSignalRowViewModel
  -> MT5VisualSignalExporter JSON
  -> ReportService / MT5TradeAuditService
```

## Garantias

- `stop_management` original continua preservado.
- Campos dinamicos sao opcionais e possuem defaults.
- Sinais antigos continuam compativeis.
- JSON visual inclui recomendacao read-only.
- Relatorio/auditoria consegue carregar a recomendacao.
- Provider demo nao passou a executar novas politicas.

## Testes

Testes focados executados:

```text
python -m unittest tests.test_lab_forex_mt5_contract tests.test_report_service tests.test_mt5_trade_audit_service tests.test_mt5_visual_signal_exporter
```

Resultado:

```text
Ran 9 tests - OK
```

## Proxima Etapa

`MISSION_TIA-007_EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_RELATORIO`

Objetivo sugerido: melhorar a exibicao do contrato read-only nas abas Forex e
Relatorio, sem executar SL/TP.
