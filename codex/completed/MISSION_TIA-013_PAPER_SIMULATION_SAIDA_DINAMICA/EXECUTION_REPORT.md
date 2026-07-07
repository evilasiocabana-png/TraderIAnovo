# EXECUTION_REPORT - MISSION_TIA-013_PAPER_SIMULATION_SAIDA_DINAMICA

## Data/Hora

2026-07-07T14:17:25-03:00

## Resultado

completed

## O Que Foi Executado

Foi criado um motor de simulacao paper read-only para saida dinamica.

O motor:

- registra cada recomendacao dinamica;
- normaliza qualquer entrada `executed=True` para `executed=False`;
- consolida a contagem de acoes recomendadas;
- compara resultado original observado versus resultado dinamico paper usando
  o backtest read-only da TIA-012;
- retorna `read_only=true` e `execution_allowed=false`.

## Arquivos Criados

- `domain/contracts/dynamic_exit_paper.py`
- `application/dynamic_exit_paper_simulation.py`
- `tests/test_dynamic_exit_paper_simulation.py`
- `docs/DYNAMIC_EXIT_PAPER_SIMULATION.md`
- `governance/traceability/DYNAMIC_EXIT_PAPER_SIMULATION_TRACEABILITY.md`
- `codex/completed/MISSION_TIA-013_PAPER_SIMULATION_SAIDA_DINAMICA/EXECUTION_REPORT.md`

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
python -m unittest tests.test_dynamic_exit_paper_simulation tests.test_dynamic_exit_backtest tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service
```

Resultado:

```text
Ran 23 tests in 0.003s - OK
```

Passou:

```text
python -m py_compile application/dynamic_exit_paper_simulation.py domain/contracts/dynamic_exit_paper.py application/dynamic_exit_backtest.py domain/contracts/dynamic_exit_backtest.py
```

Falhou parcialmente:

```text
python scripts/run_critical_ci.py
```

Resultado:

```text
Ran 88 tests in 135.543s - FAILED (failures=4)
```

Falhas observadas fora do escopo da TIA-013:

- contrato congelado de servicos publicos em `tests.test_application_api`;
- contrato congelado de metodos publicos do `DashboardService`;
- teste legado que proibe `positions_get` em `dashboard_app.py`;
- expectativa antiga do modelo `MA_RSI_FILTER`.

## Guardrails

- Nenhuma ordem enviada.
- Nenhum SL/TP movido.
- Nenhum provider demo alterado.
- Nenhum recalculo pesado de Lab adicionado.
- Simulacao paper nao executa recomendacao dinamica no Provider Demo.
- `execution_allowed` permanece `false`.

## Proxima Missao

`MISSION_TIA-014_AUTORIZAR_BREAK_EVEN_DINAMICO_DEMO`

## Commit

619526c

## Branch

main

## Push

origin/main
