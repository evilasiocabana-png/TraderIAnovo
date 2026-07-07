# PETR4 Research Execution

## Objetivo

Executar o Research Lab utilizando PETR4 diario para validar o fluxo de pesquisa
com dataset real, sem criar Alpha nova.

## Dataset

| Campo | Valor |
| --- | --- |
| Dataset | `b3_petr4_1d` |
| Arquivo | `historical_data/datasets/B3/PETR4/1d/data.csv` |
| Total de candles | 2.491 |
| Periodo | `2016-06-28 00:00` a `2026-06-26 00:00` |

## Execucao

Foi executado:

```text
ResearchLabService.run_real_data_research(symbol="B3", timeframe="PETR4", period="1d")
```

Resultado:

| Campo | Valor |
| --- | --- |
| Dataset ID | `b3_petr4_1d` |
| Campaign ID | `campaign-b3_petr4_1d` |
| Research Runner | `COMPLETED` |
| Total de candles | 2.491 |
| Total de benchmarks | 4 |
| Total de validacoes | 4 |
| Validation Suite | `INSUFFICIENT_REAL_DATA_SAMPLE` |
| Portfolio | `PORTFOLIO_EVALUATED_WITH_REAL_DATA` |

## Experimento

| Campo | Valor |
| --- | --- |
| Experimento | `Real Data Research b3_petr4_1d` |
| Estrategia usada pelo fluxo atual | `alpha001_iorb` |
| Total de trades | 0 |
| Win rate | 0.0 |
| Profit factor | 0.0 |
| Net profit | 0.0 |
| Max drawdown | 0.0 |

## Benchmark

Benchmarks executados pelo fluxo existente:

- `alpha001_iorb`
- `breakout`
- `pullback`
- `score_contexto`

Resultado consolidado:

| Campo | Valor |
| --- | --- |
| Best strategy | `alpha001_iorb` |
| Best profit | 0.0 |
| Best profit factor | 0.0 |
| Best drawdown | 0.0 |
| Best win rate | 0.0 |

## Validacoes

As validacoes retornaram `Nao confiavel` por amostra operacional nula:

- pouca amostra;
- poucas vitorias;
- profit factor baixo;
- win rate baixo.

Interpretação: a execução valida o pipeline técnico do Research Lab com dados
PETR4, mas nao valida nenhuma hipotese quantitativa.

## Research Catalog

Nao houve criacao de catalogo novo nesta missao. A rastreabilidade foi mantida
por:

- `metadata.json`;
- `checksum.sha256`;
- dataset ID `b3_petr4_1d`;
- relatorios das Missoes 211, 212 e 214.

## Classificacao

`PETR4_RESEARCH_PIPELINE_EXECUTED_WITH_WARNINGS`

## Restricoes Preservadas

- Nenhuma Alpha nova foi criada.
- Nenhuma Strategy nova foi criada.
- Research Lab nao foi alterado.
- Research Pipeline nao foi alterado.
- Benchmark nao foi alterado.
- Portfolio nao foi alterado.
- Nenhuma ordem foi executada.
- Operacao real permanece proibida.
