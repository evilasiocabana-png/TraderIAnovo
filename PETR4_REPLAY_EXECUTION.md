# PETR4 Replay Execution

## Objetivo

Executar oficialmente o Replay utilizando o dataset PETR4 certificado, sem
executar estrategias e sem executar ordens.

## Dataset

| Campo | Valor |
| --- | --- |
| Arquivo | `historical_data/datasets/B3/PETR4/1d/data.csv` |
| Ativo | `PETR4` |
| Timeframe | `1d` |
| Candles | 2.491 |
| Inicio | `2016-06-28 00:00:00` |
| Fim | `2026-06-26 00:00:00` |

## Carga

O dataset foi carregado pelo `HistoricalDataProvider` existente e entregue ao
`ReplayEngine` como lista de candles normalizados.

Resultado da carga:

| Campo | Valor |
| --- | --- |
| Dataset vazio | Nao |
| Total carregado | 2.491 |
| Erros do provider | 0 |

## Execucao do ReplayEngine

O `ReplayEngine` foi usado diretamente para evitar execucao de estrategias.

Resultado:

| Campo | Valor |
| --- | --- |
| Total de candles | 2.491 |
| Primeiro candle processado | `2016-06-28 00:00:00` |
| Segundo candle processado | `2016-06-29 00:00:00` |
| Replay finalizado | Sim |
| Candles processados | 2.491 |

## EventBus

O `EventBus` foi conectado ao `ReplayEngine`.

Eventos observados:

| Evento | Quantidade |
| --- | ---: |
| `NEW_CANDLE` | 2.491 |
| `BACKTEST_FINISHED` | 1 |

## ReplayService

O `ReplayService` foi usado apenas para carga, sem avancar candle, para evitar
execucao de estrategia.

Resultado:

| Campo | Valor |
| --- | --- |
| Status | `READY` |
| Total de candles | 2.491 |
| Current index | `-1` |

## MarketSnapshot

Foi criado um `MarketSnapshot` manual a partir do primeiro candle, sem
estrategia:

```text
symbol='PETR4'
datetime='2016-06-28 00:00:00'
regime='DAILY_EQUITY_SMOKE'
volatility=0.21000003814697266
liquidity=45291700.0
trend_strength=0.0
market_dna_score=0.0
```

## DecisionPipeline

O `DecisionPipeline` foi validado com um `StrategySignal` manual `WAIT`, sem
executar Strategy.

Resultado:

| Campo | Valor |
| --- | --- |
| Final decision | `WAIT` |
| Final confidence | 0.0 |
| Approved | `True` |
| Ordem criada | Nao |

## Classificacao

`PETR4_REPLAY_EXECUTION_PASSED`

## Restricoes Preservadas

- Nenhuma estrategia foi executada.
- Nenhuma ordem foi executada.
- Broker nao foi acessado.
- ReplayEngine nao foi alterado.
- ReplayService nao foi alterado.
- EventBus nao foi alterado.
- DecisionPipeline nao foi alterado.
- Arquitetura nao foi alterada.
