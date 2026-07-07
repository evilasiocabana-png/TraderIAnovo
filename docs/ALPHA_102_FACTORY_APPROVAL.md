# Alpha102 Factory Approval

## 1. Status

APROVADA PARA GERACAO DO PLAYBOOK.

Este documento registra a submissao da hipotese `Swing Pullback Momentum
Continuation` a Alpha Factory do TraderIA_WDO.

Nenhum codigo, Config, Strategy, Experiment, Runner, integracao operacional ou
execucao real esta autorizado por esta missao.

## 2. Hipotese submetida

### Identificacao

- `hypothesis_id`: `alpha102-swing-pullback-momentum-continuation`
- `alpha_name`: `Alpha102 Research Candidate`
- `version`: `research-185`
- `title`: `Swing Pullback Momentum Continuation`
- `familia`: `Swing Trade`
- `market`: `WDO`
- `timeframe`: `60m / 120m / diario como contexto`
- `status anterior`: `READY_FOR_ALPHA_FACTORY_REVIEW`
- `status aprovado`: `APPROVED_FOR_PLAYBOOK`

### Tese

Em mercados liquidos e direcionais, quando o ativo apresenta tendencia
mensuravel em timeframe superior e realiza um pullback controlado sem romper a
estrutura principal, a retomada do momentum na direcao da tendencia pode gerar
assimetria positiva em horizonte Swing Trade.

## 3. Validacao da Alpha Factory

### Hipotese clara

APROVADA.

A hipotese esta formulada de modo testavel, com comportamento esperado,
condicoes de entrada candidatas, direcionalidade, contexto e limitacoes. A tese
nao depende de interpretacao discricionaria: pullback, tendencia, momentum,
liquidez e contexto deverao ser mensurados por features e contratos aprovados.

### Mercados definidos

APROVADA.

Mercado inicial definido:

- WDO em Replay;
- WDO em Research Lab;
- WDO em simulacao historica controlada;
- dados normalizados por contratos oficiais.

Mercados proibidos definidos:

- conta real;
- corretora;
- MT5;
- criptoativos;
- opcoes;
- ativos sem contrato institucional aprovado;
- qualquer ambiente com envio de ordens.

### Features necessarias

APROVADA.

Features candidatas definidas:

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

As features deverao ser consumidas de componentes existentes ou contratos
aprovados. Nenhuma feature devera ser calculada dentro de uma futura Strategy.

### Contexto operacional

APROVADO.

A hipotese estabelece contexto restrito a pesquisa, Replay e simulacao
controlada. O contexto candidato exige:

- regime `TREND`;
- volatilidade moderada;
- liquidez suficiente;
- retomada pos-correcao;
- MarketContext com confianca minima;
- qualidade de dados aprovada;
- risco simulado compativel com Swing Trade.

Contextos rejeitados:

- RANGE persistente;
- LOW_LIQUIDITY;
- volatilidade extrema;
- gaps recorrentes;
- baixa confianca contextual;
- ausencia de direcionalidade mensuravel.

### Criterios de aceitacao

APROVADOS.

A hipotese so podera avancar se:

- permanecer clara, testavel e parametrizavel;
- respeitar a familia Swing Trade;
- depender apenas de features existentes ou contratos aprovados;
- possuir filtros de regime e liquidez;
- apresentar plano de validacao cientifica;
- nao exigir acesso a Broker, MT5, Dashboard ou Domain;
- nao autorizar ordem real;
- diferenciar-se de breakout puro e de reversao curta;
- passar por Research Lab, Replay, Walk-Forward, Monte Carlo e Stress Testing.

### Criterios de rejeicao

APROVADOS.

A hipotese devera ser rejeitada futuramente se:

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

## 4. Decisao institucional

A Alpha Factory considera a hipotese suficientemente clara, delimitada,
testavel e alinhada a arquitetura do TraderIA_WDO.

Decisao:

APPROVED_FOR_PLAYBOOK.

## 5. Proximas etapas autorizadas

Apenas a seguinte etapa fica autorizada:

- gerar o Playbook institucional da hipotese aprovada.

Continuam nao autorizados:

- criar Config;
- criar Strategy;
- criar Experiment;
- alterar Alpha101;
- alterar Alpha102 existente;
- alterar Domain;
- alterar ReplayEngine;
- alterar DecisionPipeline;
- integrar Broker;
- integrar MT5;
- executar ordens reais.

## 6. Conclusao

A hipotese `Swing Pullback Momentum Continuation` esta aprovada pela Alpha
Factory para geracao do Playbook.

Nenhuma implementacao de codigo foi realizada nesta missao.
