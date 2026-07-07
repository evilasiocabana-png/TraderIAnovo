# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-021_AUTORIZAR_PARABOLIC_SAR_DEMO
```

Objetivo: preparar a autorizacao controlada de `PARABOLIC_SAR` em modo demo,
preservando a separacao entre recomendacao, elegibilidade e execucao.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- autorizar qualquer politica alem de `PARABOLIC_SAR`.

Para executar, coloque o pacote da TIA-021 em `codex/inbox/` e solicite:

```text
Inbox.
```
