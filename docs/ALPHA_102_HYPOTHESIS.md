# Alpha 102 - Swing Volatility Compression Breakout

## 1. Status

APROVADA PARA GERACAO DE PLAYBOOK.

Este documento registra apenas a hipotese quantitativa oficial da Alpha102.
Nenhum codigo, configuracao, estrategia, experimento, integracao operacional ou
execucao real esta autorizado por esta missao.

## 2. Familia da estrategia

Swing Trade.

## 3. Objetivo

Definir uma hipotese quantitativa Swing Trade baseada em rompimentos apos
compressao de volatilidade, buscando capturar movimentos direcionais
multi-sessao quando o mercado sai de um regime de baixa amplitude para um
regime de expansao com confirmacao de liquidez, momentum e contexto.

## 4. Revisao de literatura quantitativa

### Momentum intermediario

Jegadeesh e Titman documentaram evidencia classica de momentum em horizontes
intermediarios, com carteiras compradas em ativos vencedores e vendidas em
ativos perdedores apresentando retornos positivos em horizontes de tres a doze
meses. Para a Alpha102, essa literatura sustenta a ideia geral de continuidade
direcional, mas nao autoriza simplesmente perseguir preco sem filtro de regime,
amostra e risco.

Referencia: https://ideas.repec.org/a/bla/jfinan/v48y1993i1p65-91.html

### Analise tecnica sob inferencia estatistica

Lo, Mamaysky e Wang propuseram um tratamento sistematico para padroes tecnicos,
reduzindo subjetividade por meio de reconhecimento formal e inferencia
estatistica. Para a Alpha102, a implicacao arquitetural e clara: rompimentos,
compressao e contexto devem ser definidos por features mensuraveis e testadas,
nao por leitura visual discricionaria.

Referencia: https://www.nber.org/papers/w7613

### Reversao e momentum de curto prazo

A literatura sobre reversao de curto prazo mostra que efeitos simples podem ser
instaveis, sensiveis a liquidez, volatilidade e regime. Estudos recentes tambem
indicam que reversao e momentum podem depender da decomposicao intraday e
overnight. A Alpha102, portanto, deve evitar operar todo rompimento e deve
exigir filtros de compressao, expansao, volume e contexto.

Referencias:

- https://www.newyorkfed.org/research/staff_reports/sr513
- https://quantpedia.com/strategies/short-term-reversal-in-stocks

### Robustez condicionada ao contexto

Avramov, Chordia, Jostova e Philipov mostram que a rentabilidade de momentum
pode depender fortemente de caracteristicas condicionais do universo analisado.
Embora o estudo seja sobre acoes e credito, a licao de pesquisa e aplicavel: a
Alpha102 deve ser validada por contexto, regime, qualidade dos dados e amostras
separadas, sem assumir universalidade da anomalia.

Referencia: https://ideas.repec.org/a/bla/jfinan/v62y2007i5p2503-2520.html

## 5. Hipotese quantitativa

A hipotese central da Alpha102 e que, em mercados liquidos, uma fase de
compressao de volatilidade seguida por rompimento direcional confirmado por
volume, momentum e contexto pode gerar assimetria positiva em horizonte Swing
Trade.

A tese nao e "comprar qualquer rompimento". A tese e pesquisar se rompimentos
apos contracao mensuravel de amplitude apresentam melhor relacao entre retorno,
drawdown e estabilidade do que rompimentos ocorridos em volatilidade ja
expandida ou em regimes laterais ruidosos.

## 6. Comportamento esperado

Espera-se que a Alpha102:

- aguarde compressao previa de volatilidade;
- identifique expansao direcional apos a compressao;
- opere apenas quando liquidez e volume confirmarem participacao;
- rejeite rompimentos sem continuidade nas sessoes seguintes;
- apresente menor frequencia de trades do que estrategias intraday;
- tenha maior dependencia de qualidade de regime do que de microestrutura;
- funcione melhor em transicoes de RANGE para TREND;
- falhe ou seja filtrada em rompimentos falsos e baixa liquidez.

## 7. Vantagem estatistica esperada

A vantagem estatistica candidata vem da combinacao de tres efeitos pesquisaveis:

- compressao reduzindo distancia inicial de stop e melhorando assimetria;
- expansao pos-compressao aumentando probabilidade de movimento multi-sessao;
- confirmacao contextual filtrando rompimentos sem participacao institucional.

A vantagem so sera considerada valida se sobreviver a:

- amostras fora do periodo inicial;
- validacao Walk-Forward;
- Monte Carlo;
- Stress Testing;
- analise de dependencia de outliers;
- estabilidade de parametros;
- comparacao contra Alpha101 e demais estrategias Swing futuras.

## 8. Limitacoes

A Alpha102 deve reconhecer as seguintes limitacoes:

- rompimentos falsos sao frequentes em mercados laterais;
- gaps podem distorcer entrada, stop e target;
- compressao excessiva pode refletir ausencia de interesse, nao oportunidade;
- volume isolado pode atrasar sinal;
- volatilidade expandida demais reduz assimetria;
- amostras Swing tendem a ter menos trades do que intraday;
- resultados podem depender fortemente do periodo macro e da estrutura do WDO;
- a tese pode falhar em regimes de baixa direcionalidade.

## 9. Mercados permitidos

Nesta primeira versao de pesquisa, somente:

- WDO em ambiente de Replay;
- WDO em Research Lab;
- WDO em simulacao historica controlada;
- dados normalizados por contratos aprovados da plataforma.

Qualquer expansao para outro ativo exige nova missao e aprovacao arquitetural.

## 10. Mercados proibidos

A Alpha102 nao deve ser pesquisada nem utilizada em:

