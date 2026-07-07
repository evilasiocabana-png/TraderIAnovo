# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-011_REGISTRAR_SAIDA_DINAMICA_NO_RELATORIO
```

Objetivo: registrar no Relatorio a politica original, recomendacao dinamica,
motivo, confianca, estado de mercado, acao executada e resultado final.

Esta missao nao deve:

- executar ordem;
- mover SL/TP;
- alterar provider demo operacional;
- permitir `dynamic_exit_allowed_to_execute_demo=true`;
- recalcular Lab pesado no ciclo leve Forex.
- fazer o Relatorio decidir saida.

Para executar, coloque o pacote da TIA-011 em `codex/inbox/` e solicite:

```text
Inbox.
```
