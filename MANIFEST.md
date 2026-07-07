# MANIFEST - TraderIA_WDO

Este manifesto e a fonte oficial unica do estado operacional do projeto
TraderIA_WDO.

O README apresenta o projeto. A Architecture Bible descreve a arquitetura. Este
arquivo responde em que ponto o projeto esta, qual sprint foi concluida, qual
missao esta ativa e quais modulos estao concluidos, em desenvolvimento ou
congelados.

## Projeto

| Campo | Valor |
| --- | --- |
| Nome | TraderIA_WDO |
| Versao | CTO-GOV-014 |
| Ultima atualizacao | 2026-06-30 |
| Responsavel arquitetural | CTO |

## Estado Atual

| Campo | Valor |
| --- | --- |
| Sprint atual | Sprint 23 - Forex-Only Dashboard UX |
| Ultima Sprint concluida | Sprint 22 - Research Calibration Separation |
| Proxima Sprint | A definir pelo CTO |
| Missao atual | Consolidar experiencia principal Forex-only no Dashboard |
| Status geral | Dashboard principal com abas visiveis `MT5 Forex`, `Laboratorio de Pesquisa`, `Replay`, `Historico MT5`, `Relatorios` e `Sistema Forex`; o Replay volta para a navegacao principal como area manual de repeticao/análise Forex par-a-par via `DashboardService`, sem PETR/WDO, datasets legados ou operacao real; oito pares Forex autorizados sao exibidos via MT5 Safe Mode com leitura de candles online, medias, RSI, momentum, volatilidade e decisao BUY/SELL/WAIT por heuristica leve; a aba `MT5 Forex` atualiza automaticamente a cada 10 segundos sem seletor manual de timeframe, consumindo o periodo recomendado pelo Lab quando houver constantes disponiveis; esse refresh online nao executa Research Lab, QuantitativeScoreEngine, TimeframeOptimizer nem Scenario Runner; Research Lab MT5 passa a executar pesquisa sob demanda por `Executar Pesquisa`, carregando snapshot separado de aproximadamente 5000 candles para avaliar cenarios parametrizados por par/timeframe/modelo e produzir ResearchConstants a partir do melhor cenario, priorizando configuracoes com alvo de 70% de `Confirmacao Historica` e variacao de timeframes; MT5 Forex consome somente constantes ja produzidas via `DashboardService.get_mt5_research_constants()`; sinais visuais MT5 sao sincronizados automaticamente por `DashboardService.load_mt5_forex_signals()` para JSON read-only consumido pelo indicador `TraderIAVisualSignals.mq5`; a aba `Relatorios` confronta o log local `.traderia/mt5_demo_execution.jsonl` com `positions_get`, `orders_get`, `history_orders_get` e `history_deals_get` do MT5, marcando `CONFERE` quando ticket, simbolo, lado e volume batem; painel `Robo Demo MT5` permanece limitado a conta DEMO com provider desabilitado por padrao, variavel `TRADERIA_DEMO_EXECUTION_ENABLED=1`, Stop Loss obrigatorio, Take Profit obrigatorio, limite diario, bloqueio de posicao duplicada por simbolo e log JSONL; o robo automatico executa exclusivamente Trade Plan `PLANO_VALIDO` produzido pelo Research Lab, via `DecisionPipeline -> DemoExecutionService -> MT5DemoExecutionProvider`, sem escolher Alpha, recalcular Score, recalcular Confirmacao Historica, stop, alvo ou RR; conta real permanece bloqueada |
| Fase atual do roadmap | Experiencia Forex-only, separando calibracao quantitativa, refresh online MT5, historico MT5 explicativo e sistema Forex |

## Arquitetura

| Campo | Valor |
| --- | --- |
| Estado da arquitetura | Clean Architecture consolidada, com dominio protegido, application como fachada, Replay e Research Lab isolados de operacao real, execucao demo segregada em provider dedicado, providers historicos desacoplados, dataset historico real catalogado e Quality Gate operacional |
| Arquitetura congelada | Sim |
| Versao arquitetural | Architecture Bible v1 |
| Filosofia institucional | Arquitetura acima da implementacao; pesquisa acima da opiniao; dados acima de achismos; evolucao incremental |
| Restricao central | Nenhuma operacao em conta real autorizada; somente execucao real em conta MT5 Demo segregada pode enviar ordens ao terminal, apos Decision Pipeline, Risk Engine, Paper Validation e habilitacao explicita por variavel de ambiente |

## Modulos

Status permitido: Nao iniciado, Em desenvolvimento, Concluido, Congelado.

| Modulo | Status |
| --- | --- |
| Domain | Congelado |
| Core | Concluido |
| Application | Congelado |
| Market | Concluido |
| Market Data | Concluido |
| Replay | Congelado |
| Research Lab | Congelado |
| Dashboard | Concluido |
| Decision Pipeline | Concluido |
| EventBus | Concluido |
| Risk Engine | Concluido |
| Feature Engine | Concluido |
| Configuration | Concluido |
| Paper Trading | Concluido |
| Execution | Em desenvolvimento |
| Broker | Nao iniciado |
| IA | Nao iniciado |

## Dados de Mercado

