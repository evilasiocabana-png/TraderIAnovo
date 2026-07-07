# Revisao Arquitetural - Data Source com DuckDB

Data: 2026-06-26

## Objetivo

Consolidar a revisao arquitetural da fase Data Source apos a introducao
completa do provider DuckDB, verificando se CSV, Parquet e DuckDB seguem o
mesmo modelo de Ports & Adapters.

Este documento e um relatorio tecnico interno. Nenhuma funcionalidade e
implementada nesta sprint.

## Escopo Avaliado

Foram avaliados os seguintes componentes:

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

`HistoricalDataProvider` continua dependendo apenas da porta
`HistoricalDataSource`. Ele recebe uma origem opaca, delega a leitura para o
adapter concreto configurado e retorna `HistoricalDataset`.

Estado verificado:

- nao importa CSV, Parquet ou DuckDB diretamente;
- nao usa `pandas`, `Path`, `open()` ou diretorios;
- nao conhece SQL, tabelas, schemas fisicos ou extensoes de arquivo;
- preserva `HistoricalDataset` como contrato normalizado.

### Provider Registry/Factory

`HistoricalDataSourceRegistry` registra factories por nome normalizado.

Providers registrados:

- `csv` -> `CsvHistoricalDataSource`;
- `parquet` -> `ParquetHistoricalDataAdapter`;
- `duckdb` -> `DuckDBHistoricalDataAdapter`.

CSV permanece como provider default por meio de
`create_default_historical_data_source()`.

### CsvHistoricalDataSource

`CsvHistoricalDataSource` encapsula o carregador CSV legado
`HistoricalDataLoader`.

Acesso fisico relacionado a CSV fica restrito a:

- `market_data/csv_historical_data_source.py`;
- `data/historical_data_loader.py`.

O loader legado ainda usa `Path` e `open()` internamente, mas esta atras do
adapter CSV e nao e consumido diretamente por Replay, Research Lab ou Dashboard.

### ParquetHistoricalDataAdapter

`ParquetHistoricalDataAdapter` isola:

- import de `pandas`;
- uso de `Path`;
- chamada `read_parquet`;
- validacao fisica de arquivo;
- normalizacao de colunas;
- conversao para `Candle`.

O adapter retorna `HistoricalDataSourceResult`, mantendo o mesmo contrato usado
pelos demais providers.

### DuckDBHistoricalDataAdapter

`DuckDBHistoricalDataAdapter` isola:

- import de `duckdb`;
- uso de `Path`;
- abertura de conexao DuckDB;
- query SQL;
- validacao de database/table;
- normalizacao de colunas;
- conversao para `Candle`.

O adapter aceita origem opaca simples ou configuracao com `database`/`path` e
`table`. Nenhuma camada superior precisa conhecer conexao, SQL ou tabela.

### HistoricalDatasetCatalog

`HistoricalDatasetCatalog` lista apenas metadados e origem opaca por
`dataset_id`. O catalogo valida o provider informado no registry, mas nao le
CSV, Parquet ou DuckDB.

Metadados expostos:

- `dataset_id`;
- `ativo`;
- `timeframe`;
- `start_date`;
- `end_date`;
- `estimated_candles`;
- `provider`.

### Data Quality

Data Quality opera sobre `HistoricalDataset` ja normalizado. As metricas sao
iguais para CSV, Parquet e DuckDB:

- total de candles;
- data/hora inicial;
- data/hora final;
- OHLC invalido;
- volume invalido ou ausente;
- gaps temporais;
- timestamps duplicados.

Nao ha regra especifica por formato fisico fora dos adapters.

### Data Readiness Gate

O gate usa a ultima validacao/status de qualidade para classificar datasets em:

- `READY_FOR_REPLAY`;
- `READY_FOR_RESEARCH`;
- `READY_FOR_REPLAY_AND_RESEARCH`;
- `NOT_READY`;
- `NOT_VALIDATED`.

CSV, Parquet e DuckDB passam pelas mesmas regras. O bloqueio de Replay e
Research Lab fica centralizado no `DashboardService`.

### Auditoria do Gate

`DataReadinessGateLogger` registra cada decisao com:

- `dataset_id`;
- `provider`;
- data/hora da avaliacao;
- acao solicitada;
- status de prontidao;
- decisao;
- motivos.

CSV, Parquet e DuckDB usam o mesmo contrato de auditoria.

