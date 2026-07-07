# MISSION_TIA-016_AUTORIZAR_CHANDELIER_EXIT_DEMO

## Objetivo

Criar uma camada segura de pre-autorizacao para `CHANDELIER_EXIT` em modo demo,
sem ligar execucao operacional nesta fase.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar o Provider Demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo=true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao autorizar politica diferente de `CHANDELIER_EXIT`.

## Resultado esperado

Autorizador read-only, testes e rastreabilidade para que uma etapa futura possa
ligar execucao demo de forma explicita e reversivel.
