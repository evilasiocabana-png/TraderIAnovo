# Alpha Sugerida 002+ - Pesquisa Individual do Modelo 3

Data: 2026-07-21

## Objetivo

Procurar, para cada par Forex, um cenario novo e independente com melhor
robustez historica do que uma configuracao global unica. O resultado foi salvo
no namespace de pesquisa do `MODELO_3`, sem substituir o M3 operacional e sem
autorizar ordens.

## Universo Avaliado

- Pares: AUDUSD, EURJPY, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF e USDJPY.
- Timeframes: H1, M30 e H4.
- Historico: 20.000 candles por par em H1 e M30; 10.000 por par em H4.
- Total lido: 400.000 candles.
- Busca: 6.000 combinacoes por par e timeframe, totalizando 144.000 candidatos.
- Custo liquido padronizado: 1,5 bps por ida e volta.
- Estresse de custo: 2,5 bps por ida e volta.

O custo e uma premissa uniforme de pesquisa. Ele nao reproduz o spread
historico dinamico exato da Pepperstone.

## Contrato Cronologico

Cada serie foi ordenada no tempo e dividida em:

1. 80% para desenvolvimento;
2. quatro blocos cronologicos dentro do desenvolvimento para estabilidade;
3. 20% finais mantidos como holdout;
4. abertura do holdout somente depois de congelar um vencedor por par e TF.

Depois dos tres estudos independentes, o seletor escolheu o melhor resultado
observado por par. Certificacao teve prioridade; em seguida foi considerado o
menor PF entre amostra total, holdout e holdout estressado, depois ICT, tamanho
da amostra e drawdown.

## Resultado Consolidado

| Par | TF | Familia | Trades | PF liquido | PF holdout | PF estresse | Retorno | DD | ICT | Situacao M3 |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| AUDUSD | M30 | LIQUIDITY_RECLAIM | 112 | 1,379 | 1,488 | 1,402 | 7,47% | 1,98% | 53,73 D | PROMISSORA_PARA_REPLAY |
| EURJPY | M30 | SQUEEZE_RELEASE | 104 | 1,533 | 2,066 | 1,888 | 7,52% | 2,61% | 54,13 D | PROMISSORA_PARA_REPLAY |
| EURUSD | M30 | SQUEEZE_RELEASE | 138 | 1,433 | 1,545 | 1,366 | 5,09% | 1,43% | 70,80 B | APROVADA_B_PARA_REPLAY |
| GBPUSD | M30 | STRUCTURE_CONTINUATION | 101 | 1,353 | 1,202 | 1,014 | 1,97% | 0,61% | 67,26 C | PROMISSORA_PARA_REPLAY |
| NZDUSD | M30 | MOMENTUM_ACCELERATION | 103 | 1,810 | 2,203 | 2,103 | 16,01% | 1,90% | 68,81 C | PROMISSORA_PARA_REPLAY |
| USDCAD | H1 | BREAKOUT_EXPANSION | 169 | 1,478 | 1,564 | 1,433 | 9,05% | 1,99% | 54,73 D | PROMISSORA_PARA_REPLAY |
| USDCHF | H4 | BREAKOUT_EXPANSION | 109 | 1,379 | 0,934 | 0,906 | 10,01% | 3,34% | 60,48 D | REJEITADA_NAO_ATIVA |
| USDJPY | H1 | MOMENTUM_ACCELERATION | 137 | 1,497 | 0,783 | 0,708 | 7,54% | 1,44% | 73,58 B | REJEITADA_NAO_ATIVA |

## Leitura Correta

- `EURUSD M30` foi o unico cenario que passou integralmente o contrato B.
- Cinco pares passaram uma triagem economica mais ampla para Replay, mas nao a
  certificacao operacional completa.
- `USDCHF` e `USDJPY` falharam fora da amostra. ICT alto isolado nao compensou
  holdout com PF abaixo de 1.
- A selecao posterior do melhor timeframe adiciona risco de comparacao multipla.
  Por isso nem mesmo a linha B e promovida automaticamente.

## Guardrails

- O artefato consolidado possui `operational=false`.
- A tabela do Lab e read-only e usa cache por data de modificacao.
- O indice runtime, Trade Plan, gates, Robo Demo, MT5 e Position Manager nao
  consomem este artefato.
- Promocao futura exige Replay visual, forward Demo e decisao explicita.

## Artefatos

- Pesquisador: `research/alpha_suggested/alpha_suggested_2_plus_individual.py`
- Seletor: `research/alpha_suggested/select_m3_best_individual.py`
- Consolidado: `.traderia/research/m3_alpha_sugerida_2_plus_best_by_pair.json`
- Evidencias H1, M30 e H4: `.traderia/research/m3_alpha_sugerida_2_plus_individual_*.json`
