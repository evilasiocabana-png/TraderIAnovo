# TraderIA Architecture Bible v1

## 1. Visao geral do TraderIA_WDO

O TraderIA_WDO e uma plataforma modular para estudo, simulacao e evolucao de
um sistema operacional voltado ao mini dolar WDO. O projeto organiza leitura de
mercado, estrategias, risco, replay, pesquisa quantitativa e dashboard em
camadas separadas.

Esta Bible registra as decisoes arquiteturais centrais do sistema. Ela deve
servir como referencia para desenvolvimento futuro e como base de conhecimento
para um GPT especializado chamado TraderIA Architect.

## 2. Objetivo do projeto

O objetivo do TraderIA_WDO e construir uma base limpa e expansivel para:

- analisar contexto de mercado;
- gerar sinais de estrategia;
- simular decisoes e operacoes paper;
- executar replays candle a candle;
- pesquisar resultados quantitativos;
- preparar, com seguranca, uma evolucao futura para operacao real.

O sistema nao nasce como um robo real conectado a corretora. Primeiro ele
consolida dominio, contratos, simulacao, replay, pesquisa e controles de risco.

## 3. Principios arquiteturais

O projeto segue Clean Architecture, SOLID e separacao de responsabilidades.

Principios centrais:

- dominio puro, sem infraestrutura;
- estrategias sem execucao de ordens;
- aplicacao como fachada para interfaces externas;
- infraestrutura isolada em adaptadores;
- contratos explicitos entre modulos;
- estado operacional em memoria nas sprints atuais;
- seguranca antes de qualquer possibilidade de ordem real;
- testes automatizados protegendo regras arquiteturais.

## 3.1 ANALISE DE IMPACTO OBRIGATORIA

Sempre que uma missao modificar uma API publica, contrato, interface, servico
de aplicacao, metodo publico ou comportamento compartilhado, deve existir uma
analise de impacto antes da entrega.

Componentes publicos incluem, entre outros:

- `DashboardService`;
- `ReplayService`;
- `ResearchLabService`;
- `ConfigurationService`;
- `MarketDataProvider`;
- `HistoricalDataProvider`;
- `EventBus`;
- `DecisionPipeline`;
- Domain Contracts;
- DTOs;
- interfaces;
- protocols;
- providers.

Antes de encerrar a implementacao, o Codex deve:

1. identificar consumidores do componente alterado;
2. verificar compatibilidade dos consumidores;
3. corrigir regressoes encontradas;
4. atualizar chamadas afetadas quando necessario;
5. executar nova validacao funcional completa.

Nao e permitido concluir uma missao quando qualquer consumidor conhecido
permanece quebrado. Regresses como `AttributeError`, `ImportError`,
`ModuleNotFoundError`, `TypeError` por assinatura, metodo publico removido,
contrato incompativel, quebra de Dashboard, quebra de Replay, quebra de
Research Lab ou quebra de integracao entre modulos devem ser eliminadas antes
da entrega.

Sempre que possivel, a retrocompatibilidade deve ser preservada. Se ela nao
for possivel, todos os consumidores conhecidos da API devem ser atualizados
antes da conclusao.

## 3.2 VALIDACAO FUNCIONAL OBRIGATORIA

A Sprint Market Data consolidou uma regra de governanca: uma entrega nao e
considerada aprovada apenas porque o codigo compila, os testes unitarios passam
ou o `AppTest` nao apresenta excecoes.

### VALIDAÇÃO POR RISCO

O TraderIA usa politica de validação por risco para equilibrar seguranca
arquitetural e velocidade de execucao.

#### BAIXO RISCO

Sao missoes de BAIXO RISCO:

- documentação;
- testes isolados;
- refatoração interna sem mudança de API pública;
- mudanças que não afetam Dashboard, Replay, Research Lab,
  `MarketDataProvider`, `HistoricalDataProvider`, `EventBus` ou contratos.

