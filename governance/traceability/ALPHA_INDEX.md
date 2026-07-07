# TraderIA Novo - Alpha Index

Catalogo rastreavel das Alphas usadas pelo Research Lab MT5.

Fonte executavel principal:

```text
application/dashboard_service.py
  _mt5_alpha_library()
  _mt5_alpha_definitions()
  _mt5_scenario_parameter_grid()
  _mt5_parameterized_candidate()
```

## Catalogo

| Alpha | Setup/modelo | Hipotese resumida | Indicadores | Funcao candidata |
| --- | --- | --- | --- | --- |
| ALPHA001 | TREND_MOMENTUM | Continuidade em tendencia com momentum e volatilidade suficientes. | EMA, RSI, ATR, Momentum, Volatilidade, RR | `_trend_momentum_parameterized_candidate` |
| ALPHA002 | TREND_PULLBACK | Pullback em tendencia estabelecida pode continuar o movimento. | EMA, ADX, RSI, ATR, RR | `_trend_pullback_parameterized_candidate` |
| ALPHA003 | BREAKOUT_CONSOLIDATION | Consolidacao com momentum pode iniciar rompimento. | ATR, Momentum, Volatilidade, RR | `_breakout_consolidation_parameterized_candidate` |
| ALPHA004 | RSI_REVERSAL | RSI extremo pode antecipar reversao curta. | RSI, ATR, RR | `_rsi_reversal_parameterized_candidate` |
| ALPHA005 | DONCHIAN_BREAKOUT | Rompimento de canal Donchian pode gerar continuacao. | Donchian, Momentum, ATR, RR | `_donchian_breakout_parameterized_candidate` |
| ALPHA006 | ADX_TREND_STRENGTH | Tendencias com ADX alto tem maior chance de continuacao. | EMA, ADX, ATR, Momentum | `_adx_trend_strength_parameterized_candidate` |
| ALPHA007 | MACD_MOMENTUM_SHIFT | Mudanca de momentum via MACD pode antecipar continuacao ou reversao curta. | MACD, MACD Signal, EMA, ATR | `_macd_momentum_shift_parameterized_candidate` |
| ALPHA008 | BOLLINGER_VOLATILITY_EXPANSION | Compressao de Bollinger seguida de expansao gera rompimentos. | Bollinger, ATR, Momentum, Tick Volume | `_bollinger_volatility_expansion_parameterized_candidate` |
| ALPHA009 | ATR_VOLATILITY_REGIME | Certas estrategias funcionam melhor em regimes de ATR alto, medio ou baixo. | ATR real, ATR medio, Volatilidade, EMA | `_atr_volatility_regime_parameterized_candidate` |
| ALPHA010 | DONCHIAN_STRUCTURE_BREAKOUT | Rompimento de maxima/minima estrutural relevante gera continuacao. | Donchian, Swing High, Swing Low, ATR, Momentum | `_donchian_structure_breakout_parameterized_candidate` |
| ALPHA011 | PIVOT_REJECTION | Rejeicoes em pivos podem gerar reversao ou continuacao. | Pivot, RSI, ATR, Candle structure | `_pivot_rejection_parameterized_candidate` |
| ALPHA012 | VWAP_MEAN_REVERSION | Distancia excessiva da VWAP pode gerar reversao a media. | VWAP, Z-Score, RSI, ATR | `_vwap_mean_reversion_parameterized_candidate` |
| ALPHA013 | SUPPORT_RESISTANCE_REACTION | Preco perto de suporte/resistencia relevante altera a probabilidade de entrada. | Suporte, Resistencia, Swing, RSI, ATR | `_support_resistance_reaction_parameterized_candidate` |
| ALPHA014 | MULTI_TIMEFRAME_ALIGNMENT | Sinais alinhados em multiplos timeframes tem maior qualidade. | EMA, Trend, Momentum, Timeframe ativo | `_multi_timeframe_alignment_parameterized_candidate` |
| ALPHA015 | LIQUIDITY_SPREAD_FILTER | Sinais com spread baixo e tick volume suficiente tem execucao mais confiavel. | Spread, Spread medio, Tick Volume | `_liquidity_spread_filter_parameterized_candidate` |

## Saidas esperadas

Cada Alpha gera cenarios `DashboardMT5ScenarioViewModel` com:

- `alpha_id`
- `pair`
- `timeframe`
- `model`
- `parameters`
- `decision`
- `score`
- `lab_confidence`
- `status`
- `reason`

## Rastreabilidade obrigatoria em mudancas

Uma missao que altere Alpha deve informar:

- Alpha afetada;
- setup/modelo afetado;
- parametro adicionado/removido;
- efeito esperado em entrada;
- efeito esperado em saida/stop management;
- teste que prova preservacao do timeframe vencedor;
- impacto no Forex, MT5 Visual e Relatorio.
