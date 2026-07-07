# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-010_EXIBIR_SAIDA_DINAMICA_NO_MT5_VISUAL
```

Objetivo: adicionar a recomendacao dinamica ao JSON visual e ao indicador MT5,
mostrando texto curto somente quando houver posicao aberta.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- poluir grafico de ativo sem posicao.

Para executar, coloque o pacote da TIA-010 em `codex/inbox/` e solicite:

```text
Inbox.
```