Validacao obrigatoria para BAIXO RISCO:

- `python app.py`;
- `python -m unittest discover -s tests`.

#### ALTO RISCO

Sao missoes de ALTO RISCO:

- alteracao em Dashboard;
- alteracao em `DashboardService`;
- alteracao em `ReplayService`;
- alteracao em `ResearchLabService`;
- alteracao em `MarketDataProvider`;
- alteracao em `HistoricalDataProvider`;
- alteracao em registry/factory de providers;
- alteracao em contratos publicos;
- alteracao em `st.session_state`;
- criacao, remocao ou mudanca de metodo publico;
- alteracao em fluxos de Replay, Research Lab ou Dataset Management.

Validacao obrigatoria para ALTO RISCO:

- `python app.py`;
- `python -m unittest discover -s tests`;
- `python -m streamlit run dashboard_app.py`;
- validacao dos fluxos principais impactados.

Se houver dúvida sobre o risco da missão, classificar como ALTO RISCO.

Validacao minima para missoes que alterem comportamento ou servicos consumidos
pela interface:

- `python app.py` deve executar sem erros;
- `python -m unittest discover -s tests` deve executar com sucesso;
- `python -m streamlit run dashboard_app.py` deve iniciar corretamente quando a
  mudanca envolver dashboard, `DashboardService` ou servicos consumidos pelo
  dashboard;
- Home, Replay, Research Lab, Estrategias, Eventos e Sistema devem permanecer
  funcionais;
- logs nao podem apresentar novas excecoes.

O projeto passa a reconhecer quatro niveis oficiais de validacao:

- Unit Tests;
- Integration Tests;
- Streamlit AppTest;
- End-to-End Validation.

Criterio arquitetural superior:

> A aplicacao funcionando possui prioridade superior ao simples fato de todos os
> testes estarem verdes.

## 3.3 CORRECAO EM CASCATA

Quando uma correcao revelar novos erros, a investigacao deve continuar ate que
a aplicacao esteja operacional. Nao se deve encerrar uma missao apos eliminar
apenas o primeiro erro se a aplicacao ainda nao funciona corretamente.

Em missões de ALTO RISCO, erros em cascata devem ser corrigidos em sequencia
ate que o app fique operacional.

Sao proibidos:

- ocultar excecoes;
- silenciar erros;
- remover funcionalidades apenas para fazer testes passarem;
- criar solucao temporaria sem justificativa arquitetural;
- contornar sintomas sem corrigir causa raiz.

Toda correcao deve preservar Clean Architecture, SOLID, Event Driven, Ports &
Adapters e os contratos do dominio.

## 3.4 Compatibilidade da interface

Sempre que uma mudanca alterar servicos consumidos pelo dashboard, a entrega
deve validar:

- compatibilidade dos metodos publicos;
- assinaturas dos metodos;
- inicializacao do dashboard;
- funcionamento de `st.session_state`;
- inexistencia de `AttributeError`;
- persistencia de estado quando aplicavel, como no Replay.

O dashboard continua proibido de acessar catalogos, providers, persistencia,
CSV, Path, pandas, diretorios ou arquivos diretamente. A interface visual deve
consumir apenas `DashboardService`.

## 3.4.1 PROIBICAO DE WORKAROUNDS

Workarounds visuais ou silenciosos nao sao aceitaveis como criterio de
conclusao. O projeto deve corrigir a causa raiz e preservar comportamento
funcional.

## 3.5 Autonomia controlada do Codex

O Codex pode investigar livremente a causa raiz, alterar a estrategia tecnica
quando necessario e continuar corrigindo erros sucessivos sem aguardar nova
autorizacao, desde que:

- preserve Clean Architecture;
- preserve SOLID;
- preserve Event Driven;
- preserve Ports & Adapters;
- preserve contratos do dominio;
- nao introduza acoplamentos indevidos;
- nao altere Alpha001, ReplayEngine ou Research Lab fora do escopo aprovado.

