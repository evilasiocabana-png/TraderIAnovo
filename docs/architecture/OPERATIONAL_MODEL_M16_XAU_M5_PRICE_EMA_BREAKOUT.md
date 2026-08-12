# Modelo Operacional M16 - XAUUSD M5 Preco/EMA20

## Status

- Identidade: `MODELO_16_XAU_M5_PRICE_EMA20_BREAKOUT_TRAILING`
- Nome curto: `M16`
- Ambiente autorizado: MT5 Demo
- Ativo/timeframe: `XAUUSD/M5`
- Lab pesado no runtime: proibido
- Conta real: bloqueada

O antigo `MODELO_16_ALPHA012_VWAP_MEAN_REVERSION` continua aposentado e existe
somente para preservar o historico. Ele nao e reativado por este contrato.

## Entrada

O M16 copia do M15 somente a mecanica da ordem pendente e do risco. Sua regra
direcional e independente:

- preco atual acima da EMA20: preparar `BUY STOP` na maxima do candle M5
  anterior fechado + 0,01;
- preco atual abaixo da EMA20: preparar `SELL STOP` na minima do candle M5
  anterior fechado - 0,01;
- BUY nasce com SL na minima exata do candle anterior;
- SELL nasce com SL na maxima exata do candle anterior;
- se o extremo ja foi rompido, o modelo aguarda o proximo candle e nao persegue
  o preco a mercado;
- nao existe TP fixo (`tp = 0`).

## Saida

O Position Manager acompanha somente posicoes abertas identificadas como M16.
A cada novo candle M5 fechado:

- BUY usa a minima exata do candle fechado como candidato;
- SELL usa a maxima exata do candle fechado como candidato;
- o SL so e alterado se ficar mais protetivo e permanecer no lado valido do
  preco;
- o SL nunca recua;
- `EARLY_EXIT` e `FULL_EXIT` permanecem desligados.

## Fluxo E Auditoria

`model16_xau_m5_price_ema_breakout.py` calcula a regra pura. O
`DashboardService` consome o snapshot XAUUSD/M5 compartilhado e materializa o
Trade Plan. Robo Demo e provider enviam a ordem pendente com comentario
`TraderIA M16`. O Position Manager modifica apenas o SL e o Relatorio preserva
modelo, Alpha `ALPHAXAU16_PRICE_EMA20_BREAKOUT` e Beta
`BETAXAU16_PREVIOUS_CANDLE_TRAILING`.

O ciclo leve nao executa Lab ou backtest. A EMA20 e calculada sobre os candles
M5 ja coletados, e o estado compacto so e regravado quando seu conteudo muda.

## Rollback

Remover somente o ID canonico M16 da lista de modelos ativos impede novas
entradas sem apagar historico ou afetar M15. Posicoes M16 ja abertas continuam
identificadas para preservacao do SL.
