# Dynamic Exit ATR Trailing Demo Traceability

## Missao

`MISSION_TIA-015_AUTORIZAR_ATR_TRAILING_DINAMICO_DEMO`

## Arquivos criados

- `application/dynamic_exit_atr_trailing_authorizer.py`
- `tests/test_dynamic_exit_atr_trailing_authorizer.py`
- `docs/DYNAMIC_EXIT_ATR_TRAILING_DEMO_AUTHORIZATION.md`

## Fluxo

```text
DynamicExitMarketReading
  -> DynamicExitRecommendation
  -> DynamicExitAtrTrailingAuthorizer
  -> DynamicExitDemoAuthorization
```

## Estado operacional

| Campo | Valor |
| --- | --- |
| Politica autorizavel | ATR_TRAILING_STOP |
| Acao autorizavel | TRAIL_BY_ATR |
| Execucao demo ligada | Nao |
| `allowed_to_execute_demo` | false |
| Provider Demo alterado | Nao |
| SL/TP movido | Nao |

## Rastreabilidade das regras

| Regra | Implementacao | Teste |
| --- | --- | --- |
| Posicao precisa andar a favor | `_moved_in_favor` | `test_marca_trend_runner_elegivel_sem_liberar_execucao_demo` |
| Posicao nova preserva stop inicial | estado `NEW_POSITION` rejeitado | `test_rejeita_posicao_nova_para_preservar_stop_inicial` |
| ATR precisa existir | validacao de `atr` | `test_rejeita_quando_atr_esta_ausente` |
| Stop precisa melhorar protecao | `_improves_stop` | `test_rejeita_stop_candidato_que_piora_protecao` |
| Stop nao pode ficar do lado errado | `_stop_before_market` | `test_rejeita_stop_candidato_do_lado_errado_do_mercado` |
| Stop precisa respeitar ruido de ATR | `_respects_atr_noise` | `test_rejeita_stop_candidato_muito_colado_no_preco` |
| Apenas ATR trailing | policy/action filtradas | `test_rejeita_politica_diferente_de_atr_trailing` |
| Nao liberar execucao nesta fase | `allowed_to_execute_demo=false` | `test_marca_trend_runner_elegivel_sem_liberar_execucao_demo` |
