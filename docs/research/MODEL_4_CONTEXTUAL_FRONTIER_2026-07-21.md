# Modelo 4 de Pesquisa - Fronteira Contextual MTF

Data: 2026-07-21

## Decisao executiva

O experimento foi salvo como `MODELO_4_PESQUISA`. O contrato operacional
`MODELO_4_ESPELHO_M1` nao foi substituido, recalculado nem alterado.

Foram avaliadas 19.065 combinacoes contextuais unicas. Nenhum dos oito pares
passou todos os gates. Portanto, o resultado correto e **M4-P nao operacional**.

Duas hipoteses justificam ampliacao de amostra:

1. USDCHF SELL, Momentum Acceleration em M30, confirmado por H1 alinhado e
   forca relativa curta;
2. AUDUSD BUY, Liquidity Reclaim em M30, com assimetria apenas compradora.

## O que ainda nao havia sido explorado

O estudo M3 procurava regras em cada timeframe separadamente. O M4-P adicionou:

- entrada na abertura do candle seguinte ao sinal fechado;
- contexto do ultimo H1 e H4 efetivamente concluidos;
- forca relativa sintetica das moedas a partir dos oito pares;
- parametros distintos para BUY, SELL ou ambos;
- regime de volatilidade por percentis moveis, e nao apenas ATR fixo;
- janela cronologica com descoberta, validacao, embargo e holdout.

O stop e o alvo permaneceram simples e fixos por ATR/RR. Assim, o experimento
mede a entrada contextual sem atribuir o resultado a uma saida sofisticada.

## Contrato temporal

| Janela | Percentual | Uso |
|---|---:|---|
| Descoberta | 0%-60% | Pesquisa e quatro blocos de estabilidade |
| Validacao | 60%-75% | Ranking pre-holdout |
| Embargo | 75%-80% | Separacao temporal sem selecao |
| Holdout | 80%-100% | Aberto somente para o vencedor congelado |

Custos: 1,5 bps por ida e volta; estresse de 2,5 bps.

## Resultado por par

| Par | Setup e contexto escolhidos | N | PF | Valid. N/PF | Holdout N/PF | PF estresse | ICT | Conclusao |
|---|---|---:|---:|---:|---:|---:|---:|---|
| AUDUSD | LIQUIDITY_RECLAIM, BUY_ONLY | 100 | 1,468 | 11 / 1,266 | 14 / 2,121 | 2,017 | 53,44 | Promissora; amostra insuficiente |
| EURJPY | SQUEEZE_RELEASE, forca lenta | 72 | 1,535 | 19 / 2,365 | 1 / infinito | infinito | 72,89 | Rejeitada; holdout de um trade nao prova nada |
| EURUSD | MOMENTUM_ACCELERATION, forca lenta, vol MID | 77 | 1,903 | 13 / 2,432 | 11 / 1,030 | 0,948 | 60,47 | Rejeitada fora da amostra |
| GBPUSD | MOMENTUM_ACCELERATION, H1/H4 nao opostos | 99 | 1,107 | 14 / 1,671 | 21 / 0,271 | 0,246 | 33,62 | Rejeitada fora da amostra |
| NZDUSD | TREND_PULLBACK, SELL_ONLY | 91 | 1,455 | 11 / 1,510 | 28 / 0,489 | 0,421 | 52,46 | Rejeitada fora da amostra |
| USDCAD | MOMENTUM_ACCELERATION, H4 nao oposto, forca lenta | 111 | 1,236 | 18 / 1,132 | 27 / 0,767 | 0,621 | 60,52 | Rejeitada fora da amostra |
| USDCHF | MOMENTUM_ACCELERATION, SELL_ONLY, H1 alinhado, forca curta >= 1,5 | 74 | 1,998 | 14 / 2,281 | 10 / 1,664 | 1,553 | 70,52 | Promissora; amostra insuficiente |
| USDJPY | MOMENTUM_ACCELERATION, SELL_ONLY, forca curta | 67 | 1,362 | 13 / 2,170 | 4 / 0,000 | 0,000 | 62,80 | Rejeitada fora da amostra |

## Maior achado metodologico

A busca curta de controle preservou o EURUSD M30 simples como aprovado. Quando
milhares de overlays foram liberados, o ranking pre-holdout escolheu uma regra
mais complexa que falhou no holdout. Isso demonstra, dentro dos proprios dados
do TraderIA, que mais filtros podem elevar o resultado de desenvolvimento e ao
mesmo tempo piorar a generalizacao.

Por esse motivo, o M4-P nao permite escolher um segundo colocado depois de ver
o holdout. O holdout foi consumido pelo experimento; trocar de candidato agora
seria data snooping.

## Fronteiras ainda abertas

Prioridade alta:

1. ampliar historico M30 para testar USDCHF e AUDUSD com pelo menos 120 trades;
2. implementar PBO/CSCV, Deflated Sharpe Ratio e Reality Check para controlar o
   efeito das milhares de tentativas;
3. usar custos historicos bid/ask, slippage, comissao, swap e rollover;
4. validar em outro periodo e, idealmente, outro broker;
5. avaliar risco agregado por moeda para evitar varias apostas equivalentes em
   USD ao mesmo tempo.

Potencial de Alpha ainda inexplorado:

- arbitragem estatistica de triangulos sinteticos, especialmente
  EURUSD x USDJPY x EURJPY;
- spreads relativos AUDUSD/NZDUSD e EURUSD/GBPUSD;
- surpresa macro e janelas de noticias, desde que a base seja versionada;
- microestrutura de ticks, spread e desequilibrio, inexistente no OHLC atual;
- deteccao de drift para suspender automaticamente uma Alpha que deixou de
  reproduzir seu regime historico.

## Guardrails

- `operational=false` no artefato.
- Nenhum consumo pelo indice runtime, Trade Plan, Robo Demo ou MT5.
- M4 operacional espelho do M1 permanece intacto.
- Candidata promissora nao equivale a candidata aprovada.
- O proximo teste deve usar dados novos; nao reutilizar o holdout atual para
  selecionar outra regra.

## Artefatos

- Motor: `research/alpha_suggested/model4_contextual_frontier.py`
- Resultado: `.traderia/research/modelo_4_pesquisa_contextual_mtf.json`
- Tabela: aba Lab, abaixo das tabelas M2 e M3.
