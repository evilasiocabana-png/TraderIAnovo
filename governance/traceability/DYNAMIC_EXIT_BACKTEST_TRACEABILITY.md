# Dynamic Exit Backtest Traceability

## Missao

`MISSION_TIA-012_BACKTEST_SAIDA_DINAMICA_READ_ONLY`

## Fluxo

```text
Lab original exit
->
Dynamic exit recommendation
->
DynamicExitBacktestTrade
->
DynamicExitBacktestEngine
->
DynamicExitBacktestComparisonReport
->
Relatorio comparativo read-only
```

## Contrato

| Campo | Origem | Uso |
| --- | --- | --- |
| `original_policy` | Lab | politica base original |
| `dynamic_action` | DynamicExitRecommendation | recomendacao comparada |
| `original_result_r` | amostra/backtest | resultado da saida original |
| `dynamic_result_r` | amostra/backtest | resultado dinamico simulado |
| `planned_rr` | plano do Lab | RR medio |
| `read_only` | guardrail | sempre `true` |
| `execution_allowed` | guardrail | sempre `false` |

## Metricas de Decisao

O backtest nao decide execucao. Ele apenas mede se a saida dinamica teria:

- melhor lucro liquido;
- menor drawdown;
- melhor expectancy;
- menor perda;
- menor dominancia de break-even;
- menor perda de ganho por saida precoce.

## Guardrail

O motor nao importa MetaTrader5, nao chama provider demo, nao envia ordem e nao
move stop.
