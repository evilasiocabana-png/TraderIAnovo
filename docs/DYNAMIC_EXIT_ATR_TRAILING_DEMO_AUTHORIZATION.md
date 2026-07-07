# Dynamic Exit ATR Trailing Demo Authorization

## Objetivo

A TIA-015 adiciona uma camada de pre-autorizacao para ATR trailing dinamico em
modo demo, mantendo o Provider Demo operacional desligado para esta politica.

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

Um caso de ATR trailing dinamico so fica elegivel quando:

- a politica base e `ATR_TRAILING_STOP`;
- a acao dinamica e `TRAIL_BY_ATR`;
- existe posicao aberta;
- a posicao andou a favor;
- o estado nao e `NEW_POSITION`, `NO_POSITION` ou `BAD_EXECUTION_CONTEXT`;
- existe ATR valido;
- o stop candidato melhora a protecao atual;
- o stop candidato fica antes do mercado;
- o stop candidato respeita ruido minimo de ATR;
- a confianca da recomendacao e pelo menos `0.55`.

## Guardrails preservados

- Sem envio de ordem real.
- Sem `order_send()` novo.
- Sem movimento automatico de SL/TP.
- Sem alteracao no Provider Demo operacional.
- Sem autorizacao para politicas diferentes de `ATR_TRAILING_STOP`.
- Sem recalculo pesado do Lab no ciclo leve Forex.

## Proxima fase

A TIA-016 deve preparar a autorizacao controlada de `CHANDELIER_EXIT`.
