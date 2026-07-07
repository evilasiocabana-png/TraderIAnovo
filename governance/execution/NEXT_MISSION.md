# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-008_IMPLEMENTAR_DYNAMIC_EXIT_RECOMMENDATION_ENGINE
```

Objetivo: criar o motor que transforma `DynamicExitMarketReading`/estado de
mercado em recomendacao dinamica read-only.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.

Para executar, coloque o pacote da TIA-008 em `codex/inbox/` e solicite:

```text
Inbox.
```
