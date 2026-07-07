# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-023_OTIMIZAR_DYNAMIC_EXIT_RUNTIME
```

Objetivo: garantir que o runtime da saida dinamica continue leve, com cache
quando possivel, tolerancia a dados ausentes e sem recalcular Lab pesado.

Esta missao nao deve:

- executar ordem real;
- mover SL/TP automaticamente;
- alterar Provider Demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true` por padrao;
- recalcular Lab pesado no ciclo leve Forex;
- quebrar compatibilidade com snapshots antigos.

Para executar, coloque o pacote da TIA-023 em `codex/inbox/` e solicite:

```text
Inbox.
```
