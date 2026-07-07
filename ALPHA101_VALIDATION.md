# ALPHA101_VALIDATION

## Missao

MISSÃO 242 — ALPHA101_VALIDATION.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Validar quantitativamente a Alpha101 sobre PETR4 diário.

## Escopo

Validação exploratória, sem operação real, sem custos, sem slippage e sem recomendação financeira.

## Dataset

| Campo | Valor |
| --- | --- |
| Ativo | PETR4 |
| Timeframe | 1d |
| Candles | 2491 |
| Período | 2016-06-28 a 2026-06-26 |
| Fonte | `historical_data/datasets/B3/PETR4/1d/data.csv` |

## Método

Foi executada uma simulação exploratória:

- sinais gerados candle a candle pela `Alpha101Strategy`;
- entrada teórica no fechamento do candle sinalizado;
- holding fixo de 5 pregões;
- trades não sobrepostos;
- sem custos;
- sem slippage;
- sem imposto;
- long-only;
- nenhuma ordem real.

Arquivos gerados:

- `reports/alpha_discovery/alpha101_validation.json`
- `reports/alpha_discovery/alpha101_trades.csv`
- `reports/alpha_discovery/alpha101_signals.csv`

## Sinais

| Métrica | Valor |
| --- | ---: |
| Candles avaliados | 2491 |
| Sinais totais | 2491 |
| BUY | 185 |
| SELL | 0 |
| WAIT | 2306 |

## Trades Exploratórios

| Métrica | Valor |
| --- | ---: |
| Trades não sobrepostos | 88 |
| Win rate | 64.77% |
| Retorno médio por trade | 1.33% |
| Retorno mediano por trade | 1.45% |
| Profit Factor | 2.15 |
| Expectancy | 1.33% |
| Retorno acumulado da simulação | 192.14% |
| Drawdown máximo | -20.03% |
| Sharpe por trade | 2.08 |
| Buy-and-hold no período | 313.70% |

## Estabilidade Anual

| Ano | Trades | Retorno médio | Soma dos retornos |
| --- | ---: | ---: | ---: |
| 2017 | 9 | 1.12% | 10.10% |
| 2018 | 13 | 3.19% | 41.42% |
| 2019 | 8 | 0.39% | 3.16% |
| 2020 | 9 | 1.60% | 14.38% |
| 2021 | 7 | 1.12% | 7.84% |
| 2022 | 8 | -0.71% | -5.69% |
| 2023 | 10 | 1.15% | 11.51% |
| 2024 | 8 | -0.09% | -0.70% |
| 2025 | 7 | 0.60% | 4.23% |
| 2026 | 9 | 3.40% | 30.62% |

## Interpretação

Pontos positivos:

- Profit Factor acima de 2.0 na simulação exploratória;
- win rate acima de 60%;
- expectativa média positiva;
- drawdown menor que buy-and-hold;
- resultado positivo em vários anos distintos;
- amostra de 88 trades não sobrepostos.

Pontos de cautela:

- buy-and-hold ainda teve retorno total superior;
- anos 2022 e 2024 foram negativos;
- não há custos, slippage ou imposto;
- a Alpha foi descoberta e testada no mesmo dataset;
- validação ainda não é out-of-sample;
- há risco de overfitting.

## Benchmark

Comparação exploratória:

| Item | Alpha101 | Buy-and-hold |
| --- | ---: | ---: |
| Retorno acumulado | 192.14% | 313.70% |
| Drawdown máximo | -20.03% | -63.55% |
| Exposição | Parcial | Total |
| Perfil | Seletivo | Passivo |

Leitura:

```text
Alpha101 não superou buy-and-hold em retorno bruto, mas reduziu drawdown e exposição.
```

## Limitações

- Validação exploratória, não certificação estatística definitiva.
- Sem custos operacionais.
- Sem validação fora da amostra.
- Sem ajuste por dividendos na lógica de sinal.
- Sem robustez por variação de parâmetros.
- Sem walk-forward formal.

## Resultado

```text
VALIDATED_FOR_RESEARCH_WITH_WARNINGS
```

## Declaração Final

Alpha101 apresentou sinais quantitativos promissores em PETR4 diário, especialmente em drawdown, win rate e Profit Factor exploratório. Ainda assim, a validação é insuficiente para operação real e exige certificação com advertências.
