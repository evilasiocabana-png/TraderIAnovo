# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-009_EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_DASHBOARD
```

Objetivo: mostrar no Dashboard/Forex a politica original do Lab, estado atual do
mercado, recomendacao dinamica, motivo, confianca, R atual, stop candidato e
execucao permitida sempre `false`.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.

Para executar, coloque o pacote da TIA-009 em `codex/inbox/` e solicite:

```text
Inbox.
```