| Campo | Valor |
| --- | --- |
| Arquitetura de dados | Concluida em `docs/MARKET_DATA_ARCHITECTURE.md` |
| Validacao de dados | Homologada em `docs/MARKET_DATA_VALIDATION.md` |
| Certificacao de dados | Certificada em `docs/MARKET_DATA_CERTIFIED.md` |
| Status oficial | `MARKET_DATA_CERTIFIED_FOR_QUANTITATIVE_RESEARCH` |
| Dataset certificado | `wdo_1m_2025` |
| Dataset de pesquisa ativo | Fluxo principal usa candles Forex online do MT5; PETR4 permanece apenas como artefato historico legado, fora da UI principal |
| Ativo operacional/configuracao | Fluxo principal Forex MT5; WDO permanece apenas como configuracao/legado, fora da UI principal |
| Caminho do dataset | Nao aplicavel ao fluxo principal Forex MT5 online |
| Provider oficial | `HistoricalDataProvider` |
| Replay com dados reais | Certificado |
| Replay PETR4 | Validado visualmente com 2491 candles |
| Perfil PETR4 no Dashboard | Exibe retorno, volatilidade, drawdown, melhores/piores dias, volume e graficos reais |
| Dashboard ViewModel Contract | `application/dashboard_view_model.py` centraliza o estado exibido pela UI via `DashboardService.get_dashboard_view_model()` |
| Quantitative Calibrated Score | `research/quantitative_score_engine.py` calibra confidence por amostra observada, win rate, retorno medio, profit factor, drawdown e diagnosticos de contexto antes de expor BUY/SELL/WAIT; parametros oficiais vivem em `ConfigurationManager` |
| Research Workbench MVP | Tela unica com candlestick, volume, Replay, Alpha e estatisticas via `DashboardService` |
| Market Reading Pipeline | Exibe Dados, Leitura do Mercado, Contexto, Setup, Decisao e Resultado no Replay |
| Research Lab com dados reais | Certificado |
| Validation Suite com dados reais | Certificada com amostra limitada |
| Benchmark com dados reais | Certificado |
| Portfolio com dados reais | Certificado |
| Dashboard com dados reais | Certificado via `DashboardService` |
| MT5 Forex Dashboard | Exibe EURUSD, GBPUSD, USDCHF, USDJPY, AUDUSD, NZDUSD, USDCAD e EURJPY via `DashboardService`, com 1000 candles por par, atualizacao automatica a cada 10 segundos, heuristica leve online, decisao BUY/SELL/WAIT somente analitica, coloracao visual por decisao, campos de Entrada Teorica read-only e plano read-only baseado nas constantes calibradas disponiveis; quando nenhuma calibracao foi executada, usa modelo padrao seguro `TREND_MOMENTUM` sem chamar o Research Lab; o seletor manual de timeframe foi removido da aba Forex principal e o periodo exibido vem da configuracao recomendada pelo Lab quando existir; a aba Replay usa somente pares Forex e cenarios filtrados por par, sem interferir no refresh Forex |
| Research Knowledge Layers | Ordem institucional congelada em `research/research_layer.py`: Camada 0 `Market Data`, Camada 1 `Indicadores`, Camada 2 `Contexto`, Camada 3 `Estrutura`, Camada 4 `Tempo`, Camada 5 `Microestrutura`, Camada 6 `Alpha`, Camada 7 `Trade Plan`, Camada 8 `Validacao`; a Camada Tempo vem antes de Validacao para responder quando a Alpha funciona antes de certificar se ela e boa; o contrato e declarativo, nao executa pesquisa, nao acessa MT5, nao envia ordens e nao altera Replay, Dashboard ou Research Engine |
| Forex Time Layer | Camada Tempo implementada em `research/forex_time_layer.py`; classifica cada candle/sinal do Research Lab por `hour_utc`, `hour_brt`, `weekday`, `forex_session`, flags de Londres, Nova York, Asia, overlap Londres/Nova York, rollover, final de sexta, abertura de domingo e fora de horario; status temporais oficiais: `SESSAO_FAVORAVEL`, `SESSAO_NEUTRA`, `SESSAO_DESFAVORAVEL`, `ROLLOVER_BLOQUEADO`, `SEXTA_FINAL_BLOQUEADO`, `DOMINGO_ABERTURA_BLOQUEADO` e `FORA_DA_JANELA`; rollover, domingo abertura, sexta final e fora da janela tornam o cenario inelegivel; sessao favoravel aplica bonus leve no `Score Tecnico`, sessao desfavoravel aplica penalidade leve, e `Confirmacao Historica` permanece inalterada; a aba Lab exibe Sessao, Janela BRT, Dia, Overlap, Rollover, Bloqueio Temporal e Motivo Tempo via `DashboardService`/ViewModel, sem acessar infraestrutura diretamente |
| Market Structure Layer | Camada 3 institucionalizada em `market/structure`; `MarketStructureAnalyzer` recebe `list[Candle]` e opcionalmente candles por timeframe/bid/ask/historico de spread/sessao, gerando `MarketStructureSnapshot` read-only com Donchian completo, Pivot, VWAP, Z-Score, Bandas de Bollinger, Tick Volume medio/relativo, spread atual/medio, slippage estimado, velocidade do preco, liquidez por sessao, bloqueio informativo por spread alto, suporte, resistencia, swing high, swing low, maxima/minima relevante, range atual, rompimento de range, distancia ate suporte/resistencia, regime formal `TREND/RANGE/VOLATILE`, forca da tendencia, compressao/expansao de volatilidade, distancia do preco ate EMAs e direcao dominante multi-timeframe; a camada nao gera compra/venda, nao executa ordens, nao acessa MT5, nao importa UI e ainda nao altera Alphas ou Trade Plan |
| Alpha Hypothesis Contract | `research/alpha_factory/AlphaHypothesis` passa a representar formalmente uma hipotese pesquisavel com hipotese formal, mercados permitidos/proibidos, camadas usadas, parametros pesquisaveis, criterios de rejeicao e criterios de aprovacao; o contrato permanece DTO imutavel, nao executa pesquisa, nao gera sinal, nao acessa Replay, MT5, Dashboard ou estrategias |
| Alpha Research Ranking | `research/alpha_factory/AlphaResearchRankingEngine` consolida resultados ja pesquisados em ranking por Alpha, ranking por par, ranking por timeframe, comparacao entre Alphas, relatorio de reprovacao, motivo da reprovacao e controle de overfitting; nao executa pesquisa, nao recalcula indicadores, nao gera sinal, nao acessa Replay, MT5 ou Dashboard |
| Alpha Validation Metrics | `research/alpha_factory/AlphaValidationMetricsEngine` consolida metricas ja apuradas por Alpha: total de trades, win rate, profit factor, expectancy, max drawdown, MAE, MFE, recovery factor, consistencia por par, consistencia por timeframe, walk-forward e out-of-sample; permanece read-only e nao executa pesquisa, Replay, Dashboard ou ordens |
| MT5 Research Trade Plan | `research/mt5_research_trade_plan.py` gera plano read-only com entrada, stop, alvo, RR, risco em pips, ganho em pips, risco percentual, ganho percentual, motivo do stop, motivo do alvo, modelo de saida e politica de gestao de stop; quando o Research Lab fornece `atr_stop_factor` e `rr` no cenario vencedor, o Trade Plan usa exatamente esses parametros para calcular `distancia_stop = max(ATR * atr_stop_factor, entrada * 0.001)` e o alvo por RR; a grade fixa interna permanece apenas como fallback para snapshots/cenarios antigos sem esses parametros; a politica de gestao tambem vem do cenario do Lab (`FIXED_STOP`, `ATR_TRAILING_STOP`, `BREAK_EVEN`, `CHANDELIER_EXIT`, `PARABOLIC_SAR`, `DONCHIAN_CHANNEL_STOP`, `MOVING_AVERAGE_EXIT`, `TIME_STOP` ou `VOLATILITY_STOP`) e e transportada como metadado/contrato para exibicao e gestao futura; o Dashboard e o export visual consomem esses campos sem executar ordens e sem alterar `DemoExecutionService` ou provider MT5 |
| Indice de Certificacao TraderIA | `research/traderia_certification_index.py` calcula o ICT de 0 a 100 a partir de Win Rate, Profit Factor, Expectancy, Drawdown, Sample Size e Recovery Factor, com filtros eliminatorios obrigatorios (`Profit Factor < 1.30`, `Expectancy <= 0`, `Trades < 100` ou `Drawdown > 25%` reprovam a Alpha); classes oficiais: `A+` 90-100, `A` 80-89, `B` 70-79, `C` 60-69, `D` 50-59 e `E` 0-49; somente `A+`, `A` e `B`, apos filtros minimos aprovados, liberam operacao Demo; `C` fica restrita a Research/Replay, `D` permanece hipotese promissora e `E` rejeitada; o ICT nao altera Encaixe Tecnico nem Confirmacao Historica, apenas decide o aceite institucional do plano |
| Replay Forex | Aba manual para repeticao/análise de cenarios por par Forex; controles `Par Forex do Replay`, `Timeframe Forex do Replay`, `Carregar par Forex` e `Executar Pesquisa do Par`; o botao de pesquisa chama `DashboardService.run_mt5_research_calibration_for_pair()` para isolar o par selecionado, exibir leitura Forex, melhor cenario do par e ranking do par; nao acessa PETR, WDO, datasets historicos legados, arquivos fisicos ou operacao real |
| MT5 Safe Mode | Ativo no painel Forex principal; fluxo `MT5 -> candles online -> medias/RSI/momentum/volatilidade -> constantes calibradas em memoria -> decisao heuristica -> Dashboard`; nao executa Research Lab, QuantitativeScoreEngine nem TimeframeOptimizer no refresh automatico MT5 |
| Research Lab MT5 Scenario Runner | Executado somente por botao `Executar Pesquisa`; carrega snapshot MT5 separado com `ConfigurationManager.quantitative_score_candles_loaded = 5000`, avalia cada par isoladamente e pesquisa uma biblioteca institucional de Alphas por par/timeframe em vez de aplicar uma configuracao fixa; a biblioteca cobre `ALPHA001 Trend Momentum`, `ALPHA002 Trend Pullback`, `ALPHA003 Breakout de Consolidacao`, `ALPHA004 RSI Reversal`, `ALPHA005 Donchian Breakout`, `ALPHA006 ADX Trend Strength`, `ALPHA007 MACD Momentum Shift`, `ALPHA008 Bollinger Volatility Expansion`, `ALPHA009 ATR Volatility Regime`, `ALPHA010 Donchian Structure Breakout`, `ALPHA011 Pivot Rejection`, `ALPHA012 VWAP Mean Reversion`, `ALPHA013 Support Resistance Reaction`, `ALPHA014 Multi-Timeframe Alignment` e `ALPHA015 Liquidity Spread Filter`; cada Alpha usa apenas os indicadores necessarios para sua hipotese, e indicador obrigatorio ausente retorna `INDICADOR_INDISPONIVEL` sem fallback silencioso; indicadores antes vazios no Forex (`EMA`, `ADX`, `MACD`, `ATR`, `ATR media`, `Bollinger`, `Tick Volume medio`, `Donchian`, `Pivot`, `VWAP`, `Z-Score`, suporte/resistencia e swing) passam pela fachada de aplicacao quando disponiveis; spread/slippage sao importados por microestrutura read-only (`symbol_info`/`symbol_info_tick`) quando o MT5 disponibiliza bid/ask/point/spread; a aba Lab exibe primeiro `Sugestoes de Setup do Lab`, lendo o snapshot/banco de pesquisa pela fachada `DashboardService.suggest_mt5_lab_setups()` e priorizando setups com `Confirmacao Historica` de 70%, ou marcando `MAIS_PROXIMO_DE_70` quando nenhum cenario atinge o alvo; exibe tambem `Ranking Final de Alphas` via `DashboardService.get_mt5_alpha_research_ranking()` e `Research Report da Alpha vencedora`, classificando cada Alpha como `APROVADA`, `REPROVADA` ou `SEM_DADOS`, listando indicadores usados, motivos, recomendacoes e evidencias estatisticas ainda ausentes como walk-forward, out-of-sample e MAE/MFE por cenario; a configuracao vencedora nao precisa usar todos os indicadores e prioriza cenarios com `Confirmacao Historica` alvo de 70%; `Encaixe Tecnico` significa que o setup parece bom agora; `Confirmacao Historica` significa que a propria regra da Alpha/cenario foi reaplicada sobre uma amostra historica dos candles disponiveis, com win rate, amostra, profit factor, expectancy e drawdown do cenario; quando nao ha amostra suficiente ou indicador historico para aquela Alpha, a confirmacao fica 0% e o cenario nao e certificado, sem reutilizar win rate generico do par/timeframe; snapshots antigos que tinham confirmacao positiva sem amostra por cenario sao ignorados e devem ser recalculados por `Executar Pesquisa`; exibe ranking de cenarios, melhor cenario geral, tabela `Melhor cenario por par` com uma linha por par consolidando compra, venda e lateralidade em colunas separadas com `Alpha`, `Encaixe Tecnico`, `Confirmacao Historica`, amostra historica e `Alvo de confirmacao`, e ultima tabela `Configuracao final por par` com uma linha independente por par contendo timeframe ideal, configuracao usada, cenario de compra e cenario de venda; grava ResearchConstants em `DashboardService.mt5_research_constants`; nao substitui o painel online, nao envia ordens e nao participa do refresh automatico do `MT5 Forex` |
| MT5 Demo Execution | Adaptador exclusivo em `infrastructure/execution/mt5_demo_execution_provider.py`; unico componente autorizado a chamar MetaTrader5/order_send; valida `initialize()`, conta demo, simbolo, posicao aberta por simbolo, stop, target, horario, limite diario de operacoes, limite diario de perda, Paper Validation e registra JSONL completo |
| MT5 Trade Reports | Aba `Relatorios` em `dashboard_app.py` consome `DashboardService.get_mt5_trade_audit_report()` e exibe auditoria cruzada TraderIA x MT5; fonte local `.traderia/mt5_demo_execution.jsonl`; fonte MT5 read-only `positions_get`, `orders_get`, `history_orders_get` e `history_deals_get`; nenhuma ordem e enviada; linhas `CONFERE` indicam ticket, simbolo, lado e volume compativeis |
| Demo Trading Runtime | Runtime em `application/demo_trading_runtime.py` executa um ciclo controlado: inicializa market data por porta de aplicacao, busca candles, gera `StrategySignal`, calcula entrada/stop/alvo, valida score/confianca/risco, prepara `ExecutionOrder` e chama somente `DemoExecutionService`; script `scripts/run_mt5_demo_runtime_once.py` faz a fiacao com MT5 demo somente quando ativado por variavel de ambiente |
| Robo Demo MT5 no Dashboard | Painel `Robo Demo MT5` em `dashboard_app.py`; UI chama apenas `DashboardService`; sem import direto de MT5 no Dashboard; volume padrao de execucao demo MT5: `0.1`; interface principal usa `Armar robo demo`, `Avaliar gatilho agora` e `Desarmar robo`; `Armar robo demo` ativa monitoramento online, chama `DashboardService.run_online_demo_robot_cycle()`, atualiza MT5, avalia o robo e reexecuta o ciclo automaticamente; monitora `TODOS` ou um par escolhido, mas executa no maximo um gatilho valido por ciclo; o ciclo manual `run_demo_robot_once()` reutiliza o mesmo fluxo temporal oficial, sem montar ordem por caminho paralelo; a ordem demo consome exclusivamente entrada, stop, alvo e RR produzidos pelo Research Lab com status `PLANO_VALIDO`; ICT e informativo para Demo; o robo nao escolhe Alpha, nao recalcula indicadores, nao recalcula Score Tecnico, nao recalcula Confirmacao Historica, ICT, stop, alvo ou RR; antes de enviar, valida kill switch, regime de mercado autorizado, horario permitido, bloqueio temporal, bloqueio macro quando houver fonte configurada, risco, conta demo e ausencia de posicao aberta por simbolo; auditoria registra Alpha, versao, Score Tecnico, Confirmacao Historica, entrada, stop, alvo, RR, candle do gatilho, ticket e posicao MT5; quando `TRADERIA_DEMO_EXECUTION_ENABLED` nao e `1`, o painel mostra `DISABLED` e nenhuma ordem e enviada |
| TRADE_DNA | Contrato de rastreabilidade cientifica registrado no historico/auditoria de cada negociacao demo: `Session Policy v2.1`, `Execution Pipeline v3.4`, `Lab Configuration v8`, `Alpha ALPHA007 v1.6`, `Trade Plan TP v5`, `Indicator Bundle Indicators v9`, `Microstructure Micro v2`, `Validation Pipeline VAL v4` e `Strategy Definition STRAT v3`; esses campos sao metadados, nao alteram calculos, indicadores, Score Tecnico, Confirmacao Historica, gatilho, risco ou execucao |
| Arvore de Rejeicao do Robo Demo | Diagnostico visual read-only no painel `Robo Demo MT5`; `DashboardService` monta etapas do ultimo candidato avaliado: kill switch, envio MT5 Demo, Research Constants, ICT, sinal direcional, gatilho novo, Trade Plan, Tempo, evento macro e Decision/Risk/Execution; a tabela apenas mostra `APROVADO` ou `BLOQUEADO` por etapa, sem alterar regras, relaxar filtros, recalcular Alpha ou acessar MT5 diretamente pela UI |
| MT5 Visual Indicator | `TRADERIA_MT5_VISUAL_INDICATOR_READY`; TraderIA sincroniza automaticamente `.traderia/traderia_signals.json` ou caminho definido por `TRADERIA_MT5_VISUAL_SIGNALS_PATH` a cada atualizacao do `MT5 Forex`; `mt5/indicators/TraderIAVisualSignals.mq5` le `traderia_signals.json` em `MQL5/Files` e desenha BUY/SELL, linha de entrada, stop, alvo, RR, modelo e status somente quando `symbol` e `timeframe` do JSON coincidem com o grafico; o `timeframe` exportado representa a janela operacional recomendada pelo Lab quando houver configuracao `RESEARCH_LAB`, enquanto `mt5_source_timeframe` preserva a janela bruta usada na leitura online; BUY usa verde, SELL usa vermelho e WAIT usa branco no status visual; sinal teorico BUY/SELL com entrada valida tambem pode ser plotado; se houver divergencia, exibe aviso discreto de timeframe; indicador nao calcula estrategia, nao envia ordens, nao acessa broker e nao altera posicoes |
| Restricao operacional | Conta real permanece proibida; execucao MT5 Demo fica desabilitada por padrao ate habilitacao explicita por variavel de ambiente e confirmacao de conta demo pelo provider |

