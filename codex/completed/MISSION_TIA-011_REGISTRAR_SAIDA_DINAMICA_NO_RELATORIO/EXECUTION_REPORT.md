# EXECUTION_REPORT - MISSION_TIA-011_REGISTRAR_SAIDA_DINAMICA_NO_RELATORIO

## Data/Hora

2026-07-07T14:00:57-03:00

## Resultado

completed

## O Que Foi Executado

Foi adicionada auditoria read-only da saida dinamica na camada de Relatorio:

- contratos `ReportRow`, `TradeAuditRow` e `DashboardMT5TradeAuditRowViewModel`
  foram expandidos com campos dinamicos;
- `ReportService` passou a expor motivo, confianca, estado, R, stop candidato,
  acao executada e resultado observado;
- `MT5TradeAuditService` passou a registrar os mesmos campos por sinal Forex;
- `DashboardService` passou a transportar os campos do log local aceito para a
  auditoria MT5;
- `dashboard_app._mt5_trade_audit_row` passou a exibir os campos na tabela de
  Relatorio;
- todos os novos campos possuem defaults para compatibilidade.

## Arquivos Criados

- `docs/DYNAMIC_EXIT_REPORT_AUDIT.md`
- `governance/traceability/DYNAMIC_EXIT_REPORT_TRACEABILITY.md`
- `codex/completed/MISSION_TIA-011_REGISTRAR_SAIDA_DINAMICA_NO_RELATORIO/EXECUTION_REPORT.md`

## Arquivos Alterados

- `domain/contracts/report_row.py`
- `domain/contracts/trade_audit.py`
- `application/report_service.py`
- `application/mt5_trade_audit_service.py`
- `application/dashboard_service.py`
- `application/dashboard_view_model.py`
- `dashboard_app.py`
- `tests/test_report_service.py`
- `tests/test_mt5_trade_audit_service.py`
- `tests/test_dashboard_app_runtime.py`
- `tests/test_dashboard_view_model.py`
- arquivos de governanca, traceability e ponteiros GPT.

## Testes Executados

Passou:

```text
python -m unittest tests.test_report_service tests.test_mt5_trade_audit_service tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_auditoria_mt5_exibe_projecoes_do_app_ao_lado_do_realizado tests.test_dashboard_view_model.DashboardViewModelContractTest.test_relatorio_mt5_confere_log_local_com_historico_da_plataforma tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service
```

Resultado:

```text
Ran 21 tests in 2.979s - OK
```

Passou:

```text
python -m py_compile dashboard_app.py application/report_service.py application/mt5_trade_audit_service.py application/dashboard_service.py application/dashboard_view_model.py domain/contracts/report_row.py domain/contracts/trade_audit.py
```

Falhou parcialmente:

```text
python scripts/run_critical_ci.py
```

Resultado:

```text
Ran 88 tests in 141.638s - FAILED (failures=4)
```

Falhas observadas fora do escopo da TIA-011:

- contrato congelado de servicos publicos em `tests.test_application_api`;
- contrato congelado de metodos publicos do `DashboardService`;
- teste legado que proibe `positions_get` em `dashboard_app.py`;
- expectativa antiga do modelo `MA_RSI_FILTER`.

## Guardrails

- Nenhuma ordem enviada.
- Nenhum SL/TP movido.
- Nenhum provider demo alterado.
- Nenhum recalculo pesado de Lab adicionado.
- Relatorio permanece read-only e nao decide saida.

## Proxima Missao

`MISSION_TIA-012_BACKTEST_SAIDA_DINAMICA_READ_ONLY`

## Commit

PENDENTE

## Branch

main

## Push

origin/main
