# Alpha 101 - Swing Pullback Contextual

## 1. Nome da estrategia

Alpha 101 - Swing Pullback Contextual.

## 2. Familia da estrategia

Swing Trade.

A Alpha101 inaugura a familia Swing Trade do TraderIA_WDO. Sua pesquisa deve
considerar horizontes superiores ao intraday, mantendo a estrategia isolada de
qualquer execucao operacional real.

## 3. Objetivo

Definir o playbook oficial da primeira hipotese quantitativa Swing Trade do
TraderIA_WDO, focada em pullbacks estruturados dentro de tendencias previamente
qualificadas por contexto, liquidez, volatilidade e validacao estatistica.

Este documento descreve apenas a tese institucional da Alpha101. Nenhuma
estrategia, classe, execucao ou integracao operacional esta autorizada por este
playbook.

## 4. Hipotese quantitativa

A hipotese central e que, em mercados com tendencia estatisticamente
identificavel, recuos controlados contra a direcao principal podem oferecer
pontos de entrada com assimetria favoravel quando o contexto permanece valido.

A Alpha101 assume que um pullback so possui qualidade quando ocorre sem ruptura
da estrutura principal, com liquidez adequada, volatilidade compativel,
momentum retomando a favor da tendencia e validacao contextual pelo Research
Lab.

## 5. Fundamentacao

### Tendencia como contexto primario

O Swing Trade depende de continuidade estrutural. A Alpha101 deve pesquisar
apenas cenarios em que a direcao dominante esteja identificada por features e
contratos existentes, sem inferencia manual ou leitura subjetiva.

### Pullback como assimetria

O pullback representa um recuo temporario dentro de uma tendencia maior. A
hipotese e que a entrada apos estabilizacao do recuo pode reduzir perseguicao de
preco e melhorar a relacao entre risco assumido e retorno esperado.

### Controle de invalidacao

A estrategia deve rejeitar pullbacks que se transformem em reversao estrutural.
Qualquer perda de contexto, queda de liquidez, volatilidade desordenada ou
rompimento de estrutura invalida a tese candidata.

## 6. Mercado-alvo

O mercado-alvo inicial e o WDO, mini contrato de dolar futuro negociado na B3,
em ambiente historico controlado.

A Alpha101 deve permanecer restrita ao ambiente de pesquisa, replay e simulacao
ate aprovacao arquitetural explicita do CTO.

## 7. Mercados permitidos

Nesta versao institucional, somente os seguintes mercados podem ser considerados
em pesquisa:

- WDO em ambiente de Replay;
- WDO em Research Lab;
- WDO em simulacao controlada sem envio de ordens.

Qualquer outro ativo depende de nova missao e aprovacao arquitetural.

## 8. Mercados proibidos

A Alpha101 nao deve ser usada em:

- WIN;
- acoes;
- opcoes;
- criptoativos;
- forex;
- mercados externos;
- conta real;
- MT5;
- corretora;
- qualquer ambiente com envio de ordem real.

## 9. Contexto

A Alpha101 deve considerar apenas contextos em que:

- a familia Swing Trade esteja explicitamente configurada;
- o timeframe de pesquisa seja compativel com operacoes multi-sessao;
- a tendencia principal esteja qualificada por contratos existentes;
- a liquidez esteja adequada;
- a volatilidade esteja suficiente, mas nao erratica;
- o MarketContext apresente confianca minima;
- a qualidade dos dados esteja aprovada pelo Data Lab;
- a amostra historica seja suficiente para pesquisa Swing Trade;
- o risco simulado seja compativel com carregamento entre sessoes.

## 10. Features utilizadas

As features candidatas para pesquisa da Alpha101 sao:

- tendencia estrutural;
- medias moveis;
- momentum;
- volatilidade;
- volume;
- liquidez;
- regime de mercado;
- distancia de preco em relacao a referencias de tendencia;
- MarketContext;
- MarketDataQualityResult;
- ResearchTimeframeProfile;
- StrategyProfile;
- validacao estatistica do Research Lab.

Nenhuma feature deve ser calculada dentro da estrategia. A Alpha101, se
implementada futuramente, devera consumir apenas contratos ja aprovados.

## 11. Gatilhos de BUY

Um gatilho de BUY somente podera ser pesquisado quando ocorrer:

- tendencia principal de alta previamente qualificada;
- pullback controlado sem perda da estrutura de alta;
- retomada de momentum comprador;
- liquidez suficiente;
- volatilidade dentro do limite aceito;
- ausencia de regime contrario dominante;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 12. Gatilhos de SELL

Um gatilho de SELL somente podera ser pesquisado quando ocorrer:

