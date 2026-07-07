# Alpha 102 - Swing Pullback Momentum Continuation

## 1. Nome da estrategia

Alpha 102 - Swing Pullback Momentum Continuation.

## 2. Familia da estrategia

Swing Trade.

A Alpha102 pertence a familia Swing Trade do TraderIA_WDO e representa uma
hipotese de continuidade direcional apos pullback controlado em tendencia
previamente qualificada.

## 3. Objetivo

Definir o playbook oficial da Alpha102, uma estrategia candidata de Swing Trade
baseada em tendencia mensuravel, pullback controlado, retomada de momentum,
liquidez adequada e contexto de mercado favoravel.

Este documento prepara etapas futuras de implementacao, mas nao implementa
codigo, nao cria Strategy, nao cria Config, nao cria Experiment e nao autoriza
qualquer execucao operacional real.

## 4. Hipotese quantitativa

Em mercados liquidos e direcionais, quando o ativo apresenta tendencia
mensuravel em timeframe superior e realiza um pullback controlado sem romper a
estrutura principal, a retomada do momentum na direcao da tendencia pode gerar
assimetria positiva em horizonte Swing Trade.

A Alpha102 nao deve comprar quedas nem vender altas de forma indiscriminada. O
evento pesquisavel e a combinacao entre tendencia valida, recuo saudavel,
preservacao estrutural e retomada confirmada.

## 5. Fundamentacao

### Momentum como anomalia pesquisavel

A literatura quantitativa documenta persistencia direcional em diferentes
horizontes e mercados. A Alpha102 deve pesquisar se essa persistencia pode ser
capturada com entrada mais eficiente apos pullback, evitando perseguicao de
preco esticado.

### Pullback como melhoria de assimetria

O pullback pode reduzir o risco de entrada tardia em tendencia. A tese e que,
quando a estrutura principal permanece intacta, a retomada do movimento pode
oferecer relacao retorno/risco superior a entradas por rompimento puro.

### Regime como filtro obrigatorio

Pullbacks em mercados laterais podem ser apenas ruido. Por isso, a Alpha102
deve operar somente quando o regime, a liquidez, a volatilidade e o
MarketContext sustentarem a leitura de continuidade.

### Validacao cientifica obrigatoria

A tese somente podera avancar apos validacao pelo Research Lab, incluindo
Replay, Walk-Forward, Monte Carlo, Stress Testing, Benchmark, Portfolio
Evaluation, robustez e reprodutibilidade.

## 6. Mercado-alvo

O mercado-alvo inicial e o WDO, mini contrato de dolar futuro negociado na B3,
em ambiente historico controlado.

A Alpha102 permanece restrita a pesquisa, replay e simulacao ate nova missao
arquitetural explicita.

## 7. Mercados permitidos

Nesta versao institucional, somente:

- WDO em ambiente de Replay;
- WDO em Research Lab;
- WDO em simulacao historica controlada;
- dados normalizados por contratos oficiais do TraderIA_WDO.

Qualquer expansao para outro mercado depende de nova missao e aprovacao do CTO.

## 8. Mercados proibidos

A Alpha102 nao deve ser utilizada em:

- conta real;
- corretora;
- MT5;
- execucao automatica;
- criptoativos;
- opcoes;
- ativos sem contrato institucional aprovado;
- qualquer ambiente com envio real de ordens.

## 9. Contexto

A Alpha102 deve considerar apenas contextos em que:

- a familia Swing Trade esteja explicitamente configurada;
- a qualidade dos dados esteja aprovada pelo Data Lab;
- exista tendencia mensuravel em timeframe superior;
- exista pullback controlado sem ruptura estrutural;
- exista liquidez minima;
- a volatilidade seja moderada e compativel com Swing Trade;
- o MarketContext apresente confianca minima;
- o regime seja favoravel a continuidade;
- a amostra historica seja suficiente para validacao Swing Trade;
- o risco simulado seja compativel com carregamento entre sessoes.

