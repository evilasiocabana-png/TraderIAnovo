# Alpha 003 - Opening Range Breakout Contextual

## 1. Nome da estrategia

Alpha 003 - Opening Range Breakout Contextual.

## 2. Objetivo

Definir o playbook oficial da terceira hipotese quantitativa do TraderIA_WDO,
focada em rompimentos controlados da faixa inicial do pregao em contextos de
fluxo, liquidez e volatilidade adequados.

Este documento descreve apenas a tese institucional da Alpha003. Nenhuma
estrategia, classe, execucao ou integracao operacional esta autorizada por este
playbook.

## 3. Hipotese quantitativa

A hipotese central e que o rompimento da faixa inicial do pregao pode capturar
movimentos direcionais relevantes quando ocorre com confirmacao de volume,
liquidez, momentum e contexto de mercado favoravel.

A Alpha003 assume que rompimentos possuem maior qualidade quando o mercado
apresenta abertura informativa, volatilidade suficiente, ausencia de ruído
excessivo e validacao contextual pelo Research Lab.

## 4. Fundamentacao

### Opening Range como referencia de preco

A faixa inicial do pregao representa a primeira zona institucional de disputa
entre compradores e vendedores. Rompimentos dessa faixa podem sinalizar
dominancia temporaria de fluxo direcional.

### Rompimento contextual

A Alpha003 nao deve operar rompimentos de forma cega. O rompimento somente pode
ser considerado quando houver confirmacao por volume, liquidez, momentum e
contexto de mercado compativel.

### Controle de falso rompimento

A estrategia deve evitar operar em cenarios de baixa liquidez, volatilidade
erratica ou ausencia de continuidade apos o rompimento. O foco e pesquisar
rompimentos com estrutura, nao perseguir movimento.

## 5. Mercado-alvo

O mercado-alvo inicial e o WDO, mini contrato de dolar futuro negociado na B3.

A Alpha003 deve permanecer restrita ao ambiente de pesquisa, replay e simulacao
ate aprovacao arquitetural explicita do CTO.

## 6. Mercados permitidos

Nesta versao institucional, somente os seguintes mercados podem ser considerados
em pesquisa:

- WDO em ambiente de Replay;
- WDO em Research Lab;
- WDO em simulacao controlada sem envio de ordens.

Qualquer outro ativo depende de nova missao e aprovacao arquitetural.

## 7. Mercados proibidos

A Alpha003 nao deve ser usada em:

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

A Alpha003 deve considerar apenas contextos em que:

- a faixa inicial do pregao esteja definida por contrato parametrizado;
- a liquidez esteja adequada;
- a volatilidade esteja suficiente para rompimento, mas nao erratica;
- o volume confirme participacao relevante;
- o momentum esteja alinhado ao rompimento;
- o MarketContext apresente confianca minima;
- a qualidade dos dados esteja aprovada pelo Data Lab;
- a amostra historica seja suficiente para pesquisa.

## 9. Features utilizadas

As features candidatas para pesquisa da Alpha003 sao:

- OpeningRange;
- maxima e minima da faixa inicial;
- distancia do preco em relacao a faixa inicial;
- volume;
- liquidez;
- volatilidade;
- momentum;
- regime de mercado;
- sessao do pregao;
- MarketContext;
- MarketDataQualityResult;
- validacao estatistica do Research Lab.

Nenhuma feature deve ser calculada dentro da estrategia. A Alpha003, se
implementada futuramente, devera consumir apenas contratos ja aprovados.

## 10. Gatilhos de BUY

Um gatilho de BUY somente podera ser pesquisado quando ocorrer:

- rompimento acima da maxima da Opening Range;
- confirmacao de volume minimo;
- momentum comprador alinhado;
- liquidez suficiente;
- volatilidade dentro do limite aceito;
- ausencia de regime lateral fraco;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 11. Gatilhos de SELL

Um gatilho de SELL somente podera ser pesquisado quando ocorrer:

- rompimento abaixo da minima da Opening Range;
- confirmacao de volume minimo;
- momentum vendedor alinhado;
- liquidez suficiente;
- volatilidade dentro do limite aceito;
- ausencia de regime lateral fraco;
- confirmacao de contexto pelo MarketContext;
- validacao minima de pesquisa para o cenario.

O sinal futuro, se aprovado, devera respeitar exclusivamente o contrato
`StrategySignal`.

## 12. Gestao

A gestao da Alpha003 deve ser parametrizada e validada no Research Lab.

Nenhum valor de risco, contrato, stop, target ou limite operacional deve ser
embutido diretamente em futura implementacao sem contrato aprovado.

A estrategia nao deve acessar diretamente RiskEngine, Broker, MT5, Dashboard ou
qualquer camada operacional.

## 13. Stop

O stop inicial deve ser parametrizado e testado por pesquisa quantitativa.

Hipoteses de stop candidatas:

- retorno para dentro da Opening Range;
- perda de momentum apos rompimento;
- stop por volatilidade;
- stop por invalidez do contexto;
- stop por tempo sem continuidade.

Nenhuma regra de stop esta autorizada para operacao real.

## 14. Target

O target inicial deve ser parametrizado e validado no Research Lab.

Hipoteses de target candidatas:

- alvo por multiplo da amplitude da Opening Range;
- alvo por relacao risco-retorno fixa;
- alvo por extensao de volatilidade;
- saida por perda de momentum;
- saida por mudanca de regime.

Nenhuma regra de target esta autorizada para operacao real.

## 15. Criterios de cancelamento

Uma entrada candidata deve ser cancelada quando:

- o rompimento retornar rapidamente para dentro da faixa inicial;
- a liquidez cair abaixo do minimo definido;
- a volatilidade exceder o limite aceito;
- o volume nao confirmar o movimento;
- o MarketContext perder confianca;
- o Data Lab indicar baixa qualidade dos dados;
- o Research Lab indicar amostra insuficiente;
- houver conflito entre momentum e direcao do rompimento.

## 16. Criterios de rejeicao

A Alpha003 deve ser rejeitada quando:

- depender de poucos eventos extremos;
- apresentar profit factor insuficiente;
- apresentar drawdown incompatavel;
- gerar sinais excessivos em falso rompimento;
- falhar em dias de baixa liquidez;
- depender de parametros extremamente sensiveis;
- apresentar baixa estabilidade estatistica;
- violar Clean Architecture;
- acessar qualquer camada operacional proibida;
- tentar executar ou sugerir ordem real.

## 17. Criterios de aceitacao

A Alpha003 so podera avancar para pesquisa estruturada quando:

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

- formacao da Opening Range;
- rompimentos da maxima e minima da faixa inicial;
- comportamento dos gatilhos de BUY e SELL;
- cancelamentos por falso rompimento;
- integracao indireta com MarketContext;
- geracao futura de `StrategySignal`, se a estrategia for aprovada;
- ausencia total de envio de ordens.

## 19. Research Lab

No Research Lab, a Alpha003 devera ser avaliada com:

- diferentes amostras de candles;
- diferentes regimes de mercado;
- variacoes controladas do tamanho da Opening Range;
- variacoes controladas de stop e target;
- comparacao com Alpha001 e Alpha002;
- analise de robustez;
- analise de sensibilidade;
- validacao walk-forward;
- simulacao Monte Carlo, quando disponivel;
- rejeicao de resultados com pouca amostra.

## 20. Metricas obrigatorias

A validacao da Alpha003 deve acompanhar, no minimo:

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

Este documento nao cria uma strategy, nao altera Alpha001, nao altera Alpha002,
nao altera Domain, nao altera RiskEngine e nao autoriza integracao com Broker,
MT5 ou corretora.

Qualquer evolucao da Alpha003 depende de nova missao, aprovacao arquitetural do
CTO, testes especificos, validacao de Research Lab e preservacao integral da
Clean Architecture do TraderIA_WDO.