- tendencia principal de baixa previamente qualificada;
- pullback controlado sem perda da estrutura de baixa;
- retomada de momentum vendedor;
- liquidez suficiente;
- volatilidade dentro do limite aceito;
- ausencia de regime contrario dominante;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 13. Gestao

A gestao da Alpha101 deve ser parametrizada e validada no Research Lab.

Nenhum valor de risco, contrato, stop, target, periodo de carregamento ou limite
operacional deve ser embutido diretamente em futura implementacao sem contrato
aprovado.

A estrategia nao deve acessar diretamente RiskEngine, Broker, MT5, Dashboard ou
qualquer camada operacional.

## 14. Stop

O stop inicial deve ser parametrizado e testado por pesquisa quantitativa.

Hipoteses de stop candidatas:

- stop por rompimento da estrutura do pullback;
- stop por volatilidade;
- stop por perda da tendencia principal;
- stop por invalidez do MarketContext;
- stop por tempo maximo sem retomada da tendencia.

Nenhuma regra de stop esta autorizada para operacao real.

## 15. Target

O target inicial deve ser parametrizado e validado no Research Lab.

Hipoteses de target candidatas:

- alvo por extensao da tendencia;
- alvo por relacao risco-retorno fixa;
- alvo por volatilidade projetada;
- saida parcial em retomada de momentum;
- saida por perda de contexto ou enfraquecimento da tendencia.

Nenhuma regra de target esta autorizada para operacao real.

## 16. Criterios de cancelamento

Uma entrada candidata deve ser cancelada quando:

- a tendencia principal perder validade;
- o pullback romper estrutura contra a tese;
- a liquidez cair abaixo do minimo definido;
- a volatilidade exceder o limite aceito;
- o momentum nao retomar a favor da tendencia;
- o MarketContext perder confianca;
- o Data Lab indicar baixa qualidade dos dados;
- o Research Lab indicar amostra insuficiente;
- houver conflito entre regime de mercado e direcao candidata.

## 17. Criterios de rejeicao

A Alpha101 deve ser rejeitada quando:

- depender de poucos eventos extremos;
- apresentar profit factor insuficiente;
- apresentar drawdown incompatavel com Swing Trade;
- gerar sinais excessivos em reversoes estruturais;
- falhar em regimes laterais prolongados;
- depender de parametros extremamente sensiveis;
- apresentar baixa estabilidade estatistica;
- apresentar baixa reprodutibilidade;
- violar Clean Architecture;
- acessar qualquer camada operacional proibida;
- tentar executar ou sugerir ordem real.

## 18. Criterios de aceitacao

A Alpha101 so podera avancar para pesquisa estruturada quando:

- possuir hipotese quantitativa clara;
- respeitar todos os contratos publicos existentes;
- consumir features aprovadas;
- operar apenas em Replay e Research Lab;
- gerar apenas `StrategySignal`;
- nao acessar Broker, MT5 ou corretora;
- demonstrar amostra minima suficiente para Swing Trade;
- apresentar drawdown controlado;
- apresentar robustez estatistica inicial;
- possuir validacao reprodutivel;
- preservar isolamento entre Strategy, Research, Risk, Decision e Dashboard.

## 19. Replay

A validacao em Replay devera observar:

- identificacao do contexto de tendencia;
- formacao e desenvolvimento do pullback;
- comportamento dos gatilhos de BUY e SELL;
- cancelamentos por invalidacao de estrutura;
- integracao indireta com MarketContext;
- respeito ao timeframe de pesquisa Swing Trade;
- geracao futura de `StrategySignal`, se a estrategia for aprovada;
- ausencia total de envio de ordens.

## 20. Research Lab

No Research Lab, a Alpha101 devera ser avaliada com:

- diferentes amostras historicas;
- diferentes regimes de mercado;
- diferentes perfis de timeframe;
- variacoes controladas de stop e target;
- comparacao com estrategias intradiarias existentes;
- analise de robustez;
- analise de sensibilidade;
- validacao walk-forward;
- simulacao Monte Carlo, quando disponivel;
- validacao de reprodutibilidade;
- rejeicao de resultados com pouca amostra.

## 21. Metricas obrigatorias

A validacao da Alpha101 deve acompanhar, no minimo:

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
- reprodutibilidade.

## 22. Aviso institucional

Este playbook descreve exclusivamente uma hipotese quantitativa para pesquisa,
replay e simulacao controlada.

Nenhuma ordem real esta autorizada.

Este documento nao cria uma strategy, nao altera Alpha001, nao altera Alpha002,
nao altera Alpha003, nao altera Domain, nao altera RiskEngine e nao autoriza
integracao com Broker, MT5 ou corretora.

Qualquer evolucao da Alpha101 depende de nova missao, aprovacao arquitetural do
CTO, testes especificos, validacao de Research Lab e preservacao integral da
Clean Architecture do TraderIA_WDO.
