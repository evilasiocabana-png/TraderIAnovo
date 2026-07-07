# Next Mission

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-025_CORRIGIR_GATES_ESTRUTURAIS_API_DASHBOARD
```

Objetivo: corrigir as pendencias estruturais que impedem o gate critico de
ficar verde apos a entrega read-only da saida dinamica.

Esta missao nao deve:

- executar ordem real;
- mover SL/TP automaticamente;
- alterar Provider Demo operacional;
- apagar `.traderia`;
- mascarar falhas de arquitetura sem reconciliar contratos;
- quebrar compatibilidade com snapshots antigos.

Escopo sugerido:

- reconciliar manifest/API freeze de servicos publicos;
- reconciliar contrato congelado de `DashboardService`;
- remover acesso direto `positions_get` do dashboard;
- revisar expectativa antiga `MA_RSI_FILTER` SELL versus resultado BUY;
- manter Dynamic Exit read-only.

Para executar, coloque o pacote da TIA-025 em `codex/inbox/` e solicite:

```text
Inbox.
```
