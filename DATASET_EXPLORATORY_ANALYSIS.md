# DATASET_EXPLORATORY_ANALYSIS

## Missao

MISSÃO 234 — DATASET_EXPLORATORY_ANALYSIS.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Realizar uma análise exploratória completa do dataset PETR4 diário para transformar os 10 anos de dados em conhecimento quantitativo inicial.

Este documento não cria Strategy, não cria Alpha e não autoriza operação real.

## Dataset

| Campo | Valor |
| --- | --- |
| Ativo | PETR4 |
| Timeframe | 1d |
| Fonte | `historical_data/datasets/B3/PETR4/1d/data.csv` |
| Período | 2016-06-28 a 2026-06-26 |
| Candles | 2491 |
| Primeiro fechamento | 9.20 |
| Último fechamento | 38.06 |

## Estatísticas Gerais

| Métrica | Valor |
| --- | --- |
| Retorno acumulado | 313.70% |
| Retorno anualizado | 15.45% |
| Retorno médio diário | 0.0929% |
| Retorno mediano diário | 0.1252% |
| Volatilidade diária | 2.64% |
| Volatilidade anualizada | 41.96% |
| Sharpe ingênuo, sem taxa livre de risco | 0.56 |
| Skewness | -1.12 |
| Kurtosis | 15.18 |
| Drawdown máximo | -63.55% |
| Dias positivos | 1303 |
| Dias negativos | 1153 |
| Percentual positivo | 52.33% |

## Distribuição dos Retornos

A distribuição dos retornos diários é assimétrica para a esquerda e possui caudas muito pesadas. Isso significa que eventos negativos extremos fazem parte estrutural da série e não podem ser tratados como ruído raro.

Eventos extremos observados:

| Evento | Data | Retorno |
| --- | --- | --- |
| Melhor dia | 2020-03-13 | 22.22% |
| Pior dia | 2020-03-09 | -29.70% |

Gráfico gerado:

```text
reports/alpha_discovery/petr4_return_hist.png
```

## Volatilidade

A volatilidade anualizada de 41.96% confirma que PETR4 diário é um ativo de alta variância. A autocorrelação do retorno absoluto foi 0.269 no lag 1, indicando clustering de volatilidade.

Implicação:

```text
Qualquer Alpha em PETR4 diario precisa tratar regime de volatilidade.
```

## Drawdown

O drawdown máximo estimado foi -63.55%. Isso impede tratar a série como tendência simples de compra e permanência.

Gráfico gerado:

```text
reports/alpha_discovery/petr4_drawdown.png
```

## Autocorrelação

| Série | Lag | Valor |
| --- | --- | --- |
| Retorno diário | 1 | -0.074 |
| Retorno diário | 5 | 0.053 |
| Retorno absoluto | 1 | 0.269 |

Leitura:

- retorno diário possui leve reversão de curtíssimo prazo;
- retorno em janela de 5 dias mostra pequena persistência;
- volatilidade possui persistência material.

## Tendência

A série teve retorno acumulado forte, mas com anos muito distintos:

| Ano | Retorno |
| --- | --- |
| 2016 | 61.63% |
| 2017 | 8.27% |
| 2018 | 40.87% |
| 2019 | 33.07% |
| 2020 | -6.10% |
| 2021 | 0.39% |
| 2022 | -13.88% |
| 2023 | 52.00% |
| 2024 | -2.82% |
| 2025 | -14.84% |
| 2026 | 23.49% |

Leitura:

```text
Existe tendência em ciclos, mas não estabilidade anual suficiente para uma regra única sem filtro de regime.
```

## Sazonalidade

### Dias da Semana

Retornos médios por dia:

| Dia | Retorno médio |
| --- | --- |
| Segunda | 0.238% |
| Terça | 0.246% |
| Quarta | 0.232% |
| Quinta | -0.110% |
| Sexta | -0.141% |

Leitura inicial:

```text
Segunda, terça e quarta foram mais positivas; quinta e sexta foram negativas na média.
```

Essa sazonalidade exige validação fora da amostra antes de virar regra.

### Meses

Meses com média mais positiva:

- Janeiro: 0.365% por dia;
- Outubro: 0.325% por dia;
- Julho: 0.296% por dia.

Meses fracos:

- Março: -0.105% por dia;
- Dezembro: -0.065% por dia;
- Fevereiro: -0.043% por dia.

## Gaps

| Métrica | Valor |
| --- | --- |
| Gap médio | 0.124% |
| Gap absoluto médio | 0.969% |

Gaps são relevantes para PETR4 diário e devem ser considerados em qualquer hipótese de entrada no fechamento e saída no fechamento seguinte.

## Volume

| Métrica | Valor |
| --- | --- |
| Volume médio | 57.3 milhões |
| Volume máximo | 490.2 milhões |
| Correlação retorno-volume | -0.097 |
| Correlação retorno absoluto-volume | 0.615 |

Leitura:

```text
Volume não explica diretamente direção, mas acompanha intensidade do movimento.
```

Isso sugere que volume pode funcionar melhor como filtro de regime/intensidade do que como gatilho direcional isolado.

## Sequências de Altas e Baixas

| Métrica | Valor |
| --- | --- |
| Maior sequência de altas | 11 dias |
| Maior sequência de baixas | 8 dias |

Leitura:

```text
A série permite persistência direcional, mas sequências longas são exceções.
```

## Triagem Inicial de Hipóteses

Testes simples sobre retorno futuro de 5 dias, sem custos e sem pretensão de backtest final:

| Hipótese | Amostra | Retorno médio futuro 5d | Mediana | Hit rate |
| --- | ---: | ---: | ---: | ---: |
| Volume momentum 5d | 322 | 0.776% | 1.011% | 58.70% |
| Breakout 20d | 216 | 0.607% | 0.898% | 59.72% |
| RSI < 30 | 253 | 0.375% | 0.674% | 56.52% |
| Bollinger baixo | 307 | 0.301% | 0.440% | 55.37% |
| Tendência baixa volatilidade | 797 | 0.263% | 0.437% | 55.96% |
| Fechamento acima da MM50 com momentum 5d | 972 | 0.147% | 0.367% | 53.50% |
| Pullback em tendência MM50 RSI 40-55 | 196 | -0.275% | -0.085% | 48.47% |

Achado crítico:

```text
A hipótese antiga de pullback em tendência não foi favorecida nesta triagem simples.
```

## Gráficos Gerados

- `reports/alpha_discovery/petr4_close.png`
- `reports/alpha_discovery/petr4_cum_return.png`
- `reports/alpha_discovery/petr4_drawdown.png`
- `reports/alpha_discovery/petr4_return_hist.png`
- `reports/alpha_discovery/petr4_volume.png`

## Limitações

- Não há custos, slippage ou impostos nesta etapa.
- A triagem usa retornos futuros simples, não simulação operacional completa.
- PETR4 é apenas um ativo, com risco específico elevado.
- A base vem de fonte gratuita e precisa manter status de pesquisa.
- Resultado histórico não autoriza operação real.

## Conclusão Quantitativa Inicial

Existe potencial exploratório em PETR4 diário, mas o edge não aparece como simples compra permanente nem como pullback genérico.

As hipóteses mais promissoras nesta primeira leitura são:

1. momentum de 5 dias com volume acima da média;
2. rompimento de máxima de 20 dias;
3. reversão após sobrevenda forte.

## Declaração Final

O dataset PETR4 diário possui informação quantitativa explorável, mas qualquer Alpha precisa nascer de validação estatística incremental, com controle de volatilidade, drawdown, regime e risco de overfitting. Operação real permanece proibida.
