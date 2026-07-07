# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-012_BACKTEST_SAIDA_DINAMICA_READ_ONLY
```

Objetivo: comparar saida original do Lab versus saida dinamica recomendada em
modo read-only, sem executar ordem e sem mover SL/TP.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- substituir politica original do Lab.

Para executar, coloque o pacote da TIA-012 em `codex/inbox/` e solicite:

```text
Inbox.
```
