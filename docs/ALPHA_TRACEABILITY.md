# TraderIA Novo - Rastreabilidade das Alphas

Este documento registra onde as Alphas Forex MT5 estao definidas, como sao
avaliadas e como devem ser rastreadas em missoes futuras.

## Fonte principal

Hoje a biblioteca Alpha001-Alpha015 do fluxo MT5 Forex esta concentrada em:

```text
application/dashboard_service.py
```

Trechos de referencia:

- `_mt5_scenario_parameter_grid()`
- `_mt5_grid_parameters()`
- `_mt5_alpha_library()`
- `_mt5_alpha_definitions()`
- `_mt5_parameterized_candidate()`
- `_mt5_scenario_for_parameters()`
- `_mt5_research_scenarios_for_row()`

## Catalogo atual

| Alpha | Modelo | Funcao candidata |
| --- | --- | --- |
| ALPHA001 | TREND_MOMENTUM | `_trend_momentum_parameterized_candidate` |
| ALPHA002 | TREND_PULLBACK | `_trend_pullback_parameterized_candidate` |
| ALPHA003 | BREAKOUT_CONSOLIDATION | `_breakout_consolidation_parameterized_candidate` |
| ALPHA004 | RSI_REVERSAL | `_rsi_reversal_parameterized_candidate` |
| ALPHA005 | DONCHIAN_BREAKOUT | `_donchian_breakout_parameterized_candidate` |
| ALPHA006 | ADX_TREND_STRENGTH | `_adx_trend_strength_parameterized_candidate` |
| ALPHA007 | MACD_MOMENTUM_SHIFT | `_macd_momentum_shift_parameterized_candidate` |
| ALPHA008 | BOLLINGER_VOLATILITY_EXPANSION | `_bollinger_volatility_expansion_parameterized_candidate` |
| ALPHA009 | ATR_VOLATILITY_REGIME | `_atr_volatility_regime_parameterized_candidate` |
| ALPHA010 | DONCHIAN_STRUCTURE_BREAKOUT | `_donchian_structure_breakout_parameterized_candidate` |
| ALPHA011 | PIVOT_REJECTION | `_pivot_rejection_parameterized_candidate` |
| ALPHA012 | VWAP_MEAN_REVERSION | `_vwap_mean_reversion_parameterized_candidate` |
| ALPHA013 | SUPPORT_RESISTANCE_REACTION | `_support_resistance_reaction_parameterized_candidate` |
| ALPHA014 | MULTI_TIMEFRAME_ALIGNMENT | `_multi_timeframe_alignment_parameterized_candidate` |
| ALPHA015 | LIQUIDITY_SPREAD_FILTER | `_liquidity_spread_filter_parameterized_candidate` |

## Fluxo de avaliacao

```text
Historico MT5 por par/timeframe
  |
  v
_mt5_research_scenarios_for_row()
  |
  +--> gera grade de parametros de entrada
  |
  +--> escolhe finalistas de entrada
  |
  +--> expande stop_management/saida
  |
  v
_mt5_scenario_for_parameters()
  |
  +--> chama candidato da Alpha
  +--> aplica camada de tempo
  +--> calcula evidencia historica
  +--> classifica ICT/certificacao
  |
  v
DashboardMT5ScenarioViewModel
```

## Resultado consolidado

O resultado final para consumo do app e:

```text
DashboardMT5HeuristicResearchViewModel
  rows
  scenario_ranking
  best_scenarios_by_market
  best_scenario
  winner_research_configuration
```

Para a tela de sugestoes, a fonte preferida deve ser `rows` e
`final_configuration`, porque ali esta a decisao consolidada por par. O ranking
bruto serve para auditoria e melhoria de pesquisa.

## Campos de rastreabilidade obrigatorios

Toda melhoria de Alpha deve preservar ou explicitar:

- `alpha`
- `modelo`
- `pair`
- `timeframe`
- `decision`
- `score`
- `lab_confidence`
- `status`
- `reason`
- parametros testados
- `stop_management`
- criterios de aceite
- testes executados

## Regra para GPT/Codex

Uma missao que proponha nova Alpha ou alteracao de Alpha deve:

1. declarar a Alpha afetada;
2. declarar funcao candidata afetada;
3. declarar parametros novos/removidos;
4. atualizar este documento ou um documento especifico da Alpha;
5. incluir teste que mostre que o Lab nao voltou a forcar tudo para M1;
6. provar que Forex continua usando o timeframe consolidado pelo Lab.
