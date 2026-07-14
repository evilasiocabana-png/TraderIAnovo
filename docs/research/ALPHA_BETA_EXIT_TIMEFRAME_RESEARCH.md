# Pesquisa Alpha x Beta de Saida por Timeframe

Gerado em: `2026-07-13T17:30:33.850527+00:00`
Candles solicitados por par/timeframe: `5000`

## Mapeamento de timeframe

- Entrada `M1` -> Saida `M1`
- Entrada `M5` -> Saida `M1`
- Entrada `M15` -> Saida `M1`
- Entrada `M30` -> Saida `M5`
- Entrada `H1` -> Saida `M5`

## Catalogo BETA003+

- `BETA003` `FIXED_RISK_TARGET`: HOLD - Mantem stop inicial e alvo RR; base de comparacao.
- `BETA004` `BREAK_EVEN_AFTER_1R`: PROTECT - Move para break-even somente depois de 1R.
- `BETA005` `ATR_TRAILING_AFTER_1R`: PROTECT - Aciona trailing por ATR depois de 1R; nunca afasta stop.
- `BETA006` `STRUCTURE_TRAILING_AFTER_1R`: PROTECT - Protege por estrutura/swing depois de 1R.
- `BETA007` `MOMENTUM_DECAY_FULL_EXIT`: FULL_EXIT - Fecha quando momentum curto vira contra a posicao.
- `BETA008` `CHANDELIER_ATR_EXIT`: PROTECT - Trailing tipo chandelier baseado em maxima/minima e ATR.

## Cobertura de candles

- `AUDUSD H1`: 5000 candles, 2025-09-22T09:00:00+00:00 -> 2026-07-13T20:00:00+00:00
- `AUDUSD M1`: 5000 candles, 2026-07-08T08:58:00+00:00 -> 2026-07-13T20:30:00+00:00
- `AUDUSD M15`: 5000 candles, 2026-04-30T18:45:00+00:00 -> 2026-07-13T20:30:00+00:00
- `AUDUSD M30`: 5000 candles, 2026-02-17T17:00:00+00:00 -> 2026-07-13T20:30:00+00:00
- `AUDUSD M5`: 5000 candles, 2026-06-18T11:20:00+00:00 -> 2026-07-13T20:30:00+00:00
- `EURJPY M30`: 5000 candles, 2026-02-17T16:00:00+00:00 -> 2026-07-13T20:30:00+00:00
- `EURJPY M5`: 5000 candles, 2026-06-18T11:25:00+00:00 -> 2026-07-13T20:30:00+00:00
- `EURUSD H1`: 5000 candles, 2025-09-22T09:00:00+00:00 -> 2026-07-13T20:00:00+00:00
- `EURUSD M1`: 5000 candles, 2026-07-08T09:00:00+00:00 -> 2026-07-13T20:30:00+00:00
- `EURUSD M15`: 5000 candles, 2026-04-30T18:45:00+00:00 -> 2026-07-13T20:30:00+00:00
- `EURUSD M30`: 5000 candles, 2026-02-17T17:00:00+00:00 -> 2026-07-13T20:30:00+00:00
- `EURUSD M5`: 5000 candles, 2026-06-18T11:30:00+00:00 -> 2026-07-13T20:30:00+00:00
- `NZDUSD H1`: 5000 candles, 2025-09-22T09:00:00+00:00 -> 2026-07-13T20:00:00+00:00
- `NZDUSD M5`: 5000 candles, 2026-06-18T10:10:00+00:00 -> 2026-07-13T20:30:00+00:00
- `USDCAD M1`: 5000 candles, 2026-07-08T09:01:00+00:00 -> 2026-07-13T20:30:00+00:00
- `USDCAD M30`: 5000 candles, 2026-02-17T17:00:00+00:00 -> 2026-07-13T20:30:00+00:00
- `USDCAD M5`: 5000 candles, 2026-06-18T11:15:00+00:00 -> 2026-07-13T20:30:00+00:00
- `USDCHF H1`: 5000 candles, 2025-09-22T08:00:00+00:00 -> 2026-07-13T20:00:00+00:00
- `USDCHF M30`: 5000 candles, 2026-02-17T14:30:00+00:00 -> 2026-07-13T20:30:00+00:00
- `USDCHF M5`: 5000 candles, 2026-06-18T09:10:00+00:00 -> 2026-07-13T20:30:00+00:00
- `USDJPY M1`: 5000 candles, 2026-07-08T08:41:00+00:00 -> 2026-07-13T20:30:00+00:00
- `USDJPY M15`: 5000 candles, 2026-04-30T17:15:00+00:00 -> 2026-07-13T20:30:00+00:00

## Recomendacao por Alpha

## Leitura consolidada para decisao

