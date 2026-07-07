# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-019_AUTORIZAR_TIME_STOP_DEMO
```

Objetivo: preparar a autorizacao controlada de `TIME_STOP` em modo demo,
preservando a separacao entre recomendacao, elegibilidade e execucao.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- autorizar qualquer politica alem de `TIME_STOP`.

Para executar, coloque o pacote da TIA-019 em `codex/inbox/` e solicite:

```text
Inbox.
```
