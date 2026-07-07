# Dynamic Exit Moving Average Demo Traceability

## Missao

`MISSION_TIA-020_AUTORIZAR_MOVING_AVERAGE_EXIT_DEMO`

## Arquivos criados

- `application/dynamic_exit_moving_average_authorizer.py`
- `tests/test_dynamic_exit_moving_average_authorizer.py`
- `docs/DYNAMIC_EXIT_MOVING_AVERAGE_DEMO_AUTHORIZATION.md`

## Fluxo

```text
DynamicExitMarketReading
  -> DynamicExitRecommendation
  -> DynamicExitMovingAverageAuthorizer
  -> DynamicExitDemoAuthorization
```

## Estado operacional

| Campo | Valor |
| --- | --- |
| Politica autorizavel | MOVING_AVERAGE_EXIT |
| Acao autorizavel | TIGHTEN_BY_MOMENTUM_LOSS |
| Execucao demo ligada | Nao |
| `allowed_to_execute_demo` | false |
| Provider Demo alterado | Nao |
| Posicao fechada | Nao |

## Rastreabilidade das regras

| Regra | Implementacao | Teste |
| --- | --- | --- |
| Exige perda de tendencia | filtro de estado | `test_rejeita_estado_sem_perda_de_tendencia` |
| Momentum deve estar contra | `_has_momentum_against` | `test_rejeita_momentum_ainda_favoravel` |
| Bloqueia perda deteriorada | `r_multiple >= -0.25` | `test_rejeita_perda_deteriorada` |
| Exige confianca minima | `confidence >= 0.55` | `test_rejeita_confianca_baixa` |
| Apenas Moving Average Exit | policy/action filtradas | `test_rejeita_politica_diferente_de_moving_average_exit` |
| Nao liberar execucao nesta fase | `allowed_to_execute_demo=false` | `test_marca_reversal_risk_elegivel_sem_liberar_execucao_demo` |
