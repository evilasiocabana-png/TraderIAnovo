# Dynamic Exit - Parabolic SAR Demo Authorization

## Status

Read-only pre-authorization.

## Objetivo

`PARABOLIC_SAR` fica preparado para uma futura autorizacao demo controlada em
cenarios de reversao rapida, sem alterar a operacao atual.

## Entrada

- `DynamicExitMarketReading`
- `DynamicExitRecommendation`

## Regra de elegibilidade

Para ser marcado como elegivel:

- politica: `PARABOLIC_SAR`;
- acao: `TIGHTEN_BY_MOMENTUM_LOSS`;
- posicao aberta;
- estado: `REVERSAL_RISK` ou `PROTECTED_POSITION`;
- momentum contra a posicao;
- stop candidato presente;
- stop candidato melhora a protecao;
- stop candidato permanece do lado correto do mercado;
- `r_multiple >= -0.15`;
- confianca minima `0.57`.

## Saida

Retorna `DynamicExitDemoAuthorization`.

Mesmo quando elegivel:

```text
eligible_to_authorize = true
allowed_to_execute_demo = false
execution_mode = READ_ONLY_PRE_AUTHORIZATION
```

## Guardrails

- Nao envia ordem.
- Nao move SL/TP.
- Nao altera Provider Demo.
- Nao altera Dashboard, MT5 visual ou Relatorio operacional.
- Nao recalcula Lab pesado.

## Proxima etapa

Depois de encerrar as politicas individuais, a proxima missao recomendada e
`MISSION_TIA-022_UNIFICAR_DYNAMIC_EXIT_ENGINE`.
