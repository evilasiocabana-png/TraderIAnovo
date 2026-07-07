# Market Data Architecture

## 1. Objetivo

Definir a arquitetura oficial para ingestao de dados historicos e dados em
tempo real no TraderIA_WDO.

Este documento e exclusivamente arquitetural. Ele nao implementa codigo, nao
cria providers concretos, nao altera Replay, nao altera Research Lab, nao
altera Dashboard e nao autoriza integracao com corretora, MT5, B3, Nelogica ou
qualquer API externa.

## 2. Principios

- Dados de mercado entram na plataforma por portas oficiais.
- Fontes fisicas permanecem isoladas em adapters.
- Replay nunca acessa arquivos, bancos, APIs ou formatos fisicos diretamente.
- Research Lab nunca acessa arquivos, bancos, APIs ou formatos fisicos
  diretamente.
- Dashboard consome Market Data apenas por fachadas de aplicacao.
- Dados historicos e dados em tempo real compartilham contratos normalizados.
- Validacao, qualidade e readiness acontecem antes de alimentar Replay,
  Research Lab, Feature Lab ou estrategias.
- EventBus pode distribuir eventos normalizados, mas nao deve conhecer adapters
  concretos.

## 3. Componentes Oficiais

### DataProvider

`DataProvider` representa a porta conceitual de entrada de dados de mercado.

Responsabilidades:

- expor dados normalizados para a camada de aplicacao;
- esconder detalhes de origem fisica;
- manter contrato comum entre historico e tempo real;
- entregar dados em formato aceito pelo Data Lab e pelos consumidores
  autorizados.

Nao deve:

- conhecer CSV, Parquet, DuckDB, PostgreSQL, MT5, Nelogica ou B3 diretamente;
- abrir arquivos;
- executar queries diretamente;
- publicar ordens;
- acionar estrategias.

### HistoricalDataProvider

`HistoricalDataProvider` e o ponto autorizado para resolucao de datasets
historicos.

Responsabilidades:

- receber uma origem historica opaca;
- delegar leitura ao adapter registrado;
- retornar dataset historico normalizado;
- expor metadados do catalogo historico;
- alimentar Data Quality, ReplayService e ResearchLabService por contratos
  normalizados.

Adapters historicos permitidos pela arquitetura:

- CSV adapter;
- Parquet adapter;
- DuckDB adapter;
- futuros adapters PostgreSQL, B3, Nelogica ou outros, somente por missao
  explicita.

O `HistoricalDataProvider` nao deve conhecer detalhes de formato fisico.

### LiveDataProvider

`LiveDataProvider` sera a porta oficial futura para dados em tempo real.

Responsabilidades:

- receber ticks, candles parciais ou candles fechados de uma fonte live;
- normalizar eventos de mercado;
- publicar eventos de dados no fluxo oficial;
- preservar isolamento entre infraestrutura externa e plataforma;
- permitir consumo por Feature Lab, Context Lab, Decision Lab e simuladores
  autorizados.

Nao deve:

- enviar ordens;
- acessar Broker operacional;
- acionar Strategy diretamente;
- recalcular indicadores complexos;
- substituir Replay;
- escrever em banco sem missao explicita;
- autorizar operacao real.

Qualquer provider live concreto deve ser adapter de infraestrutura e depender
da porta, nunca o contrario.

## 4. Contratos

### MarketDataContract

Contrato normalizado de candle:

- `symbol`;
- `timeframe`;
- `timestamp`;
- `open`;
- `high`;
- `low`;
- `close`;
- `volume`;
- `is_valid`;
- `metadata`.

Uso esperado:

- Data Lab;
- Feature Lab;
- Context Lab;
- Research Lab;
- Replay;
- validadores de qualidade.

### HistoricalDataset

Contrato agregado para datasets historicos.

Uso esperado:

- entrega de candles carregados por `HistoricalDataProvider`;
- catalogacao;
- Data Quality;
- ReplayService;
- ResearchLabService.

### MarketDataEvent

Contrato futuro para eventos de dados normalizados.

Campos conceituais minimos:

- `event_id`;
- `symbol`;
- `timeframe`;
- `timestamp`;
- `event_type`;
- `payload`;
- `provider_id`;
- `sequence`;
- `metadata`.

Tipos de evento previstos:

- `HISTORICAL_DATASET_LOADED`;
- `CANDLE_VALIDATED`;
- `CANDLE_REJECTED`;
- `LIVE_TICK_RECEIVED`;
- `LIVE_CANDLE_UPDATED`;
- `LIVE_CANDLE_CLOSED`;
- `DATA_QUALITY_UPDATED`;
- `DATA_READY_FOR_REPLAY`;
- `DATA_READY_FOR_RESEARCH`.

Este documento nao cria o contrato em codigo.

## 5. Fluxo Historico

```text
Fonte historica opaca
        |
        v
Historical Adapter
        |
        v
HistoricalDataProvider
        |
        v
HistoricalDataset / MarketDataContract
        |
        v
DataPipeline
        |
        +--> CandleValidator
        +--> MarketDataQualityEngine
        +--> Data Readiness Gate
        |
        v
Application Services
        |
        +--> ReplayService -> ReplayEngine
        +--> ResearchLabService -> Research Lab
```

Regras:

- ReplayEngine recebe apenas candles normalizados.
- Research Lab recebe apenas datasets/candles normalizados.
- Nenhum consumidor superior acessa CSV, Parquet, DuckDB, Path, pandas, SQL ou
  arquivos.

## 6. Fluxo em Tempo Real

```text
Fonte live externa
        |
        v
Live Adapter
        |
        v
LiveDataProvider
        |
        v
MarketDataEvent / MarketDataContract
        |
        v
EventBus
        |
        +--> DataPipeline
        +--> FeaturePipeline
        +--> ContextPipeline
        +--> Decision Lab
        +--> Monitoramento autorizado
```

Regras:

- Live adapter isola API externa, socket, streaming, autenticacao e formato
  nativo.
- LiveDataProvider publica apenas dados normalizados.
- EventBus distribui eventos, mas nao conhece provider concreto.
- Estrategias continuam retornando apenas `StrategySignal`.
- Nenhum fluxo live autoriza envio de ordem real.

## 7. Fluxo de Eventos

O fluxo oficial de eventos deve seguir o padrao:

```text
Provider
  -> Normalizacao
  -> Validacao
  -> Evento normalizado
  -> EventBus
  -> Consumidores autorizados
```

Eventos de dados devem ser idempotentes quando possivel, rastreaveis por
`event_id` e ordenaveis por `timestamp` e `sequence`.

Consumidores autorizados:

- Data Lab;
- Feature Lab;
- Context Lab;
- ReplayService;
- ResearchLabService;
- DashboardService;
- logs e auditoria, quando aprovados.

Consumidores proibidos:

- estrategias acessando provider diretamente;
- Dashboard acessando provider diretamente;
- Domain acessando infraestrutura;
- DecisionPipeline acessando fonte fisica;
- qualquer executor de ordem real.

## 8. Integracao com Replay

Replay deve consumir dados historicos exclusivamente via camada de aplicacao.

Fluxo autorizado:

```text
HistoricalDataProvider
  -> HistoricalDataset
  -> Data Quality / Readiness
  -> ReplayService
  -> ReplayEngine
```

Regras:

- ReplayEngine nao carrega dados.
- ReplayEngine nao conhece provider.
- ReplayEngine nao conhece catalogo.
- ReplayEngine nao conhece arquivo, banco, CSV, Parquet ou DuckDB.
- ReplayService e o ponto de orquestracao autorizado.

## 9. Integracao com Research Lab

Research Lab deve consumir datasets historicos e resultados de qualidade por
`ResearchLabService`.

Fluxo autorizado:

```text
HistoricalDataProvider
  -> HistoricalDataset
  -> Data Quality / Readiness
  -> ResearchLabService
  -> Research Lab / ResearchPipeline
```

Regras:

- Research Lab nao resolve fonte fisica.
- ResearchPipeline nao acessa providers concretos.
- Experimentos recebem candles/datasets normalizados.
- Validation, Benchmark, Portfolio e Knowledge Base consomem resultados de
  pesquisa, nao fontes de dados.

## 10. Catalogo e Metadados

O catalogo historico deve expor apenas metadados e referencias opacas.

Metadados permitidos:

- `dataset_id`;
- `symbol`;
- `timeframe`;
- `period`;
- `provider_id`;
- `format`;
- `schema_version`;
- `quality_status`;
- `readiness_status`;
- `fingerprint`;
- `metadata`.

O catalogo nao deve expor caminhos fisicos para Dashboard, Replay ou Research
Lab.

## 11. Qualidade e Readiness

Todo dado deve passar por validacao antes de alimentar fluxos sensiveis.

Etapas:

- validacao de candle;
- avaliacao de qualidade;
- deteccao de gaps e duplicidades;
- classificacao de readiness;
- auditoria da decisao;
- liberacao para Replay, Research ou ambos.

Estados previstos:

- `READY_FOR_REPLAY`;
- `READY_FOR_RESEARCH`;
- `READY_FOR_REPLAY_AND_RESEARCH`;
- `NOT_READY`;
- `NOT_VALIDATED`.

## 12. Proibicoes

E proibido:

- Replay acessar fonte fisica diretamente;
- Research Lab acessar fonte fisica diretamente;
- Dashboard acessar provider diretamente;
- estrategia carregar dados;
- Domain depender de provider, arquivo, API externa ou banco;
- LiveDataProvider enviar ordem;
- EventBus conhecer adapter concreto;
- adapters concretos vazarem para camadas superiores;
- criar integracao real com corretora sem missao explicita;
- persistir candles sem missao explicita.

## 13. Evolucao Recomendada

Ordem recomendada para evolucao futura:

1. Formalizar contratos `DataProvider`, `HistoricalDataProvider` e
   `LiveDataProvider`.
2. Formalizar `MarketDataEvent`.
3. Criar registry de providers live.
4. Criar adapters live simulados antes de qualquer fonte externa real.
5. Integrar eventos live ao EventBus.
6. Integrar Data Quality ao fluxo live.
7. Criar replay de eventos live gravados, somente por missao futura.
8. Avaliar persistencia de candles, somente por missao futura.

## 14. Status Arquitetural

Status:

`MARKET_DATA_ARCHITECTURE_DEFINED`

Esta arquitetura preserva Clean Architecture, Ports & Adapters, SOLID e
Event Driven Architecture.

Nenhum codigo foi implementado.
Nenhuma integracao externa foi criada.
Nenhuma logica operacional foi alterada.