## Programa Market Data

| Campo | Valor |
| --- | --- |
| Missoes | 194-200 |
| Status do programa | Concluido |
| Arquitetura | `MARKET_DATA_ARCHITECTURE_DEFINED` |
| Homologacao | `HOMOLOGATED_FOR_REPLAY_AND_RESEARCH_WITH_LIMITED_SAMPLE` |
| Certificacao | `MARKET_DATA_CERTIFIED_FOR_QUANTITATIVE_RESEARCH` |
| Dataset historico certificado | `wdo_1m_2025` |
| Replay | Utiliza dados historicos reais por `ReplayService`; certificado |
| Research Lab | Utiliza dados historicos reais por `ResearchLabService`; certificado |
| Validation Suite | Utiliza dados historicos reais; certificada com amostra limitada |
| Benchmark | Utiliza dados historicos reais; certificado |
| Portfolio Evaluation | Utiliza dados historicos reais; certificado |
| Dashboard | Utiliza dados historicos reais somente via `DashboardService`; certificado |
| EventBus | Fluxo preservado; sem alteracao operacional |
| MT5 Read-Only | Adaptador isolado em `infrastructure/market_data`; fonte de candles apenas; sem ordens |
| Live Research Memory | Ultimos snapshots live mantidos somente em memoria de sessao e expostos via `DashboardService` |
| Live Research Summary | Resumo estatistico da sessao live calculado somente em memoria e exposto no painel read-only |
| Live Research Signal Quality | Qualidade dos sinais live agregada por estrategia em memoria e exibida via `DashboardService` |
| Live Experiment Runner | Experimento live em memoria para estatisticas de `StrategySignal`, com timeframe e desvio de confianca |
| Sprint UI 1 | Dashboard reorganizado em navegacao profissional por tabs, somente camada de apresentacao |
| Sprint UI 2 | Painel Live Research reorganizado em secoes profissionais e somente leitura |
| Performance | Quality Gate `PASSED` em 87.106 segundos |
| Integridade | Catalogo, metadados, importacao, normalizacao e contagem de candles aprovados |
| Limitacao estatistica | Dataset de certificacao possui amostra minima; novas aprovacoes estatisticas exigem datasets maiores |

