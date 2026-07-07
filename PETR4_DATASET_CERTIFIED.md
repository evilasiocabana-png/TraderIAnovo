# PETR4 Dataset Certified

## Objetivo

Certificar oficialmente o pipeline PETR4 diario do TraderIA para pesquisa
quantitativa exploratoria.

## Status Institucional

`PETR4_DATASET_CERTIFIED_FOR_QUANTITATIVE_RESEARCH`

Com warnings:

- fonte gratuita Yahoo Finance;
- volume zero em 10 registros do bruto;
- gaps ainda nao reconciliados com calendario oficial B3;
- convencao estrutural `B3/PETR4/1d` interpretada pelo catalogo legado como
  `symbol/timeframe/period`;
- Alpha001 nao e estrategia apropriada para PETR4 diario e gerou 0 trades.

## Dataset Certificado

| Campo | Valor |
| --- | --- |
| Ativo | `PETR4` |
| Timeframe | `1d` |
| Arquivo institucional | `historical_data/datasets/B3/PETR4/1d/data.csv` |
| Arquivo bruto | `historical_data/datasets/B3/PETR4/1d/raw/yahoo_finance_petr4_sa_20160628_20260628_chart.csv` |
| Total de candles | 2.491 |
| Inicio | `2016-06-28` |
| Fim | `2026-06-26` |
| Hash institucional | `7bf7b56f65096266bc3fc329ba3fefe3ab5e793aa2127ae6854c7b58d4235923` |
| Hash bruto | `a3fd3442f26bc0716463425c9f654c7561907d27e5413c1c762a70383dcfa21e` |

## Checklist

| Item | Status | Evidencia |
| --- | --- | --- |
| HistoricalDataProvider | CERTIFIED | Carregou 2.491 candles sem erros. |
| Replay | CERTIFIED | ReplayEngine processou 2.491 candles e publicou eventos. |
| Research Lab | CERTIFIED_WITH_WARNINGS | Research Runner `COMPLETED`, mas Alpha001 gerou 0 trades. |
| Validation Suite | CERTIFIED_WITH_WARNINGS | Executada, status `INSUFFICIENT_REAL_DATA_SAMPLE`. |
| Benchmark | CERTIFIED_WITH_WARNINGS | Benchmarks executados com metricas zeradas. |
| Portfolio | CERTIFIED | `PORTFOLIO_EVALUATED_WITH_REAL_DATA`. |
| Dashboard | CERTIFIED | `DashboardService` carregou o dataset no Replay com status `READY`. |

## Dashboard

Validacao via fachada:

```text
DashboardService.load_historical_replay_csv(data.csv)
```

Resultado:

| Campo | Valor |
| --- | --- |
| Replay status | `READY` |
| Total de candles | 2.491 |
| DashboardData replay total | 2.491 |
| Estrategias listadas | `alpha001_iorb`, `breakout`, `pullback`, `score_contexto`, `smart_money` |

## Conclusao

O TraderIA esta apto a utilizar PETR4 diario como dataset real para pesquisa
quantitativa exploratoria. A certificacao cobre pipeline de dados, carga,
Replay, Research Lab, Benchmark, Portfolio e Dashboard.

Esta certificacao nao aprova estrategia, nao aprova operacao real e nao
substitui o objetivo institucional de WDO 1m.

## Proxima Fase

Com a Sprint 12 certificada, o projeto pode iniciar a Sprint 13 - Alpha Factory
PETR4, com pesquisa documental da Alpha101.

## Restricoes Preservadas

- Nenhuma arquitetura foi alterada.
- Nenhum provider foi criado.
- Replay nao foi alterado.
- Research Lab nao foi alterado.
- Validation Suite nao foi alterada.
- Benchmark nao foi alterado.
- Portfolio nao foi alterado.
- Dashboard nao acessou provider diretamente.
- Nenhuma corretora foi conectada.
- Nenhuma ordem foi executada.
- Operacao real permanece proibida.
