# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-007_EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_RELATORIO
```

Objetivo sugerido: exibir melhor os campos `dynamic_exit_*` nas abas Forex e
Relatorio, mantendo a saida dinamica apenas como leitura/auditoria. Esta missao
nao deve executar gestao real de SL/TP.

Para executar, coloque um pacote em `codex/inbox/` e solicite:

```text
Inbox.
```

O Codex deve executar apenas a primeira missao autorizada, respeitando a
governanca deste diretorio.
