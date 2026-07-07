# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-014_AUTORIZAR_BREAK_EVEN_DINAMICO_DEMO
```

Objetivo: autorizar de forma controlada a primeira politica demo da saida
dinamica: break-even dinamico.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- autorizar qualquer politica alem de break-even dinamico.

Para executar, coloque o pacote da TIA-014 em `codex/inbox/` e solicite:

```text
Inbox.
```
