# MISSION_TIA-014_AUTORIZAR_BREAK_EVEN_DINAMICO_DEMO

## Objetivo

Criar uma camada segura de pre-autorizacao para break-even dinamico em modo
demo, sem ligar execucao operacional nesta fase.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar o Provider Demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo=true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao autorizar politica diferente de `BREAK_EVEN`.

## Resultado esperado

Contrato, autorizador read-only, testes e rastreabilidade para que a etapa
seguinte possa ligar execucao demo de forma explicita e reversivel.
