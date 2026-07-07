# Dynamic Exit Donchian Demo Traceability

## Missao

`MISSION_TIA-017_AUTORIZAR_DONCHIAN_CHANNEL_STOP_DEMO`

## Arquivos criados

- `application/dynamic_exit_donchian_authorizer.py`
- `tests/test_dynamic_exit_donchian_authorizer.py`
- `docs/DYNAMIC_EXIT_DONCHIAN_DEMO_AUTHORIZATION.md`

## Fluxo

```text
DynamicExitMarketReading
  -> DynamicExitRecommendation
  -> DynamicExitDonchianAuthorizer
  -> DynamicExitDemoAuthorization
```

## Estado operacional

| Campo | Valor |
| --- | --- |
| Politica autorizavel | DONCHIAN_CHANNEL_STOP |
| Acao autorizavel | TRAIL_BY_STRUCTURE |
| Execucao demo ligada | Nao |
| `allowed_to_execute_demo` | false |
| Provider Demo alterado | Nao |
| SL/TP movido | Nao |

## Rastreabilidade das regras

| Regra | Implementacao | Teste |
| --- | --- | --- |
| Exige tendencia ou protecao | estados `TREND_RUNNER`/`PROTECTED_POSITION` | `test_rejeita_estado_sem_tendencia_ou_protecao` |
| Exige ao menos 0.75R | `reading.r_multiple >= 0.75` | `test_rejeita_quando_r_menor_que_minimo` |
| Momentum nao pode estar contra | `_momentum_against` | `test_rejeita_momentum_contra_posicao` |
| Stop precisa melhorar protecao | `_improves_stop` | `test_rejeita_stop_candidato_que_piora_protecao` |
| Stop nao pode ficar do lado errado | `_stop_before_market` | `test_rejeita_stop_candidato_do_lado_errado_do_mercado` |
| Volatilidade deve ser valida | `volatility > 0` quando presente | `test_rejeita_volatilidade_invalida` |
| Apenas Donchian | policy/action filtradas | `test_rejeita_politica_diferente_de_donchian` |
| Nao liberar execucao nesta fase | `allowed_to_execute_demo=false` | `test_marca_trend_runner_elegivel_sem_liberar_execucao_demo` |
