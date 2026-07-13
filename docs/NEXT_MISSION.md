# Next Mission

## Missao Recomendada

Criar health check operacional e sentinela de velocidade da TraderIA Novo.

## Objetivo

Implementar uma validacao rapida que confirme se as tres abas principais tem
dados minimos e nao dependem de ciclo bloqueante:

- MT5 Forex
- Lab
- Relatorios
- Saida Teorica MT5

## Escopo

Criar script em `scripts/` que:

1. instancia `DashboardService`;
2. valida `get_light_dashboard_view_model()`;
3. valida existencia de `.traderia/mt5_research_snapshot.json`;
4. valida existencia de `.traderia/traderia_mt5_history.sqlite`;
5. valida `get_mt5_trade_audit_report()` em tempo aceitavel;
6. valida que a Saida Teorica MT5 usa snapshot leve do Position Manager;
7. mede tempo de montagem das tabelas criticas sem renderizar historico inteiro;
8. imprime um resumo claro.

## Pendencia De Velocidade Registrada

O usuario sinalizou em 2026-07-13 que a velocidade do app precisa continuar
no radar. Esta pendencia nao autoriza reduzir leitura de mercado essencial,
mas exige medir e proteger:

- tempo de abertura da aba Relatorios;
- tempo de atualizacao da Saida Teorica MT5;
- custo de leitura do Position Manager;
- custo de leitura do historico MT5;
- ausencia de varredura do snapshot pesado do Lab no ciclo leve;
- paginacao das tabelas grandes.

## Criterios De Aceite

- Script executa em menos de 15 segundos quando MT5 nao trava.
- Nao dispara leitura MT5 pesada por padrao.
- Retorna codigo de saida diferente de zero em falha critica.
- Documenta resultado em `docs/EXECUTION_LOG.md`.
- Aponta claramente qual etapa ficou lenta quando passar do limite.
- Mantem a leitura de indicadores necessaria para BETA002 sem bloquear a UI.

## Arquivos Provaveis

- `scripts/traderianovo_health_check.py`
- `tests/test_traderianovo_health_check.py`
- `docs/EXECUTION_LOG.md`
