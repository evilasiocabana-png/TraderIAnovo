# Alpha 001 - Institutional Opening Range Breakout (IORB)

## 1. Nome da estrategia

Alpha 001 - Institutional Opening Range Breakout (IORB).

## 2. Objetivo

Criar a primeira estrategia proprietaria do TraderIA_WDO, focada em capturar
rompimentos institucionais da faixa inicial do mercado no WDO, sempre em
ambiente de pesquisa, replay e simulacao.

## 3. Hipotese quantitativa

A hipotese central e que, em dias com contexto favoravel, volatilidade
suficiente, liquidez adequada e momentum direcional, o rompimento da Opening
Range pode indicar continuacao de fluxo institucional.

A estrategia assume que rompimentos da maxima ou minima inicial tendem a ter
maior qualidade quando alinhados a regime, momentum e validacao historica.

## 4. Mercado-alvo: WDO

O mercado-alvo inicial e o WDO, mini contrato de dolar futuro negociado na B3.

Nenhum outro ativo esta autorizado nesta primeira versao do playbook.

## 5. Conceito profissional

### Opening Range Breakout

A estrategia observa a faixa inicial do pregao e busca rompimentos da maxima
ou minima formada nesse intervalo.

### Volatility Breakout

O rompimento so deve ser considerado quando existir volatilidade suficiente
para sustentar deslocamento de preco.

### Trend Continuation

A entrada busca continuidade direcional depois que o mercado confirma pressao
compradora ou vendedora.

### Filtros institucionais de contexto

O sinal deve ser filtrado por regime de mercado, liquidez, volatilidade,
momentum e confianca da pesquisa quantitativa.

## 6. O que a estrategia tenta capturar

A Alpha 001 tenta capturar movimentos direcionais iniciados apos a formacao da
faixa de abertura, evitando entradas em contexto fraco, lateral ou sem amostra
historica suficiente.

Ela nao tenta prever o mercado. Ela tenta reagir a rompimentos qualificados.

## 7. Mercados proibidos

A estrategia nao deve operar nos seguintes cenarios:

- baixa liquidez;
- baixa volatilidade;
- regime `RANGE`;
- Research confidence insuficiente;
- pouca amostra historica.

## 8. Condicoes obrigatorias para operar

Uma operacao so pode ser considerada quando todas as condicoes abaixo forem
atendidas:

- regime favoravel;
- volatilidade suficiente;
- liquidez suficiente;
- momentum favoravel;
- research confidence minimo.

## 9. Opening Range

A Opening Range inicial deve ser formada entre 09:00 e 09:15.

Durante esse periodo, a estrategia deve registrar:

- maxima da faixa;
- minima da faixa.

Nenhuma entrada deve ser considerada antes da faixa estar completa.

## 10. Condicao de BUY

Uma condicao de compra so pode existir quando ocorrer:

- rompimento da maxima da Opening Range;
- confirmacao por momentum;
- regime favoravel.

O sinal gerado futuramente deve respeitar o contrato `StrategySignal`.

## 11. Condicao de SELL

Uma condicao de venda so pode existir quando ocorrer:

- rompimento da minima da Opening Range;
- confirmacao por momentum;
- regime favoravel.

O sinal gerado futuramente deve respeitar o contrato `StrategySignal`.

## 12. Stop

O stop inicial deve ser configuravel pelo `ConfigurationManager`.

Nenhum valor fixo deve ser embutido diretamente na estrategia sem justificativa
arquitetural.

## 13. Target

O alvo inicial deve ser configuravel pelo `ConfigurationManager`.

Nenhum valor fixo deve ser embutido diretamente na estrategia sem justificativa
arquitetural.

## 14. Quando cancelar entrada

A entrada deve ser cancelada quando:

- o rompimento perder momentum;
- o mercado voltar para dentro da Opening Range;
- a volatilidade cair abaixo do minimo aceitavel;
- a liquidez ficar insuficiente;
- o regime deixar de ser favoravel;
- a pesquisa quantitativa indicar baixa confianca;
- houver pouca amostra historica para o cenario.

## 15. Quando nao operar

A estrategia nao deve operar quando:

- a Opening Range ainda nao estiver completa;
- o mercado estiver em regime `RANGE`;
- o mercado apresentar baixa liquidez;
- o mercado apresentar baixa volatilidade;
- o momentum estiver neutro ou contrario;
- o Research Lab nao tiver validacao minima;
- os criterios de risco do sistema nao forem atendidos.

## 16. Como validar no Replay

A validacao inicial deve ser feita no Replay, candle a candle, observando:

- formacao correta da Opening Range;
- rompimentos da maxima e da minima;
- geracao de `StrategySignal`;
- comportamento em BUY, SELL e WAIT;
- interacao com features, regime e pesquisa quantitativa;
- historico paper sem envio de ordem real.

## 17. Como validar no Research Lab

No Research Lab, a estrategia deve ser submetida a experimentos com:

- diferentes amostras de candles;
- variacoes controladas de stop e target;
- benchmarks comparativos;
- validacao estatistica;
- analise de drawdown;
- rejeicao de resultados com pouca amostra.

## 18. Metricas minimas

A validacao deve acompanhar, no minimo:

- `total_trades`;
- `win_rate`;
- `profit_factor`;
- `max_drawdown_points`;
- `net_profit_points`.

## 19. Criterios de rejeicao

A estrategia deve ser rejeitada quando:

- tiver poucas operacoes para avaliacao;
- apresentar profit factor insuficiente;
- apresentar drawdown incompatavel com o risco;
- depender de um unico dia ou de poucos eventos extremos;
- operar demais em mercado lateral;
- gerar sinais contraditorios;
- falhar no Replay;
- falhar no Research Lab;
- violar qualquer regra arquitetural do TraderIA_WDO.

## 20. Criterios de aceitacao

A estrategia so pode avancar quando:

- respeitar Clean Architecture;
- retornar apenas `StrategySignal`;
- nao executar ordens;
- nao acessar Broker;
- nao acessar Risk Engine diretamente;
- funcionar no Replay;
- apresentar validacao aceitavel no Research Lab;
- possuir amostra minima suficiente;
- exibir drawdown controlado;
- demonstrar consistencia estatistica inicial.

## 21. Aviso

Este playbook descreve uma estrategia para pesquisa e simulacao.

Nenhuma ordem real esta autorizada.

Este documento nao e recomendacao financeira.

Qualquer evolucao para paper trading externo, corretora, MT5 ou operacao real
depende de novas missoes, validacoes formais, travas de risco e aprovacao
arquitetural explicita.
