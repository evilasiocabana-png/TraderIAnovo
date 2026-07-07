# Alpha 201 - Position Trend Contextual

## 1. Nome da estrategia

Alpha 201 - Position Trend Contextual.

## 2. Familia da estrategia

Position Trade.

A Alpha201 inaugura a familia Position Trade do TraderIA_WDO. Sua pesquisa deve
considerar horizontes mais longos que Swing Trade, mantendo a estrategia
isolada de qualquer execucao operacional real.

## 3. Objetivo

Definir o playbook oficial da primeira hipotese quantitativa Position Trade do
TraderIA_WDO, focada em capturar tendencias estruturais persistentes quando
contexto, dados, risco e pesquisa sustentarem uma tese de carregamento.

Este documento descreve apenas a tese institucional da Alpha201. Nenhuma
estrategia, classe, execucao ou integracao operacional esta autorizada por este
playbook.

## 4. Hipotese quantitativa

A hipotese central e que movimentos direcionais estruturais podem persistir por
periodos prolongados quando ha alinhamento entre tendencia, volatilidade
controlada, liquidez suficiente, regime favoravel e validacao estatistica.

A Alpha201 assume que uma posicao so possui qualidade quando a direcao
principal permanece consistente em multiplos recortes temporais, sem deteriorar
o contexto de mercado, o risco simulado ou a reprodutibilidade da pesquisa.

## 5. Fundamentacao

### Tendencia estrutural

O Position Trade depende de continuidade de tendencia em horizonte mais longo.
A Alpha201 deve pesquisar apenas cenarios em que a direcao dominante esteja
qualificada por contratos e features existentes, sem leitura subjetiva ou
intervencao operacional.

### Carregamento como tese quantitativa

O carregamento de posicao exige que o contexto continue valido alem de uma
unica sessao. A hipotese e que sinais com confirmacao estrutural podem reduzir
ruido de curto prazo e capturar movimentos mais amplos.

### Controle de degradacao

A estrategia deve rejeitar cenarios em que a tendencia perca persistencia,
a volatilidade fique erratica, a liquidez deteriore ou a validacao do Research
Lab indique fragilidade estatistica.

## 6. Mercado-alvo

O mercado-alvo inicial e o WDO, mini contrato de dolar futuro negociado na B3,
em ambiente historico controlado.

A Alpha201 deve permanecer restrita ao ambiente de pesquisa, replay e simulacao
ate aprovacao arquitetural explicita do CTO.

## 7. Mercados permitidos

Nesta versao institucional, somente os seguintes mercados podem ser considerados
em pesquisa:

- WDO em ambiente de Replay;
- WDO em Research Lab;
- WDO em simulacao controlada sem envio de ordens.

Qualquer outro ativo depende de nova missao e aprovacao arquitetural.

## 8. Mercados proibidos

A Alpha201 nao deve ser usada em:

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

A Alpha201 deve considerar apenas contextos em que:

- a familia Position Trade esteja explicitamente configurada;
- o timeframe de pesquisa seja compativel com carregamento prolongado;
- a tendencia estrutural esteja qualificada por contratos existentes;
- a liquidez esteja adequada;
- a volatilidade esteja sustentavel para carregamento;
- o MarketContext apresente confianca minima;
- a qualidade dos dados esteja aprovada pelo Data Lab;
- a amostra historica seja suficiente para pesquisa Position Trade;
- o risco simulado seja compativel com exposicao prolongada;
- a reprodutibilidade esteja validada.

## 10. Features utilizadas

As features candidatas para pesquisa da Alpha201 sao:

- tendencia estrutural;
- inclinacao de medias moveis;
- momentum de longo prazo;
- volatilidade realizada;
- volume;
- liquidez;
- regime de mercado;
- persistencia direcional;
- distancia de preco em relacao a referencias de tendencia;
- MarketContext;
- MarketDataQualityResult;
- ResearchTimeframeProfile;
- StrategyProfile;
- RiskProfile;
- validacao estatistica do Research Lab.

Nenhuma feature deve ser calculada dentro da estrategia. A Alpha201, se
implementada futuramente, devera consumir apenas contratos ja aprovados.

## 11. Gatilhos de BUY

Um gatilho de BUY somente podera ser pesquisado quando ocorrer:

- tendencia estrutural de alta previamente qualificada;
- persistencia direcional positiva;
- momentum comprador sustentado;
- liquidez suficiente;
- volatilidade dentro do limite aceito para carregamento;
- ausencia de regime contrario dominante;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario;
- risco simulado compativel com exposicao prolongada.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 12. Gatilhos de SELL

Um gatilho de SELL somente podera ser pesquisado quando ocorrer:

- tendencia estrutural de baixa previamente qualificada;
- persistencia direcional negativa;
- momentum vendedor sustentado;
- liquidez suficiente;
- volatilidade dentro do limite aceito para carregamento;
- ausencia de regime contrario dominante;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario;
- risco simulado compativel com exposicao prolongada.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 13. Gestao

