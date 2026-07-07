# Alpha 301 - Long Short Relative Value Contextual

## 1. Nome da estrategia

Alpha 301 - Long Short Relative Value Contextual.

## 2. Familia da estrategia

Long & Short.

A Alpha301 inaugura a familia Long & Short do TraderIA_WDO. Sua pesquisa deve
considerar relacoes entre instrumentos, spreads, correlacao e divergencias
relativas, mantendo a estrategia isolada de qualquer execucao operacional real.

## 3. Objetivo

Definir o playbook oficial da primeira hipotese quantitativa Long & Short do
TraderIA_WDO, focada em capturar distorcoes relativas entre dois instrumentos
quando contexto, liquidez, risco e pesquisa sustentarem uma tese pareada.

Este documento descreve apenas a tese institucional da Alpha301. Nenhuma
estrategia, classe, execucao ou integracao operacional esta autorizada por este
playbook.

## 4. Hipotese quantitativa

A hipotese central e que pares de instrumentos historicamente relacionados
podem apresentar divergencias temporarias de valor relativo. Quando a relacao
permanece estatisticamente valida, o spread pode oferecer assimetria para uma
posicao comprada no instrumento relativamente descontado e vendida no
instrumento relativamente esticado.

A Alpha301 assume que um sinal Long & Short so possui qualidade quando a
correlacao historica, a liquidez dos dois lados, a estabilidade do spread, o
controle de risco e a validacao estatistica sustentam a tese.

## 5. Fundamentacao

### Valor relativo

O Long & Short depende da comparacao entre instrumentos, e nao de uma leitura
direcional isolada. A Alpha301 deve pesquisar apenas pares cuja relacao tenha
base historica, liquidez adequada e dados suficientes para avaliacao.

### Spread como objeto de pesquisa

O spread entre os instrumentos representa a unidade central da hipotese. A
pesquisa deve avaliar afastamento, reversao, persistencia, ruptura e
estabilidade do spread sem depender de opiniao discricionaria.

### Neutralidade parcial de mercado

A estrategia busca reduzir dependencia direcional isolada, mas nao assume risco
nulo. O Research Lab deve medir exposicao residual, drawdown do spread,
dependencia de outliers e degradacao de correlacao.

## 6. Mercado-alvo

O mercado-alvo inicial e o ambiente historico controlado do TraderIA_WDO,
utilizando pares previamente autorizados pelo CTO.

A Alpha301 deve permanecer restrita ao ambiente de pesquisa, replay e simulacao
ate aprovacao arquitetural explicita do CTO.

## 7. Mercados permitidos

Nesta versao institucional, somente os seguintes cenarios podem ser considerados
em pesquisa:

- pares autorizados em ambiente de Replay;
- pares autorizados em Research Lab;
- simulacao controlada sem envio de ordens;
- datasets historicos com qualidade aprovada pelo Data Lab.

Qualquer par, ativo ou bolsa depende de nova missao e aprovacao arquitetural.

## 8. Mercados proibidos

A Alpha301 nao deve ser usada em:

- conta real;
- MT5;
- corretora;
- criptoativos;
- forex;
- opcoes;
- mercados externos nao autorizados;
- instrumentos sem liquidez validada;
- pares sem dados historicos suficientes;
- qualquer ambiente com envio de ordem real.

## 9. Contexto

A Alpha301 deve considerar apenas contextos em que:

- a familia Long & Short esteja explicitamente configurada;
- os dois instrumentos estejam cadastrados e habilitados;
- o spread esteja disponivel como feature validada;
- a correlacao historica esteja acima do minimo aceito;
- a liquidez seja adequada em ambos os lados;
- a volatilidade do spread esteja dentro do limite aceito;
- o MarketContext apresente confianca minima;
- a qualidade dos dados esteja aprovada pelo Data Lab;
- a amostra historica seja suficiente para pesquisa Long & Short;
- o risco simulado seja compativel com exposicao pareada.

## 10. Features utilizadas

As features candidatas para pesquisa da Alpha301 sao:

- spread entre instrumentos;
- z-score do spread;
- correlacao;
- beta relativo;
- cointegracao, quando disponivel como feature aprovada;
- volatilidade do spread;
- liquidez dos dois instrumentos;
- volume dos dois instrumentos;
- regime de mercado;
- MarketContext;
- MarketDataQualityResult;
- ResearchTimeframeProfile;
- StrategyProfile;
- RiskProfile;
- validacao estatistica do Research Lab.

Nenhuma feature deve ser calculada dentro da estrategia. A Alpha301, se
implementada futuramente, devera consumir apenas contratos ja aprovados.

## 11. Gatilhos de LONG

Um gatilho de LONG somente podera ser pesquisado quando ocorrer:

- instrumento principal relativamente descontado;
- z-score do spread abaixo do limite negativo parametrizado;
- correlacao historica valida;
- liquidez suficiente nos dois instrumentos;
- volatilidade do spread dentro do limite aceito;
- ausencia de ruptura estrutural da relacao;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario;
- risco simulado compativel com exposicao pareada.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 12. Gatilhos de SHORT

Um gatilho de SHORT somente podera ser pesquisado quando ocorrer:

- instrumento principal relativamente esticado;
- z-score do spread acima do limite positivo parametrizado;
- correlacao historica valida;
- liquidez suficiente nos dois instrumentos;
- volatilidade do spread dentro do limite aceito;
- ausencia de ruptura estrutural da relacao;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario;
- risco simulado compativel com exposicao pareada.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 13. Gestao

A gestao da Alpha301 deve ser parametrizada e validada no Research Lab.

Nenhum valor de risco, tamanho relativo, hedge ratio, stop, target, periodo de
carregamento ou limite operacional deve ser embutido diretamente em futura
implementacao sem contrato aprovado.

A estrategia nao deve acessar diretamente RiskEngine, Broker, MT5, Dashboard ou
qualquer camada operacional.

## 14. Stop

O stop inicial deve ser parametrizado e testado por pesquisa quantitativa.

Hipoteses de stop candidatas:

- stop por ruptura do spread;
- stop por perda de correlacao;
- stop por deterioracao de liquidez em qualquer perna;
- stop por volatilidade excessiva do spread;
- stop por invalidez do MarketContext;
- stop por limite de drawdown simulado.

Nenhuma regra de stop esta autorizada para operacao real.

## 15. Target

O target inicial deve ser parametrizado e validado no Research Lab.

Hipoteses de target candidatas:

- retorno do spread a media;
- retorno parcial do z-score;
- alvo por relacao risco-retorno fixa;
- saida por normalizacao da divergencia;
- saida por perda de contexto;
- saida por degradacao da correlacao.

Nenhuma regra de target esta autorizada para operacao real.

## 16. Criterios de cancelamento

Uma entrada candidata deve ser cancelada quando:

- a correlacao cair abaixo do minimo definido;
- o spread romper limite estrutural;
- a liquidez cair abaixo do minimo em qualquer instrumento;
- a volatilidade do spread exceder o limite aceito;
- houver conflito entre regime de mercado e tese pareada;
- o MarketContext perder confianca;
- o Data Lab indicar baixa qualidade dos dados;
- o Risk Lab bloquear pesquisa ou simulacao;
- o Research Lab indicar amostra insuficiente;
- qualquer uma das pernas deixar de estar disponivel.

## 17. Criterios de rejeicao

A Alpha301 deve ser rejeitada quando:

- depender de poucos eventos extremos;
- apresentar profit factor insuficiente;
- apresentar drawdown incompatavel com Long & Short;
- falhar em mudancas de regime;
- depender de pares instaveis;
- depender de parametros extremamente sensiveis;
- apresentar baixa estabilidade estatistica;
- apresentar baixa reprodutibilidade;
- apresentar baixa robustez em campanhas;
- violar Clean Architecture;
- acessar qualquer camada operacional proibida;
- tentar executar ou sugerir ordem real.

## 18. Criterios de aceitacao

A Alpha301 so podera avancar para pesquisa estruturada quando:

- possuir hipotese quantitativa clara;
- respeitar todos os contratos publicos existentes;
- consumir features aprovadas;
- operar apenas em Replay e Research Lab;
- gerar apenas `StrategySignal`;
- nao acessar Broker, MT5 ou corretora;
- demonstrar amostra minima suficiente para Long & Short;
- apresentar drawdown controlado;
- apresentar robustez estatistica inicial;
- possuir validacao reprodutivel;
- preservar isolamento entre Strategy, Research, Risk, Decision e Dashboard.

## 19. Replay

A validacao em Replay devera observar:

- formacao do spread entre instrumentos;
- comportamento do z-score do spread;
- estabilidade da correlacao;
- comportamento dos gatilhos de LONG e SHORT;
- cancelamentos por ruptura da relacao;
- integracao indireta com MarketContext;
- geracao futura de `StrategySignal`, se a estrategia for aprovada;
- ausencia total de envio de ordens.

## 20. Research Lab

No Research Lab, a Alpha301 devera ser avaliada com:

- diferentes pares autorizados;
- diferentes amostras historicas;
- diferentes regimes de mercado;
- variacoes controladas de z-score;
- variacoes controladas de hedge ratio;
- variacoes controladas de stop e target;
- analise de robustez;
- analise de sensibilidade;
- validacao walk-forward;
- simulacao Monte Carlo, quando disponivel;
- validacao de reprodutibilidade;
- campanhas com multiplos periodos;
- rejeicao de resultados com pouca amostra.

## 21. Metricas obrigatorias

A validacao da Alpha301 deve acompanhar, no minimo:

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
- estabilidade de correlacao;
- resultado por campanha.

## 22. Aviso institucional

Este playbook descreve exclusivamente uma hipotese quantitativa para pesquisa,
replay e simulacao controlada.

Nenhuma ordem real esta autorizada.

Este documento nao cria uma strategy, nao altera Alpha001, nao altera Alpha002,
nao altera Alpha003, nao altera Alpha101, nao altera Alpha201, nao altera
Domain, nao altera RiskEngine e nao autoriza integracao com Broker, MT5 ou
corretora.

Qualquer evolucao da Alpha301 depende de nova missao, aprovacao arquitetural do
CTO, testes especificos, validacao de Research Lab e preservacao integral da
Clean Architecture do TraderIA_WDO.
