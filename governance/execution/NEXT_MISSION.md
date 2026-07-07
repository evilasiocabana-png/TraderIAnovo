# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-024_VALIDACAO_FINAL_DYNAMIC_EXIT
```

Objetivo: fazer a auditoria final da saida dinamica, validando contratos,
testes, MT5 visual, Provider Demo, Relatorios, rollback e ausencia de
regressoes operacionais.

Esta missao nao deve:

- executar ordem real;
- mover SL/TP automaticamente;
- executar ordem real;
- mover SL/TP automaticamente;
- alterar Provider Demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true` sem autorizacao formal;
- apagar `.traderia`;
- quebrar compatibilidade com snapshots antigos.

Para executar, coloque o pacote da TIA-024 em `codex/inbox/` e solicite:

```text
Inbox.
```
