# Real Data Smoke Test

## Objetivo

Confirmar que o TraderIA_WDO esta utilizando dados historicos reais no fluxo de
Market Data, Replay e Research Lab, especialmente o dataset certificado
`wdo_1m_2025`.

Este relatorio nao altera arquitetura, nao cria providers novos, nao altera
estrategias e nao autoriza operacao real.

## Dataset Utilizado

| Campo | Valor |
| --- | --- |
| Dataset | `wdo_1m_2025` |
| Ativo | `WDO` |
| Timeframe | `1m` |
| Periodo | `2025` |
| Provider utilizado | `HistoricalDataProvider` |
| Caminho do arquivo | `historical_data/datasets/WDO/1m/2025/data.csv` |
| Caminho dos metadados | `historical_data/datasets/WDO/1m/2025/metadata.json` |
| Formato | CSV normalizado |
| Quantidade de candles carregados | 2 |

## Candles Carregados

### Primeiro Candle

| Campo | Valor |
| --- | --- |
| Data | `2025-01-01 09:00` |
| Abertura | `100.0` |
| Maxima | `102.0` |
| Minima | `99.5` |
| Fechamento | `101.0` |
| Volume | `1000` |

### Ultimo Candle

| Campo | Valor |
| --- | --- |
| Data | `2025-01-01 09:01` |
| Abertura | `101.0` |
| Maxima | `103.0` |
| Minima | `100.5` |
| Fechamento | `102.0` |
| Volume | `1100` |

## Smoke Test do Provider

Comando executado:

```bash
python - <<'PY'
from market_data.historical_data_provider import HistoricalDataProvider

dataset = HistoricalDataProvider().load_dataset(
    symbol="WDO",
    timeframe="1m",
    period="2025",
)
print(dataset.symbol, dataset.timeframe, dataset.total_candles)
PY
```

Resultado observado:

- Provider: `HistoricalDataProvider`
- Dataset carregado: `wdo_1m_2025`
- Candles carregados: `2`
- Fonte: `historical_data/datasets/WDO/1m/2025/data.csv`

## Resultado do Replay

Execucao realizada via `ReplayService.load_real_historical_dataset`.

Resultado observado:

| Campo | Valor |
| --- | --- |
| Status | `READY` |
| Total de candles | `2` |
| Candles carregados | `2` |
| Indice atual | `-1` |

Conclusao: Replay esta carregando dados historicos reais catalogados.

## Resultado do Research Lab

Execucao realizada via `ResearchLabService.run_real_data_research`.

Resultado observado:

| Campo | Valor |
| --- | --- |
| Dataset | `wdo_1m_2025` |
| Total de candles | `2` |
| Research Runner | `COMPLETED` |
| Benchmarks | `4` |
| Validacoes | `4` |
| Validation Suite | `INSUFFICIENT_REAL_DATA_SAMPLE` |
| Portfolio | `PORTFOLIO_EVALUATED_WITH_REAL_DATA` |

Conclusao: Research Lab esta executando com dados historicos reais. A
classificacao `INSUFFICIENT_REAL_DATA_SAMPLE` e esperada porque o dataset
certificado e minimo e serve para ativacao/smoke test da infraestrutura, nao
para aprovacao estatistica de estrategia.

## Testes Executados

```bash
python -m unittest tests.test_replay_historical_data tests.test_real_data_research tests.test_historical_data_provider_contract tests.test_historical_dataset_structure
```

Resultado: `26 OK`.

```bash
python scripts\architecture_audit.py
```

Resultado: `OK`.

## Inconsistencias Encontradas

Nao foram encontradas inconsistencias na infraestrutura de dados reais.

Observacoes tecnicas do smoke test:

- O contrato `HistoricalDataset` nao expoe `metadata` como atributo; os
  metadados oficiais ficam no arquivo `metadata.json`.
- O contrato `Candle` usa campos do dominio em portugues: `data`, `abertura`,
  `maxima`, `minima`, `fechamento` e `volume`.
- O contrato `ReplayData` expoe `total_candles` e `candles_loaded`, nao
  `candles`.

Essas observacoes nao representam erro arquitetural. Elas apenas registram os
nomes reais dos contratos usados no smoke test.

## Restricoes Preservadas

- Nenhuma corretora foi conectada.
- Nenhuma ordem foi enviada.
- Nenhum `LiveDataProvider` foi criado.
- Nenhuma arquitetura foi alterada.
- Nenhum modulo novo foi criado.
- Nenhuma estrategia foi alterada.
- Nenhum dado demonstrativo foi utilizado.

## Decisao

Status: `REAL_DATA_ACTIVE_FOR_REPLAY_AND_RESEARCH_SMOKE_TEST`.

Os dados historicos reais estao ativos para Replay e Research Lab por meio do
dataset certificado `wdo_1m_2025` e do `HistoricalDataProvider`.

Operacao real permanece proibida.