## 3.6 Checklist obrigatorio de entrega

Toda entrega deve informar:

- classificacao de risco usada;
- justificativa da classificacao;
- causa raiz dos problemas encontrados;
- analise de impacto quando houver API publica ou comportamento compartilhado
  alterado;
- sequencia de correcoes realizadas;
- arquivos modificados;
- decisoes arquiteturais tomadas;
- testes adicionados ou ajustados;
- validacoes executadas;
- fluxos testados;
- quantidade total de testes aprovados;
- confirmacao de funcionamento do Dashboard;
- confirmacao de funcionamento do Replay;
- confirmacao de funcionamento do Research Lab;
- confirmacao de inexistencia de novas excecoes.

## 4. Regras de arquitetura

As regras formais estao em [ARCHITECTURE_RULES.md](ARCHITECTURE_RULES.md).

Resumo das regras:

- estrategias apenas retornam `BUY`, `SELL` ou `WAIT`;
- Market DNA classifica contexto, mas nao opera;
- IA futura nao podera enviar ordens;
- `domain/` nao depende de banco, dashboard, corretora ou arquivos;
- execucao de ordens deve ser centralizada;
- estrategias devem suportar backtest, simulacao, replay e tempo real;
- operacao real exige backtest, paper trading, limites e logs completos.

## 4.1 Checkpoint Data Source

A fase Data Source foi encerrada apos a introducao dos providers CSV, Parquet e
DuckDB. O checkpoint tecnico esta documentado em
[docs/DATA_SOURCE_ARCHITECTURE_REVIEW.md](docs/DATA_SOURCE_ARCHITECTURE_REVIEW.md).

Fluxo consolidado:

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
          -> HistoricalDataset
      -> Data Quality
      -> Data Readiness Gate
      -> Auditoria do Gate
      -> Metricas por Provider
      -> ReplayService
          -> ReplayEngine
      -> ResearchLabService
          -> ResearchLab
