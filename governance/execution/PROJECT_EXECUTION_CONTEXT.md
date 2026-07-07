# Project Execution Context

`traderiaianovo` e uma base limpa para evoluir o TraderIA com governanca por
Inbox, GPT e arquitetura read-only para MT5.

## Fluxo

1. Ler `governance/execution/`.
2. Ler `codex/inbox/`.
3. Mover a primeira missao autorizada para `codex/processing/`.
4. Executar somente o escopo autorizado.
5. Testar.
6. Gerar relatorio.
7. Mover para `completed/` ou `failed/`.
8. Atualizar governanca.
9. Commit + push.

## Guardrails

- MT5 e read-only.
- Nenhuma ordem real.
- UI consome apenas `application/DashboardService`.
- Lab decide parametros.
- Forex MT5 le dados leves.
- Relatorio consolida dados.
