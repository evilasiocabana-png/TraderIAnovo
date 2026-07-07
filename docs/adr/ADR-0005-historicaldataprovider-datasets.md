# ADR-0005: HistoricalDataProvider como Ponto Autorizado para Datasets Históricos

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

O projeto passou a suportar dados históricos vindos de CSV, Parquet e DuckDB.

## Problema

Se Replay, Research Lab ou Dashboard conhecerem formatos físicos, a troca de
fonte de dados quebra Clean Architecture e Ports & Adapters.

## Alternativas Consideradas

- Cada camada carregar sua própria fonte histórica.
- Usar adapters concretos diretamente nas camadas superiores.
- Centralizar resolução em HistoricalDataProvider e registry de fontes.

## Decisão Adotada

`HistoricalDataProvider` é o ponto autorizado para resolução de datasets
históricos.

## Justificativa

O provider centraliza obtenção de datasets e mantém CSV, Parquet e DuckDB
isolados em adapters.

## Impactos Positivos

- Troca de fonte exige novo adapter, não alteração das camadas superiores.
- Replay e Research continuam consumindo candles pelo contrato esperado.
- Dashboard não conhece CSV, Parquet, DuckDB, Path, pandas ou arquivos.

## Impactos Negativos

- Novas fontes exigem registro no provider/registry.

## Riscos

- Acesso direto a adapter concreto fora da camada autorizada gera acoplamento.

## Consequências Futuras

Toda nova fonte histórica deve entrar como adapter/provider.

## Referências

- market_data/historical_data_provider.py
- market_data/historical_data_source_registry.py
- market_data/historical_dataset_catalog.py
- tests/test_provider_architecture.py

## Sprints Relacionadas

- SPRINT MARKET DATA 005 a 007
- SPRINT DATA SOURCE 001 a 021
- SPRINT CTO 011