## 10. Features utilizadas

As features candidatas para pesquisa da Alpha102 sao:

- tendencia por media movel ou slope;
- distancia em relacao a media de referencia;
- ATR;
- volatilidade realizada;
- momentum;
- volume relativo;
- profundidade do pullback;
- recuperacao pos-pullback;
- regime de mercado;
- liquidez;
- MarketContext;
- MarketDataQualityResult;
- ResearchTimeframeProfile;
- StrategyProfile;
- ValidationSuiteResult;
- ValidationCertificationResult.

Nenhuma feature deve ser calculada dentro da estrategia. A Alpha102, se
implementada futuramente, devera consumir apenas contratos e componentes
aprovados.

## 11. Gatilhos de BUY

Um gatilho de BUY somente podera ser pesquisado quando ocorrer:

- tendencia superior positiva previamente qualificada;
- pullback controlado contra a tendencia;
- preservacao da estrutura principal de alta;
- retomada de momentum comprador;
- volume ou liquidez confirmando participacao;
- volatilidade compativel com assimetria;
- MarketContext sem contradicao direcional;
- ausencia de rejeicao estrutural apos a retomada.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 12. Gatilhos de SELL

Um gatilho de SELL somente podera ser pesquisado quando ocorrer:

- tendencia superior negativa previamente qualificada;
- repique controlado contra a tendencia;
- preservacao da estrutura principal de baixa;
- retomada de momentum vendedor;
- volume ou liquidez confirmando participacao;
- volatilidade compativel com assimetria;
- MarketContext sem contradicao direcional;
- ausencia de rejeicao estrutural apos a retomada.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 13. Gestao

A gestao da Alpha102 deve ser parametrizada e validada exclusivamente no
Research Lab.

Nenhum valor de risco, stop, target, periodo de carregamento, tamanho de posicao
ou filtro operacional pode ser hardcoded em futura implementacao.

A estrategia nao deve acessar diretamente RiskEngine, Broker, MT5, Dashboard,
DecisionPipeline ou qualquer camada operacional.

## 14. Stop

O stop inicial devera ser parametrizado e testado por pesquisa quantitativa.

Hipoteses de stop candidatas:

- stop por ruptura da estrutura do pullback;
- stop por perda da tendencia principal;
- stop por volatilidade;
- stop por invalidez do MarketContext;
- stop por tempo maximo sem retomada;
- stop por gap contra a posicao;
- stop por degradacao de liquidez.

Nenhuma regra de stop esta autorizada para operacao real.

## 15. Target

O target inicial devera ser parametrizado e validado no Research Lab.

Hipoteses de target candidatas:

- alvo por extensao da tendencia;
- alvo por relacao risco-retorno fixa;
- alvo por volatilidade projetada;
- saida por perda de momentum;
- saida por perda de MarketContext;
- saida por tempo maximo de carregamento;
- saida por retorno ao regime lateral.

Nenhuma regra de target esta autorizada para operacao real.

## 16. Criterios de cancelamento

Uma entrada candidata deve ser cancelada quando:

- a tendencia principal perder validade;
- o pullback romper a estrutura contra a tese;
- a retomada de momentum nao ocorrer;
- a liquidez cair abaixo do minimo definido;
- a volatilidade exceder limite compativel com Swing Trade;
- o MarketContext perder confianca;
- o regime indicar lateralidade persistente;
- houver gap excessivo;
- o Data Lab indicar baixa qualidade dos dados;
- o Research Lab indicar amostra insuficiente.

## 17. Criterios de rejeicao

A Alpha102 deve ser rejeitada quando:

- funcionar apenas em periodo isolado;
- apresentar baixa amostra;
- depender de poucos eventos extremos;
- apresentar profit factor insuficiente;
- apresentar drawdown incompatavel com Swing Trade;
- falhar em Walk-Forward;
- falhar em Monte Carlo;
- falhar em Stress Testing;
- apresentar alta correlacao com Alpha101 sem ganho incremental;
- piorar o portfolio;
- depender de parametros estreitos ou instaveis;
- violar Clean Architecture;
- acessar qualquer camada operacional proibida;
- tentar executar, aprovar ou sugerir ordem real.

