# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-015_AUTORIZAR_ATR_TRAILING_DINAMICO_DEMO
```

Objetivo: preparar a autorizacao controlada do ATR trailing dinamico em modo
demo, preservando a separacao entre recomendacao, elegibilidade e execucao.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- autorizar qualquer politica alem de ATR trailing dinamico.

Para executar, coloque o pacote da TIA-015 em `codex/inbox/` e solicite:

```text
Inbox.
```
