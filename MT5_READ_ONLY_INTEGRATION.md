# MT5 Read-Only Integration

## Objetivo

Integrar o TraderIA_WDO ao MetaTrader 5 em modo somente leitura, usando o MT5 apenas como fonte de candles para pesquisa, replay futuro, dashboard, feature engineering e memoria de mercado.

Esta entrega nao autoriza operacao real, envio de ordens, fechamento de posicoes, execucao automatica, Broker, Execution Engine ou IA operacional.

## Arquivos criados

- `infrastructure/__init__.py`
- `infrastructure/market_data/__init__.py`
- `infrastructure/market_data/market_data_provider_interface.py`
- `infrastructure/market_data/mt5_market_data_provider.py`
- `scripts/validate_mt5_read_only_connection.py`
- `tests/test_mt5_market_data_provider.py`
- `tests/test_validate_mt5_read_only_connection_script.py`
- `MT5_READ_ONLY_INTEGRATION.md`

## Arquivos alterados

- `requirements.txt`
- `MANIFEST.md`

## Arquitetura

Foi criada uma camada nova e isolada em `infrastructure/market_data/`.

O adaptador `MT5MarketDataProvider` fica fora do dominio, fora da aplicacao, fora do Replay, fora do Research Lab, fora das estrategias e fora do Risk Engine.

A porta `IMarketDataProvider` define somente operacoes read-only:

- conectar na fonte externa;
- selecionar simbolo;
- obter candles como entidades `Candle`.

O adaptador usa `ConfigurationManager` como fonte de configuracao consultada e aceita `MT5_LOGIN`, `MT5_PASSWORD` e `MT5_SERVER` por configuracao externa ou variaveis de ambiente. Nenhuma credencial foi embutida no codigo.

## Fluxo dos dados

```text
MetaTrader 5
↓
MT5MarketDataProvider
↓
copy_rates_from_pos
↓
Conversao para domain.Candle
↓
EventBus.publish(NEW_CANDLE, Candle)
↓
Consumidores futuros autorizados
```

O provider nunca retorna dicionarios como saida publica. A saida publica de candles e sempre `list[Candle]`.

## Alteracao aplicada

- Importacao tardia da biblioteca oficial `MetaTrader5`, evitando acoplamento em modulos superiores.
- Inicializacao do terminal por `initialize()`.
- Login com parametros externos.
- Selecao de simbolo por `symbol_select`.
- Leitura de candles por `copy_rates_from_pos`.
- Conversao para `Candle`.
- Publicacao de `NEW_CANDLE` no `EventBus`.

## Testes realizados

- `python -m unittest tests.test_mt5_market_data_provider`
- `python scripts\architecture_audit.py`
- `python -m unittest tests.test_architecture_rules tests.test_architecture_regression`
- `python app.py`
- `python -m unittest discover -s tests`

## Resultados

- Testes focados do MT5: OK, 4 testes.
- Architecture Audit: OK.
- Testes de arquitetura: OK, 18 testes.
- Smoke de runtime `app.py`: OK.
- Suite completa: OK, 3166 testes.

## Validacao manual de conexao real

Foi criado o script:

```text
scripts/validate_mt5_read_only_connection.py
```

Uso esperado:

```text
set MT5_LOGIN=<login>
set MT5_PASSWORD=<senha>
set MT5_SERVER=<servidor>
set MT5_SYMBOL=EURUSD
python scripts\validate_mt5_read_only_connection.py
```

Parametros opcionais:

- `MT5_SYMBOL`, padrao `EURUSD`.
- `MT5_TIMEFRAME`, padrao `H1`.
- `MT5_CANDLE_COUNT`, padrao `10`.

O script falha com mensagem clara se as credenciais estiverem ausentes, se o terminal nao conectar, se o simbolo nao estiver disponivel ou se menos de cinco candles forem retornados.

Na validacao local sem credenciais, o script retornou corretamente:

