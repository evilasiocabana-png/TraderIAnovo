# Checkpoint Arquitetural - Sprint Data Source

Data: 2026-06-26

## Objetivo

Encerrar formalmente a fase Data Source depois da introducao dos providers CSV,
Parquet e DuckDB, registrando o estado arquitetural estavel antes de avaliar
novas fontes fisicas como PostgreSQL, MT5, Nelogica ou B3.

Este documento e um checkpoint tecnico interno. Nenhuma funcionalidade e
implementada por este checkpoint.

## Checkpoint Final - Sprint Data Source 021

O estado final aprovado da fase Data Source e:

- `HistoricalDataProvider` permanece independente da origem fisica;
- `HistoricalDataSourceRegistry` registra providers historicos por nome;
- CSV permanece como provider historico default;
- Parquet permanece como provider alternativo registrado;
- DuckDB permanece como provider alternativo registrado;
- `CsvHistoricalDataSource` isola leitura CSV e integracao com loader legado;
- `ParquetHistoricalDataAdapter` isola leitura Parquet, `pandas`, `Path` e
  `read_parquet`;
- `DuckDBHistoricalDataAdapter` isola leitura DuckDB, conexao, SQL, `Path` e
  configuracao de tabela;
- `HistoricalDatasetCatalog` expoe apenas metadados e origens opacas;
- Data Quality valida `HistoricalDataset` normalizado, sem regra especifica de
  CSV, Parquet ou DuckDB;
- Data Readiness Gate bloqueia ou libera Replay/Research Lab usando a mesma
  classificacao para todos os providers;
- auditoria do gate registra provider, acao, decisao, readiness e motivos;
- metricas por provider consolidam catalogo, qualidade e auditoria;
- `DashboardService` e a fachada unica para o dashboard visual;
- `ReplayService` e `ResearchLabService` continuam desacoplados do formato
  fisico;
- `ReplayEngine` e `ResearchLab` seguem trabalhando com `list[Candle]`.

## Regras Obrigatorias da Fase Data Source

Estas regras devem ser preservadas em qualquer sprint futura:

- CSV so pode ser acessado pelo adapter CSV.
- Parquet so pode ser acessado pelo adapter Parquet.
- DuckDB so pode ser acessado pelo adapter DuckDB.
- `pandas.read_parquet()` so pode aparecer no adapter Parquet.
- conexao DuckDB, SQL e configuracao de tabela so podem aparecer no adapter
  DuckDB ou em testes especificos do adapter.
- `pandas.read_csv()` nao pode aparecer em Replay, Research Lab, Dashboard ou
  `DashboardService`.
- `Path`, `open()`, diretorios e arquivos fisicos so podem aparecer em adapters
  ou componentes explicitamente classificados como infraestrutura.
- Replay nunca acessa CSV, Parquet, DuckDB ou qualquer formato fisico
  diretamente.
- Research Lab nunca acessa CSV, Parquet, DuckDB ou qualquer formato fisico
  diretamente.
- Dashboard nunca acessa provider, catalogo, registry, persistencia, adapter,
  CSV, Parquet, DuckDB, `Path`, `pandas`, diretorios ou arquivos diretamente.
- Dashboard consome Data Source, qualidade, readiness, auditoria e metricas
  exclusivamente por `DashboardService`.
- Toda nova fonte historica deve entrar como novo adapter/provider atras da
  porta `HistoricalDataSource`.
- `HistoricalDataProvider` nao deve conhecer detalhes de CSV, Parquet, DuckDB,
  PostgreSQL, MT5, Nelogica, B3 ou qualquer origem fisica futura.
- `HistoricalDataset` permanece o contrato normalizado entregue as camadas de
  aplicacao.
- Candles historicos nao devem ser persistidos ate existir sprint explicita
  para persistencia de candles.
- Exportacoes CSV da Alpha001 permanecem separadas do fluxo de Data Source.

## Escopo Avaliado

Foram avaliados os seguintes pontos do fluxo historico:

- `HistoricalDataProvider`;
- Provider Registry/Factory;
- `CsvHistoricalDataSource`;
- `ParquetHistoricalDataAdapter`;
- `DuckDBHistoricalDataAdapter`;
- `HistoricalDatasetCatalog`;
- Data Quality;
- Data Readiness Gate;
- auditoria do gate;
- metricas por provider;
- `DashboardService`;
- Replay;
- Research Lab.

