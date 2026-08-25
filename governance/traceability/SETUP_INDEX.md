# TraderIA Novo - Setup Index

`M24_CONTRACT=M24_SETUP_V19_20260823; SHA256=d918353322bc17fd17e1c7d0ba47272cf19431ef2c60d9cd1686829f2802c05f`

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
| BETA002_REVERSAL_SIGNAL | ALPHA016 | reversao do fluxo anterior | EMAs, momentum, volatilidade, ATR | Pesquisa existente |
| MULTI_CURRENCY_GRID_MEAN_REVERSION | ALPHA017 | reversao a media em extremo nao tendencial | Bollinger, Z-Score, RSI, `adx_max`, ATR | Somente Replay; sem grade operacional |
| M24_XAU_RSI50_BASKET | ALPHA024 | novos cruzamentos preco/SMA20 e RSI14/50, assincronos e mantidos; CONTINUATION Stop associada ao TP da INITIAL | distancia SMA/ATR informativa; INITIAL e REENTRY com TP Fibonacci 100%; CONTINUATION sem TP; lateralizacao reposiciona SL/TP da REENTRY aberta em RR 3:1 | RSI50 INITIAL apos carencia de 2 M5; CONTINUATION encerra ao atingir RSI70/30; sem inversao SMA; todos os papeis em 0,10 lote e sem volume novo na lateralizacao |
| M25_XAU_SOURCE_AGGREGATOR | ALPHA025 | copia plano executavel de M8, M10 ou M18-M22 | XAUUSD/M5, fonte, papel, ordem, entrada, SL e TP herdados | saida tecnica da fonte + Full Exit M25 em +US$1.000 |

O setup M24 e definido em `application/model24_setup_contract.py`. Textos da
interface, plano e documentos nao podem manter copias independentes da regra.
O M25 nao possui formula propria: seu contrato e a lista imutavel de fontes
ficam em `application/model25_multi_asset_rsi50_basket.py`.

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
