# Pesquisa de Stop e Alvo - Modelos 8, 9 e 10

Data: 2026-07-31
Status: pesquisa concluida, sem promocao automatica ao runtime

## Contratos avaliados

| Modelo | Direcao | Entrada | Regra |
| --- | --- | --- | --- |
| M8 | H1 | M5 | Trend Pullback identico ao M2 |
| M9 | M15 | M1 | Trend Pullback identico ao M2 |
| M10 | D1 | M15 | Trend Pullback identico ao M2 |

Foram usados 5.000 candles de entrada por par, com EMA 20/50 no contexto,
EMA 9/21 na entrada, ADX14 acima de 20, pullback na faixa das medias e candle
fechado de confirmacao. O M10 formou D1 a partir do H1 local, pois o banco
historico nao possuia uma serie D1 separada.

## Grade testada

- Stop ATR: 0,75; 1,00; 1,25; 1,50; 2,00; 2,50.
- Alvo: 1,00R; 1,50R; 2,00R; 2,50R; 3,00R.
- Total: 30 combinacoes por par e modelo.
- Entrada: abertura seguinte ao candle fechado de confirmacao.
- Colisao de stop e alvo no mesmo candle: stop primeiro.
- Sobreposicao: uma posicao por modelo e par.
- Custos: resultado bruto, sem spread, comissao ou swap.

## Resultado agregado

| Modelo | Melhor stop unico | Melhor alvo unico | Trades | Resultado | PF |
| --- | ---: | ---: | ---: | ---: | ---: |
| M8 | 2,00 ATR | 1,00R | 726 | -34,00R | 0,91 |
| M9 | 2,00 ATR | 1,00R | 407 | -37,00R | 0,83 |
| M10 | 2,50 ATR | 2,50R | 414 | -18,50R | 0,94 |

Conclusao: nenhuma combinacao unica de stop e alvo ficou positiva quando
aplicada aos oito pares de um mesmo modelo. Portanto, o estudo nao autoriza
substituir os parametros operacionais atuais por um vencedor global.

## Melhores combinacoes individuais

### M8

| Par | Stop | Alvo | Resultado | PF |
| --- | ---: | ---: | ---: | ---: |
| AUDUSD | 0,75 ATR | 1,00R | -3,00R | 0,96 |
| EURJPY | 2,00 ATR | 1,00R | -2,00R | 0,95 |
| EURUSD | 2,00 ATR | 1,00R | -13,00R | 0,72 |
| GBPUSD | 1,25 ATR | 1,00R | 6,00R | 1,12 |
| NZDUSD | 1,50 ATR | 1,50R | 10,50R | 1,18 |
| USDCAD | 0,75 ATR | 2,50R | 0,00R | 1,00 |
| USDCHF | 2,50 ATR | 3,00R | 2,00R | 1,06 |
| USDJPY | 1,50 ATR | 1,00R | -3,00R | 0,94 |

### M9

| Par | Stop | Alvo | Resultado | PF |
| --- | ---: | ---: | ---: | ---: |
| AUDUSD | 0,75 ATR | 1,00R | -3,00R | 0,90 |
| EURJPY | 0,75 ATR | 3,00R | -7,00R | 0,63 |
| EURUSD | 0,75 ATR | 1,00R | -14,00R | 0,50 |
| GBPUSD | 0,75 ATR | 2,00R | 11,00R | 1,41 |
| NZDUSD | 1,50 ATR | 1,50R | 0,00R | 1,00 |
| USDCAD | 0,75 ATR | 2,00R | 3,00R | 1,18 |
| USDCHF | 2,50 ATR | 1,50R | -4,00R | 0,86 |
| USDJPY | 0,75 ATR | 2,50R | 2,50R | 1,25 |

### M10

| Par | Stop | Alvo | Resultado | PF |
| --- | ---: | ---: | ---: | ---: |
| AUDUSD | 2,00 ATR | 2,00R | -6,00R | 0,86 |
| EURJPY | 2,50 ATR | 2,50R | 6,00R | 1,18 |
| EURUSD | 0,75 ATR | 1,50R | 23,50R | 1,32 |
| GBPUSD | 2,50 ATR | 3,00R | -7,00R | 0,79 |
| NZDUSD | 1,50 ATR | 3,00R | 11,00R | 1,22 |
| USDCAD | 2,00 ATR | 3,00R | 10,00R | 1,21 |
| USDCHF | 2,50 ATR | 2,50R | 6,00R | 1,18 |
| USDJPY | 2,00 ATR | 1,50R | 6,50R | 1,13 |

## Rastreabilidade

- Motor: `research/alpha_suggested/model8_10_exit_research.py`.
- Banco: `.traderia/traderia_mt5_history.sqlite`.
- Artefato Replay: `.traderia/research/model8_10_stop_target_research.json`.
- Interface: Replay -> Pesquisa de stop e alvo por modelo.
- O artefato informa SHA-256 do banco, periodo, ranking completo e metricas do
  vencedor de cada par, sem carregar livros de operacoes que a tela nao usa.

## Guardrail

O resultado permanece `RESEARCH_ONLY_NOT_PROMOTED`. Mudar stop ou alvo do M8,
M9 ou M10 exige decisao explicita posterior, teste fora da amostra e avaliacao
com custos reais.