Esta consolidacao cruza duas fontes:

- Simulacao dedicada com candles MT5: usa 5000 candles por par/timeframe e testa a saida em timeframe menor.
- Ranking pesado atual do Lab: usado como fallback quando a simulacao dedicada nao encontrou amostra suficiente para aquela Alpha.

| Alpha | Modelo | Recomendacao direta 5000 candles | Fallback pelo Lab pesado | Observacao |
| --- | --- | --- | --- | --- |
| ALPHA001 | TREND_MOMENTUM | BETA003 FIXED_RISK_TARGET, H1 -> M5 | BETA005 ATR_TRAILING_AFTER_1R | Simulacao favoreceu deixar o trade buscar RR; trailing fica como plano secundario. |
| ALPHA002 | TREND_PULLBACK | Sem amostra suficiente | BETA005 ATR_TRAILING_AFTER_1R | Precisa nova rodada com mais sinais antes de ativar beta dedicado. |
| ALPHA003 | BREAKOUT_CONSOLIDATION | Sem amostra suficiente | Sem aprovado no snapshot atual | Nao promover para operacao sem nova calibracao. |
| ALPHA004 | RSI_REVERSAL | Sem amostra suficiente | Sem aprovado no snapshot atual | Nao promover para operacao sem nova calibracao. |
| ALPHA005 | DONCHIAN_BREAKOUT | Sem amostra suficiente | BETA005 ATR_TRAILING_AFTER_1R | Rompimento favorece protecao por ATR apos andar. |
| ALPHA006 | ADX_TREND_STRENGTH | BETA003 FIXED_RISK_TARGET, M15 -> M1 | BETA004 BREAK_EVEN_AFTER_1R | Simulacao favoreceu alvo/stop fixo; break-even fica defensivo. |
| ALPHA007 | MACD_MOMENTUM_SHIFT | Sem amostra suficiente | BETA005 ATR_TRAILING_AFTER_1R | Momentum favorece trailing, mas precisa validacao operacional. |
| ALPHA008 | BOLLINGER_VOLATILITY_EXPANSION | BETA003 FIXED_RISK_TARGET, H1 -> M5 | Sem aprovado no snapshot atual | Nao ligar sem confirmar no Lab oficial. |
| ALPHA009 | ATR_VOLATILITY_REGIME | Sem amostra suficiente | BETA005 ATR_TRAILING_AFTER_1R | Coerente com regime de volatilidade. |
| ALPHA010 | DONCHIAN_STRUCTURE_BREAKOUT | Sem amostra suficiente | Sem aprovado no snapshot atual | Nao promover para operacao sem nova calibracao. |
| ALPHA011 | PIVOT_REJECTION | Sem amostra suficiente | BETA005 ATR_TRAILING_AFTER_1R | Fallback fraco; validar antes de ativar. |
| ALPHA012 | VWAP_MEAN_REVERSION | Sem amostra suficiente | BETA005 ATR_TRAILING_AFTER_1R | Fallback fraco; validar antes de ativar. |
| ALPHA013 | SUPPORT_RESISTANCE_REACTION | Sem amostra suficiente | BETA004 BREAK_EVEN_AFTER_1R | Reacao em zona pede protecao rapida, nao full exit. |
| ALPHA014 | MULTI_TIMEFRAME_ALIGNMENT | BETA007 MOMENTUM_DECAY_FULL_EXIT, M1 -> M1 | BETA004 BREAK_EVEN_AFTER_1R | Unica amostra em que full exit apareceu melhor; usar apenas como pesquisa, nao runtime direto. |
| ALPHA015 | LIQUIDITY_SPREAD_FILTER | BETA003 FIXED_RISK_TARGET, H1 -> M5 | Sem aprovado no snapshot atual | Preservar plano inicial foi superior na simulacao. |
| ALPHA016 | BETA002_REVERSAL_SIGNAL | BETA003 FIXED_RISK_TARGET, H1 -> M5, resultado negativo | BETA005 ATR_TRAILING_AFTER_1R | Alpha 016 ainda nao deve ser promovida; o teste ficou negativo. |

Decisao conservadora desta rodada: criar BETA003+ como catalogo de pesquisa, mas nao ativar operacionalmente nenhuma BETA nova sem uma segunda calibracao oficial do Lab.

### ALPHA001 - TREND_MOMENTUM

Recomendado: `BETA003 FIXED_RISK_TARGET` | Par teste dominante `EURUSD` | Entrada `H1` -> Saida `M5` | trades `14` | win `0.7143` | avg R `1.4318` | PF `6.0115` | DD `1.0`

