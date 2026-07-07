# Dynamic Exit Backtest Read-Only

## Status

Implementado em modo read-only pela `MISSION_TIA-012`.

## Objetivo

Comparar a saida original do Lab contra a saida dinamica recomendada, sem
executar ordens e sem mover SL/TP.

## Motor

```text
application/dynamic_exit_backtest.py
```

O motor recebe uma lista de `DynamicExitBacktestTrade` e retorna um
`DynamicExitBacktestComparisonReport`.

## Metricas

O relatorio compara original e dinamico por:

- lucro liquido em R;
- drawdown maximo em R;
- win rate;
- profit factor;
- expectancy;
- duracao media;
- RR medio.

Tambem calcula:

- dominancia de break-even;
- ganho perdido por saida precoce;
- protecao contra perda;
- vencedor comparativo.

## Guardrails

- `read_only = true`.
- `execution_allowed = false`.
- Nenhuma ordem enviada.
- Nenhum SL/TP movido.
- Nenhum provider demo alterado.
- Nenhum ciclo leve Forex alterado.
- Politica original do Lab continua preservada.

## Arquivos Principais

```text
domain/contracts/dynamic_exit_backtest.py
application/dynamic_exit_backtest.py
tests/test_dynamic_exit_backtest.py
```

## Validacao

```text
python -m unittest tests.test_dynamic_exit_backtest tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service
python -m py_compile application/dynamic_exit_backtest.py domain/contracts/dynamic_exit_backtest.py
```