## Alpha

| Campo | Valor |
| --- | --- |
| Alpha ativa | Alpha 001 - IORB permanece disponivel; Alpha101 registrada para PETR4 diario em pesquisa |
| Hipotese | Alpha001 pesquisa abertura institucional do WDO; Alpha101 pesquisa continuidade diaria PETR4 por volume, momentum e breakout |
| Status | Pesquisa e simulacao; Alpha101 `CERTIFIED_WITH_WARNINGS` |
| Replay | Alpha001 e Alpha101 disponiveis para validacao visual e candle a candle via seletor de Alpha |
| Research | Alpha101 validada exploratoriamente com 88 trades nao sobrepostos; Profit Factor 2.15; drawdown maximo -20.03%; operacao real proibida |
| Validacao | Somente pesquisa, replay, simulacao e paper trading visual; ordem real nao autorizada |
| Dados reais | Infraestrutura certificada para pesquisa quantitativa com dados historicos reais; amostra atual e limitada para aprovacao estatistica de estrategia |

## Qualidade

| Campo | Valor |
| --- | --- |
| Testes | 3310 testes automatizados aprovados na ultima validacao registrada |
| Cobertura | Nao mensurada formalmente neste manifesto |
| Build | PASSED na ultima validacao local registrada |
| Quality Gate | Suite completa `python -m unittest discover -s tests` PASSED em 2026-06-30 |
| Tempo do Quality Gate | 221.870 segundos na ultima suite completa registrada |
| Auditoria arquitetural | PASSED apos alinhamento do manifesto arquitetural com `DemoExecutionService` e `ExecutionResult` |
| Validacao focada atual | `python -m unittest tests.test_dashboard_view_model tests.test_dashboard_app_runtime tests.test_dashboard_facade tests.test_demo_execution_service tests.test_mt5_demo_execution_provider` PASSED com 86 testes em 2026-06-30; auditoria visual das abas `MT5 Forex`, `Laboratorio de Pesquisa`, `Replay`, `Historico MT5`, `Relatorios` e `Sistema Forex` sem excecoes, sem PETR4/WDO e sem botao manual de exportacao visual |