| Beta | Par | Entrada | Saida | Trades | Win | Avg R | PF | DD | Score |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BETA003 FIXED_RISK_TARGET | EURUSD | H1 | M5 | 14 | 0.7143 | 1.4318 | 6.0115 | 1.0 | 1.7776 |
| BETA004 BREAK_EVEN_AFTER_1R | EURUSD | H1 | M5 | 14 | 0.7143 | 1.4318 | 6.0115 | 1.0 | 1.7776 |
| BETA008 CHANDELIER_ATR_EXIT | EURUSD | H1 | M5 | 14 | 0.7143 | 1.4221 | 5.9773 | 1.0 | 1.7678 |
| BETA006 STRUCTURE_TRAILING_AFTER_1R | EURUSD | H1 | M5 | 14 | 0.7143 | 1.4197 | 5.9689 | 1.0 | 1.7654 |
| BETA005 ATR_TRAILING_AFTER_1R | EURUSD | H1 | M5 | 14 | 0.7143 | 1.409 | 5.9316 | 1.0 | 1.7548 |

### ALPHA002 - TREND_PULLBACK

Sem amostra suficiente para recomendacao.

### ALPHA003 - BREAKOUT_CONSOLIDATION

Sem amostra suficiente para recomendacao.

### ALPHA004 - RSI_REVERSAL

Sem amostra suficiente para recomendacao.

### ALPHA005 - DONCHIAN_BREAKOUT

Sem amostra suficiente para recomendacao.

### ALPHA006 - ADX_TREND_STRENGTH

Recomendado: `BETA003 FIXED_RISK_TARGET` | Par teste dominante `EURUSD` | Entrada `M15` -> Saida `M1` | trades `8` | win `0.625` | avg R `0.875` | PF `3.3333` | DD `2.0`

| Beta | Par | Entrada | Saida | Trades | Win | Avg R | PF | DD | Score |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BETA003 FIXED_RISK_TARGET | EURUSD | M15 | M1 | 8 | 0.625 | 0.875 | 3.3333 | 2.0 | 1.07 |
| BETA004 BREAK_EVEN_AFTER_1R | EURUSD | M15 | M1 | 8 | 0.625 | 0.875 | 3.3333 | 2.0 | 1.07 |
| BETA006 STRUCTURE_TRAILING_AFTER_1R | EURUSD | M15 | M1 | 8 | 0.625 | 0.875 | 3.3333 | 2.0 | 1.07 |
| BETA007 MOMENTUM_DECAY_FULL_EXIT | EURUSD | M15 | M1 | 8 | 0.625 | 0.875 | 3.3333 | 2.0 | 1.07 |
| BETA008 CHANDELIER_ATR_EXIT | EURUSD | M15 | M1 | 8 | 0.625 | 0.7393 | 2.9715 | 2.0 | 0.9126 |

### ALPHA007 - MACD_MOMENTUM_SHIFT

Sem amostra suficiente para recomendacao.

### ALPHA008 - BOLLINGER_VOLATILITY_EXPANSION

Recomendado: `BETA003 FIXED_RISK_TARGET` | Par teste dominante `EURUSD` | Entrada `H1` -> Saida `M5` | trades `8` | win `0.75` | avg R `0.7054` | PF `3.8216` | DD `1.0`

| Beta | Par | Entrada | Saida | Trades | Win | Avg R | PF | DD | Score |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BETA003 FIXED_RISK_TARGET | EURUSD | H1 | M5 | 8 | 0.75 | 0.7054 | 3.8216 | 1.0 | 0.9847 |
| BETA004 BREAK_EVEN_AFTER_1R | EURUSD | H1 | M5 | 8 | 0.75 | 0.7054 | 3.8216 | 1.0 | 0.9847 |
| BETA005 ATR_TRAILING_AFTER_1R | EURUSD | H1 | M5 | 8 | 0.75 | 0.7054 | 3.8216 | 1.0 | 0.9847 |
| BETA006 STRUCTURE_TRAILING_AFTER_1R | EURUSD | H1 | M5 | 8 | 0.75 | 0.7054 | 3.8216 | 1.0 | 0.9847 |
| BETA007 MOMENTUM_DECAY_FULL_EXIT | EURUSD | H1 | M5 | 8 | 0.75 | 0.7054 | 3.8216 | 1.0 | 0.9847 |

### ALPHA009 - ATR_VOLATILITY_REGIME

Sem amostra suficiente para recomendacao.

### ALPHA010 - DONCHIAN_STRUCTURE_BREAKOUT

Sem amostra suficiente para recomendacao.

### ALPHA011 - PIVOT_REJECTION

Sem amostra suficiente para recomendacao.

### ALPHA012 - VWAP_MEAN_REVERSION

Sem amostra suficiente para recomendacao.

### ALPHA013 - SUPPORT_RESISTANCE_REACTION

Sem amostra suficiente para recomendacao.

