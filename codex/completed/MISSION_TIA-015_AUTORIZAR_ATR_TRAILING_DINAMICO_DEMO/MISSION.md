# MISSION_TIA-015_AUTORIZAR_ATR_TRAILING_DINAMICO_DEMO

## Objetivo

Criar uma camada segura de pre-autorizacao para ATR trailing dinamico em modo
demo, sem ligar execucao operacional nesta fase.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar o Provider Demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo=true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao autorizar politica diferente de `ATR_TRAILING_STOP`.

## Resultado esperado

Autorizador read-only, testes e rastreabilidade para que uma etapa futura possa
ligar execucao demo de forma explicita e reversivel.
