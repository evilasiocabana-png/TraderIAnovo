# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-013_PAPER_SIMULATION_SAIDA_DINAMICA
```

Objetivo: rodar a saida dinamica em modo simulado/paper, registrando cada
recomendacao e comparando com o resultado real da politica original.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- executar recomendacao dinamica no Provider Demo.

Para executar, coloque o pacote da TIA-013 em `codex/inbox/` e solicite:

```text
Inbox.
```
