# Historical Dataset Catalog

Este pacote contem o catalogo estrutural de datasets historicos do TraderIA_WDO.

O catalogo e responsavel apenas por descobrir e descrever datasets disponiveis
na estrutura oficial:

```text
historical_data/datasets/<symbol>/<timeframe>/<period>/
```

Exemplo:

```text
historical_data/datasets/WDO/1m/2025/
```

## Responsabilidade

`HistoricalDatasetCatalog` pode:

- localizar datasets disponiveis;
- listar ativos;
- listar timeframes;
- listar periodos;
- retornar metadados estruturais;
- validar a estrutura de diretorios.

`HistoricalDatasetCatalog` nao pode:

- abrir CSV;
- abrir Parquet;
- abrir DuckDB;
- carregar candles;
- usar pandas;
- executar Replay;
- acessar Research Lab;
- depender do Dashboard.

## Metadados

Quando existir `metadata.json`, ele deve descrever:

- `symbol`
- `timeframe`
- `source`
- `exchange`
- `timezone`
- `first_timestamp`
- `last_timestamp`
- `candle_count`
- `format`
- `version`

O catalogo nao interpreta candles. Ele apenas devolve descricoes e caminhos
estruturais para que providers/adapters oficiais possam atuar em outro nivel da
arquitetura.