## Fluxo Atual Consolidado

```text
Dashboard
  -> DashboardService
      -> HistoricalDatasetCatalog
          -> HistoricalDataSourceRegistry
              -> CsvHistoricalDataSource
              -> ParquetHistoricalDataAdapter
              -> DuckDBHistoricalDataAdapter
      -> HistoricalDataProvider
          -> HistoricalDataSource
              -> CsvHistoricalDataSource
              -> ParquetHistoricalDataAdapter
              -> DuckDBHistoricalDataAdapter
          -> HistoricalDataset
      -> Data Quality
      -> HistoricalDatasetQualityRepository
      -> Data Readiness Gate
      -> DataReadinessGateLogger
      -> HistoricalProviderMetrics
      -> ReplayService
          -> ReplayEngine
      -> ResearchLabService
          -> ResearchLab
```

## Dependencias Atuais

### HistoricalDataProvider

`HistoricalDataProvider` depende da porta `HistoricalDataSource` e implementa
`MarketDataProvider`. Ele recebe uma origem opaca, delega a leitura para a fonte
historica concreta e retorna sempre `HistoricalDataset`.

Estado atual:

- nao importa CSV, Parquet ou DuckDB diretamente;
- nao usa `pandas`, `Path`, `open()` ou diretorios;
- nao conhece SQL, tabelas, schemas fisicos ou extensoes de arquivo;
- preserva `HistoricalDataset` como contrato normalizado para aplicacao.

### Provider Registry/Factory

`HistoricalDataSourceRegistry` registra factories por nome normalizado. O
registry default registra:

- `csv` -> `CsvHistoricalDataSource`;
- `parquet` -> `ParquetHistoricalDataAdapter`;
- `duckdb` -> `DuckDBHistoricalDataAdapter`.

CSV segue como default via `create_default_historical_data_source()`, que cria a
fonte `csv`. A troca futura de provider continua exigindo apenas novo adapter e
registro no factory.

### CsvHistoricalDataSource

`CsvHistoricalDataSource` encapsula o carregador CSV legado
`HistoricalDataLoader`. A leitura fisica de CSV permanece isolada em:

- `market_data/csv_historical_data_source.py`;
- `data/historical_data_loader.py`.

Nenhuma camada superior deve chamar o loader diretamente.

### ParquetHistoricalDataAdapter

`ParquetHistoricalDataAdapter` isola:

- import de `pandas`;
- uso de `Path`;
- chamada `read_parquet`;
- normalizacao de aliases de colunas;
- conversao de linhas para `Candle`;
- erros especificos de estrutura ou arquivo Parquet.

O adapter retorna `HistoricalDataSourceResult`, mantendo o mesmo contrato usado
por CSV e DuckDB.

### DuckDBHistoricalDataAdapter

`DuckDBHistoricalDataAdapter` isola:

- import de `duckdb`;
- uso de `Path`;
- abertura de conexao;
- query SQL;
- validacao de database/table;
- normalizacao de aliases de colunas;
- conversao de linhas para `Candle`;
- erros especificos de estrutura, arquivo, tabela ou conexao DuckDB.

O adapter retorna `HistoricalDataSourceResult`, mantendo o mesmo contrato usado
por CSV e Parquet.

### HistoricalDatasetCatalog

`HistoricalDatasetCatalog` lista apenas metadados e origens opacas por
`dataset_id`. Ele valida se o provider informado esta registrado no registry.

Metadados expostos:

- `dataset_id`;
- `ativo`;
- `timeframe`;
- `start_date`;
- `end_date`;
- `estimated_candles`;
- `provider`.

O catalogo nao lista diretorios e nao abre arquivos.

### Data Quality

O relatorio de qualidade e calculado em `DashboardService` depois que o dataset
foi resolvido via `HistoricalDataProvider`.

Metricas atuais:

- total de candles;
- data/hora inicial;
- data/hora final;
- candles com OHLC invalido;
- candles com volume invalido ou ausente;
- gaps temporais;
- timestamps duplicados.

O resultado e persistido como metadado/status/historico. Candles historicos
ainda nao sao persistidos.

### Data Readiness Gate

O gate usa a ultima validacao/status de qualidade para classificar o dataset em:

