# Dynamic Exit MT5 Visual Traceability

## Missao

`MISSION_TIA-010_EXIBIR_SAIDA_DINAMICA_NO_MT5_VISUAL`

## Fluxo

```text
Lab policy
->
DynamicExitMarketReading
->
DynamicExitRecommendation
->
DashboardMT5ForexSignalRowViewModel
->
MT5VisualSignalExporter
->
dynamic_exit_visual_text
->
TraderIAVisualSignals.mq5
->
Grafico MT5 somente quando ha posicao aberta
```

## Contrato

| Campo | Origem | Uso |
| --- | --- | --- |
| `dynamic_exit_policy` | politica base do Lab | auditoria |
| `dynamic_exit_action` | recomendacao read-only | texto visual |
| `dynamic_exit_reason` | motor dinamico | motivo visual |
| `dynamic_exit_confidence` | motor dinamico | confianca visual |
| `dynamic_exit_market_state` | leitura de mercado | estado visual |
| `dynamic_exit_candidate_stop` | motor dinamico | stop candidato visual |
| `dynamic_exit_allowed_to_execute_demo` | guardrail | sempre `false` |
| `dynamic_exit_visual_text` | exportador MT5 | texto curto no grafico |

## Regra de Limpeza do Grafico

O campo `dynamic_exit_visual_text` e vazio para ativos sem posicao. O indicador
continua desenhando informacao operacional somente dentro de
`IsPositionedTradeBlock(block)`.

## Garantia

Esta camada observa e exibe. Ela nao decide, nao executa ordem e nao move
SL/TP.
