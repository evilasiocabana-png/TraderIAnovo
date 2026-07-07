# Dynamic Exit Volatility Demo Traceability

## Missao

`MISSION_TIA-018_AUTORIZAR_VOLATILITY_STOP_DEMO`

## Arquivos criados

- `application/dynamic_exit_volatility_authorizer.py`
- `tests/test_dynamic_exit_volatility_authorizer.py`
- `docs/DYNAMIC_EXIT_VOLATILITY_DEMO_AUTHORIZATION.md`

## Fluxo

```text
DynamicExitMarketReading
  -> DynamicExitRecommendation
  -> DynamicExitVolatilityAuthorizer
  -> DynamicExitDemoAuthorization
```

## Estado operacional

| Campo | Valor |
| --- | --- |
| Politica autorizavel | VOLATILITY_STOP |
| Acao autorizavel | TRAIL_BY_ATR |
| Execucao demo ligada | Nao |
| `allowed_to_execute_demo` | false |
| Provider Demo alterado | Nao |
| SL/TP movido | Nao |

## Rastreabilidade das regras

| Regra | Implementacao | Teste |
| --- | --- | --- |
| Estado inseguro rejeitado | filtro de estados | `test_rejeita_estado_inseguro` |
| Exige ao menos 0.50R | `reading.r_multiple >= 0.50` | `test_rejeita_quando_r_menor_que_minimo` |
| ATR precisa existir | validacao de `atr` | `test_rejeita_atr_ausente` |
| Volatilidade precisa ser valida | validacao de `volatility` | `test_rejeita_volatilidade_invalida` |
| Stop precisa melhorar protecao | `_improves_stop` | `test_rejeita_stop_candidato_que_piora_protecao` |
| Stop nao pode ficar do lado errado | `_stop_before_market` | `test_rejeita_stop_candidato_do_lado_errado_do_mercado` |
| Stop precisa respeitar ruido | `_respects_volatility_noise` | `test_rejeita_stop_muito_colado_no_ruido` |
| Apenas Volatility Stop | policy/action filtradas | `test_rejeita_politica_diferente_de_volatility_stop` |
| Nao liberar execucao nesta fase | `allowed_to_execute_demo=false` | `test_marca_trend_runner_elegivel_sem_liberar_execucao_demo` |