```text
ERRO: credenciais ausentes nas variaveis de ambiente: MT5_LOGIN, MT5_PASSWORD, MT5_SERVER
```

Suite atualizada apos o script manual:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3168 testes.

## Validacao real Pepperstone Demo

Validacao executada com a conta demo `61551556`, servidor `Pepperstone-Demo`, simbolo `EURUSD` e timeframe `H1`.

Comando usado, sem expor senha:

```text
MT5_LOGIN=61551556
MT5_PASSWORD=<redacted>
MT5_SERVER=Pepperstone-Demo
MT5_SYMBOL=EURUSD
MT5_TIMEFRAME=H1
python scripts\validate_mt5_read_only_connection.py
```

Resultado:

```text
MT5 READ ONLY VALIDATION: OK
Simbolo: EURUSD
Timeframe: H1
Candles convertidos para Candle: 10
Modo: somente leitura de candles.
Conexao MT5 encerrada com seguranca.
```

Intervalo retornado na validacao:

- Primeiro candle: `2026-06-26T19:00:00+00:00`.
- Ultimo candle: `2026-06-29T04:00:00+00:00`.

Tambem foi ajustado o adaptador para usar o fluxo oficial `initialize(path, login, password, server)`, que e o formato aceito pelo terminal Pepperstone nesta maquina.

