# Dynamic Exit Time Stop Demo Traceability

## Missao

`MISSION_TIA-019_AUTORIZAR_TIME_STOP_DEMO`

## Arquivos criados

- `application/dynamic_exit_time_stop_authorizer.py`
- `tests/test_dynamic_exit_time_stop_authorizer.py`
- `docs/DYNAMIC_EXIT_TIME_STOP_DEMO_AUTHORIZATION.md`

## Fluxo

```text
DynamicExitMarketReading
  -> DynamicExitRecommendation
  -> DynamicExitTimeStopAuthorizer
  -> DynamicExitDemoAuthorization
```

## Estado operacional

| Campo | Valor |
| --- | --- |
| Politica autorizavel | TIME_STOP |
| Acao autorizavel | TIME_DECAY_EXIT_WATCH |
| Execucao demo ligada | Nao |
| `allowed_to_execute_demo` | false |
| Provider Demo alterado | Nao |
| Posicao fechada | Nao |

## Rastreabilidade das regras

| Regra | Implementacao | Teste |
| --- | --- | --- |
| Exige TIME_DECAY | filtro de estado | `test_rejeita_estado_diferente_de_time_decay` |
| Exige tempo minimo | `minutes >= 240` | `test_rejeita_tempo_insuficiente` |
| Exige baixo progresso em R | `abs(r_multiple) <= 0.25` | `test_rejeita_operacao_com_progresso_relevante` |
| Momentum nao pode favorecer permanencia | `_has_favorable_momentum` | `test_rejeita_momentum_favoravel` |
| Exige confianca minima | `confidence >= 0.45` | `test_rejeita_confianca_baixa` |
| Apenas Time Stop | policy/action filtradas | `test_rejeita_politica_diferente_de_time_stop` |
| Nao liberar execucao nesta fase | `allowed_to_execute_demo=false` | `test_marca_time_decay_elegivel_sem_liberar_execucao_demo` |