## Roadmap

| Campo | Valor |
| --- | --- |
| Fase atual | Forex-only Dashboard UX |
| Sprint seguinte | A definir pelo CTO |
| Sprint posterior | A definir pelo CTO |
| Objetivos imediatos | Manter `MT5 Forex` em atualizacao automatica leve sem seletor manual de timeframe; executar Research Lab MT5 apenas sob demanda por `Executar Pesquisa`; usar a aba `Replay` para analisar cenarios Forex um par por vez; exibir ranking de cenarios, melhor cenario por par, melhor cenario geral e configuracao final independente por par com timeframe ideal, compra e venda no Laboratorio; consumir ResearchConstants ja produzidas; evoluir a Camada 3 de Estrutura de Mercado sem acoplar UI, Alpha ou execucao; manter PETR4/WDO fora da navegacao principal; preservar conta real proibida |

## Restricoes Operacionais

| Restricao | Status |
| --- | --- |
| Operacao real em conta real | Proibida |
| Envio de ordens para conta real | Proibido |
| Envio de ordens para conta MT5 Demo | Autorizado somente pelo fluxo `Research Lab -> Research Constants -> MT5 Forex -> Trade Plan -> DecisionPipeline -> DemoExecutionService -> MT5DemoExecutionProvider`, orquestrado pela fachada `DashboardService`, com `TRADERIA_DEMO_EXECUTION_ENABLED=1`, conta demo confirmada, SL/TP obrigatorios, limites de risco e log JSONL; o robo demo apenas executa Trade Plan `PLANO_VALIDO` e nao recalcula decisao, Alpha, score, confirmacao, stop, alvo ou RR |
| Integracao com broker | Nao autorizada |
| Integracao operacional com MT5 | Autorizada somente para conta demo pelo provider segregado; market data permanece read-only nos demais fluxos |
| IA executando ordens | Proibida |
| Estrategias executando ordens | Proibido |
| Domain acessando infraestrutura | Proibido |
| Replay acessando arquivos fisicos diretamente | Proibido |
| Research Lab acessando arquivos fisicos diretamente | Proibido |
| Dashboard acessando providers diretamente | Proibido |
| Arquitetura congelada | Sim |

