# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY
```

Objetivo sugerido: implementar apenas campos e contratos read-only para a saida
dinamica, com testes de preservacao Lab -> Forex -> MT5 -> Relatorio. Esta
missao nao deve executar gestao real de SL/TP.

Para executar, coloque um pacote em `codex/inbox/` e solicite:

```text
Inbox.
```

O Codex deve executar apenas a primeira missao autorizada, respeitando a
governanca deste diretorio.
