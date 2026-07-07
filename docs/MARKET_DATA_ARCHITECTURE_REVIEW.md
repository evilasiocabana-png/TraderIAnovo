# Revisao Arquitetural - Sprint Market Data

Data: 2026-06-26

## Objetivo

Consolidar o estado atual da arquitetura de Market Data antes da evolucao para
novas fontes historicas como Parquet, DuckDB ou PostgreSQL.

Este documento nao introduz nova funcionalidade. Ele registra dependencias,
acoplamentos remanescentes, riscos e recomendacoes para as proximas sprints.

## Checkpoint Final - Sprint Market Data 030

Este checkpoint encerra formalmente a Sprint Market Data e fixa o estado
arquitetural estavel antes da entrada de novas fontes fisicas de dados.

O estado final aprovado e:

- `MarketDataProvider` e a fachada de carregamento historico para camadas de
  aplicacao;
- `HistoricalDataProvider` transforma uma origem opaca em `HistoricalDataset`;
- `HistoricalDataSource` isola a fonte fisica por adaptador;
- `HistoricalDatasetCatalog` lista metadados de datasets sem expor arquivos;
- Data Quality valida candles carregados via provider;
- Data Readiness Gate decide se o dataset pode alimentar Replay, Research Lab
  ou ambos;
- `ReplayService` orquestra Replay usando dataset/candles resolvidos via Market
  Data;
- `ReplayEngine` recebe apenas `list[Candle]`;
- `ResearchLabService` orquestra experimentos usando dataset/candles resolvidos
  via Market Data;
- `ResearchLab` recebe apenas `list[Candle]`;
- `DashboardService` e a unica fachada consumida pelo dashboard visual;
- `dashboard_app.py` nao acessa infraestrutura de Market Data diretamente.

## Regras Arquiteturais Obrigatorias

Estas regras devem ser preservadas em qualquer sprint futura:

- Replay nunca acessa CSV diretamente.
- Replay nunca acessa `pandas`, `Path`, `open()`, diretorios ou arquivos para
  carregar dados historicos.
- Research Lab nunca acessa CSV diretamente para carregar dados historicos.
- Research Lab nunca acessa `pandas`, `Path`, `open()`, diretorios ou arquivos
  para resolver datasets historicos.
- Dashboard nunca acessa provider, catalogo, registry, persistencia, adapter
  CSV, `Path`, `pandas`, diretorios ou arquivos diretamente.
- Dashboard consome dados historicos, qualidade, readiness, auditoria e metricas
  exclusivamente via `DashboardService`.
- Toda nova fonte fisica deve entrar como adapter/provider atras da porta
  `HistoricalDataSource`.
- `HistoricalDataProvider` nao deve conhecer o formato fisico da fonte.
- `HistoricalDataset` continua sendo o objeto normalizado entregue as camadas de
  aplicacao.
- Candles historicos nao devem ser persistidos ate existir uma missao explicita
  para isso.
- Exportacoes CSV da Alpha001 permanecem separadas do fluxo de Market Data.

## Fluxo Atual

```text
Dashboard
  -> DashboardService
      -> HistoricalDatasetCatalog
      -> HistoricalDataProvider
          -> HistoricalDataSource
              -> CsvHistoricalDataSource
                  -> HistoricalDataLoader
      -> HistoricalDataset
      -> Data Quality
      -> Data Readiness Gate
      -> ReplayService
          -> ReplayEngine
      -> ResearchLabService
          -> ResearchLab
      -> HistoricalDatasetQualityRepository
          -> JsonHistoricalDatasetQualityRepository
      -> DataReadinessGateLogger
          -> InMemoryDataReadinessGateLogger
```

## Dependencias Documentadas

### MarketDataProvider

`MarketDataProvider` e a interface de alto nivel consumida por servicos de
aplicacao que precisam carregar dados historicos. `HistoricalDataProvider`
implementa essa interface e retorna sempre `HistoricalDataset`.

### HistoricalDataProvider

`HistoricalDataProvider` depende apenas de `HistoricalDataSource`, nao conhece
CSV diretamente e nao importa `CsvHistoricalDataSource`.

Responsabilidade atual:

- carregar uma origem opaca;
- normalizar o resultado em `HistoricalDataset`;
- expor erros da fonte concreta;
- manter lista simples de datasets carregados em memoria.

### HistoricalDataSource e Adaptador CSV

`HistoricalDataSource` e a porta para fontes fisicas. `CsvHistoricalDataSource`
e a implementacao concreta atual e encapsula o uso do `HistoricalDataLoader`.

CSV esta isolado em:

- `market_data/csv_historical_data_source.py`;
- `data/historical_data_loader.py`;
- registry default em `market_data/historical_data_source_registry.py`.

### HistoricalDataset

`HistoricalDataset` permanece como objeto de transporte normalizado contendo:

- symbol;
- timeframe;
- start_date;
- end_date;
- list[Candle].

