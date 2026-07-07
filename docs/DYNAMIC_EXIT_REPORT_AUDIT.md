# Dynamic Exit Report Audit

## Status

Implementado em modo read-only pela `MISSION_TIA-011`.

## Objetivo

Registrar na aba Relatorio a trilha da saida dinamica sem transformar o
Relatorio em fonte de decisao.

## Campos Registrados

- politica original do Lab;
- recomendacao dinamica;
- motivo da recomendacao;
- confianca da recomendacao;
- estado atual de mercado;
- R atual;
- stop candidato;
- acao de saida executada;
- resultado final observado;
- execucao de saida permitida.

## Regra Operacional

O Relatorio apenas observa e compara. Ele nao decide saida, nao envia ordem e
nao move SL/TP.

## Arquivos Principais

```text
domain/contracts/report_row.py
domain/contracts/trade_audit.py
application/report_service.py
application/mt5_trade_audit_service.py
application/dashboard_service.py
dashboard_app.py
```

## Compatibilidade

Todos os novos campos possuem defaults. Registros antigos continuam carregando
com `N/D`, `0.0`, `NONE` ou `NO_POSITION`.

## Validacao

```text
python -m unittest tests.test_report_service tests.test_mt5_trade_audit_service tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_auditoria_mt5_exibe_projecoes_do_app_ao_lado_do_realizado tests.test_dashboard_view_model.DashboardViewModelContractTest.test_relatorio_mt5_confere_log_local_com_historico_da_plataforma tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service
python -m py_compile dashboard_app.py application/report_service.py application/mt5_trade_audit_service.py application/dashboard_service.py application/dashboard_view_model.py domain/contracts/report_row.py domain/contracts/trade_audit.py
```
