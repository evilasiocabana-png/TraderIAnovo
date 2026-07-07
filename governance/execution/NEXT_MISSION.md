# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-022_UNIFICAR_DYNAMIC_EXIT_ENGINE
```

Objetivo: consolidar as leituras, recomendacoes e pre-autorizacoes de saida
dinamica em um motor unico auditavel, preservando fallback seguro para a
politica original do Lab.

Esta missao nao deve:

- executar ordem real;
- mover SL/TP automaticamente;
- alterar Provider Demo operacional sem novo guardrail explicito;
- permitir `dynamic_exit_allowed_to_execute_demo=true` por padrao;
- recalcular Lab pesado no ciclo leve Forex;
- quebrar compatibilidade com snapshots antigos.

Para executar, coloque o pacote da TIA-022 em `codex/inbox/` e solicite:

```text
Inbox.
```
