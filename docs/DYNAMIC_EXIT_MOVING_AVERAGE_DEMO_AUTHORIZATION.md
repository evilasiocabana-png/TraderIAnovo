# Dynamic Exit Moving Average Demo Authorization

## Objetivo

A TIA-020 adiciona uma camada de pre-autorizacao para
`MOVING_AVERAGE_EXIT` em modo demo, mantendo a execucao operacional desligada.

## Regra operacional desta fase

Nesta etapa, a camada apenas informa se um caso seria elegivel para autorizacao
futura. Ela nao executa ordem, nao fecha posicao e nao liga
`dynamic_exit_allowed_to_execute_demo`.

```text
eligible_to_authorize=true
allowed_to_execute_demo=false
execution_mode=READ_ONLY_PRE_AUTHORIZATION
```

## Condicoes para elegibilidade

Um caso de Moving Average Exit so fica elegivel quando:

- a politica base e `MOVING_AVERAGE_EXIT`;
- a acao dinamica e `TIGHTEN_BY_MOMENTUM_LOSS`;
- existe posicao aberta;
- o estado atual indica reversao, tempo deteriorado ou posicao protegida;
- existe preco atual e entrada;
- o momentum confirma perda de tendencia;
- a operacao nao esta em perda deteriorada: `R >= -0.25`;
- a confianca da recomendacao e pelo menos `0.55`.

## Guardrails preservados

- Sem envio de ordem real.
- Sem `order_send()` novo.
- Sem fechamento automatico de posicao.
- Sem alteracao no Provider Demo operacional.
- Sem autorizacao para politicas diferentes de `MOVING_AVERAGE_EXIT`.
- Sem recalculo pesado do Lab no ciclo leve Forex.

## Proxima fase

A TIA-021 deve preparar a autorizacao controlada de `PARABOLIC_SAR`.
