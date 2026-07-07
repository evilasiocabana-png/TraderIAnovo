# Alpha 002 - VWAP Mean Reversion Contextual

## 1. Nome da estrategia

Alpha 002 - VWAP Mean Reversion Contextual.

## 2. Objetivo

Definir o playbook oficial da segunda hipotese quantitativa do TraderIA_WDO,
focada em reversao controlada para VWAP em contextos de exaustao intradiaria.

Este documento descreve apenas a tese institucional da Alpha002. Nenhuma
estrategia, classe, execucao ou integracao operacional esta autorizada por este
playbook.

## 3. Hipotese quantitativa

A hipotese central e que, em determinados regimes intradiarios, afastamentos
estatisticamente relevantes do preco em relacao a VWAP podem indicar excesso
temporario de fluxo e possibilidade de reversao parcial.

A Alpha002 assume que sinais de reversao possuem maior qualidade quando o
mercado apresenta liquidez adequada, volatilidade controlada, perda de momentum
direcional e confirmacao contextual pelo Research Lab.

## 4. Mercado-alvo

O mercado-alvo inicial e o WDO, mini contrato de dolar futuro negociado na B3.

A Alpha002 deve permanecer restrita ao ambiente de pesquisa, replay e simulacao
ate aprovacao arquitetural explicita do CTO.

## 5. Fundamentacao

### VWAP como referencia institucional

A VWAP representa uma referencia intradiaria relevante para leitura de preco
medio ponderado por volume. A hipotese considera que afastamentos exagerados
podem sinalizar assimetria temporaria entre preco negociado e referencia de
fluxo.

### Mean Reversion contextual

A estrategia nao deve operar reversao de forma cega. A reversao so pode ser
considerada quando o contexto indicar reducao de momentum, liquidez suficiente
e ausencia de rompimento direcional forte.

### Controle de regime

A Alpha002 deve evitar operar contra tendencias fortes. Seu uso natural e em
cenarios de exaustao, lateralidade qualificada ou deslocamento excessivo sem
confirmacao de continuidade.

## 6. Mercados permitidos

Nesta versao institucional, somente os seguintes mercados podem ser considerados
em pesquisa:

- WDO em ambiente de Replay;
- WDO em Research Lab;
- WDO em simulacao controlada sem envio de ordens.

Qualquer outro ativo depende de nova missao e aprovacao arquitetural.

## 7. Mercados proibidos

A Alpha002 nao deve ser usada em:

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

## 8. Contexto

A Alpha002 deve considerar apenas contextos em que:

- a VWAP esteja disponivel como feature validada;
- a liquidez esteja adequada;
- o spread operacional simulado seja compativel;
- o regime nao indique tendencia forte persistente;
- o momentum mostre desaceleracao;
- a amostra historica seja suficiente;
- a qualidade dos dados esteja aprovada pelo Data Lab.

## 9. Features utilizadas

As features candidatas para pesquisa da Alpha002 sao:

- VWAP;
- distancia percentual do preco em relacao a VWAP;
- volatilidade intradiaria;
- volume;
- liquidez;
- momentum;
- regime de mercado;
- sessao do pregao;
- MarketContext;
- MarketDataQualityResult;
- validacao estatistica do Research Lab.

Nenhuma feature deve ser calculada dentro da estrategia. A Alpha002, se
implementada futuramente, devera consumir apenas contratos ja aprovados.

## 10. Gatilhos de BUY

Um gatilho de BUY somente podera ser pesquisado quando ocorrer:

- preco abaixo da VWAP por distancia minima parametrizada;
- perda de momentum vendedor;
- liquidez suficiente;
- volatilidade dentro do limite aceito;
- ausencia de regime de queda forte;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 11. Gatilhos de SELL

Um gatilho de SELL somente podera ser pesquisado quando ocorrer:

- preco acima da VWAP por distancia minima parametrizada;
- perda de momentum comprador;
- liquidez suficiente;
- volatilidade dentro do limite aceito;
- ausencia de regime de alta forte;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 12. Gestao

A gestao da Alpha002 deve ser parametrizada e validada no Research Lab.