### Metricas por Provider

`DashboardService.get_historical_provider_metrics()` consolida catalogo,
status de qualidade e logs do gate por provider.

Providers minimos retornados:

- `csv`;
- `parquet`;
- `duckdb`.

Metricas por provider:

- datasets catalogados;
- datasets validados;
- datasets aprovados;
- datasets reprovados;
- datasets sem validacao;
- avaliacoes do gate;
- decisoes `ALLOWED`;
- decisoes `BLOCKED`;
- ultima validacao;
- ultima avaliacao do gate.

### DashboardService

`DashboardService` permanece como fachada unica para o dashboard. Ele orquestra:

- catalogo;
- selecao de dataset;
- qualidade;
- readiness;
- auditoria;
- metricas por provider;
- carga controlada do Replay;
- execucao controlada do Research Lab.

Esta concentracao ainda e aceitavel como fachada de aplicacao, mas deve ser
monitorada para nao virar ponto de acoplamento excessivo.

### Replay

`ReplayService` depende de `MarketDataProvider`/`HistoricalDataProvider` para
resolver datasets historicos. `ReplayEngine` continua recebendo apenas
`list[Candle]`.

Estado verificado:

- nao ha acesso direto a Parquet ou DuckDB;
- nao ha `pandas`, `duckdb.connect`, `read_parquet` ou `Path` no Replay;
- existe metodo legado com nome `load_historical_csv`, mantido por
  compatibilidade. O nome e um risco semantico baixo, mas a cadeia de dados ja
  passa pelo provider historico.

### Research Lab

`ResearchLabService` usa provider historico para carregar datasets de pesquisa.
O Research Lab continua trabalhando com `list[Candle]`.

Estado verificado:

- nao ha acesso direto a Parquet ou DuckDB;
- nao ha `pandas`, `duckdb.connect` ou `read_parquet`;
- existem funcoes de exportacao Alpha001 para CSV e uso de `Path`/`open()` para
  escrita de relatorios. Isso nao e leitura historica de Data Source e nao
  representa violacao do fluxo CSV/Parquet/DuckDB.

## Varredura de Acessos Diretos

### Acessos legitimos encontrados

- `data/historical_data_loader.py`: `Path` e `open()` usados pelo loader CSV
  legado atras de `CsvHistoricalDataSource`;
- `market_data/parquet_historical_data_adapter.py`: `pandas`, `Path` e
  `read_parquet` isolados no adapter Parquet;
- `market_data/duckdb_historical_data_adapter.py`: `duckdb`, `Path`, conexao e
  query SQL isolados no adapter DuckDB;
- `market_data/json_historical_dataset_quality_repository.py`: `Path` e
  `open()` isolados no adapter de persistencia de metadados/qualidade.

### Pontos observados sem violacao critica

- `application/dashboard_service.py` usa `Path`/`tempfile` para tratar upload
  temporario e origem opaca de dataset, sem o dashboard acessar arquivos
  diretamente.
- `application/research_lab_service.py` usa CSV/`Path`/`open()` para exportacao
  de resultados Alpha001, fora do fluxo de leitura historica Data Source.
- `dashboard_app.py` contem texto/campo de exportacao Alpha001 para CSV, fora
  do fluxo de providers historicos.

### Ausencias relevantes

- `dashboard_app.py` nao importa catalogo, registry, providers, adapters,
  persistencia, `pandas`, `duckdb`, `Path` ou `open()`.
- `ReplayEngine` nao conhece CSV, Parquet, DuckDB ou persistencia.
- Dominio e contratos permanecem sem dependencia de infraestrutura.

## Aderencia Arquitetural

### Clean Architecture

Status: aderente.

As dependencias continuam apontando para dentro: dominio e contratos nao
dependem de infraestrutura; aplicacao orquestra casos de uso; adapters ficam em
`market_data` e infraestrutura auxiliar.

### SOLID

Status: aderente com ponto de atencao.

Cada adapter possui responsabilidade unica sobre sua origem fisica. O registry
permite extensao por novos providers. O ponto de atencao e o crescimento de
`DashboardService`, que concentra muitas orquestracoes de aplicacao.

### Event Driven

Status: parcialmente aderente ao escopo atual.

O sistema possui `EventBus` e auditoria estruturada do gate, mas a auditoria de
readiness ainda e chamada diretamente pela fachada. Nao ha violacao critica,
mas uma futura evolucao pode transformar decisoes do gate em eventos de
aplicacao persistiveis.

