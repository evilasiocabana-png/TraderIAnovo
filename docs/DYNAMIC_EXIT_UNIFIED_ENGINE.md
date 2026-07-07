# Dynamic Exit Unified Engine

## Status

Read-only.

## Objetivo

Unificar o fluxo da saida dinamica:

```text
TradePlan/Lab policy
-> DynamicExitMarketReading
-> DynamicExitMarketStateClassifier
-> DynamicExitRecommendationEngine
-> policy authorizer
-> DynamicExitEngineResult
```

## Contratos

- `DynamicExitEngineInput`
- `DynamicExitEngineResult`

## Regras

- uma entrada unica;
- uma recomendacao dinamica;
- uma pre-autorizacao auditavel;
- fallback seguro para politica sem autorizador;
- `allowed_to_execute_demo=false` sempre nesta fase.

## Politicas roteadas

- `ATR_TRAILING_STOP`
- `BREAK_EVEN`
- `CHANDELIER_EXIT`
- `DONCHIAN_CHANNEL_STOP`
- `MOVING_AVERAGE_EXIT`
- `PARABOLIC_SAR`
- `TIME_STOP`
- `VOLATILITY_STOP`

## Guardrails

- nao envia ordem;
- nao move SL/TP;
- nao altera Provider Demo;
- nao recalcula Lab pesado;
- nao decide pelo Relatorio;
- nao substitui a politica original do Lab.