A gestao da Alpha201 deve ser parametrizada e validada no Research Lab.

Nenhum valor de risco, contrato, stop, target, periodo de carregamento,
exposicao maxima ou limite operacional deve ser embutido diretamente em futura
implementacao sem contrato aprovado.

A estrategia nao deve acessar diretamente RiskEngine, Broker, MT5, Dashboard ou
qualquer camada operacional.

## 14. Stop

O stop inicial deve ser parametrizado e testado por pesquisa quantitativa.

Hipoteses de stop candidatas:

- stop por perda da tendencia estrutural;
- stop por volatilidade;
- stop por deterioracao de liquidez;
- stop por invalidez do MarketContext;
- stop por quebra de persistencia direcional;
- stop por limite de drawdown simulado.

Nenhuma regra de stop esta autorizada para operacao real.

## 15. Target

O target inicial deve ser parametrizado e validado no Research Lab.

Hipoteses de target candidatas:

- alvo por extensao da tendencia estrutural;
- alvo por relacao risco-retorno fixa;
- alvo por volatilidade projetada;
- saida parcial por exaustao de momentum;
- saida por mudanca de regime;
- saida por perda de persistencia direcional.

Nenhuma regra de target esta autorizada para operacao real.

## 16. Criterios de cancelamento

Uma entrada candidata deve ser cancelada quando:

- a tendencia estrutural perder validade;
- a persistencia direcional desaparecer;
- a liquidez cair abaixo do minimo definido;
- a volatilidade exceder o limite aceito;
- o momentum divergir da direcao candidata;
- o MarketContext perder confianca;
- o Data Lab indicar baixa qualidade dos dados;
- o Risk Lab bloquear pesquisa ou simulacao;
- o Research Lab indicar amostra insuficiente;
- houver conflito entre regime de mercado e direcao candidata.

## 17. Criterios de rejeicao

A Alpha201 deve ser rejeitada quando:

- depender de poucos eventos extremos;
- apresentar profit factor insuficiente;
- apresentar drawdown incompatavel com Position Trade;
- gerar sinais excessivos em regimes laterais;
- falhar em mudancas estruturais de regime;
- depender de parametros extremamente sensiveis;
- apresentar baixa estabilidade estatistica;
- apresentar baixa reprodutibilidade;
- apresentar baixa robustez em campanhas;
- violar Clean Architecture;
- acessar qualquer camada operacional proibida;
- tentar executar ou sugerir ordem real.

## 18. Criterios de aceitacao

A Alpha201 so podera avancar para pesquisa estruturada quando:

- possuir hipotese quantitativa clara;
- respeitar todos os contratos publicos existentes;
- consumir features aprovadas;
- operar apenas em Replay e Research Lab;
- gerar apenas `StrategySignal`;
- nao acessar Broker, MT5 ou corretora;
- demonstrar amostra minima suficiente para Position Trade;
- apresentar drawdown controlado;
- apresentar robustez estatistica inicial;
- possuir validacao reprodutivel;
- preservar isolamento entre Strategy, Research, Risk, Decision e Dashboard.

## 19. Replay

A validacao em Replay devera observar:

- identificacao da tendencia estrutural;
- persistencia direcional ao longo do periodo analisado;
- comportamento dos gatilhos de BUY e SELL;
- cancelamentos por perda de estrutura;
- integracao indireta com MarketContext;
- respeito ao timeframe de pesquisa Position Trade;
- geracao futura de `StrategySignal`, se a estrategia for aprovada;
- ausencia total de envio de ordens.

## 20. Research Lab

No Research Lab, a Alpha201 devera ser avaliada com:

- diferentes amostras historicas;
- diferentes regimes de mercado;
- diferentes perfis de timeframe;
- variacoes controladas de stop e target;
- comparacao com estrategias intradiarias e Swing Trade existentes;
- analise de robustez;
- analise de sensibilidade;
- validacao walk-forward;
- simulacao Monte Carlo, quando disponivel;
- validacao de reprodutibilidade;
- campanhas com multiplos periodos;
- rejeicao de resultados com pouca amostra.

## 21. Metricas obrigatorias

A validacao da Alpha201 deve acompanhar, no minimo:

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
- consistencia por regime;
- resultado por campanha.

## 22. Aviso institucional

Este playbook descreve exclusivamente uma hipotese quantitativa para pesquisa,
replay e simulacao controlada.

Nenhuma ordem real esta autorizada.

Este documento nao cria uma strategy, nao altera Alpha001, nao altera Alpha002,
nao altera Alpha003, nao altera Alpha101, nao altera Domain, nao altera
RiskEngine e nao autoriza integracao com Broker, MT5 ou corretora.

Qualquer evolucao da Alpha201 depende de nova missao, aprovacao arquitetural do
CTO, testes especificos, validacao de Research Lab e preservacao integral da
Clean Architecture do TraderIA_WDO.