Replay e Research Lab continuam trabalhando com `list[Candle]` no nucleo de
execucao, sem conhecer CSV.

### HistoricalDatasetCatalog

O catalogo expoe metadados e fontes opacas por `dataset_id`.

Metadados expostos:

- dataset_id;
- ativo;
- timeframe;
- start_date;
- end_date;
- estimated_candles;
- provider.

Nao ha listagem de diretorios no catalogo.

### Data Quality

O relatorio de qualidade e produzido em `DashboardService` a partir do dataset
resolvido via `HistoricalDataProvider`.

Metricas atuais:

- total de candles;
- data/hora inicial;
- data/hora final;
- OHLC invalido;
- volume invalido;
- gaps temporais;
- timestamps duplicados.

O resultado e persistido como metadado/status, sem persistir candles.

### Data Readiness Gate

O gate classifica o dataset selecionado em:

- `READY_FOR_REPLAY`;
- `READY_FOR_RESEARCH`;
- `READY_FOR_REPLAY_AND_RESEARCH`;
- `NOT_READY`;
- `NOT_VALIDATED`.

O bloqueio obrigatorio esta centralizado em `DashboardService` antes de:

- carregar Replay;
- executar Research Lab.

O gate registra auditoria estruturada via porta `DataReadinessGateLogger`.

### Replay

`ReplayService` depende de `MarketDataProvider` e `HistoricalDataset`.
`ReplayEngine` recebe apenas `list[Candle]`.

Ponto importante:

- `ReplayService.load_historical_csv()` ainda existe como metodo de
  compatibilidade, mas delega para `load_historical_data()` e passa pela camada
  de Market Data.

### Research Lab

`ResearchLabService` depende de `MarketDataProvider` para resolver dados
historicos. O `ResearchLab` executa sobre `list[Candle]`.

Pontos importantes:

- `run_historical_csv_experiment()` ainda existe como metodo de compatibilidade,
  mas delega para `run_historical_data_experiment()`;
- exportacao CSV da Alpha001 permanece separada do fluxo de Market Data.

### DashboardService

`DashboardService` e a fachada da interface e concentra:

- catalogo de datasets;
- selecao de dataset;
- carregamento orquestrado de Replay;
- execucao orquestrada de Research Lab;
- qualidade do dataset;
- persistencia de status/historico de qualidade via porta;
- Data Readiness Gate;
- auditoria e metricas do gate.

Este e o principal ponto de acoplamento de aplicacao. A decisao e aceitavel
enquanto ele seguir como fachada/orquestrador, mas merece atencao por tamanho e
numero de responsabilidades.

### Dashboard

O dashboard visual consome apenas `DashboardService`.

Nao ha imports diretos de:

- `market_data`;
- catalogo;
- provider;
- registry;
- adaptador CSV;
- repositores de qualidade;
- logger do readiness gate.

Observacao: ha UI de exportacao CSV da Alpha001, mas ela chama
`DashboardService.export_alpha001_results_to_csv()` e nao manipula CSV
diretamente.

## Varredura de Acessos Diretos

### CSV

Achados esperados e aceitaveis:

- `market_data/csv_historical_data_source.py`;
- `data/historical_data_loader.py`;
- `market_data/historical_data_source_registry.py`, como registro default;
- exportacao Alpha001 em `application/research_lab_service.py`;
- metodos legados de compatibilidade em `ReplayService`, `ResearchLabService` e
  `DashboardService`.

Risco: metodos com nome `csv` em camadas de aplicacao podem induzir novas
features a usar CSV como conceito de aplicacao em vez de origem concreta via
provider.

### pandas

Nao foram encontrados usos de `pandas` nos arquivos de producao analisados.

### Path, open(), diretorios e arquivos

Achados aceitaveis:

- `data/historical_data_loader.py`: leitura fisica do CSV legado;
- `market_data/json_historical_dataset_quality_repository.py`: persistencia JSON
  de metadados/status/historico de qualidade;
- `application/research_lab_service.py`: exportacao explicita de resultados
  Alpha001;
- `application/dashboard_service.py`: suporte legado a upload CSV temporario.

Nao foram encontrados acessos diretos a arquivos no dashboard visual para o
fluxo de datasets historicos.

### Providers, registry e persistencia no Dashboard

Nao foram encontrados imports diretos de provider, registry, catalogo ou
persistencia no `dashboard_app.py`.

## Acoplamentos Remanescentes

### 1. DashboardService concentra muitas responsabilidades

Severidade: Media

`DashboardService` atua como fachada, mas hoje tambem contem regras de qualidade,
readiness, persistencia de status, auditoria do gate, metricas do gate e suporte
legado a upload CSV.

Impacto:

- arquivo cresce rapidamente;
- novas regras de qualidade/readiness podem aumentar a complexidade;
- testes continuam robustos, mas a evolucao para multiplas fontes pode ficar mais
  trabalhosa.

Recomendacao:

- extrair, em sprint futura, servicos de aplicacao pequenos:
  - `HistoricalDatasetQualityService`;
  - `DataReadinessGateService`;
  - `DataReadinessAuditService`.