Validacoes apos a conexao real:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest tests.test_validate_mt5_read_only_connection_script tests.test_mt5_market_data_provider`: OK, 6 testes.
- `python -m unittest discover -s tests`: OK, 3168 testes.

## Live Research Service

Foi criado o servico:

```text
application/live_research_service.py
```

Fluxo implementado em modo read-only:

```text
MT5
↓
MT5MarketDataProvider
↓
MT5MarketDataService
↓
CandleHistory
↓
FeatureEngine
↓
RegimeEngine
↓
ResearchService
↓
MarketSnapshot
↓
StrategyFactory / Strategies registradas
↓
StrategySignal
↓
DecisionPipeline
```

O fluxo termina em `DecisionPipeline`. Todos os `DecisionContext` gerados pelo modo live recebem `RiskDecision` com `allowed=False`, `max_contracts=0` e justificativa de pesquisa live read-only. Nenhuma ordem e criada.

Validacao real executada com Pepperstone Demo:

- Simbolo: `EURUSD`.
- Timeframe: `H1`.
- Candles recebidos: 10.
- Candles em `CandleHistory`: 10.
- Estrategias avaliadas: 6.
- `DecisionContext` gerados: 6.
- Contextos aprovados para operacao: 0.

Validacoes apos o `LiveResearchService`:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3176 testes.

## Dashboard Live Read-Only Panel

O estado do `LiveResearchService` foi exposto ao dashboard somente pela fachada `DashboardService`.

Campo adicionado em `DashboardData`:

- `live_research_data`

Metodo adicionado em `DashboardService`:

- `get_live_research_data()`

Painel visual criado:

```text
Live Research READ ONLY
```

Informacoes exibidas:

- simbolo;
- timeframe;
- candles ingeridos;
- estrategias avaliadas;
- StrategySignals gerados;
- DecisionContexts gerados;
- ultima decisao;
- ultima confianca;
- status de seguranca `READ ONLY`.

O painel nao possui botoes operacionais, nao envia ordens, nao fecha ordens, nao acessa infraestrutura diretamente e nao le posicoes ou ordens abertas.

Validacoes apos o painel:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3177 testes.

## Live Research Session Memory

O `LiveResearchService` passou a manter, somente em memoria de sessao, os ultimos snapshots resumidos do pipeline live.

Campos preservados por snapshot:

- timestamp;
- simbolo;
- timeframe;
- decisao;
- confianca;
- quantidade de `StrategySignal`;
- quantidade de `DecisionContext`.

O limite de retencao e configuravel em memoria por `snapshot_history_limit` e pode ser ajustado por `set_snapshot_history_limit()`. Nenhum banco, arquivo ou persistencia externa foi criado.

Exposicao pela fachada:

- `DashboardService.get_live_research_data()`;
- `DashboardService.list_live_research_history()`.

O painel `Live Research READ ONLY` passou a exibir uma tabela simples com o historico da sessao, sem controles operacionais e sem acesso direto a infraestrutura.

Validacoes apos memoria de sessao:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3179 testes.

## Live Research Session Summary

O `LiveResearchService` passou a calcular um resumo estatistico da sessao live atual usando apenas os snapshots mantidos em memoria.

Campos calculados:

- total de snapshots;
- distribuicao `BUY` / `SELL` / `WAIT`;
- confianca media;
- maior confianca;
- menor confianca;
- ultima decisao;
- ultimo timestamp.

Exposicao pela fachada:

- `DashboardService.get_live_research_session_summary()`;
- campo `session_summary` em `live_research_data`.

O painel `Live Research READ ONLY` exibe o resumo por metricas visuais antes da tabela de historico. Nenhum banco, arquivo, estrategia, risk engine ou decision pipeline foi alterado.

Validacoes apos resumo da sessao:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3180 testes.

## Live Research Signal Quality View

O `LiveResearchService` passou a preservar, dentro de cada snapshot em memoria, os sinais individuais gerados por estrategia. A partir desses registros, calcula uma visao agregada de qualidade dos sinais da sessao live.

Campos calculados por estrategia:

- quantidade total de sinais;
- distribuicao `BUY` / `SELL` / `WAIT`;
- confianca media;
- ultima decisao.

Exposicao pela fachada:

- `DashboardService.list_live_research_signal_quality()`;
- campo `signal_quality` em `live_research_data`.

O painel `Live Research READ ONLY` passou a exibir uma tabela de qualidade dos sinais por estrategia. A tabela e somente leitura e deriva apenas da memoria de sessao.

Validacoes apos Signal Quality View:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3181 testes.

## Live Experiment Runner

Foi criado o executor de experimentos live em memoria:

```text
research/live_experiment_runner.py
```

Responsabilidades implementadas:

- receber cada `StrategySignal`;
- registrar timestamp;
- registrar simbolo;
- registrar estrategia;
- registrar decisao;
- registrar confianca;
- registrar regime;
- manter experimento somente em memoria;
- calcular estatisticas da sessao.

Estatisticas calculadas:

- total de sinais;
- distribuicao `BUY` / `SELL` / `WAIT`;
- confianca media;
- desvio padrao da confianca;
- distribuicao por regime;
- distribuicao por estrategia.

Exposicao pela camada de aplicacao:

- `ResearchLabService.list_live_experiment_signals()`;
- `ResearchLabService.live_experiment_summary()`;
- `DashboardService.list_live_experiment_signals()`;
- `DashboardService.get_live_experiment_summary()`.

O `DashboardService` compartilha a mesma instancia de `LiveExperimentRunner` entre `LiveResearchService` e `ResearchLabService`, preservando o estado live em memoria de sessao.

O painel `Live Research READ ONLY` passou a exibir o resumo e a tabela dos sinais do experimento live. Nao ha avaliacao de PnL, lucro, execucao, posicao, ordem aberta, broker ou envio de ordens.

Validacoes apos Live Experiment Runner:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3184 testes.

## Live Experiment Runner Sprint 1 Consolidation

O contrato do `LiveExperimentRunner` foi consolidado conforme Sprint 1 da fase de plataforma de pesquisa quantitativa.

Campos oficiais registrados por sinal:

- timestamp;
- simbolo;
- timeframe;
- estrategia;
- decisao;
- confidence;
- regime.

Metricas oficiais da sessao:

- `total_signals`;
- `BUY`;
- `SELL`;
- `WAIT`;
- `confidence_mean`;
- `confidence_std`;
- `regime_distribution`;
- `strategy_distribution`.

Validacoes apos consolidacao do Sprint 1:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3184 testes.

## Sprint UI 1 - Dashboard Layout

Foi reorganizado somente o layout de apresentacao do `dashboard_app.py`, sem alterar arquitetura, dominio, pipeline, research, market ou contratos de negocio.

Nova navegacao visual:

- `HOME`;
- `Status Geral`;
- `Sistema`;
- `Replay`;
- `Live`;
- `Research`.

Componentes usados:

- containers;
- tabs;
- columns;
- expanders;
- metrics.

O Dashboard continua consumindo exclusivamente `DashboardService` como fachada. A mudanca reaproveita renderizadores existentes e altera apenas a composicao visual.

Validacoes apos Sprint UI 1:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3184 testes.

## Sprint UI 2 - Live Research Dashboard

Foi reorganizado somente o painel Live Research no `dashboard_app.py`, sem alterar arquitetura, dominio, application, research, market, Strategy, RiskEngine ou DecisionPipeline.

Nova organizacao visual:

- `LIVE STATUS`;
- `SESSION SUMMARY`;
- `SIGNAL QUALITY`;
- `LIVE HISTORY`;
- `SYSTEM HEALTH`.

Melhorias aplicadas:

- destaque visual `READ ONLY`;
- metricas agrupadas por finalidade;
- formatacao consistente de confidence;
- badges textuais para decisao;
- timestamps normalizados para exibicao;
- tabelas read-only com `st.dataframe` para qualidade de sinais e historico live.

O Dashboard continua consumindo exclusivamente `DashboardService` como fachada e nao acessa infraestrutura diretamente.

Validacoes apos Sprint UI 2:

- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3184 testes.

## Dashboard ViewModel Contract

Foi criado o contrato unico de ViewModel do Dashboard:

```text
application/dashboard_view_model.py
```

O `DashboardService` passou a expor:

```text
get_dashboard_view_model()
```

Estrutura oficial do contrato:

- `system_status`;
- `replay_status`;
- `live_research_status`;
- `live_session_summary`;
- `live_signal_quality`;
- `live_history`;
- `research_status`;
- `safety_status`.

O `dashboard_app.py` passou a consumir o ViewModel pela fachada `DashboardService`, mantendo fallback temporario para campos legados por compatibilidade. A partir desta entrega, novas informacoes relevantes do backend devem ser refletidas na UI pela inclusao explicita de campos no ViewModel, evitando que o dashboard busque dados em varios servicos internos.

Nenhuma regra quantitativa, operacional ou de negocio foi criada no dashboard. A UI permanece somente leitura, sem Broker, sem `order_send`, sem posicoes e sem ordens abertas.

Validacoes apos Dashboard ViewModel Contract:

- `python -m unittest tests.test_dashboard_view_model tests.test_application_api tests.test_dashboard_facade tests.test_dashboard_app_runtime tests.test_dashboard_service_contract tests.test_application_services`: OK, 49 testes.
- `python scripts\architecture_audit.py`: OK.
- `python -m unittest discover -s tests`: OK, 3187 testes.

## Limites da validacao

A conexao real com Pepperstone nao foi executada nesta maquina porque credenciais reais nao foram fornecidas no ambiente. A validacao automatizada usa um modulo MT5 falso para confirmar contrato, conversao, publicacao de eventos e ausencia de capacidade operacional.

Para conexao real, o ambiente deve fornecer:

- `MT5_LOGIN`
- `MT5_PASSWORD`
- `MT5_SERVER`

## Garantia de modo read-only

O adaptador criado nao possui metodos para envio de ordens, fechamento de posicoes, execucao operacional ou consulta/manipulacao de posicoes.

Nenhum destes componentes foi alterado:

- DecisionPipeline
- RiskEngine
- Strategy
- ReplayEngine
- ResearchLab
- HistoricalDataProvider

O MT5 foi integrado apenas como fonte de candles.

## Declaracao Final

O TraderIA_WDO possui agora um adaptador MT5 read-only isolado em infraestrutura, capaz de converter candles para entidades de dominio e publicar `NEW_CANDLE`, sem habilitar qualquer operacao real.
