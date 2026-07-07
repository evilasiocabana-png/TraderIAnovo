# EXECUTION_REPORT - MISSION_TIA-025_DIAGNOSTICO_LENTIDAO_E_RESET_FILAS_RUNTIME

## Data

2026-07-07T16:12:46-03:00

## Status

completed

## Objetivo

Adicionar diagnostico de lentidao e reset seguro de filas/caches temporarios do
runtime no dashboard, sem apagar dados persistentes e sem acionar MT5.

## Arquivos alterados

- `dashboard_app.py`
- `tests/test_dashboard_app_runtime.py`
- `governance/execution/EXECUTION_STATE.json`
- `governance/execution/NEXT_MISSION.md`
- `governance/execution/MISSION_INDEX.md`
- `governance/execution/EXECUTION_LOG.md`
- `codex/inbox/RESULTADO_DO_ULTIMO_INBOX.md`
- `docs/GPT_SYNC_STATUS.md`
- `codex/completed/LATEST_EXECUTION_REPORT.md`

## Arquitetura impactada

- UI Streamlit: novo expander `Diagnostico de performance / lentidao` em
  `Sistema Forex`.
- Runtime: helpers de snapshot leve, limpeza idempotente e medicao de render.
- Tests: cobertura de limpeza segura de estado temporario.

## Implementacao

- Snapshot leve sem leitura externa MT5.
- Botao `Limpar filas e caches temporarios do runtime`.
- Acao `Pausar ciclo automatico MT5 Forex` quando auto-cycle UI estiver ativo.
- Medicao simples de tempo por aba ativa.
- Limpeza restrita a `st.session_state` temporario e caches Streamlit.

## Guardrails

- Nenhum `order_send()` novo foi criado.
- Nenhum SL/TP foi movido.
- `.traderia` nao foi apagado.
- Historicos, banco local, parametros do Lab e configuracoes persistentes nao
  sao removidos pela limpeza.
- O diagnostico nao recalcula Lab nem dispara leitura MT5 pesada.

## Testes executados

```text
python -m unittest tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_runtime_cleanup_remove_apenas_estado_temporario
python -m py_compile dashboard_app.py
python -m unittest tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_workbench_renderiza_layout_profissional_sem_excecoes tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_sistema_forex_nao_exibe_dataset_legado tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_runtime_cleanup_remove_apenas_estado_temporario
python -m compileall dashboard_app.py application
python scripts\run_critical_ci.py
```

## Resultado dos testes

- Teste novo de limpeza segura: OK.
- `py_compile dashboard_app.py`: OK.
- `compileall dashboard_app.py application`: OK.
- AppTest selecionado: dois testes antigos falham por expectativa de `st.tabs`
  e navegacao antiga, nao por excecao do novo reset.
- Gate critico: falhou por pendencias estruturais ja conhecidas:
  - contrato congelado de servicos publicos em `application`;
  - contrato congelado de metodos de `DashboardService`;
  - `positions_get` em `dashboard_app.py`;
  - expectativa antiga `MA_RSI_FILTER` SELL versus resultado BUY.

## Criterios de aceite

- Botao de limpeza adicionado.
- Diagnostico de performance adicionado.
- Pausa de auto-cycle UI adicionada.
- Limpeza nao apaga persistencia.
- Limpeza nao aciona MT5 nem Lab.
- Limpeza e idempotente.
- Teste unitario de limpeza segura criado.

## Rollback

Reverter o commit desta missao remove controles de diagnostico/reset e o teste
novo sem afetar MT5, Provider Demo, `.traderia` ou parametros do Lab.

## Commit

7478a2c Execute MISSION_TIA-025 runtime performance diagnostics

## Branch

main

## Push

origin/main confirmado apos push.
