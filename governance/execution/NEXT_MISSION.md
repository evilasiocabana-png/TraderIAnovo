# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-020_AUTORIZAR_MOVING_AVERAGE_EXIT_DEMO
```

Objetivo: preparar a autorizacao controlada de `MOVING_AVERAGE_EXIT` em modo demo,
preservando a separacao entre recomendacao, elegibilidade e execucao.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- autorizar qualquer politica alem de `MOVING_AVERAGE_EXIT`.

Para executar, coloque o pacote da TIA-020 em `codex/inbox/` e solicite:

```text
Inbox.
```
