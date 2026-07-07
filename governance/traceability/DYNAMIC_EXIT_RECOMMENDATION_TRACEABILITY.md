# Dynamic Exit Recommendation Traceability

## Missao

`MISSION_TIA-008_IMPLEMENTAR_DYNAMIC_EXIT_RECOMMENDATION_ENGINE`

## Fluxo

```text
DynamicExitMarketReading
↓
DynamicExitRecommendationEngine
↓
DynamicExitRecommendation
↓
Dashboard/Forex/MT5 Visual/Relatorio read-only
```

## Mapeamento

| Estado | Politica | Acao |
| --- | --- | --- |
| `NO_POSITION` | qualquer | `NO_ACTION_BAD_CONTEXT` |
| `BAD_EXECUTION_CONTEXT` | qualquer | `NO_ACTION_BAD_CONTEXT` |
| `NEW_POSITION` | qualquer | `KEEP_ORIGINAL_PLAN` |
| `PROTECTED_POSITION` | qualquer | `KEEP_ORIGINAL_PLAN` |
| `TREND_RUNNER` | `ATR_TRAILING_STOP` | `TRAIL_BY_ATR` |
| `TREND_RUNNER` | `DONCHIAN_CHANNEL_STOP`/`CHANDELIER_EXIT` | `TRAIL_BY_STRUCTURE` |
| `TREND_RUNNER` | `BREAK_EVEN` | `KEEP_ORIGINAL_PLAN` |
| `REVERSAL_RISK` | `BREAK_EVEN` | `PROTECT_TO_BREAK_EVEN` |
| `REVERSAL_RISK` | demais | `TIGHTEN_BY_MOMENTUM_LOSS` |
| `TIME_DECAY` | qualquer | `TIME_DECAY_EXIT_WATCH` |

## Garantia

Toda recomendacao e read-only:

```text
allowed_to_execute_demo = false
```

## Testes

```text
tests/test_dynamic_exit_recommendation_service.py
```
