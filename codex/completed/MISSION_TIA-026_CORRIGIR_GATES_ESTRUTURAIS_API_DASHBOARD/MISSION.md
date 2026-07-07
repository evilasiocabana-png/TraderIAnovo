# MISSION_TIA-026_CORRIGIR_GATES_ESTRUTURAIS_API_DASHBOARD

## Origem

Missao executada por autorizacao direta do usuario a partir da recomendacao
registrada em `governance/execution/NEXT_MISSION.md`.

## Objetivo

Corrigir os gates estruturais que ficaram pendentes apos a entrega read-only da
saida dinamica.

## Escopo

- Reconciliar manifest/API freeze de servicos publicos.
- Reconciliar contrato congelado de `DashboardService`.
- Remover acesso direto proibido do dashboard a operacoes MT5.
- Corrigir divergencia funcional do modelo `MA_RSI_FILTER`.
- Preservar Dynamic Exit read-only.

## Guardrails

- Nao executar ordem real.
- Nao mover SL/TP automaticamente.
- Nao alterar Provider Demo operacional.
- Nao apagar `.traderia`.
- Nao mascarar falhas de arquitetura sem reconciliar contratos.
- Manter compatibilidade operacional do dashboard.

