# Dynamic Exit Chandelier Demo Authorization

## Objetivo

A TIA-016 adiciona uma camada de pre-autorizacao para `CHANDELIER_EXIT` em modo
demo, mantendo a execucao operacional desligada.

## Regra operacional desta fase

Nesta etapa, a camada apenas informa se um caso seria elegivel para autorizacao
futura. Ela nao executa ordem, nao move SL/TP e nao liga
`dynamic_exit_allowed_to_execute_demo`.

```text
eligible_to_authorize=true
allowed_to_execute_demo=false
execution_mode=READ_ONLY_PRE_AUTHORIZATION
```

## Condicoes para elegibilidade

Um caso de Chandelier Exit so fica elegivel quando:

- a politica base e `CHANDELIER_EXIT`;
- a acao dinamica e `TRAIL_BY_STRUCTURE`;
- existe posicao aberta;
- o estado atual e `TREND_RUNNER`;
- a posicao andou a favor;
- o trade tem pelo menos `1R` de progresso;
- o momentum nao esta contra a posicao;
- existe ATR valido;
- o stop candidato melhora a protecao atual;
- o stop candidato fica antes do mercado;
- o stop candidato respeita distancia minima de Chandelier;
- a confianca da recomendacao e pelo menos `0.60`.

## Guardrails preservados

- Sem envio de ordem real.
- Sem `order_send()` novo.
- Sem movimento automatico de SL/TP.
- Sem alteracao no Provider Demo operacional.
- Sem autorizacao para politicas diferentes de `CHANDELIER_EXIT`.
- Sem recalculo pesado do Lab no ciclo leve Forex.

## Proxima fase

A TIA-017 deve preparar a autorizacao controlada de `DONCHIAN_CHANNEL_STOP`.
