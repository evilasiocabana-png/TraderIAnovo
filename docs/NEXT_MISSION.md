# Next Mission

## Missao Recomendada

Criar health check operacional da TraderIA Novo.

## Objetivo

Implementar uma validacao rapida que confirme se as tres abas principais tem
dados minimos e nao dependem de ciclo bloqueante:

- MT5 Forex
- Lab
- Relatorios

## Escopo

Criar script em `scripts/` que:

1. instancia `DashboardService`;
2. valida `get_light_dashboard_view_model()`;
3. valida existencia de `.traderia/mt5_research_snapshot.json`;
4. valida existencia de `.traderia/traderia_mt5_history.sqlite`;
5. valida `get_mt5_trade_audit_report()` em tempo aceitavel;
6. imprime um resumo claro.

## Criterios De Aceite

- Script executa em menos de 15 segundos quando MT5 nao trava.
- Nao dispara leitura MT5 pesada por padrao.
- Retorna codigo de saida diferente de zero em falha critica.
- Documenta resultado em `docs/EXECUTION_LOG.md`.

## Arquivos Provaveis

- `scripts/traderianovo_health_check.py`
- `tests/test_traderianovo_health_check.py`
- `docs/EXECUTION_LOG.md`

