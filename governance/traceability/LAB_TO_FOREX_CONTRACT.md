# TraderIA Novo - Contract Lab -> Forex

Este contrato rastreia como o resultado do Lab chega ao ciclo leve Forex MT5.

## Fonte do Lab

```text
.traderia/mt5_research_snapshot.json
DashboardService.get_mt5_research_constants()
DashboardService.suggest_mt5_lab_setups()
```

O GitHub nao versiona `.traderia`; ele versiona o contrato e a rastreabilidade.

## Dados entregues ao Forex

| Campo | Origem | Consumidor |
| --- | --- | --- |
| `pair` | linha consolidada do Lab | Forex row |
| `timeframe` / `ideal_timeframe` | Lab | `_mt5_lab_timeframes_by_pair()` |
| `recommended_heuristic` | Lab | modelo ativo do Forex |
| `decision` | Lab/Forex | entrada teorica |
| `final_configuration.alpha` | Lab | `lab_alpha_id` |
| `final_configuration.modelo` | Lab | `active_model` |
| `final_configuration.stop_management` | Lab | TradePlan e visual MT5 |
| `final_configuration.rr` | Lab | alvo/risco |
| `confidence` | Lab | exibicao e auditoria |
| `score` | Lab | ranking/encaixe |

## Caminho no codigo

```text
DashboardService._mt5_lab_timeframes_by_pair()
  -> DashboardService.load_mt5_forex_signals()
  -> MT5MarketDataService.load_forex_signal_dashboard_for_timeframes()
  -> DashboardService._to_view_model_mt5_forex_signal_row()
```

## Regras

- O Forex nao decide timeframe quando o Lab tem timeframe consolidado.
- O Forex nao recalcula biblioteca de Alphas no ciclo leve.
- O Forex pode buscar candles atuais no timeframe do Lab.
- Falta de cache nao deve forcar todos os pares para M1 sem registro.

## Testes associados

- `tests/test_dashboard_view_model.py`
- `tests/test_lab_forex_mt5_contract.py`
- testes que validam `lab_timeframe`, `lab_alpha_id` e `stop_management`.
