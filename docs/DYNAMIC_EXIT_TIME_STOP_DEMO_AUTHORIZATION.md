# Dynamic Exit Time Stop Demo Authorization

## Objetivo

A TIA-019 adiciona uma camada de pre-autorizacao para `TIME_STOP` em modo demo,
mantendo a execucao operacional desligada.

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

Um caso de Time Stop so fica elegivel quando:

- a politica base e `TIME_STOP`;
- a acao dinamica e `TIME_DECAY_EXIT_WATCH`;
- existe posicao aberta;
- o estado atual e `TIME_DECAY`;
- existe preco atual, entrada e tempo em posicao;
- o tempo em posicao e pelo menos `240` minutos;
- o trade nao tem progresso relevante: `abs(R) <= 0.25`;
- o momentum nao favorece a permanencia na posicao;
- a confianca da recomendacao e pelo menos `0.45`.

## Guardrails preservados

- Sem envio de ordem real.
- Sem `order_send()` novo.
- Sem fechamento automatico de posicao.
- Sem alteracao no Provider Demo operacional.
- Sem autorizacao para politicas diferentes de `TIME_STOP`.
- Sem recalculo pesado do Lab no ciclo leve Forex.

## Proxima fase

A TIA-020 deve preparar a autorizacao controlada de `MOVING_AVERAGE_EXIT`.