- `READY_FOR_REPLAY`;
- `READY_FOR_RESEARCH`;
- `READY_FOR_REPLAY_AND_RESEARCH`;
- `NOT_READY`;
- `NOT_VALIDATED`.

O bloqueio de Replay e Research Lab esta centralizado em `DashboardService`. As
decisoes sao registradas via `DataReadinessGateLogger` com provider, acao,
status, decisao e motivos.

### Auditoria do Gate

`DataReadinessGateLogger` registra avaliacoes do gate em contrato unico para
CSV, Parquet e DuckDB.

Campos registrados:

- `dataset_id`;
- `provider`;
- data/hora da avaliacao;
- acao solicitada;
- status de prontidao;
- decisao;
- motivos.

### Metricas por Provider

`DashboardService.get_historical_provider_metrics()` consolida catalogo,
status de qualidade e logs do gate por provider.

Providers minimos retornados:

- `csv`;
- `parquet`;
- `duckdb`.

Metricas por provider:

- total de datasets catalogados;
- total de datasets validados;
- total de datasets aprovados;
- total de datasets reprovados;
- total de datasets sem validacao;
- total de avaliacoes do gate;
- total de `ALLOWED`;
- total de `BLOCKED`;
- data/hora da ultima validacao;
- data/hora da ultima avaliacao do gate.

### DashboardService

`DashboardService` e a fachada de aplicacao consumida pelo dashboard. Ele
orquestra:

- listagem e selecao de datasets;
- resumo geral de saude;
- metricas por provider historico;
- qualidade de dataset selecionado;
- readiness do dataset selecionado;
- auditoria e metricas do gate;
- carga controlada do Replay;
- execucao controlada do Research Lab.

Esta concentracao e aceitavel como fachada de aplicacao, mas e o principal
ponto de atencao arquitetural para proximas sprints.

### Replay

`ReplayService` depende de `MarketDataProvider`/`HistoricalDataProvider` para
carregar dados historicos e de `HistoricalDataset` para carga ja resolvida.

`ReplayEngine` continua recebendo apenas `list[Candle]`.

Observacao: `ReplayService.load_historical_csv()` permanece como metodo de
compatibilidade, mas delega para `load_historical_data()` e nao le CSV
diretamente.

### Research Lab

`ResearchLabService` usa `MarketDataProvider` para resolver dados historicos e
executa experimentos com `list[Candle]`.

Observacao: `run_historical_csv_experiment()` permanece como metodo de
compatibilidade, delegando para `run_historical_data_experiment()`.

Exportacao CSV da Alpha001 permanece fora do fluxo Data Source e nao representa
leitura historica de Market Data.

### Dashboard

`dashboard_app.py` consome apenas `DashboardService` para fluxos historicos. Ele
nao importa `market_data`, catalogo, registry, provider, adapters, Parquet,
DuckDB ou repositorio de persistencia.

O dashboard exibe o campo `provider` apenas como metadado entregue pela fachada,
sem instanciar provider nem acessar formato fisico.

## Verificacao de Acessos Diretos

### Acessos Aceitos e Isolados

- CSV fisico:
  - `data/historical_data_loader.py`;
  - `market_data/csv_historical_data_source.py`.
- Parquet fisico:
  - `market_data/parquet_historical_data_adapter.py`.
- DuckDB fisico:
  - `market_data/duckdb_historical_data_adapter.py`.
- Persistencia JSON de qualidade:
  - `market_data/json_historical_dataset_quality_repository.py`.
- Registro de providers:
  - `market_data/historical_data_source_registry.py`.

### Acessos em Camadas Superiores

Foram encontrados nomes legados com `csv` em camadas superiores:

- `ReplayService.load_historical_csv()`;
- `ResearchLabService.run_historical_csv_experiment()`;
- `DashboardService.load_historical_replay_csv()`;
- suporte a upload CSV historico legado em `DashboardService`;
- exportacao CSV da Alpha001.

Classificacao: risco baixo a medio.

Justificativa: os metodos de carga historica com nome CSV delegam para provider
ou sao compatibilidade de UI/upload legado. Nao ha uso direto de
`pandas.read_csv()` nessas camadas. A exportacao CSV da Alpha001 e funcionalidade
separada de resultado de pesquisa, nao fonte historica.

## Aderencia Arquitetural