## Regra de Conclusao de Sprint CTO

Toda Sprint CTO somente pode ser considerada concluida apos:

1. Implementacao aprovada.
2. Testes executados.
3. Atualizacao obrigatoria do `MANIFEST.md`.
4. Atualizacao do `CHANGELOG`, quando aplicavel.

Sem atualizacao do `MANIFEST.md`, a Sprint permanece em andamento.

## Historico

| Sprint | Objetivo | Status | Data | Observacoes |
| --- | --- | --- | --- | --- |
| Sprint 8 | Congelar arquitetura-base apos Replay Engine, Paper Trading visual, Research Lab, Benchmark Comparator, Experiment Validator, Research Advisor e Dashboard | Concluido | 2026-06-26 | Marco de congelamento arquitetural antes da fase Alpha |
| Alpha 001 | Desenvolver e validar a primeira estrategia proprietaria IORB em pesquisa e simulacao | Em desenvolvimento | 2026-06-26 | Ordem real nao autorizada |
| Data Source Checkpoint | Consolidar providers CSV, Parquet e DuckDB sob contrato comum de dados historicos | Concluido | 2026-06-26 | Replay e Research Lab permanecem sem conhecer formato fisico |
| SPRINT CTO 034 | Criar relatorio executivo consolidado do Quality Gate | Concluido | 2026-06-27 | `reports/quality_gate_summary.json` criado; Quality Gate preserva propagacao de falhas |
| Missao CTO - Institucionalizacao do MANIFEST.md | Criar fonte oficial unica para estado operacional do projeto e simplificar README | Concluido | 2026-06-27 | README deixa de registrar andamento do projeto; MANIFEST.md passa a ser Single Source of Truth |
| Missoes 194-200 | Projetar, implementar, validar e certificar infraestrutura de dados historicos reais | Concluido | 2026-06-28 | `MARKET_DATA_CERTIFIED_FOR_QUANTITATIVE_RESEARCH`; Replay, Research Lab, Validation Suite, Benchmark, Portfolio e Dashboard certificados com dados reais; operacao real permanece proibida |
| Missao 201 | Atualizar `MANIFEST.md` apos conclusao do Programa Market Data | Concluido | 2026-06-28 | Sprint 12 - Institutional Manifest Update; sincronizacao institucional com documentos oficiais de arquitetura, validacao e certificacao |
| Missao 221 | Corrigir estabilidade visual da aba Replay ao carregar PETR4 no Streamlit | Concluido | 2026-06-28 | `STREAMLIT_REPLAY_RENDER_STABILITY_FIX.md`; PETR4 carrega 2491 candles sem erro `removeChild`; WDO permanece ativo operacional/configuracao; operacao real permanece proibida |
| Missao 221 - DATASET_PROFILE_VALUE_PANEL | Criar painel visual de perfil quantitativo do dataset PETR4 | Concluido | 2026-06-28 | `DATASET_PROFILE_VALUE_PANEL.md`; Home exibe retorno acumulado, retorno anualizado, volatilidade, drawdown, melhores/piores dias, volume e graficos reais; 3159 testes OK; operacao real permanece proibida |
| Missoes 234-243 | Executar Sprint 17 - Alpha Discovery Lab para PETR4 diario | Concluido | 2026-06-28 | EDA, geracao de hipoteses, feature discovery, feature importance, Alpha101 Research, Factory Approval, Playbook, Strategy, Validation e Certification concluidos; Alpha101 `CERTIFIED_WITH_WARNINGS`; 3162 testes OK; Architecture Audit OK; operacao real permanece proibida |
| MT5 Read-Only Integration | Criar adaptador isolado para receber candles do MetaTrader 5 sem capacidade operacional | Concluido | 2026-06-28 | `MT5_READ_ONLY_INTEGRATION.md`; `MT5MarketDataProvider` converte candles para `domain.Candle` e publica `NEW_CANDLE`; 3166 testes OK; Architecture Audit OK; envio de ordens permanece proibido |
| MT5 Read-Only Connection Validation | Criar script manual seguro para validar conexao real MT5 Pepperstone por variaveis de ambiente | Concluido | 2026-06-28 | `scripts/validate_mt5_read_only_connection.py`; default `EURUSD` `H1`; falha clara sem credenciais; 3168 testes OK; Architecture Audit OK; nenhuma funcao operacional adicionada |
| Live Research Service | Consumir candles MT5 read-only e executar cadeia analitica ate DecisionPipeline | Concluido | 2026-06-28 | `application/live_research_service.py`; EURUSD H1 real validado com 10 candles, 6 StrategySignals e 6 DecisionContexts; todos bloqueados para operacao real; 3176 testes OK; Architecture Audit OK |
| Dashboard Live Read-Only Panel | Expor ultimo estado do LiveResearchService no Dashboard via DashboardService | Concluido | 2026-06-28 | Painel `Live Research READ ONLY`; exibe simbolo, timeframe, candles, StrategySignals, DecisionContexts e seguranca; dashboard segue sem acesso a infraestrutura; 3177 testes OK; Architecture Audit OK |
| Live Research Session Memory | Persistir historico visual dos ultimos snapshots live em memoria de sessao | Concluido | 2026-06-28 | `LiveResearchService` mantem historico configuravel em memoria; `DashboardService` expoe linhas read-only; dashboard exibe tabela simples; 3179 testes OK; Architecture Audit OK; nenhuma persistencia externa ou capacidade operacional criada |
| Live Research Session Summary | Gerar resumo estatistico da sessao live atual em memoria | Concluido | 2026-06-28 | Calcula total de snapshots, distribuicao BUY/SELL/WAIT, confianca media, maior/menor confianca, ultima decisao e ultimo timestamp; exposto via `DashboardService`; 3180 testes OK; Architecture Audit OK |
| Live Research Signal Quality View | Exibir qualidade dos sinais gerados na sessao live por estrategia | Concluido | 2026-06-28 | Calcula quantidade de sinais, distribuicao BUY/SELL/WAIT, confianca media e ultima decisao por estrategia; tabela read-only no painel live; 3181 testes OK; Architecture Audit OK |
| Live Experiment Runner | Avaliar estatisticamente sinais live sem PnL e sem operacao | Concluido | 2026-06-29 | `research/live_experiment_runner.py`; registra StrategySignals em memoria com timestamp, simbolo, timeframe, estrategia, decisao, confidence e regime; calcula total, BUY/SELL/WAIT, confianca media, desvio de confianca, distribuicao por regime e estrategia; exposto por `ResearchLabService` e `DashboardService`; 3184 testes OK; Architecture Audit OK |
| Sprint UI 1 - Dashboard Layout | Reorganizar o Dashboard como plataforma profissional de Quant Research | Concluido | 2026-06-29 | `dashboard_app.py`; layout com tabs HOME, Status Geral, Sistema, Replay, Live e Research; somente UI; `DashboardService` permanece fachada unica; 3184 testes OK; Architecture Audit OK |
| Sprint UI 2 - Live Research Dashboard | Refazer painel Live Research em secoes claras e somente leitura | Concluido | 2026-06-29 | `dashboard_app.py`; secoes LIVE STATUS, SESSION SUMMARY, SIGNAL QUALITY, LIVE HISTORY e SYSTEM HEALTH; formata confidence, decisoes e timestamps; nenhuma logica de negocio alterada; 3184 testes OK; Architecture Audit OK |
| Missao 245 - MT5 Forex Signal Dashboard | Transformar o dashboard principal em tela Forex MT5 read-only com oito pares e decisao BUY/SELL/WAIT | Concluido | 2026-06-29 | `MT5_FOREX_SIGNAL_DASHBOARD.md`; EURUSD, GBPUSD, USDCHF, USDJPY, AUDUSD, NZDUSD, EURJPY e GBPJPY exibidos via `DashboardService`; 3195 testes OK; Architecture Audit OK; nenhuma capacidade de envio de ordens |
| Quantitative Calibrated Score | Substituir confidence heuristica do painel Forex por score calibrado no Research Lab | Concluido | 2026-06-29 | `research/quantitative_score_engine.py`; confidence deriva de amostra, win rate, retorno medio, profit factor, drawdown e penalizacao por baixa volatilidade; 3200 testes OK; Architecture Audit OK; operacao real permanece proibida |
| Quantitative Score Diagnostic | Expor diagnostico do score calibrado sem alterar formula principal | Concluido | 2026-06-29 | Campos `matched_context_count`, `rejected_reason`, buckets de volatilidade/RSI/media, penalidades e drivers expostos via `DashboardService`; 3200 testes OK; Architecture Audit OK; operacao real permanece proibida |
| Quantitative Score Configuration | Tornar o score quantitativo totalmente parametrizavel pelo `ConfigurationManager` | Concluido | 2026-06-29 | Parametros de candles, lookback, forward return, medias, RSI, volatilidade, amostra minima, profit factor minimo, win rate minimo, confidence floor/ceiling e buckets centralizados; painel read-only `Research Configuration`; 3207 testes OK; Architecture Audit OK |
| Hotfix MT5 Forex Heuristic Rollback | Restaurar painel MT5 Forex funcional e isolar Research pesado do refresh principal | Concluido | 2026-06-29 | Fluxo principal do MT5 Forex voltou a usar somente candles, medias, RSI, momentum, volatilidade e decisao heuristica; `QuantitativeScoreEngine`, `TimeframeOptimizer`, botao `Recalcular Research` e diagnosticos pesados foram desconectados do painel principal; Streamlit validado em `http://localhost:8510`; 3248 testes OK; Architecture Audit OK; nenhuma ordem real adicionada |
| MT5 Forex Visual Decision Coloring | Colorir linhas do painel MT5 Forex por decisao | Concluido | 2026-06-29 | Linhas BUY em verde, SELL em vermelho e WAIT em branco; alteracao exclusivamente visual em `dashboard_app.py`; 51 testes focados OK; Architecture Audit OK; nenhuma logica operacional alterada |
| MT5 Forex Research Model Alignment | Alinhar a tabela MT5 Forex aos modelos ativos recomendados pelo Research Lab | Concluido | 2026-06-29 | Decisao BUY/SELL/WAIT vem do modelo ativo por par/timeframe; tabela exibe todos os indicadores do laboratorio e destaca em azul os indicadores usados na decisao; exemplo validado: `NZDUSD H1` usa `MA_RSI_FILTER`; 3256 testes OK; Architecture Audit OK; nenhuma ordem real adicionada |
| MT5 Theoretical Entry Radar | Detectar entrada teorica read-only no candle de gatilho | Concluido | 2026-06-29 | Aba MT5 Forex exibe Entrada Teorica, Candle do Sinal, Preco Teorico, Direcao Teorica e Motivo Entrada; gatilho ocorre quando o regime de mercado autoriza BUY/SELL do modelo ativo; registro apenas em memoria; 3258 testes OK; Architecture Audit OK; nenhuma ordem real adicionada |
| MT5 Demo Execution Dashboard | Permitir envio real para conta MT5 Demo com travas institucionais | Concluido | 2026-06-29 | Painel `Robo Demo MT5` aciona somente `DashboardService.run_demo_robot_once`; provider permanece desabilitado por padrao e exige `TRADERIA_DEMO_EXECUTION_ENABLED=1`; `MT5DemoExecutionProvider` bloqueia conta nao demo, exige SL/TP, impede posicao duplicada por simbolo e registra JSONL; `architecture_manifest.json` reconhece `DemoExecutionService` e `ExecutionResult`; 3280 testes OK; Architecture Audit OK; conta real permanece proibida |
| MT5 Research Trade Plan | Fazer o Research Lab definir entrada, stop, alvo e RR para o MT5 Forex | Concluido | 2026-06-29 | `research/mt5_research_trade_plan.py` cria plano read-only com melhor combinacao leve de saida `ATR_RR_RESEARCH_SELECTION`; tabela MT5 Forex exibe `Plano Research`, `Entrada Research`, `Stop Research`, `Alvo Research`, `RR Research`, `Modelo Saida`, `Score Saida` e combinacoes avaliadas; `Robo Demo MT5` consome o plano do Research Lab e nao recalcula stop/alvo no botao; execucao bloqueia sem `PLANO_VALIDO`; conta real permanece proibida |
| Forex-Only Dashboard UX | Limpar a experiencia visual principal para operar somente com Forex MT5 | Concluido | 2026-06-30 | Navegacao principal consolidada em `MT5 Forex`, `Laboratorio de Pesquisa`, `Historico MT5` e `Sistema Forex`; PETR4, WDO, Replay historico, Dataset legado e Alpha001 saem da experiencia principal; `Historico MT5` passa a listar somente candles Forex; `Sistema Forex` mostra somente estado MT5, robo demo, configuracao Forex e seguranca; 3310 testes OK; Architecture Audit OK; conta real permanece proibida |
| MT5 Demo Temporal Robot UX | Separar ativacao do robo demo de execucao imediata em massa | Concluido | 2026-06-29 | Painel `Robo Demo MT5` passou a oferecer `Armar robo demo`, `Avaliar gatilho agora` e `Desarmar robo`; selecao `TODOS` significa monitoramento, nao envio em lote; `DashboardService.evaluate_armed_demo_robot_once()` processa no maximo um gatilho valido por avaliacao e exige regime de mercado autorizado com plano do Research Lab; 3293 testes OK; Architecture Audit OK; conta real permanece proibida |
| Research Calibration Separation | Separar definitivamente Research Lab MT5 do refresh online MT5 Forex | Concluido | 2026-06-30 | `DashboardService.get_dashboard_view_model()` deixou de recalcular pesquisa automaticamente; `DashboardService.run_mt5_research_calibration()` executa calibracao sob demanda; `MT5MarketDataService.load_forex_research_snapshot()` carrega snapshot separado de 5000 candles sem substituir o painel online de 1000 candles; Research Lab produz constantes/modelos em memoria; MT5 Forex permanece leve e read-only; conta real permanece proibida |
| Research Lab Scenario Runner | Testar cenarios parametrizados de pesquisa por par/timeframe/modelo | Concluido | 2026-07-01 | Aba Lab executa apenas por `Executar Pesquisa`; `DashboardService.run_mt5_research_calibration()` usa snapshot historico de 5000 candles e roda a pesquisa um par por vez, variando timeframes e gerando ranking de cenarios parametrizados por modelo, EMA curta/longa, RSI thresholds, ATR stop factor, RR, momentum threshold e volatility threshold; a selecao final prioriza configuracoes com alvo de 70% de `Confirmacao Historica`, aceitando subconjunto de indicadores conforme o modelo vencedor; ultima tabela consolida uma linha independente por par com timeframe ideal, configuracao usada, cenario de compra e cenario de venda; melhor cenario por par gera ResearchConstants consumidas pelo Forex; MT5 Forex continua sem executar Scenario Runner; conta real permanece proibida |
| MT5 Demo Online Robot Cycle | Ativar monitoramento online automatico apos armar o robo demo | Concluido | 2026-06-29 | `DashboardService.run_online_demo_robot_cycle()` atualiza MT5 antes de avaliar o robo armado; dashboard arma o robo, inicia ciclo automatico, reexecuta a cada intervalo e nao repete candle ja avaliado; se um par tem gatilho sem plano completo, o robo continua monitorando os demais pares; 3295 testes OK; Architecture Audit OK; conta real permanece proibida |
| MT5 Visual Signals Indicator | Plotar sinais do TraderIA no grafico MT5 sem transferir logica para o terminal | Concluido | 2026-06-29 | `application/mt5_visual_signal_exporter.py` gera JSON visual read-only; `mt5/indicators/TraderIAVisualSignals.mq5` desenha setas BUY/SELL, entrada, stop, alvo, RR, modelo e status; sincronizacao visual automatica via `DashboardService.load_mt5_forex_signals()`; 3301 testes OK; Architecture Audit OK; indicador nao envia ordens |
| MT5 Visual Timeframe Alignment | Alinhar timeframe visual do MT5 ao timeframe do TraderIA | Concluido | 2026-06-29 | Template e perfis MT5 normalizados para M1 (`period_type=0`, `period_size=1`); `TraderIAVisualSignals.mq5` plota apenas quando `symbol == chart symbol` e `timeframe == chart timeframe`; em divergencia mostra `Sinal disponivel em ... grafico atual ...`; 3307 testes OK; Architecture Audit OK; Research Lab, entrada, execucao demo e regras de ordem nao foram alterados |
| Forex Dashboard Audit and Restore Point | Auditar abas principais e marcar novo ponto de recuperacao | Concluido | 2026-06-30 | Abas `MT5 Forex`, `Laboratorio de Pesquisa`, `Historico MT5` e `Sistema Forex` auditadas no browser em `localhost:8501`; sem excecoes visuais, sem PETR4/WDO, com `Visual MT5 AUTOMATICO`; 70 testes focados OK; Architecture Audit OK; restore point local criado em `.traderia/restore_points` |
| MT5 Trade Reports Audit | Criar aba de relatorios para confrontar negociacoes TraderIA x MT5 | Concluido | 2026-06-30 | Nova aba `Relatorios`; log local `.traderia/mt5_demo_execution.jsonl` confrontado com `positions_get`, `orders_get`, `history_orders_get` e `history_deals_get`; linhas `CONFERE` quando ticket, simbolo, lado e volume batem; 86 testes focados OK; Architecture Audit OK; nenhuma ordem real adicionada |
