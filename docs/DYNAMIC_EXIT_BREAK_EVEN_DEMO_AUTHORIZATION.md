# Dynamic Exit Break-Even Demo Authorization

## Objetivo

A TIA-014 adiciona uma camada de pre-autorizacao para o break-even dinamico em
modo demo, mantendo o sistema operacional seguro.

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

Um caso de break-even dinamico so fica elegivel quando:

- a politica base e `BREAK_EVEN`;
- a acao dinamica e `PROTECT_TO_BREAK_EVEN`;
- existe posicao aberta;
- a posicao andou a favor;
- o estado nao e `TREND_RUNNER`;
- o contexto nao e `NO_POSITION` nem `BAD_EXECUTION_CONTEXT`;
- o stop candidato melhora a protecao atual;
- o stop candidato fica antes do mercado;
- a confianca da recomendacao e pelo menos `0.50`.

## Guardrails preservados

- Sem envio de ordem real.
- Sem `order_send()` novo.
- Sem movimento automatico de SL/TP.
- Sem alteracao no Provider Demo operacional.
- Sem autorizacao para politicas diferentes de `BREAK_EVEN`.
- Sem recalculo pesado do Lab no ciclo leve Forex.

## Proxima fase

A TIA-015 deve tratar `ATR_TRAILING_STOP` dinamico em modo controlado, mantendo
a mesma separacao entre elegibilidade, autorizacao e execucao.