Nenhum valor de risco, contrato, stop, target ou limite operacional deve ser
embutido diretamente em futura implementacao sem contrato aprovado.

A estrategia nao deve acessar diretamente RiskEngine, Broker, MT5, Dashboard ou
qualquer camada operacional.

## 13. Stop

O stop inicial deve ser parametrizado e testado por pesquisa quantitativa.

Hipoteses de stop candidatas:

- stop por distancia maxima da VWAP;
- stop por volatilidade;
- stop por rompimento da extremidade de exaustao;
- stop por invalidez do contexto.

Nenhuma regra de stop esta autorizada para operacao real.

## 14. Target

O target inicial deve ser parametrizado e validado no Research Lab.

Hipoteses de target candidatas:

- retorno parcial ate a VWAP;
- retorno ate zona intermediaria entre preco extremo e VWAP;
- alvo por relacao risco-retorno fixa;
- saida por perda de momentum da reversao.

Nenhuma regra de target esta autorizada para operacao real.

## 15. Criterios de cancelamento

Uma entrada candidata deve ser cancelada quando:

- o mercado acelerar contra a reversao;
- a tendencia forte for confirmada;
- a liquidez cair abaixo do minimo definido;
- a volatilidade exceder o limite aceito;
- o preco nao reduzir a distancia para VWAP;
- o MarketContext perder confianca;
- o Data Lab indicar baixa qualidade dos dados;
- o Research Lab indicar amostra insuficiente.

## 16. Criterios de rejeicao

A Alpha002 deve ser rejeitada quando:

- depender de poucos eventos extremos;
- apresentar profit factor insuficiente;
- apresentar drawdown incompatavel;
- gerar sinais excessivos em tendencia forte;
- falhar em regime de alta volatilidade;
- depender de parametros extremamente sensiveis;
- apresentar baixa estabilidade estatistica;
- violar Clean Architecture;
- acessar qualquer camada operacional proibida;
- tentar executar ou sugerir ordem real.

## 17. Criterios de aceitacao

A Alpha002 so podera avancar para pesquisa estruturada quando:

- possuir hipotese quantitativa clara;
- respeitar todos os contratos publicos existentes;
- consumir features aprovadas;
- operar apenas em Replay e Research Lab;
- gerar apenas `StrategySignal`;
- nao acessar Broker, MT5 ou corretora;
- demonstrar amostra minima suficiente;
- apresentar drawdown controlado;
- apresentar robustez estatistica inicial;
- possuir validacao reprodutivel.

## 18. Replay

A validacao em Replay devera observar:

- formacao da VWAP ao longo do pregao;
- distancia do preco em relacao a VWAP;
- comportamento dos gatilhos de BUY e SELL;
- cancelamentos por contexto invalido;
- integracao indireta com MarketContext;
- geracao futura de `StrategySignal`, se a estrategia for aprovada;
- ausencia total de envio de ordens.

## 19. Research Lab

No Research Lab, a Alpha002 devera ser avaliada com:

- diferentes amostras de candles;
- diferentes regimes de mercado;
- variacoes controladas de distancia para VWAP;
- variacoes controladas de stop e target;
- comparacao com Alpha001;
- analise de robustez;
- analise de sensibilidade;
- validacao walk-forward;
- simulacao Monte Carlo, quando disponivel;
- rejeicao de resultados com pouca amostra.

## 20. Metricas obrigatorias

A validacao da Alpha002 deve acompanhar, no minimo:

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
- qualidade dos dados.

## 21. Aviso institucional

Este playbook descreve exclusivamente uma hipotese quantitativa para pesquisa,
replay e simulacao controlada.

Nenhuma ordem real esta autorizada.

Este documento nao cria uma strategy, nao altera Alpha001, nao altera Domain,
nao altera RiskEngine e nao autoriza integracao com Broker, MT5 ou corretora.

Qualquer evolucao da Alpha002 depende de nova missao, aprovacao arquitetural do
CTO, testes especificos, validacao de Research Lab e preservacao integral da
Clean Architecture do TraderIA_WDO.
