# Dynamic Exit Chandelier Demo Traceability

## Missao

`MISSION_TIA-016_AUTORIZAR_CHANDELIER_EXIT_DEMO`

## Arquivos criados

- `application/dynamic_exit_chandelier_authorizer.py`
- `tests/test_dynamic_exit_chandelier_authorizer.py`
- `docs/DYNAMIC_EXIT_CHANDELIER_DEMO_AUTHORIZATION.md`

## Fluxo

```text
DynamicExitMarketReading
  -> DynamicExitRecommendation
  -> DynamicExitChandelierAuthorizer
  -> DynamicExitDemoAuthorization
```

## Estado operacional

| Campo | Valor |
| --- | --- |
| Politica autorizavel | CHANDELIER_EXIT |
| Acao autorizavel | TRAIL_BY_STRUCTURE |
| Execucao demo ligada | Nao |
| `allowed_to_execute_demo` | false |
| Provider Demo alterado | Nao |
| SL/TP movido | Nao |

## Rastreabilidade das regras

| Regra | Implementacao | Teste |
| --- | --- | --- |
| Exige trend runner | estado `TREND_RUNNER` | `test_rejeita_estado_que_nao_e_trend_runner` |
| Exige ao menos 1R | `reading.r_multiple >= 1.0` | `test_rejeita_quando_r_menor_que_um` |
| Momentum nao pode estar contra | `_momentum_against` | `test_rejeita_momentum_contra_posicao` |
| Stop precisa melhorar protecao | `_improves_stop` | `test_rejeita_stop_candidato_que_piora_protecao` |
| Stop nao pode ficar do lado errado | `_stop_before_market` | `test_rejeita_stop_candidato_do_lado_errado_do_mercado` |
| Stop precisa respeitar distancia de Chandelier | `_respects_chandelier_distance` | `test_rejeita_stop_sem_distancia_minima_de_chandelier` |
| Apenas Chandelier | policy/action filtradas | `test_rejeita_politica_diferente_de_chandelier` |
| Nao liberar execucao nesta fase | `allowed_to_execute_demo=false` | `test_marca_trend_runner_elegivel_sem_liberar_execucao_demo` |
