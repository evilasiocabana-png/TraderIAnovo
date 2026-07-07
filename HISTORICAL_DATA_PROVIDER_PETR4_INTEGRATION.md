# HistoricalDataProvider PETR4 Integration

## Objetivo

Integrar de forma controlada o dataset certificado da PETR4 ao fluxo existente
do `HistoricalDataProvider`, sem criar provider novo e sem alterar arquitetura.

## Artefatos Utilizados

| Artefato | Caminho |
| --- | --- |
| CSV bruto validado | `historical_data/datasets/B3/PETR4/1d/raw/yahoo_finance_petr4_sa_20160628_20260628_chart.csv` |
| CSV institucional para provider | `historical_data/datasets/B3/PETR4/1d/data.csv` |
| Metadados | `historical_data/datasets/B3/PETR4/1d/metadata.json` |
| Checksum | `historical_data/datasets/B3/PETR4/1d/checksum.sha256` |

## Decisao Tecnica

O CSV bruto da Missao 211 foi preservado intacto.

Para compatibilidade com o `HistoricalDataProvider` existente, foi criado
`data.csv` como copia institucional derivada do bruto, mantendo OHLCV e
`adjusted_close`, mas usando a coluna `timestamp` com horario diario
`00:00:00`.

Motivo: o loader historico legado aceita `date` como alias, mas valida
timestamp apenas nos formatos com hora. Nenhum codigo foi alterado.

## Hashes

| Arquivo | SHA-256 |
| --- | --- |
| `data.csv` | `7bf7b56f65096266bc3fc329ba3fefe3ab5e793aa2127ae6854c7b58d4235923` |
| CSV bruto | `a3fd3442f26bc0716463425c9f654c7561907d27e5413c1c762a70383dcfa21e` |

## Carga Pelo HistoricalDataProvider

Execucao direta:

```text
HistoricalDataProvider().load("historical_data/datasets/B3/PETR4/1d/data.csv", symbol="PETR4", timeframe="1d")
```

Resultado:

| Campo | Valor |
| --- | --- |
| Dataset vazio | Nao |
| Total de candles | 2.491 |
| Inicio | `2016-06-28 00:00:00` |
| Fim | `2026-06-26 00:00:00` |
| Erros do provider | 0 |
| Primeiro candle | `PETR4 2016-06-28 00:00:00` |
| Ultimo candle | `PETR4 2026-06-26 00:00:00` |

## Carga Catalogada

Execucao catalogada:

```text
HistoricalDataProvider().load_dataset("B3", "PETR4", "1d")
```

Resultado:

| Campo | Valor |
| --- | --- |
| Dataset existe | Sim |
| Dataset vazio | Nao |
| Total de candles | 2.491 |
| Inicio | `2016-06-28 00:00` |
| Fim | `2026-06-26 00:00` |
| Erros do provider | 0 |

## Warning de Convencao Estrutural

A estrutura solicitada para PETR4 foi:

```text
historical_data/datasets/B3/PETR4/1d/
```

O catalogo estrutural legado interpreta os tres niveis como:

```text
symbol/timeframe/period
```

Portanto, a carga catalogada funciona como:

```text
symbol = B3
timeframe = PETR4
period = 1d
```

Isso nao bloqueia a carga, mas deve ser corrigido em missao futura de
convencao de catalogo para ativos multi-mercado, sem alterar o provider nesta
missao.

## Compatibilidade Com Replay

`ReplayService.load_historical_data(data.csv)` retornou:

| Campo | Valor |
| --- | --- |
| Status | `READY` |
| Total de candles | 2.491 |
| Current index | `-1` |

Nenhum candle foi avancado nesta checagem de provider.

## Compatibilidade Com Research Lab

`ResearchLabService.run_historical_data_experiment(...)` executou usando o
provider existente.

Resultado:

| Campo | Valor |
| --- | --- |
| Experimento | `PETR4 Daily Research Smoke` |
| Estrategia | `alpha001_iorb` |
| Total de trades | 0 |
| Resultado liquido | 0.0 |
| Experimentos em memoria | 1 |

Observacao: a Alpha001 e intraday/WDO e nao deve ser interpretada como pesquisa
valida de PETR4 diario. Este teste valida apenas o fluxo do Research Lab.

## Classificacao

`INTEGRATED_WITH_WARNINGS`

## Restricoes Preservadas

- Nenhum provider foi criado.
- `HistoricalDataProvider` nao foi alterado.
- Replay nao foi alterado.
- Research Lab nao foi alterado.
- Validation Suite nao foi alterada.
- Benchmark nao foi alterado.
- Portfolio nao foi alterado.
- EventBus nao foi alterado.
- DecisionPipeline nao foi alterado.
- Nenhuma estrategia foi criada.
- Nenhuma corretora foi conectada.
- Nenhuma ordem foi executada.
- Operacao real permanece proibida.