### ALPHA014 - MULTI_TIMEFRAME_ALIGNMENT

Recomendado: `BETA007 MOMENTUM_DECAY_FULL_EXIT` | Par teste dominante `USDCAD` | Entrada `M1` -> Saida `M1` | trades `15` | win `0.4` | avg R `0.2797` | PF `1.7088` | DD `2.9754`

| Beta | Par | Entrada | Saida | Trades | Win | Avg R | PF | DD | Score |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BETA007 MOMENTUM_DECAY_FULL_EXIT | USDCAD | M1 | M1 | 15 | 0.4 | 0.2797 | 1.7088 | 2.9754 | 0.3113 |
| BETA003 FIXED_RISK_TARGET | USDCAD | M1 | M1 | 15 | 0.4 | 0.2075 | 1.404 | 3.1849 | 0.2123 |
| BETA004 BREAK_EVEN_AFTER_1R | USDCAD | M1 | M1 | 15 | 0.3333 | 0.2198 | 1.4918 | 4.0 | 0.1893 |
| BETA008 CHANDELIER_ATR_EXIT | USDCAD | M1 | M1 | 15 | 0.4 | 0.1578 | 1.3496 | 3.9221 | 0.1299 |
| BETA006 STRUCTURE_TRAILING_AFTER_1R | USDCAD | M1 | M1 | 15 | 0.3333 | 0.1631 | 1.324 | 4.3493 | 0.1086 |

### ALPHA015 - LIQUIDITY_SPREAD_FILTER

Recomendado: `BETA003 FIXED_RISK_TARGET` | Par teste dominante `EURUSD` | Entrada `H1` -> Saida `M5` | trades `8` | win `0.75` | avg R `0.9436` | PF `4.7743` | DD `1.0`

| Beta | Par | Entrada | Saida | Trades | Win | Avg R | PF | DD | Score |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BETA003 FIXED_RISK_TARGET | EURUSD | H1 | M5 | 8 | 0.75 | 0.9436 | 4.7743 | 1.0 | 1.28 |
| BETA004 BREAK_EVEN_AFTER_1R | EURUSD | H1 | M5 | 8 | 0.75 | 0.9436 | 4.7743 | 1.0 | 1.28 |
| BETA006 STRUCTURE_TRAILING_AFTER_1R | EURUSD | H1 | M5 | 8 | 0.75 | 0.9346 | 4.7385 | 1.0 | 1.2689 |
| BETA008 CHANDELIER_ATR_EXIT | EURUSD | H1 | M5 | 8 | 0.75 | 0.9177 | 4.671 | 1.0 | 1.248 |
| BETA005 ATR_TRAILING_AFTER_1R | EURUSD | H1 | M5 | 8 | 0.75 | 0.9148 | 4.659 | 1.0 | 1.2443 |

### ALPHA016 - BETA002_REVERSAL_SIGNAL

Recomendado: `BETA003 FIXED_RISK_TARGET` | Par teste dominante `NZDUSD` | Entrada `H1` -> Saida `M5` | trades `11` | win `0.3636` | avg R `-0.0876` | PF `0.8624` | DD `7.0`

| Beta | Par | Entrada | Saida | Trades | Win | Avg R | PF | DD | Score |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BETA003 FIXED_RISK_TARGET | NZDUSD | H1 | M5 | 11 | 0.3636 | -0.0876 | 0.8624 | 7.0 | -0.2722 |
| BETA004 BREAK_EVEN_AFTER_1R | NZDUSD | H1 | M5 | 11 | 0.3636 | -0.0876 | 0.8624 | 7.0 | -0.2722 |
| BETA006 STRUCTURE_TRAILING_AFTER_1R | NZDUSD | H1 | M5 | 11 | 0.3636 | -0.131 | 0.7941 | 7.0 | -0.3197 |
| BETA005 ATR_TRAILING_AFTER_1R | NZDUSD | H1 | M5 | 11 | 0.3636 | -0.1357 | 0.7867 | 7.0 | -0.3249 |
| BETA008 CHANDELIER_ATR_EXIT | NZDUSD | H1 | M5 | 11 | 0.3636 | -0.145 | 0.7722 | 7.0 | -0.335 |

### EVENT_POST_ROLLOVER_DAILY_OPEN - POST_ROLLOVER_DAILY_OPEN

Sem amostra suficiente para recomendacao.

## Observacoes

- Esta pesquisa nao ativa nenhuma BETA no runtime.
- O teste usa candles reais lidos do MT5 e uma simulacao local de saida por R.
- A entrada simulada respeita a familia da Alpha, mas nao substitui a validacao pesada oficial do Research Lab.
- Para virar operacional, a BETA escolhida deve entrar no catalogo oficial e depois passar por backtest do Lab.
