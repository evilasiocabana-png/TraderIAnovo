# Plano Arquitetural - DuckDB Historical Data Source

Data: 2026-06-26

## Objetivo

Preparar a futura integracao de DuckDB como provider historico do TraderIA sem
implementar DuckDB nesta sprint.

Este documento e apenas um plano tecnico interno. Ele nao adiciona dependencia
`duckdb`, nao cria adapter, nao altera contratos do dominio e nao modifica
fluxos funcionais.

## Posicao no Fluxo Existente

DuckDB devera entrar como mais uma fonte fisica atras da porta
`HistoricalDataSource`, preservando o contrato ja usado por CSV e Parquet.

Fluxo futuro previsto:

```text
Dashboard
  -> DashboardService
      -> HistoricalDatasetCatalog
          -> Provider Registry/Factory
              -> CsvHistoricalDataSource
              -> ParquetHistoricalDataAdapter
              -> DuckDBHistoricalDataAdapter
      -> HistoricalDataProvider
          -> HistoricalDataSource
              -> DuckDBHistoricalDataAdapter
          -> HistoricalDataset
      -> Data Quality
      -> Data Readiness Gate
      -> ReplayService
          -> ReplayEngine
      -> ResearchLabService
          -> ResearchLab
```

## Componentes e Responsabilidades

### HistoricalDataProvider

Responsabilidade preservada:

- receber uma origem opaca;
- delegar a leitura para `HistoricalDataSource`;
- retornar `HistoricalDataset`;
- nao conhecer DuckDB, SQL, tabelas, arquivos `.duckdb`, conexoes ou queries.

Nenhuma mudanca de contrato deve ser necessaria.

### Provider Registry/Factory

Responsabilidade futura:

- registrar `duckdb` como provider historico opcional;
- criar `DuckDBHistoricalDataAdapter` por nome;
- manter `csv` como provider default;
- permitir selecionar DuckDB sem alterar Replay, Research Lab, Dashboard ou
  dominio.

Registro futuro previsto:

```text
duckdb -> DuckDBHistoricalDataAdapter
```

### DuckDBHistoricalDataAdapter

Responsabilidade futura:

- implementar `HistoricalDataSource`;
- isolar import e uso da dependencia `duckdb`;
- abrir conexoes DuckDB somente dentro do adapter;
- receber origem opaca, como caminho de banco, configuracao ou objeto de query;
- executar consulta controlada para recuperar candles historicos;
- normalizar colunas para o contrato canonico:
  - `datetime`;
  - `open`;
  - `high`;
  - `low`;
  - `close`;
  - `volume`;
- converter registros para `list[Candle]`;
- retornar `HistoricalDataSourceResult`;
- traduzir erros de banco, tabela, schema, permissao e dados vazios para
  mensagens controladas;
- nunca vazar cursor, conexao, SQL bruto ou detalhes de arquivo para camadas
  superiores.

O adapter devera seguir o mesmo comportamento externo dos adapters CSV e
Parquet: entrada opaca, saida normalizada.

### HistoricalDatasetCatalog

Responsabilidade futura:

- listar datasets DuckDB como metadados, nao candles;
- expor `provider="duckdb"` apenas como metadado;
- manter origem fisica como valor opaco associado ao `dataset_id`;
- nao abrir conexao DuckDB;
- nao listar tabelas diretamente sem um adapter/servico de descoberta
  apropriado.

Metadados devem permanecer iguais:

- `dataset_id`;
- `ativo`;
- `timeframe`;
- `start_date`;
- `end_date`;
- `estimated_candles`;
- `provider`.

### Data Quality

Responsabilidade preservada:

- validar `HistoricalDataset` ja normalizado;
- aplicar as mesmas regras usadas para CSV e Parquet;
- nao criar regra especifica de DuckDB fora do adapter;
- nao consultar DuckDB diretamente.

Metricas preservadas:

- total de candles;
- data/hora inicial;
- data/hora final;
- OHLC invalido;
- volume invalido ou ausente;
- gaps temporais;
- timestamps duplicados.

### Data Readiness Gate

Responsabilidade preservada:

- usar status/historico de qualidade;
- classificar datasets DuckDB nos mesmos estados:
  - `READY_FOR_REPLAY`;
  - `READY_FOR_RESEARCH`;
  - `READY_FOR_REPLAY_AND_RESEARCH`;
  - `NOT_READY`;
  - `NOT_VALIDATED`;
- bloquear Replay e Research Lab quando aplicavel;
- registrar provider `duckdb` na auditoria, sem criar log separado.

### DashboardService

Responsabilidade preservada:

- continuar sendo a fachada unica do dashboard;
- orquestrar catalogo, qualidade, readiness, metricas e execucao;
- receber e propagar `dataset_id`/metadados;
- nao importar `duckdb`;
- nao abrir conexao DuckDB;
- nao conhecer tabela, query, arquivo, cursor ou schema fisico.

