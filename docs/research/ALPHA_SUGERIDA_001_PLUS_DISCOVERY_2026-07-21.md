# Pesquisa Alpha Sugerida 1+

Data: 2026-07-21

## Decisao

O identificador `ALPHA_SUGERIDA_001_PLUS` permanece reservado, mas nenhuma
Alpha foi promovida com esse nome. Nenhuma candidata inedita atingiu classe A
no holdout cronologico. O Modelo 2 nao foi alterado e nenhuma ordem foi
autorizada por esta pesquisa.

## Base

- fonte: leitura MT5 Pepperstone Demo, somente leitura;
- timeframe: H1;
- pares: EURUSD, GBPUSD, USDCHF, USDJPY, EURJPY, AUDUSD, NZDUSD e USDCAD;
- amostra ampliada: 20.000 candles por par, 160.000 candles no total;
- periodo aproximado: maio de 2023 a julho de 2026;
- divisao congelada: 60% treino, 20% validacao e 20% holdout;
- o holdout foi consultado somente depois do ranking por treino e validacao.

Os dados ampliados e resultados detalhados ficam somente no runtime local:

```text
.traderia/research/alpha_sugerida_h1_20000_snapshot.json
.traderia/research/alpha_sugerida_1_plus_discovery.json
.traderia/research/alpha_sugerida_1_plus_global_h1_20000.json
.traderia/research/alpha_sugerida_1_plus_pairwise_h1_20000.json
.traderia/research/alpha_sugerida_1_plus_session_regime_h1_20000.json
```

## Familias novas pesquisadas

1. `COMPRESSION_RELEASE`: compressao ATR seguida de rompimento e expansao.
2. `TREND_IMPULSE`: impulso alinhado a medias, ADX, momentum e volume.
3. `PULLBACK_REJECTION`: rejeicao de pullback com candle, RSI e tendencia.
4. `LIQUIDITY_SWEEP_RECLAIM`: varredura de maxima/minima com retorno a estrutura.

Na ultima passagem foram adicionados filtros de sessao Forex, dia da semana,
eficiencia do movimento, inclinacao da EMA 50 e regime ATR.

## Resultados

### Base original de 5.000 candles

A melhor candidata global foi `TREND_IMPULSE`, mas caiu de ICT 52,56 no treino
para 32,84 no holdout. Foi rejeitada.

Na calibracao por par, o melhor resultado estavel foi USDCAD H1 com PF total
1,732 e ICT 72,42, classe B. Como o objetivo era superar B, ela nao foi
promovida.

Essa configuracao B foi reexecutada sem alteracao nos 20.000 candles. O trecho
mais recente continuou forte, com 120 trades, PF 1,893 e ICT 75,33, mas a
amostra completa retornou 578 trades, PF 1,092 e ICT 51,19. O resultado dos
5.000 candles era dependente do regime recente e nao caracteriza uma vantagem
historica persistente.

### Base ampliada de 20.000 candles

A tentativa de regra global voltou a perder vantagem no holdout. A calibracao
por par e a busca com sessao/regime tambem nao produziram ICT A.

O padrao mais estavel na ultima busca ocorreu em USDCAD H1 durante a
sobreposicao Londres/Nova York, usando impulso de tendencia e inclinacao
alinhada. O PF permaneceu proximo de 1,40 em treino, validacao, holdout e amostra
completa, mas o ICT total foi 45,92. O baixo acerto de uma estrutura RR 2,5 e o
componente de recovery atual zerado impedem certificacao alta.

## Interpretacao

Forcar uma nota A no mesmo historico exigiria escolher limites depois de olhar
o holdout ou reduzir o alvo apenas para elevar a taxa de acerto. Ambos os
caminhos produziriam sobreajuste ou uma nota artificial, nao uma Alpha melhor.

O ICT atual tambem favorece estrategias de alto acerto e penaliza estruturas de
RR alto. Alem disso, o componente de recovery usa retorno medio por trade
dividido pelo drawdown acumulado e ficou zerado nas pesquisas observadas. O ICT
deve permanecer informativo ate essa escala ser auditada separadamente.

## Proximo contrato

- M1 continua consumindo somente as Alphas oficiais do Lab atual.
- Novas Alphas sugeridas permanecem em Research e Replay.
- M2 pode ser o destino operacional dessas Alphas depois de aprovadas, sem
  misturar o contrato do M1.
- A promocao exige, no minimo, ICT A no holdout, filtros minimos aprovados,
  estresse de custos, walk-forward e validacao Demo futura.
- Ate essa aprovacao, `ALPHA_SUGERIDA_001_PLUS` nao aparece como Alpha ativa e
  nao envia ordens.
