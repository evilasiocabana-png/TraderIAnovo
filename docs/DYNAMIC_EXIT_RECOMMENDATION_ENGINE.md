# Dynamic Exit Recommendation Engine

## Status

Implementado em modo read-only pela `MISSION_TIA-008`.

## Objetivo

Transformar a leitura de estado de mercado da TIA-007 em uma recomendacao
auditavel de saida dinamica.

## Entrada

```text
DynamicExitMarketReading
policy
plan_status
```

## Saida

```text
DynamicExitRecommendation
```

Campos garantidos:

- `policy`
- `action`
- `reason`
- `confidence`
- `market_state`
- `r_multiple`
- `candidate_stop`
- `allowed_to_execute_demo`
- `source`

## Acoes

```text
KEEP_ORIGINAL_PLAN
PROTECT_TO_BREAK_EVEN
TRAIL_BY_ATR
TRAIL_BY_STRUCTURE
TIGHTEN_BY_MOMENTUM_LOSS
TIME_DECAY_EXIT_WATCH
NO_ACTION_BAD_CONTEXT
```

## Guardrail Principal

```text
allowed_to_execute_demo = false
```

O motor recomenda, mas nao executa. Ele nao move SL/TP, nao envia ordem e nao
altera provider demo.

## Arquivo Principal

```text
application/dynamic_exit_recommendation_service.py
```

## Integracao Atual

O `DashboardService` passou a delegar a recomendacao para o
`DynamicExitRecommendationEngine`, mantendo o classificador de estado de mercado
da TIA-007 como fonte da leitura.

## Limitacao Atual

A recomendacao ainda e exibida/transportada nos campos existentes. A proxima
camada deve melhorar a exibicao no Forex/Dashboard sem alterar comportamento
operacional.
