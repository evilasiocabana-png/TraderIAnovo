# TraderIA Novo - Setup Index

Indice dos setups/modelos operacionais pesquisados pelo Lab e consumidos pelo
Forex MT5.

## Fonte executavel

```text
application/dashboard_service.py
  _mt5_scenario_parameter_grid()
  _mt5_grid_parameters()
  _mt5_research_scenarios_for_row()
  _mt5_scenario_for_parameters()

research/mt5_research_trade_plan.py
  MT5ResearchTradePlanEngine
```

## Setup operacional

Um setup operacional e composto por:

```text
Alpha + modelo + par + timeframe + parametros de entrada
+ decision + stop_management + RR + evidencia historica
```

## Setups conhecidos

| Setup/modelo | Alpha principal | Entrada | Parametros comuns | Saida |
| --- | --- | --- | --- | --- |
| TREND_MOMENTUM | ALPHA001 | continuacao BUY/SELL por EMA/momentum | `ema_curta`, `ema_longa`, `momentum_threshold`, `volatility_threshold`, `atr_stop_factor`, `rr` | Lab escolhe `stop_management` |
| TREND_PULLBACK | ALPHA002 | pullback em tendencia | `pullback_tolerance`, `adx_min`, EMAs, RSI, ATR, RR | Lab escolhe `stop_management` |
| BREAKOUT_CONSOLIDATION | ALPHA003 | rompimento apos consolidacao | `momentum_threshold`, `volatility_threshold`, ATR, RR | Lab escolhe `stop_management` |
| RSI_REVERSAL | ALPHA004 | reversao por RSI extremo | `rsi_sobrevenda`, `rsi_sobrecompra`, ATR, RR | Lab escolhe `stop_management` |
| DONCHIAN_BREAKOUT | ALPHA005 | rompimento de canal | `donchian_period`, `breakout_buffer`, momentum, ATR, RR | Lab escolhe `stop_management` |
| ADX_TREND_STRENGTH | ALPHA006 | tendencia forte por ADX/EMA/momentum | `adx_min`, EMAs, momentum, ATR | Lab escolhe `stop_management` |
| MACD_MOMENTUM_SHIFT | ALPHA007 | mudanca de momentum MACD | MACD, sinal, EMAs, ATR, RR | Lab escolhe `stop_management` |
| BOLLINGER_VOLATILITY_EXPANSION | ALPHA008 | expansao apos compressao | `bollinger_width_threshold`, momentum, volume, ATR, RR | Lab escolhe `stop_management` |
| ATR_VOLATILITY_REGIME | ALPHA009 | regime de volatilidade | `atr_regime`, EMAs, ATR | Lab escolhe `stop_management` |
| DONCHIAN_STRUCTURE_BREAKOUT | ALPHA010 | rompimento estrutural | `donchian_period`, swing, momentum, ATR, RR | Lab escolhe `stop_management` |
| PIVOT_REJECTION | ALPHA011 | rejeicao em pivot | pivot, RSI, ATR | Lab escolhe `stop_management` |
| VWAP_MEAN_REVERSION | ALPHA012 | reversao a VWAP | `z_threshold`, VWAP, RSI, ATR | Lab escolhe `stop_management` |
| SUPPORT_RESISTANCE_REACTION | ALPHA013 | reacao em suporte/resistencia | suporte, resistencia, swing, RSI, ATR | Lab escolhe `stop_management` |
| MULTI_TIMEFRAME_ALIGNMENT | ALPHA014 | alinhamento do timeframe ativo | EMAs, trend, momentum | Lab escolhe `stop_management` |
| LIQUIDITY_SPREAD_FILTER | ALPHA015 | filtro de liquidez/spread | spread, spread medio, tick volume | Lab escolhe `stop_management` |

## Stop management suportado

| Politica | Origem | Parametros rastreaveis |
| --- | --- | --- |
| FIXED_STOP | Lab/TradePlan | nenhum |
| ATR_TRAILING_STOP | Lab/TradePlan | `atr_trailing_factor`, `atr_trailing_activation_rr` |
| BREAK_EVEN | Lab/TradePlan | `break_even_trigger_rr`, `break_even_offset_pips` |
| CHANDELIER_EXIT | Lab/TradePlan | `chandelier_period`, `chandelier_atr_factor` |
| PARABOLIC_SAR | Lab/TradePlan | `sar_step`, `sar_max_step` |
| DONCHIAN_CHANNEL_STOP | Lab/TradePlan | `donchian_stop_period` |
| MOVING_AVERAGE_EXIT | Lab/TradePlan | `exit_ma_period`, `exit_ma_type` |
| TIME_STOP | Lab/TradePlan | `max_bars_in_trade`, `max_minutes_in_trade` |
| VOLATILITY_STOP | Lab/TradePlan | `volatility_window`, `volatility_multiplier` |

## Regra de preservacao

Nao substituir o stop management escolhido pelo Lab por `FIXED_STOP` por
compatibilidade visual. Se algum consumidor nao suportar a politica, a missao
deve declarar fallback e atualizar contratos/testes.
