# EXECUTION_REPORT - MISSION_TIA-020_AUTORIZAR_MOVING_AVERAGE_EXIT_DEMO

## Data

2026-07-07T15:18:33-03:00

## Status

completed

## Objetivo

Criar pre-autorizacao segura para `MOVING_AVERAGE_EXIT` demo sem ligar
execucao operacional.

## Arquivos criados

- `application/dynamic_exit_moving_average_authorizer.py`
- `tests/test_dynamic_exit_moving_average_authorizer.py`
- `docs/DYNAMIC_EXIT_MOVING_AVERAGE_DEMO_AUTHORIZATION.md`
- `governance/traceability/DYNAMIC_EXIT_MOVING_AVERAGE_DEMO_TRACEABILITY.md`

## Arquivos alterados

- `governance/traceability/TRACEABILITY_INDEX.md`
- `governance/execution/EXECUTION_STATE.json`
- `governance/execution/NEXT_MISSION.md`
- `governance/execution/MISSION_INDEX.md`
- `governance/execution/EXECUTION_LOG.md`
- `codex/inbox/RESULTADO_DO_ULTIMO_INBOX.md`
- `docs/GPT_SYNC_STATUS.md`
- `codex/completed/LATEST_EXECUTION_REPORT.md`

## Arquitetura impactada

- Application: novo autorizador read-only para Moving Average Exit dinamico.
- Tests: cobertura de regras de elegibilidade e rejeicao.
- Governance: rastreabilidade e ponteiros para GPT/GitHub.

## Guardrails

- `allowed_to_execute_demo` permanece `false`.
- Nenhum `order_send()` novo foi criado.
- Provider Demo operacional nao foi alterado.
- Nenhuma posicao foi fechada por esta missao.
- Nenhuma politica alem de `MOVING_AVERAGE_EXIT` e elegivel nesta fase.

## Testes executados

```text
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_moving_average_authorizer.py
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_time_stop_authorizer.py
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_volatility_authorizer.py
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_donchian_authorizer.py
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_chandelier_authorizer.py
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_atr_trailing_authorizer.py
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_break_even_authorizer.py
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_recommendation_service.py
$env:PYTHONPATH=(Get-Location).Path; python -m unittest discover -s tests -p test_dynamic_exit_market_state_service.py
python -m py_compile application\dynamic_exit_moving_average_authorizer.py application\dynamic_exit_time_stop_authorizer.py application\dynamic_exit_volatility_authorizer.py application\dynamic_exit_donchian_authorizer.py application\dynamic_exit_chandelier_authorizer.py application\dynamic_exit_atr_trailing_authorizer.py application\dynamic_exit_break_even_authorizer.py domain\contracts\dynamic_exit_demo_authorization.py
python scripts\run_critical_ci.py
```

## Resultado dos testes

- Testes focados: 75 testes OK.
- Py compile: OK.
- Gate critico: falhou por pendencias estruturais fora do escopo:
  - contrato congelado de servicos publicos em `application`;
  - contrato congelado de metodos de `DashboardService`;
  - uso de `positions_get` em `dashboard_app.py`;
  - expectativa antiga `MA_RSI_FILTER` SELL versus resultado BUY;
  - expectativa antiga `TREND_MOMENTUM` WAIT versus resultado BUY.

## Criterios de aceite

- Pre-autorizador identifica Moving Average Exit elegivel.
- Casos perigosos sao rejeitados.
- Execucao demo permanece desligada.
- Provider Demo nao foi alterado.
- Rastreabilidade criada.

## Rollback

Reverter o commit desta missao remove autorizador, testes e documentacao sem
afetar provider, MT5 ou Dashboard.

## Commit

b7b5516

## Branch

main

## Push

origin/main confirmado apos push.