### Ports & Adapters

Status: aderente.

CSV, Parquet e DuckDB sao adapters concretos atras da porta
`HistoricalDataSource`. `HistoricalDataProvider`, Replay, Research Lab e
DashboardService consomem contratos normalizados, nao formatos fisicos.

## Riscos Classificados

### Medio - DashboardService como fachada ampla

`DashboardService` acumula catalogo, selecao, qualidade, readiness, auditoria,
metricas, Replay e Research Lab. A fachada ainda protege o dashboard, mas pode
dificultar manutencao se novas fontes e novas politicas de qualidade crescerem.

Recomendacao: em sprint futura, extrair servicos de aplicacao internos para
Data Quality, Readiness e Provider Metrics, mantendo o `DashboardService` como
fachada publica.

### Medio - Adapter DuckDB aceita SQL/table como configuracao opaca

DuckDB introduz tabela e SQL. Hoje isso esta isolado no adapter, mas ha risco
de chamadas futuras passarem a montar queries fora dele.

Recomendacao: manter a origem DuckDB como objeto opaco e criar, se necessario,
um DTO de infraestrutura especifico do adapter sem expor SQL a camadas
superiores.

### Baixo - Nomes legados com CSV em servicos de aplicacao

Existem nomes como `load_historical_csv` e `run_historical_csv_experiment` por
compatibilidade. Eles podem induzir futuras sprints a pensar em CSV como
contrato.

Recomendacao: criar aliases neutros e planejar deprecacao documental dos nomes
legados, preservando retrocompatibilidade ate todos os consumidores migrarem.

### Baixo - Persistencia de qualidade em JSON local

`JsonHistoricalDatasetQualityRepository` usa arquivo local para persistir
metadados e historico. A dependencia esta isolada em adapter, mas nao e ideal
para auditoria multiusuario ou historico de longo prazo.

Recomendacao: manter como adapter simples ate uma sprint explicita de
persistencia operacional.

### Baixo - Duplicacao de parsing entre Parquet e DuckDB

Parquet e DuckDB possuem logica parecida de normalizacao e conversao para
`Candle`.

Recomendacao: considerar extrair helper interno de normalizacao somente se a
duplicacao crescer; nao antecipar abstracao antes de nova fonte real ou aumento
de complexidade.

## Violacoes Encontradas

Nao foram encontradas violacoes criticas de Clean Architecture, SOLID,
Event Driven ou Ports & Adapters no fluxo Data Source com DuckDB.

Nao foram encontrados acessos diretos indevidos a CSV, Parquet, DuckDB,
`pandas`, `Path`, `open()`, diretorios, arquivos, providers ou persistencia em
Replay, ReplayEngine, Research Lab, Dashboard ou dominio dentro do fluxo de
leitura historica.

## Recomendacoes para Proximas Sprints

1. Criar servicos de aplicacao internos para Data Quality, Readiness e metricas
   por provider, mantendo `DashboardService` apenas como fachada publica.
2. Planejar aliases neutros para metodos legados com `csv` no nome, com
   retrocompatibilidade.
3. Definir contrato opaco mais explicito para fontes que exigem configuracao
   composta, como DuckDB e futuros bancos relacionais.
4. Evoluir auditoria do Data Readiness Gate para adapter persistente quando a
   rastreabilidade precisar sobreviver ao ciclo de vida da aplicacao.
5. Manter testes de contrato comparativo obrigatorios para toda nova fonte:
   CSV, Parquet, DuckDB, PostgreSQL, MT5 ou Nelogica.
6. Preservar a regra de que dashboard visual acessa dados historicos apenas via
   `DashboardService`.

## Conclusao

A fase Data Source com DuckDB preserva o modelo Ports & Adapters. CSV, Parquet
e DuckDB estao isolados em adapters concretos, o registry permite selecao por
provider, `HistoricalDataProvider` permanece independente da origem fisica e
Replay/Research Lab continuam consumindo dados normalizados como
`HistoricalDataset` ou `list[Candle]`.

O principal risco atual nao e uma violacao, mas a concentracao crescente de
orquestracao em `DashboardService`. A proxima evolucao arquitetural deve
priorizar a decomposicao interna dessa fachada sem expor infraestrutura ao
dashboard.
