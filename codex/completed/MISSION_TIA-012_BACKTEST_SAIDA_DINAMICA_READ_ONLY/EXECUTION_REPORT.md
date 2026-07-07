# EXECUTION_REPORT - MISSION_TIA-012_BACKTEST_SAIDA_DINAMICA_READ_ONLY

## Data/Hora

2026-07-07T14:09:55-03:00

## Resultado

completed

## O Que Foi Executado

Foi criado um motor read-only para comparar a saida original do Lab contra a
saida dinamica recomendada.

O motor calcula:

- lucro liquido;
- drawdown;
- win rate;
- profit factor;
- expectancy;
- duracao media;
- RR medio;
- dominancia de break-even;
- ganho perdido por saida precoce;
- protecao contra perda;
- vencedor comparativo.

## Arquivos Criados

- `domain/contracts/dynamic_exit_backtest.py`
- `application/dynamic_exit_backtest.py`
- `tests/test_dynamic_exit_backtest.py`
- `docs/DYNAMIC_EXIT_BACKTEST_READ_ONLY.md`
- `governance/traceability/DYNAMIC_EXIT_BACKTEST_TRACEABILITY.md`
- `codex/completed/MISSION_TIA-012_BACKTEST_SAIDA_DINAMICA_READ_ONLY/EXECUTION_REPORT.md`

## Arquivos Alterados

- `governance/traceability/TRACEABILITY_INDEX.md`
- `governance/execution/NEXT_MISSION.md`
- `governance/execution/MISSION_INDEX.md`
- `governance/execution/EXECUTION_STATE.json`
- `governance/execution/EXECUTION_LOG.md`
- ponteiros de ultimo inbox/GPT.

## Testes Executados

Passou:

```text
python -m unittest tests.test_dynamic_exit_backtest tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service
```

Resultado:

```text
Ran 19 tests in 0.006s - OK
```

Passou:

```text
python -m py_compile application/dynamic_exit_backtest.py domain/contracts/dynamic_exit_backtest.py
```

Falhou parcialmente:

```text
python scripts/run_critical_ci.py
```

Resultado:

```text
Ran 88 tests in 96.871s - FAILED (failures=4)
```

Falhas observadas fora do escopo da TIA-012:

- contrato congelado de servicos publicos em `tests.test_application_api`;
- contrato congelado de metodos publicos do `DashboardService`;
- teste legado que proibe `positions_get` em `dashboard_app.py`;
- expectativa antiga do modelo `MA_RSI_FILTER`.

## Guardrails

- Nenhuma ordem enviada.
- Nenhum SL/TP movido.
- Nenhum provider demo alterado.
- Nenhum recalculo pesado de Lab adicionado.
- Backtest permanece read-only.
- `execution_allowed` permanece `false`.

## Proxima Missao

`MISSION_TIA-013_PAPER_SIMULATION_SAIDA_DINAMICA`

## Commit

PENDENTE

## Branch

main

## Push

origin/main
