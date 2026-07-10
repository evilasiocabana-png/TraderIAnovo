# EXECUTION_REPORT - MISSION_COST_MANAGER_MT5_REAL_COSTS

## Status

completed

## Objetivo executado

Criar uma camada centralizada para custos reais e estimados do MT5, separando:

- spread;
- comissao/corretagem;
- swap;
- fee;
- rollover.

## Resultado

Foi criado o `CostManager` em `application/cost_manager.py`.

O sistema agora possui:

- `SymbolCostSnapshot`;
- `TradeCostEstimate`;
- `RealTradeCost`;
- leitura read-only de dados de custo por simbolo;
- estimativa de custo antes da entrada sem corretagem hardcoded;
- agregacao de custo real apos execucao;
- regra oficial `net_profit = profit + commission + swap + fee`.

## Integracao

O provider MT5 passou a expor `get_symbol_cost_data(symbol)`, lendo:

- bid;
- ask;
- spread;
- swap long;
- swap short;
- tick value;
- tick size;
- contract size;
- digits;
- point.

O processo externo do MT5 tambem recebeu a acao read-only `cost_snapshot`.

O relatorio MT5 passou a transportar:

- `mt5_commission`;
- `mt5_swap`;
- `mt5_fee`;
- `mt5_open_cost`.

No dashboard, `Custo aberto` deixou de representar risco projetado e passou a
representar custo operacional real:

```text
Custo aberto = commission + swap + fee
```

`Risco em aberto` continua representando o risco projetado pelo stop/plano.

## Documentacao

Criado:

- `docs/MT5_COST_MANAGER.md`

## Validacao

Executado com sucesso:

```text
python -m unittest tests.test_cost_manager
python -m unittest tests.test_mt5_market_data_provider.MT5MarketDataProviderTest.test_get_symbol_cost_data_le_custos_read_only tests.test_mt5_market_data_provider.MT5MarketDataProviderTest.test_provider_nao_expoe_capacidade_operacional
python -m unittest tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_resumo_em_negociacao_soma_lucros_das_operacoes_abertas tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_auditoria_mt5_mostra_custo_aberto_por_operacao_aberta
python -m unittest tests.test_dashboard_view_model.DashboardViewModelContractTest.test_relatorio_mt5_confere_log_local_com_historico_da_plataforma
python -m py_compile application\cost_manager.py application\dashboard_service.py application\dashboard_view_model.py dashboard_app.py infrastructure\market_data\mt5_market_data_provider.py
```

## Guardrails preservados

- Nenhuma regra de entrada do Lab foi alterada.
- Nenhum RR foi alterado.
- Nenhum envio de ordem foi alterado.
- Nenhum movimento de SL/TP foi feito.
- Nenhuma corretagem foi hardcoded.
- Rollover continua sendo evento temporal, nao custo.
- Swap continua sendo custo/credito financeiro informado pelo MT5/corretora.

## Proxima missao pendente

Permanece no inbox:

- `MISSION_ROLLOVER_FIRST_DAILY_OPERATION_LAB_DECISION`