### Clean Architecture

Status: aderente com ressalvas.

- Dominio continua sem dependencia de infraestrutura.
- Fontes fisicas ficam em adapters.
- Camadas de aplicacao consomem portas/fachadas.
- Ressalva: `DashboardService` concentra muitas responsabilidades de
  orquestracao e deve ser monitorado para nao virar uma camada de dominio
  escondida.

### SOLID

Status: aderente com riscos controlados.

- Open/Closed preservado para novas fontes via registry.
- Dependency Inversion preservada entre provider e `HistoricalDataSource`.
- Single Responsibility esta mais pressionado em `DashboardService`.

### Ports & Adapters

Status: aderente.

- `HistoricalDataSource` funciona como porta para origem historica.
- CSV, Parquet e DuckDB sao adapters concretos.
- Registry/factory compoe adapters sem vazar formato para Replay, Research Lab
  ou Dashboard.

### Event Driven

Status: preservado no escopo atual.

- O fluxo de Replay continua com `EventBus`.
- O Data Readiness Gate registra auditoria estruturada.
- Ainda nao ha publicacao de eventos de validacao/decisao em barramento global,
  o que e aceitavel no estado atual, mas pode evoluir.

## Riscos Remanescentes

### Medio - DashboardService com responsabilidades crescentes

`DashboardService` concentra catalogo, qualidade, readiness, auditoria,
metricas, Replay e Research Lab. O acoplamento ainda e aceitavel como fachada,
mas a manutencao pode ficar mais fragil se novas fontes e novos gates forem
incluidos sem extrair servicos de aplicacao especializados.

Recomendacao: em sprint futura, considerar extrair servicos internos de
aplicacao como `DatasetQualityService`, `DataReadinessGateService` e
`ProviderMetricsService`, mantendo `DashboardService` apenas como fachada.

### Medio - Configuracao composta de DuckDB

DuckDB exige database/table e executa SQL dentro do adapter. Isso esta isolado,
mas deve permanecer opaco para camadas superiores.

Recomendacao: manter qualquer configuracao composta de DuckDB como origem opaca
ou DTO de infraestrutura, nunca como contrato de aplicacao.

### Baixo - Metodos publicos legados com nome CSV

Metodos de compatibilidade ainda carregam `csv` no nome. Eles nao violam a
arquitetura hoje porque delegam ao provider ou tratam upload legado, mas podem
induzir novas implementacoes a reintroduzir leitura direta.

Recomendacao: planejar deprecacao gradual ou wrappers mais genericos, mantendo
retrocompatibilidade enquanto existirem consumidores.

### Baixo - Catalogo ainda manual e em memoria

`HistoricalDatasetCatalog` descobre datasets apenas quando registrados em
memoria. Isso e suficiente para o checkpoint atual, mas a descoberta automatica
de fontes reais exigira adapters de catalogo ou registradores especificos.

Recomendacao: criar uma porta de descoberta de datasets por provider antes de
integrar PostgreSQL, MT5, Nelogica ou B3.

### Baixo - Auditoria do gate em memoria

`InMemoryDataReadinessGateLogger` nao persiste historico entre execucoes. Isso
atende ao estado atual, mas limita auditoria operacional real.

Recomendacao: criar adapter persistente para logs do gate quando a aplicacao
entrar em validacao operacional prolongada.

## Proximas Fontes Possiveis

As fontes abaixo permanecem futuras e nao foram implementadas neste checkpoint:

- PostgreSQL;
- MT5;
- Nelogica;
- B3;
- APIs externas de market data;
- bancos locais especializados em candles.

Todas devem entrar como adapter/provider atras da porta `HistoricalDataSource`,
com testes de contrato para carga, catalogo, qualidade, readiness, auditoria e
metricas por provider.

## Conclusao

A fase Data Source esta formalmente encerrada com CSV, Parquet e DuckDB
preservando a arquitetura Ports & Adapters. Os tres providers estao isolados em
adapters concretos, `HistoricalDataProvider` continua independente da origem
fisica e as camadas superiores seguem consumindo contratos normalizados de
aplicacao.

O estado atual esta apto para avaliar novas fontes, desde que as proximas
sprints mantenham a regra de entrada por adapter/provider e nao exponham
infraestrutura ao Dashboard, Replay, Research Lab ou dominio.