```

Regras obrigatorias:

- CSV so pode ser acessado pelo adapter CSV.
- Parquet so pode ser acessado pelo adapter Parquet.
- DuckDB so pode ser acessado pelo adapter DuckDB.
- Replay nunca acessa formato fisico diretamente.
- Research Lab nunca acessa formato fisico diretamente.
- Dashboard nunca acessa provider, catalogo, registry, persistencia ou arquivos
  diretamente.
- Toda nova fonte historica deve entrar como novo adapter/provider atras da
  porta `HistoricalDataSource`.
- `HistoricalDataProvider` deve continuar independente da origem fisica.
- `HistoricalDataset` permanece o contrato normalizado para camadas de
  aplicacao.

Fontes futuras possiveis, sem implementacao neste checkpoint:

- PostgreSQL;
- MT5;
- Nelogica;
- B3;
- bancos locais de candles;
- APIs externas de market data.

## 5. Estrutura de pastas atual

```text
TraderIA_WDO/
app.py
config.py
requirements.txt
ARCHITECTURE_RULES.md
TRADERIA_ARCHITECTURE_BIBLE.md
analytics/
application/
backtest/
core/
database/
domain/
market/
replay/
research/
risk/
strategies/
tests/
```

Pastas de dados e saidas locais tambem existem, como `data/`, `logs/` e
`resultados/`, mas nao fazem parte do dominio.

## 6. Fluxo principal do sistema

O fluxo atual e demonstrativo:

1. `app.py` cria uma leitura de mercado.
2. O sistema monta o contexto operacional.
3. Estrategias retornam `StrategySignal`.
4. O risco avalia permissao operacional.
5. O `DecisionPipeline` centraliza a decisao.
6. Eventos sao publicados no `EventBus`.
7. Logs e estado operacional sao mantidos em memoria.
8. O dashboard consome dados via `DashboardService`.

No Replay, o fluxo e candle a candle:

1. `ReplayService` avanca um candle.
2. `CandleHistory` recebe o candle.
3. `FeatureEngine` gera features.
4. `RegimeEngine` classifica regime.
5. `ResearchService` calcula pesquisa quantitativa.
6. Estrategia gera `StrategySignal`.
7. `DecisionPipeline` gera `DecisionContext`.
8. Uma ordem paper pode ser visualizada, sem Broker real.
9. Uma posicao paper pode abrir e fechar por stop ou target.
10. Historico, curva, metricas e drawdown paper sao atualizados.

## 7. Camada de dominio

A pasta `domain/` contem entidades e contratos puros. Ela nao deve conhecer
Streamlit, banco de dados, arquivos, corretora, Broker, MT5 ou dashboard.

Elementos importantes:

- `Candle`;
- `Operacao`;
- `MarketState`;
- contratos em `domain/contracts/`.

Contratos principais:

- `StrategySignal`;
- `MarketSnapshot`;
- `RiskDecision`;
- `ExecutionOrder`;
- `BacktestResult`;
- `DecisionContext`.

## 8. Camada core

A pasta `core/` contem componentes centrais de orquestracao e estado.

Responsabilidades:

- motor principal;
- barramento de eventos;
- gerenciamento de ordens simuladas;
- gerenciamento de posicao;
- sessao operacional;
- configuracao central;
- pipeline de decisao.

O `core/` pode coordenar, mas deve evitar carregar detalhes de UI.

## 9. Camada application

A pasta `application/` contem servicos de aplicacao. Esta camada e a ponte
autorizada entre o dashboard e os modulos internos.

Servicos importantes:

- `DashboardService`;
- `MarketService`;
- `SystemService`;
- `SessionService`;
- `ConfigurationService`;
- `RegimeService`;
- `ResearchService`;
- `ReplayService`;
- `ResearchLabService`.

Regra pratica: o dashboard deve depender apenas de `DashboardService`.

## 10. Camada market

A pasta `market/` concentra leitura e analise de mercado.

Componentes atuais:

- `MarketDNA`;
- `RegimeEngine`;
- `CandleHistory`;
- `TemporalMarketAnalyzer`;
- `FeatureEngine`;
- `FeatureStore`;
- `MarketMemory`;
- modulos de volatilidade, volume e regime.

Essa camada descreve o mercado. Ela nao executa ordens.

## 11. Camada replay

A pasta `replay/` contem o motor base de replay.

O `ReplayEngine` simula a passagem do mercado candle a candle. Ele nao executa
estrategias por conta propria, nao acessa Broker e nao toma decisao operacional
real. A orquestracao mais completa fica no `ReplayService`, na camada
`application/`.

## 12. Camada research

A pasta `research/` contem pesquisa quantitativa e laboratorio.

Componentes atuais:

- `ResearchEngine`;
- `research_seed`;
- `ResearchLab`.

O Research nao opera. Ele calcula qualidade estatistica, executa experimentos
em memoria e prepara dados para analise.

## 13. Dashboard

O dashboard e implementado em `dashboard_app.py` com Streamlit.

Regras:

- deve importar apenas `DashboardService`;
- nao deve acessar banco diretamente;
- nao deve acessar arquivos diretamente;
- nao deve instanciar `ReplayService`, `ResearchLab` ou `ConfigurationManager`;
- deve exibir dados prontos vindos da camada application.

Abas atuais:

- Home;
- Market DNA;
- Replay;
- Research Lab;
- Estrategias;
- Eventos;
- Sistema.

## 14. EventBus

O `EventBus` e o barramento oficial de eventos do sistema.

Eventos oficiais incluem:

- `SYSTEM_STARTED`;
- `NEW_CANDLE`;
- `MARKET_DNA_UPDATED`;
- `STRATEGY_SIGNAL_CREATED`;
- `DECISION_CREATED`;
- `ORDER_CREATED`;
- `ORDER_CLOSED`;
- `BACKTEST_FINISHED`;
- `FEATURE_SNAPSHOT_CREATED`;
- `REGIME_ANALYSIS_CREATED`;
- `RESEARCH_ANALYSIS_CREATED`.

O EventBus permite desacoplar produtores e consumidores de eventos.

## 15. DecisionPipeline

O `DecisionPipeline` centraliza a tomada de decisao.

Ele recebe:

- `StrategySignal`;
- `MarketSnapshot`;
- `RiskDecision`.

Ele retorna:

- `DecisionContext`.

Na versao atual, o pipeline apenas centraliza e repassa:

- `final_decision = StrategySignal.decision`;
- `final_confidence = StrategySignal.confidence`;
- `approved = RiskDecision.allowed`.

No futuro, novas regras podem entrar aqui, sem acoplar estrategia ao risco.

## 16. ConfigurationManager

O `ConfigurationManager` centraliza parametros do sistema em memoria.

Campos importantes:

- ativo;
- capital inicial;
- contratos;
- stop em pontos;
- alvo em pontos;
- limites diarios;
- score minimo;
- confianca minima;
- modo simulacao;
- versao.

O dashboard nao deve acessar `ConfigurationManager` diretamente. O acesso visual
passa por `DashboardService` e `ConfigurationService`.

## 17. OperationSession

A `OperationSession` representa o estado da sessao operacional em memoria.

Ela armazena:

- data da sessao;
- horarios;
- operacoes do dia;
- vitorias e derrotas;
- lucro e prejuizo;
- posicao atual;
- ultimo sinal;
- ultimo evento;
- status do sistema.

O `SessionManager` atualiza a sessao a partir de eventos.

## 18. Replay Engine

O `ReplayEngine` e o motor base de replay candle a candle.

Ele sabe:

- carregar candles;
- iniciar;
- parar;
- resetar;
- avancar candle;
- informar estado atual.

Ele publica eventos quando integrado ao `EventBus`, mas nao executa ordens,
estrategias ou risco real.

## 19. Research Lab

O `ResearchLab` executa experimentos quantitativos em memoria.

Na versao atual:

- executa apenas um replay por experimento;
- nao otimiza parametros;
- nao usa IA;
- nao usa banco;
- nao usa arquivos;
- nao integra Broker, corretora, MT5 ou ordens reais.

O dashboard acessa o laboratorio apenas por `DashboardService` e
`ResearchLabService`.

## 20. O que as estrategias podem e nao podem fazer

Estrategias podem:

- analisar `MarketState`;
- usar dados de mercado recebidos por contrato;
- retornar `StrategySignal`;
- explicar motivos do sinal.

Estrategias nao podem:

- abrir ordens;
- fechar ordens;
- alterar ordens;
- chamar Broker;
- chamar RiskEngine diretamente;
- acessar dashboard;
- acessar banco;
- acessar corretora;
- acessar MT5.

## 21. O que a IA podera e nao podera fazer no futuro

IA podera:

- ajustar score;
- ajustar confidence;
- sugerir risk_multiplier;
- classificar contexto;
- auxiliar pesquisa;
- explicar cenarios.

IA nao podera:

- enviar ordem;
- abrir posicao;
- fechar posicao;
- modificar ordem operacional;
- ignorar limites de risco;
- operar sem backtest e paper trading.

Qualquer IA futura sera auxiliar, nao executora.

## 22. O que o sistema ainda nao faz

O sistema ainda nao:

- conecta em corretora real;
- envia ordem real;
- integra MT5 operacional;
- usa dados historicos reais massivos;
- otimiza parametros automaticamente;
- usa IA ou Machine Learning;
- persiste resultados do Research Lab;
- executa operacao real com dinheiro;
- substitui validacao humana.

## 23. Roadmap futuro

Possiveis proximas etapas:

- conectar fonte real de candles;
- criar importador historico;
- persistir experimentos do Research Lab;
- criar otimizacao controlada de parametros;
- ampliar metricas de backtest;
- criar relatorios exportaveis;
- integrar paper trading externo;
- evoluir RiskEngine;
- adicionar validacoes pre-operacao real;
- criar sprint futura de End-to-End Validation para fluxos completos da
  aplicacao;
- criar o GPT TraderIA Architect com base nesta Bible.

A futura End-to-End Validation deve complementar Unit Tests, Integration Tests
e Streamlit AppTest. Ela nao deve ser implementada sem uma sprint especifica e
deve cobrir fluxos completos como abertura do dashboard, Replay, Research Lab,
estado de sessao e ausencia de excecoes em runtime.

## 24. Glossario

`StrategySignal`: contrato retornado por estrategias com decisao, score,
confianca e motivos.

`MarketSnapshot`: foto normalizada do contexto de mercado.

`RiskDecision`: decisao de risco informando se a operacao e permitida.

`ExecutionOrder`: contrato de ordem normalizada. No Replay atual, usado apenas
como preview paper.

`DecisionContext`: resultado centralizado do `DecisionPipeline`.

`Market DNA`: classificacao contextual do mercado.

`Replay`: simulacao candle a candle.

`Paper Position`: posicao simulada em memoria, sem envio real.

`Paper Equity Curve`: curva acumulada em pontos das operacoes paper.

`Drawdown`: queda da curva em relacao ao pico anterior.

`Research Lab`: laboratorio de experimentos quantitativos em memoria.

`DashboardService`: fachada unica consumida pelo dashboard.

`EventBus`: barramento de eventos do sistema.

`ConfigurationManager`: ponto central de configuracao em memoria.

## Architecture Review v1.0

A arquitetura-base do TraderIA_WDO foi considerada madura para encerrar a fase
de infraestrutura apos a consolidacao dos seguintes componentes:

- Replay Engine;
- Paper Trading visual;
- Research Lab;
- Benchmark Comparator;
- Experiment Validator;
- Research Advisor;
- Dashboard;
- 255 testes automatizados.

Essa revisao marca o fim da etapa estrutural inicial. O projeto passa a ter
uma base suficiente para evoluir com foco em pesquisa quantitativa, validacao
de estrategias e desenvolvimento controlado de novas hipoteses operacionais.

## Arquitetura congelada

A arquitetura-base esta congelada. Novos modulos estruturais so devem ser
criados com justificativa forte, quando houver ganho claro de separacao,
testabilidade, extensibilidade ou protecao das regras de dominio.

A partir deste ponto, o foco principal deixa de ser criacao de infraestrutura
e passa a ser:

- desenvolvimento de estrategias;
- validacao estatistica;
- pesquisa quantitativa;
- melhoria dos experimentos;
- evolucao controlada do Replay e do Research Lab.

A integracao com corretora, MT5 ou qualquer outro provedor operacional ainda
nao esta autorizada.

O uso de IA ainda nao esta autorizado.

A operacao real ainda nao esta autorizada.

Qualquer mudanca que tente aproximar o sistema de execucao real deve ser
bloqueada ate que existam backtests, replay, paper trading, limites de risco,
logs completos e aprovacao arquitetural explicita.

## Sprint Alpha 001

O objetivo da Sprint Alpha 001 e desenvolver a primeira estrategia proprietaria
do TraderIA.

Essa estrategia deve respeitar integralmente as regras arquiteturais ja
definidas:

- estrategias retornam apenas `StrategySignal`;
- estrategias nao executam ordens;
- estrategias nao acessam Broker;
- estrategias nao acessam Risk Engine diretamente;
- estrategias devem funcionar em backtest, simulacao, replay e tempo real;
- toda validacao deve passar por testes automatizados e pesquisa quantitativa.