## 18. Criterios de aceitacao

A Alpha102 so podera avancar para implementacao quando:

- possuir Config parametrizada em missao propria;
- preservar a familia Swing Trade;
- consumir apenas contratos aprovados;
- nao calcular features internamente;
- gerar apenas `StrategySignal`;
- operar apenas em Replay e Research Lab;
- nao acessar Broker, MT5, Dashboard ou Domain;
- demonstrar amostra minima suficiente;
- apresentar drawdown controlado;
- apresentar robustez estatistica;
- passar por Walk-Forward;
- passar por Monte Carlo;
- passar por Stress Testing;
- obter certificacao cientifica adequada na Validation Suite;
- demonstrar valor incremental em Benchmark e Portfolio Evaluation;
- preservar isolamento entre Strategy, Research, Risk, Decision e Dashboard.

## 19. Replay

A validacao em Replay devera observar:

- identificacao da tendencia superior;
- formacao do pullback;
- preservacao da estrutura principal;
- retomada de momentum;
- confirmacao de volume/liquidez;
- comportamento em gaps;
- comportamento em regimes laterais;
- comportamento do MarketContext;
- geracao futura de `StrategySignal`, se autorizada;
- ausencia total de envio de ordens.

## 20. Research Lab

No Research Lab, a Alpha102 devera ser avaliada com:

- diferentes amostras historicas;
- diferentes regimes de mercado;
- diferentes perfis de timeframe;
- variacoes controladas de profundidade de pullback;
- variacoes controladas de stop e target;
- comparacao com Alpha101 e demais Alphas;
- analise de robustez;
- analise de sensibilidade;
- dependencia de outliers;
- validacao Walk-Forward;
- validacao Monte Carlo;
- Stress Testing;
- Validation Suite;
- certificacao cientifica;
- Benchmark;
- Portfolio Evaluation;
- rejeicao de resultados com pouca amostra.

## 21. Metricas obrigatorias

A validacao da Alpha102 deve acompanhar, no minimo:

- `total_trades`;
- `win_rate`;
- `profit_factor`;
- `net_profit_points`;
- `gross_profit_points`;
- `gross_loss_points`;
- `max_drawdown_points`;
- `max_drawdown_percent`;
- `expectancy`;
- estabilidade de parametros;
- dependencia de outliers;
- qualidade da amostra;
- qualidade dos dados;
- robustez;
- reprodutibilidade;
- `scientific_score`;
- `robustness_score`;
- `reproducibility_score`;
- `diversification_score`;
- certificacao da Validation Suite;
- impacto no portfolio.

## 22. Pronto para implementacao

Este playbook esta aprovado para a proxima etapa arquitetural:

- criar ou evoluir `Alpha102Config`, se autorizado por nova missao;
- criar ou evoluir `Alpha102Strategy`, se autorizado por nova missao;
- criar ou evoluir `Alpha102Experiment`, se autorizado por nova missao;
- integrar a Alpha102 ao ecossistema de pesquisa, se autorizado por nova missao.

Essas etapas dependem de novas missoes explicitas.

## 23. Aviso institucional

Este playbook descreve exclusivamente uma estrategia candidata para pesquisa,
replay e simulacao controlada.

Nenhuma ordem real esta autorizada.

Este documento nao cria uma Strategy, nao altera Alpha001, nao altera Alpha002,
nao altera Alpha003, nao altera Alpha101, nao altera Domain, nao altera
RiskEngine e nao autoriza integracao com Broker, MT5 ou corretora.

Qualquer evolucao da Alpha102 depende de nova missao, aprovacao arquitetural do
CTO, testes especificos, validacao do Research Lab e preservacao integral da
Clean Architecture do TraderIA_WDO.