### 2. Metodos legados com nomenclatura CSV na aplicacao

Severidade: Media

Ainda existem:

- `DashboardService.load_historical_replay_csv()`;
- `ReplayService.load_historical_csv()`;
- `ResearchLabService.run_historical_csv_experiment()`.

Eles delegam para providers e mantem compatibilidade, mas o nome explicita CSV
em uma camada que ja deveria falar em dataset/source.

Impacto:

- risco de futuras chamadas pularem a selecao por dataset/catalogo;
- risco semantico quando Parquet/DuckDB/PostgreSQL entrarem no projeto.

Recomendacao:

- marcar esses metodos como compatibilidade legada;
- introduzir nomes neutros:
  - `load_historical_data()`;
  - `run_historical_data_experiment()`;
  - `load_selected_historical_dataset_to_replay()`.

### 3. Registry default ainda importa adaptador CSV diretamente

Severidade: Baixa

`historical_data_source_registry.py` registra CSV como default importando
`CsvHistoricalDataSource`.

Impacto:

- aceitavel para o estado atual;
- ao adicionar DuckDB/Parquet/PostgreSQL, esse modulo pode virar ponto de
  configuracao central.

Recomendacao:

- manter enquanto houver uma unica fonte;
- quando houver multiplas fontes reais, criar bootstrap de infraestrutura para
  registrar adaptadores fora do nucleo do registry.

### 4. Persistencia JSON dentro de `market_data`

Severidade: Baixa

`JsonHistoricalDatasetQualityRepository` esta em `market_data`, junto dos
contratos e adaptadores. Funciona como primeiro adaptador, mas mistura pacote de
porta e implementacao concreta.

Impacto:

- aceitavel no projeto atual;
- pode ficar menos claro quando surgirem PostgreSQL/DuckDB.

Recomendacao:

- em sprint futura, considerar subpacotes:
  - `market_data/ports`;
  - `market_data/adapters`;
  - ou `infrastructure/market_data`.

### 5. Readiness Gate usa thresholds simples

Severidade: Baixa

O gate diferencia Replay/Research por regras simples:

- um candle limpo libera Replay;
- gaps liberam Research mas bloqueiam Replay;
- sem gaps e amostra suficiente libera ambos.

Impacto:

- bom para MVP;
- a regra de amostra minima para Research provavelmente precisara de calibragem
  estatistica.

Recomendacao:

- parametrizar criterios por timeframe/estrategia em sprint futura.

## Violacoes Encontradas

Nao foram encontradas violacoes criticas no fluxo novo de Market Data.

Pontos de atencao, nao classificados como violacoes criticas:

- nomenclatura CSV legada em metodos de aplicacao;
- `DashboardService` muito concentrado;
- registry default acoplado ao adaptador CSV;
- persistencia JSON ainda no pacote `market_data`.

## Riscos por Severidade

### Alta

Nenhum risco alto identificado no estado atual.

### Media

- crescimento do `DashboardService` como fachada com excesso de regras;
- metodos legados com nome CSV em camadas de aplicacao.

### Baixa

- registry default importando CSV diretamente;
- persistencia JSON no pacote `market_data`;
- thresholds de readiness ainda simples;
- Data Readiness Gate Logger default em memoria nao sobrevive a reinicio da
  aplicacao.

## Recomendacoes para Proximas Sprints

1. Extrair `DataReadinessGateService` para reduzir responsabilidade do
   `DashboardService`.
2. Extrair `HistoricalDatasetQualityService` para concentrar metricas e
   validacoes de dataset.
3. Tornar os metodos legados com `csv` explicitamente deprecated ou escondidos
   da UI.
4. Criar bootstrap de infraestrutura para registrar adaptadores historicos.
5. Preparar estrutura de pastas para portas e adaptadores de Market Data antes
   de adicionar DuckDB/Parquet/PostgreSQL.
6. Persistir auditoria do Data Readiness Gate caso ela precise sobreviver a
   reinicio do sistema.
7. Definir criterios configuraveis de readiness por uso:
   - Replay;
   - Research Lab;
   - estrategia;
   - timeframe.

## Conclusao

A arquitetura atual preserva o objetivo principal das sprints Market Data:
Replay, Research Lab e Dashboard nao dependem diretamente da origem fisica dos
dados historicos.

O fluxo novo esta pronto para receber novas fontes desde que a proxima etapa
adicione adaptadores atras da porta `HistoricalDataSource` e evite reintroduzir
CSV, caminhos ou arquivos nas camadas superiores.

## Fontes Futuras Possiveis

As fontes abaixo ficam registradas apenas como proximas possibilidades
arquiteturais. Nenhuma delas foi implementada neste checkpoint:

- Parquet;
- DuckDB;
- PostgreSQL;
- MT5;
- Nelogica;
- outras fontes historicas plugadas por novo adapter de
  `HistoricalDataSource`.