- conta real;
- corretora;
- MT5;
- execucao automatica;
- criptoativos;
- forex externo;
- opcoes;
- acoes;
- WIN;
- qualquer ativo sem contrato institucional aprovado;
- qualquer ambiente que envie ordens.

## 11. Timeframe

Timeframes candidatos para pesquisa:

- 60 minutos;
- 120 minutos;
- diario como contexto superior.

O timeframe operacional final nao esta definido nesta missao e devera ser
validado posteriormente pelo Research Lab.

## 12. Holding period

Holding period candidato:

- minimo: 1 sessao;
- alvo de pesquisa: 2 a 7 sessoes;
- limite maximo candidato: 10 sessoes.

Qualquer carregamento entre sessoes devera ser tratado apenas como simulacao e
pesquisa, sem autorizacao operacional real.

## 13. Features candidatas

A Alpha102 devera pesquisar, no minimo:

- volatilidade realizada;
- ATR;
- compressao de range;
- expansao de range;
- volume relativo;
- liquidez;
- momentum;
- distancia para maxima/minima da consolidacao;
- regime de mercado;
- MarketContext;
- MarketDataQualityResult;
- ResearchTimeframeProfile;
- StrategyProfile;
- resultados da Validation Suite.

Nenhuma feature deve ser calculada dentro de futura Strategy. A estrategia
futura, se autorizada, devera consumir apenas contratos aprovados.

## 14. Contexto

A hipotese so pode ser pesquisada quando:

- a qualidade dos dados estiver aprovada;
- o mercado apresentar liquidez minima;
- houver compressao de volatilidade mensuravel;
- o regime nao indicar ruido extremo sem direcao;
- o MarketContext possuir confianca minima;
- a amostra historica for suficiente para Swing Trade;
- o risco simulado for compativel com carregamento multi-sessao.

## 15. Gatilhos candidatos

### BUY

Um gatilho de BUY somente podera ser pesquisado quando:

- houver compressao previa de volatilidade;
- o preco romper a referencia superior da consolidacao;
- volume ou liquidez confirmarem participacao;
- momentum ficar alinhado ao rompimento;
- o MarketContext nao contradisser a direcao;
- a volatilidade pos-rompimento nao inviabilizar a assimetria.

### SELL

Um gatilho de SELL somente podera ser pesquisado quando:

- houver compressao previa de volatilidade;
- o preco romper a referencia inferior da consolidacao;
- volume ou liquidez confirmarem participacao;
- momentum ficar alinhado ao rompimento;
- o MarketContext nao contradisser a direcao;
- a volatilidade pos-rompimento nao inviabilizar a assimetria.

## 16. Filtros obrigatorios

A Alpha102 devera rejeitar sinais quando:

- nao houver compressao mensuravel;
- a expansao ocorrer em volume insuficiente;
- o spread ou proxy de liquidez for inadequado;
- houver gap excessivo contra assimetria;
- o regime for lateral com baixa confianca;
- a volatilidade estiver excessivamente erratica;
- o Data Lab indicar baixa qualidade;
- o Research Lab indicar amostra insuficiente;
- houver dependencia excessiva de poucos eventos extremos.

## 17. Criterios de aceitacao

A hipotese podera avancar para Playbook quando:

- estiver descrita de forma clara e testavel;
- respeitar a familia Swing Trade;
- definir mercados, timeframes e holding period candidatos;
- depender apenas de features mensuraveis;
- preservar Clean Architecture;
- nao acessar Broker, MT5, Dashboard ou Domain;
- tiver plano de validacao por Replay e Research Lab;
- exigir Walk-Forward, Monte Carlo e Stress Testing;
- prever criterios objetivos de rejeicao;
- for aprovada pela Alpha Factory para etapa de Playbook.

## 18. Criterios de rejeicao

A Alpha102 devera ser rejeitada se, na pesquisa futura:

- apresentar profit factor insuficiente;
- apresentar drawdown incompatavel com Swing Trade;
- depender de poucos trades extremos;
- falhar em Walk-Forward;
- falhar em Monte Carlo;
- falhar em Stress Testing;
- apresentar baixa reprodutibilidade;
- depender de parametros estreitos ou instaveis;
- funcionar apenas em um periodo historico especifico;
- exigir qualquer acesso operacional proibido;
- tentar aprovar compra, venda ou ordem real.

## 19. Submissao a Alpha Factory

Objeto conceitual submetido:

- `AlphaHypothesis`

Campos institucionais:

- `hypothesis_id`: `alpha102-volatility-compression-breakout`;
- `alpha_name`: `Alpha102`;
- `version`: `1`;
- `title`: `Swing Volatility Compression Breakout`;
- `market`: `WDO`;
- `timeframe`: `60m / 120m / diario como contexto`;
- `status`: `APPROVED_FOR_PLAYBOOK`;
- `author`: `TraderIA CTO`;
- `validation_plan`: `Replay, Research Lab, Walk-Forward, Monte Carlo, Stress Testing, Robustness, Reproducibility`.

Decisao:

APROVADA PARA GERACAO DO PLAYBOOK.

## 20. Proibicoes desta missao

Esta missao nao cria:

- Config;
- Strategy;
- Experiment;
- Runner;
- Pipeline;
- integracao com Broker;
- integracao com MT5;
- integracao com IA;
- envio de ordem;
- alteracao no Domain;
- alteracao em estrategias existentes.

## 21. Conclusao

A Alpha102 possui hipotese quantitativa clara, alinhada a literatura de
momentum, padroes tecnicos formalizaveis e validacao condicionada por regime.
A tese esta aprovada apenas para geracao futura do Playbook institucional.

Nenhuma operacao real esta autorizada.
