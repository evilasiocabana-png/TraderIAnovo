# Alpha102 Research - Swing Pullback Momentum Continuation

## 1. Status

HIPOTESE PRONTA PARA SUBMISSAO A ALPHA FACTORY.

Este documento registra apenas pesquisa quantitativa e hipotese candidata.
Nenhum codigo, configuracao, estrategia, experimento, integracao operacional
ou execucao real esta autorizado por esta missao.

## 2. Objetivo

Realizar a pesquisa quantitativa da proxima hipotese da familia Swing Trade,
selecionando uma tese unica, testavel e alinhada ao ecossistema TraderIA_WDO.

## 3. Revisao de literatura quantitativa

### Momentum intermediario

Jegadeesh e Titman documentaram que estrategias compradas em ativos vencedores
e vendidas em perdedores, em horizontes intermediarios, apresentaram retornos
positivos em amostras historicas de acoes. A implicacao para Swing Trade nao e
copiar a regra diretamente, mas reconhecer que continuidade direcional apos
forca previa e uma anomalia quantitativa amplamente estudada.

Referencia:
https://onlinelibrary.wiley.com/doi/abs/10.1111/j.1540-6261.1993.tb04702.x

### Time-series momentum em futuros

Moskowitz, Ooi e Pedersen documentaram persistencia de retornos de 1 a 12 meses
em futuros de indices, moedas, commodities e bonds. A evidencia e relevante
para o TraderIA_WDO porque a Alpha candidata pode ser formulada como momentum
temporal do proprio ativo, sem depender de comparacao cross-sectional.

Referencia:
https://ideas.repec.org/a/eee/jfinec/v104y2012i2p228-250.html

### Trend following de longo historico

Hurst, Ooi e Pedersen estudaram trend-following em uma amostra de longo prazo,
incluindo multiplos mercados e ambientes economicos. A principal licao para a
Alpha candidata e que seguir tendencias pode possuir valor estatistico, mas
precisa ser testado sob regimes, custos, gaps, drawdowns e estabilidade de
parametros.

Referencia:
https://www.aqr.com/Insights/Research/Journal-Article/A-Century-of-Evidence-on-Trend-Following-Investing

### Regras tecnicas formalizaveis

Brock, Lakonishok e LeBaron testaram regras tecnicas simples, incluindo medias
moveis e rompimentos de faixas, com inferencia estatistica e bootstrap. Para a
Alpha candidata, isso reforca que padroes tecnicos so sao aceitaveis se forem
transformados em regras mensuraveis, auditaveis e validadas fora da amostra.

Referencia:
https://ideas.repec.org/a/bla/jfinan/v47y1992i5p1731-64.html

## 4. Estrategias Swing amplamente estudadas

As familias de estrategias Swing mais recorrentes na literatura e na pratica
quantitativa incluem:

- momentum de medio prazo;
- time-series momentum;
- trend-following por media movel;
- breakout de faixa;
- pullback em tendencia;
- reversao de curto prazo;
- carry e term structure em futuros;
- volatilidade/compressao seguida de expansao.

Para esta pesquisa, a hipotese selecionada nao sera reversao curta nem novo
breakout de compressao, porque a Alpha102 existente ja cobre compressao de
volatilidade. A tese selecionada sera um pullback de continuidade em tendencia.

## 5. Hipotese quantitativa selecionada

### Nome candidato

Swing Pullback Momentum Continuation.

### Hipotese

Em mercados liquidos e direcionais, quando o ativo apresenta tendencia
mensuravel em timeframe superior e realiza um pullback controlado sem romper a
estrutura principal, a retomada do momentum na direcao da tendencia pode gerar
assimetria positiva em horizonte Swing Trade.

Em termos praticos, a tese nao e comprar queda nem vender alta. A tese e
pesquisar se recuos moderados dentro de uma tendencia validada oferecem melhor
relacao retorno/risco do que entradas por rompimento tardio ou perseguicao de
preco esticado.

## 6. Vantagem estatistica potencial

A vantagem estatistica potencial vem da combinacao de quatro elementos:

- persistencia direcional documentada em momentum e trend-following;
- entrada apos recuo, reduzindo risco de comprar ou vender movimento esticado;
- filtro de regime, evitando aplicar pullback em mercado lateral;
- confirmacao de retomada, evitando antecipar reversoes sem evidencia.

A hipotese tenta capturar continuidade, mas com preco de entrada mais eficiente
do que um breakout puro.

## 7. Mercados candidatos

### Permitidos para pesquisa

- WDO em Replay;
- WDO em Research Lab;
- futuros liquidos, apenas como expansao futura mediante nova missao;
- series historicas normalizadas por contratos oficiais.

### Proibidos nesta pesquisa

- conta real;
- corretora;
- MT5;
- criptoativos;
- opcoes;
- ativos sem contrato institucional aprovado;
- qualquer ambiente com envio de ordens.

## 8. Regimes candidatos

A hipotese deve ser pesquisada apenas em:

- TREND;
- TREND com volatilidade moderada;
- retomada pos-correcao;
- liquidez suficiente;
- MarketContext com confianca minima.

Deve ser rejeitada ou filtrada em:

- RANGE persistente;
- LOW_LIQUIDITY;
- VOLATILE extremo;
- gaps recorrentes;
- regimes com baixa confianca contextual;
- mercados sem direcionalidade mensuravel.

## 9. Timeframes candidatos

Timeframes de pesquisa:

- 60 minutos para gatilho;
- 120 minutos para confirmacao;
- diario para contexto superior.

Holding period candidato:

- minimo: 1 sessao;
- alvo: 2 a 7 sessoes;
- limite maximo de pesquisa: 10 sessoes.

## 10. Features candidatas

A hipotese devera depender apenas de features mensuraveis e reutilizaveis:

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
- ResearchTimeframeProfile.

Nenhuma feature deve ser calculada dentro de uma futura Strategy.

## 11. Gatilhos candidatos

### BUY

Pesquisar BUY apenas quando:

- tendencia superior estiver positiva;
- ocorrer pullback controlado;
- preco nao violar estrutura principal;
- momentum voltar a ficar positivo;
- volume/liquidez confirmarem retomada;
- MarketContext nao contradisser direcao;
- risco simulado permanecer compativel com Swing Trade.

### SELL

Pesquisar SELL apenas quando:

- tendencia superior estiver negativa;
- ocorrer repique controlado contra a tendencia;
- preco nao violar estrutura principal;
- momentum voltar a ficar negativo;
- volume/liquidez confirmarem retomada;
- MarketContext nao contradisser direcao;
- risco simulado permanecer compativel com Swing Trade.

## 12. Limitacoes

A hipotese possui limitacoes relevantes:

- pullbacks podem se transformar em reversoes completas;
- tendencia pode estar estatisticamente atrasada;
- entradas podem ocorrer tarde apos retomada;
- gaps podem invalidar stop e assimetria;
- filtros demais podem reduzir amostra;
- amostras Swing tendem a ter menos trades;
- resultados podem depender fortemente de regime macro;
- parametros estreitos podem gerar overfitting.

## 13. Riscos

Riscos de pesquisa:

- confundir reversao com pullback;
- dependencia de poucos eventos extremos;
- baixa robustez em Monte Carlo;
- falha em Walk-Forward;
- baixa diversificacao em relacao a Alpha101;
- alta similaridade com outras estrategias de momentum;
- degradacao em regimes laterais;
- drawdown por sequencia de falsos pullbacks.

## 14. Criterios de validacao

A hipotese so podera avancar se passar por:

- Replay controlado;
- Research Lab;
- Walk-Forward;
- Monte Carlo;
- Stress Testing;
- Validation Suite;
- Benchmark contra Alpha101, Alpha102 atual e demais Alphas;
- Portfolio Evaluation;
- analise de robustez;
- analise de reprodutibilidade;
- analise de dependencia de outliers;
- avaliacao de similaridade e diversificacao.

Metricas minimas:

- total_trades;
- win_rate;
- profit_factor;
- net_profit_points;
- max_drawdown_points;
- expectancy;
- robustness_score;
- reproducibility_score;
- scientific_score;
- diversification_score.

## 15. Criterios de aceitacao

A hipotese podera ser submetida a Alpha Factory se:

- for clara, testavel e parametrizavel;
- respeitar a familia Swing Trade;
- depender apenas de features existentes ou contratos aprovados;
- possuir filtros de regime e liquidez;
- apresentar plano de validacao cientifica;
- nao exigir acesso a Broker, MT5, Dashboard ou Domain;
- nao autorizar ordem real;
- diferenciar-se de breakout puro e de reversao curta.

## 16. Criterios de rejeicao futura

A hipotese devera ser rejeitada se:

- funcionar apenas em periodo isolado;
- apresentar baixa amostra;
- depender de poucos outliers;
- falhar em Walk-Forward;
- falhar em Monte Carlo;
- falhar em Stress Testing;
- apresentar alta correlacao com Alpha101 sem ganho incremental;
- piorar o portfolio;
- exigir parametros instaveis;
- violar Clean Architecture.

## 17. Submissao a Alpha Factory

Objeto conceitual:

- `AlphaHypothesis`

Campos candidatos:

- `hypothesis_id`: `alpha102-swing-pullback-momentum-continuation`;
- `alpha_name`: `Alpha102 Research Candidate`;
- `version`: `research-185`;
- `title`: `Swing Pullback Momentum Continuation`;
- `market`: `WDO`;
- `timeframe`: `60m / 120m / diario como contexto`;
- `status`: `READY_FOR_ALPHA_FACTORY_REVIEW`;
- `author`: `TraderIA CTO`;
- `validation_plan`: `Replay, Research Lab, Walk-Forward, Monte Carlo, Stress Testing, Benchmark, Portfolio Evaluation`.

## 18. Decisao da pesquisa

Hipotese selecionada:

Swing Pullback Momentum Continuation.

Decisao:

PRONTA PARA SUBMISSAO A ALPHA FACTORY.

Nenhum codigo foi implementado.
Nenhuma Strategy foi criada.
Nenhuma Config foi criada.
Nenhum Experiment foi criado.
Nenhuma operacao real esta autorizada.
