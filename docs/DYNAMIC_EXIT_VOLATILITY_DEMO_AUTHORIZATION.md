# Dynamic Exit Volatility Demo Authorization

## Objetivo

A TIA-018 adiciona uma camada de pre-autorizacao para `VOLATILITY_STOP` em modo
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

Um caso de Volatility Stop so fica elegivel quando:

- a politica base e `VOLATILITY_STOP`;
- a acao dinamica e `TRAIL_BY_ATR`;
- existe posicao aberta;
- o estado nao e `NEW_POSITION`, `NO_POSITION` ou `BAD_EXECUTION_CONTEXT`;
- a posicao andou a favor;
- o trade tem pelo menos `0.50R` de progresso;
- existe ATR valido;
- existe volatilidade valida;
- o stop candidato melhora a protecao atual;
- o stop candidato fica antes do mercado;
- o stop candidato respeita ruido minimo de ATR/volatilidade;
- a confianca da recomendacao e pelo menos `0.56`.

## Guardrails preservados

- Sem envio de ordem real.
- Sem `order_send()` novo.
- Sem movimento automatico de SL/TP.
- Sem alteracao no Provider Demo operacional.
- Sem autorizacao para politicas diferentes de `VOLATILITY_STOP`.
- Sem recalculo pesado do Lab no ciclo leve Forex.

## Proxima fase

A TIA-019 deve preparar a autorizacao controlada de `TIME_STOP`.
