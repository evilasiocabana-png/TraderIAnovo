# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-027_ATUALIZAR_BASELINE_ARQUITETURAL_INFORMATIVO
```

Objetivo: atualizar ou revisar o baseline arquitetural informativo apos o
manifest e os contratos terem sido reconciliados.

Esta missao nao deve:

- executar ordem real;
- mover SL/TP automaticamente;
- alterar Provider Demo operacional;
- apagar `.traderia`;
- mascarar falhas de arquitetura;
- quebrar compatibilidade com snapshots antigos.

Escopo sugerido:

- revisar `architecture_baseline.json`;
- confirmar que o drift e apenas informativo;
- atualizar baseline somente se os arquivos adicionados forem intencionais;
- manter `architecture_audit.py` OK e `run_critical_ci.py` verde.

Para executar, coloque o pacote da TIA-027 em `codex/inbox/` e solicite:

```text
Inbox.
```
