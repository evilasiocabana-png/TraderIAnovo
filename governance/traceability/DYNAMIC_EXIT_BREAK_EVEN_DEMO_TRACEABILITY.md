# Dynamic Exit Break-Even Demo Traceability

## Missao

`MISSION_TIA-014_AUTORIZAR_BREAK_EVEN_DINAMICO_DEMO`

## Arquivos criados

- `domain/contracts/dynamic_exit_demo_authorization.py`
- `application/dynamic_exit_break_even_authorizer.py`
- `tests/test_dynamic_exit_break_even_authorizer.py`
- `docs/DYNAMIC_EXIT_BREAK_EVEN_DEMO_AUTHORIZATION.md`

## Fluxo

```text
DynamicExitMarketReading
  -> DynamicExitRecommendation
  -> DynamicExitBreakEvenAuthorizer
  -> DynamicExitDemoAuthorization
```

## Estado operacional

| Campo | Valor |
| --- | --- |
| Politica autorizavel | BREAK_EVEN |
| Acao autorizavel | PROTECT_TO_BREAK_EVEN |
| Execucao demo ligada | Nao |
| `allowed_to_execute_demo` | false |
| Provider Demo alterado | Nao |
| SL/TP movido | Nao |

## Rastreabilidade das regras

| Regra | Implementacao | Teste |
| --- | --- | --- |
| Posicao precisa andar a favor | `_moved_in_favor` | `test_rejeita_quando_posicao_nao_andou_a_favor` |
| Nao cortar tendencia forte | estado `TREND_RUNNER` rejeitado | `test_rejeita_tendencia_forte_para_nao_cortar_trade_promissor` |
| Stop precisa melhorar protecao | `_improves_stop` | `test_rejeita_stop_candidato_que_piora_protecao` |
| Stop nao pode ficar do lado errado | `_stop_before_market` | `test_rejeita_stop_candidato_do_lado_errado_do_mercado` |
| Apenas BREAK_EVEN | policy/action filtradas | `test_rejeita_politica_diferente_de_break_even` |
| Nao liberar execucao nesta fase | `allowed_to_execute_demo=false` | `test_marca_elegivel_sem_liberar_execucao_demo` |