### Replay

Responsabilidade preservada:

- receber `HistoricalDataset` ou candles resolvidos;
- carregar `ReplayEngine` apenas com `list[Candle]`;
- nunca acessar DuckDB diretamente;
- nunca conhecer SQL, conexao, tabela ou arquivo DuckDB.

### Research Lab

Responsabilidade preservada:

- executar experimentos com `list[Candle]`;
- resolver historico via `MarketDataProvider`/`HistoricalDataProvider`;
- nunca acessar DuckDB diretamente;
- nunca conhecer SQL, conexao, tabela ou arquivo DuckDB.

## Proibicoes Arquiteturais

Nao poderao acessar DuckDB diretamente:

- Replay;
- `ReplayEngine`;
- `ReplayService`;
- Research Lab;
- `ResearchLabService`;
- Alpha001;
- Dashboard;
- `DashboardService`;
- dominio;
- contratos do dominio;
- estrategias;
- componentes de risco;
- `DecisionPipeline`.

Tambem ficam proibidos fora do adapter DuckDB:

- `import duckdb`;
- conexoes DuckDB;
- SQL de leitura historica;
- conhecimento de tabela/coluna fisica;
- leitura de arquivo `.duckdb`;
- cursores;
- paths de banco;
- regras especificas de schema DuckDB.

## Limites de Contrato

O contrato externo deve permanecer:

```text
HistoricalDataSource.load(source: object) -> HistoricalDataSourceResult
HistoricalDataProvider.load(source, symbol, timeframe) -> HistoricalDataset
```

Nao deve haver alteracao em:

- `HistoricalDataset`;
- `Candle`;
- contratos do dominio;
- `ReplayService`;
- `ResearchLabService`;
- `DashboardService`;
- `dashboard_app.py`.

## Riscos e Cuidados

### Medio - Query e schema acoplados ao adapter

DuckDB introduz SQL e possivel variacao de schema. O adapter deve concentrar
esse conhecimento e oferecer aliases/normalizacao sem vazar nomes fisicos.

Mitigacao: testes de contrato com schemas minimos, aliases e falhas controladas.

### Medio - Origem opaca pode carregar configuracao demais

Se a origem DuckDB exigir caminho, tabela, filtros e query, ha risco de vazar
configuracao para camadas superiores.

Mitigacao: definir um objeto/configuracao de infraestrutura ou registrar origem
opaca no catalogo, mantendo o dashboard restrito a `dataset_id`.

### Medio - Performance e volume de candles

DuckDB pode retornar grandes volumes. O adapter deve prever filtros por dataset
e evitar carregar universo inteiro sem necessidade.

Mitigacao: catalogo com metadados e fontes opacas bem definidas; consultas
controladas por dataset.

### Baixo - Dependencia opcional

A dependencia `duckdb` nao deve ser obrigatoria ate a sprint de implementacao.

Mitigacao: nao adicionar `duckdb` ao `requirements.txt` nesta sprint e, na
sprint futura, tratar erro de dependencia ausente dentro do adapter.

### Baixo - Catalogo real de tabelas

Listar datasets a partir de tabelas DuckDB exigira descoberta fisica. Isso nao
deve entrar no `HistoricalDatasetCatalog` diretamente sem adapter/porta propria.

Mitigacao: criar discovery adapter futuro, se necessario.

## Plano Futuro de Implementacao

1. Criar `DuckDBHistoricalDataAdapter` implementando `HistoricalDataSource`.
2. Isolar `import duckdb` dentro do adapter.
3. Registrar provider `duckdb` no registry default.
4. Criar testes de contrato comparando CSV, Parquet e DuckDB.
5. Criar testes de erro controlado para dependencia ausente, tabela inexistente,
   schema invalido e dataset vazio.
6. Integrar catalogo por metadados, sem listagem direta de banco em camadas
   superiores.
7. Reutilizar Data Quality, Data Readiness Gate, auditoria e metricas por
   provider sem regra especial fora do adapter.
8. Validar `python app.py`, testes completos e dashboard Streamlit.

## Criterio de Prontidao Para Sprint de Codigo

Antes de implementar DuckDB, deve existir decisao explicita sobre:

- formato da origem opaca;
- schema canonico minimo;
- nomes de tabelas ou estrategia de discovery;
- limites de volume;
- dependencia opcional no ambiente;
- estrategia de testes com banco temporario.

## Conclusao

DuckDB deve entrar como adapter de infraestrutura atras de
`HistoricalDataSource`. O restante do sistema deve continuar enxergando apenas
`HistoricalDataset`, metadados de catalogo, qualidade, readiness e metricas via
`DashboardService`.

Nenhuma camada superior deve conhecer DuckDB diretamente.
