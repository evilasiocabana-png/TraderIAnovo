# Smart Trader API Audit

## Resumo Executivo

Esta auditoria avaliou a viabilidade da Smart Trader API da Clear como fonte
oficial de Market Data do TraderIA_WDO.

Conclusao objetiva:

**NAO**

A Smart Trader API nao deve ser adotada agora como fonte oficial de Market Data
do TraderIA.

Justificativa: o portal oficial em `https://devs.clear.com.br/` confirma que a
Smart Trader API fornece endpoints REST e WebSocket para dados de mercado em
tempo real, incluindo cotacoes e livro de ofertas, alem de endpoints de ordens,
custodia, garantia, simulador e autenticacao. Porem, a documentacao oficial
consultada nao confirmou suporte a candles historicos, candles de 1 minuto,
profundidade historica, armazenamento/licenciamento para pesquisa quantitativa
ou dataset historico WDO 1m. Portanto, ela nao atende ao requisito atual do
TraderIA: expansao de dataset historico real para pesquisa quantitativa.

Esta missao foi exclusivamente de pesquisa tecnica. Nenhum codigo foi
implementado, nenhum provider foi criado e nenhuma arquitetura foi alterada.

## Documentos Oficiais do TraderIA Consultados

- `MANIFEST.md`
- `TRADERIA_ARCHITECTURE_BIBLE.md`
- `ARCHITECTURE_RULES.md`
- `docs/MARKET_DATA_ARCHITECTURE.md`
- `docs/MARKET_DATA_CERTIFIED.md`
- `HISTORICAL_DATA_EXPANSION_PLAN.md`
- `HISTORICAL_DATASET_REPORT.md`

## Fontes Pesquisadas

### Smart Trader API / Clear

- Portal oficial: [Smart Trader API - Clear Corretora](https://devs.clear.com.br/)
- Evidencia localizada via Chrome logado: o portal oficial abre como
  `Smart Trader API` e apresenta documentacao de REST, WebSocket, simulador,
  autenticacao, custodia, garantias, dados de mercado e ordens.
- Limitacao: o acesso por requisicao direta fora do Chrome foi bloqueado pela
  CDN da XP/Clear, mas a navegacao pelo Chrome logado permitiu leitura da
  documentacao principal.
- Resultado: a documentacao confirma market data em tempo real, mas nao
  confirma dados historicos/candles 1m.

### B3

- [B3 for Developers](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/b3-for-developers/)
- [Market Data B3 - Perguntas frequentes](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/distribuidores/perguntas-frequentes/)
- [UP2DATA Cloud - B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/perguntas-frequentes/acesso-ao-up2data-cloud.htm)
- [Cotacoes historicas - B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/mercado-a-vista/cotacoes-historicas/)
- [Politica Comercial de Market Data B3](https://www.b3.com.br/data/files/6D/77/9D/65/0AB929106EEC8429AC094EA8/Politica%20Comercial%20de%20Market%20Data%20v3.0.4.1.pdf)

### Cedro / Market Data Cloud

- [Documentacao Market Data Cloud](https://www.marketdatacloud.com.br/documentacao/)
- [API Market Data - Cedro Technologies](https://www.cedrotech.com/blog/api-market-data/)
- [API Socket e WebSocket - Cedro Technologies](https://www.cedrotech.com/blog/api-socket-and-websocket/)

## Evidencias Oficiais Relevantes

### Smart Trader API

O portal oficial da Clear foi localizado e acessado via Chrome logado.

Evidencias confirmadas na documentacao oficial:

- a Smart Trader API e uma interface para integracao com servicos de envio de
  ordens da XP Inc.;
- fornece tambem acesso a dados de mercado, gerenciamento de ordens e
  informacoes de custodia e garantias;
- inicialmente esta disponivel somente para Day Trade na marca Clear;
- exige credenciais geradas na area logada do portal da Clear: `API_KEY`,
  `API_SECRET` e chaves RSA;
- chamadas autenticadas usam Bearer Token gerado por `API_KEY` e `API_SECRET`;
- envio de ordem exige assinatura do corpo da requisicao no header usando chave
  privada RSA;
- possui ambientes simulado e real, segregados por credenciais e URLs;
- oferece endpoints RESTFul para custodia, garantia, envio/cancelamento/edicao
  de ordens, historico intraday de ordens e consulta de dados de mercado;
- para dados de mercado REST, a navegacao exibiu endpoints `GETdetails`,
  `GETquote`, `GETbook` e `GETaggregate-book`;
- oferece WebSocket para status de ordens e dados de mercado;
- para WebSocket de dados de mercado, a navegacao exibiu `WSSmarketdata`;
- a documentacao descreve dados de mercado em tempo real como livros de ofertas
  e cotacoes.

Itens nao confirmados oficialmente:

- candles historicos;
- candles de 1 minuto;
- OHLC historico;
- historico de ticks;
- profundidade historica disponivel;
- permissao de armazenamento de dados para pesquisa;
- permissao de redistribuicao;
- custos especificos da API;
- rate limits;
- suporte explicito a WDO historico 1m;
- suporte explicito a dataset para Research Lab.

### B3

A B3 documenta Market Data B3 como servico de distribuicao de dados por UMDF,
com dados em tempo real ou atraso de 15 minutos, L1 e L2, cobrindo mercado a
vista, opcoes, futuros e cambio. A B3 tambem documenta acesso direto via
infraestrutura B3/RCB e acesso indireto por distribuidores autorizados.

A B3 documenta que o UP2DATA Cloud disponibiliza 30 dias corridos de dados
historicos em nuvem, com arquivos em CSV, TXT, JSON e XML, mediante kit de
acesso com credenciais e certificado.

A B3 tambem documenta series historicas de cotacoes para mercado a vista desde
1986. Para Market Data B3, a politica comercial define dados historicos como
informacoes de sessoes anteriores geradas pelas plataformas de Market Data B3.

### Cedro

O Market Data Cloud da Cedro apresenta documentacao para API Rest, API Socket,
WebSocket, LIB Python, Tick By Tick, End Of Day e Serie Historica. A Cedro
declara disponibilidade de market data para B3, moedas, indices, taxas e outros
mercados, com informacoes em tempo real e delay.

## Acesso

| Pergunta | Smart Trader API / Clear |
| --- | --- |
| Como obter acesso? | A documentacao informa necessidade de gerar credenciais no portal Clear: `API_KEY`, `API_SECRET` e chaves RSA. |
| Existe processo de homologacao? | A documentacao confirma ambiente simulado para testes, mas nao detalha processo institucional de homologacao. |
| Existe sandbox? | Sim, ha ambiente simulado. |
| Existe ambiente de producao? | Sim, ha ambiente real segregado por credenciais e URLs. |

## Autenticacao

| Item | Status |
| --- | --- |
| Tipo de autenticacao | Bearer Token e assinatura RSA para envio de ordens. |
| Tokens | Token gerado por `API_KEY` e `API_SECRET`. |
| Certificados | Nao confirmado; a documentacao observada menciona chaves RSA, nao certificado digital. |
| Renovacao | Nao confirmada na leitura realizada. |

Observacao: a missao nao gerou credenciais, nao testou token e nao executou
qualquer chamada autenticada.

## Market Data

| Funcionalidade | Smart Trader API / Clear |
| --- | --- |
| Candles historicos | Nao confirmado |
| Candles 1 minuto | Nao confirmado |
| Tick Data | Nao confirmado |
| OHLC | Nao confirmado |
| Volume | Nao confirmado |
| Negocios | Nao confirmado |
| Livro de ofertas | Confirmado como dado de mercado em tempo real |
| Times & Trades | Nao confirmado explicitamente |
| Streaming | Confirmado via WebSocket para dados de mercado em tempo real |
| WebSocket | Confirmado: `WSSmarketdata` |
| REST | Confirmado: `GETdetails`, `GETquote`, `GETbook`, `GETaggregate-book` |

Conclusao: ha evidencia oficial suficiente para afirmar que a Smart Trader API
fornece dados de mercado em tempo real. Nao ha evidencia suficiente para
afirmar que ela atende ao escopo de dados historicos do TraderIA.

## Historico

| Item | Smart Trader API / Clear |
| --- | --- |
| Quantidade de historico disponivel | Nao confirmado |
| Limitacoes | Nao confirmadas |
| Timeframes disponiveis | Nao confirmado |
| Ativos disponiveis | Nao confirmado |
| WDO suportado? | Nao confirmado |
| WIN suportado? | Nao confirmado |
| B3 suportada? | A API e voltada ao ambiente Clear/XP para negociacao, mas a documentacao lida nao detalhou cobertura historica por ativo. |

O portal oficial confirma market data em tempo real, mas nao foi encontrada
documentacao confirmando WDO/WIN historico, candles 1m ou historico OHLCV.

## Limites

| Item | Smart Trader API / Clear |
| --- | --- |
| Rate limit | Nao confirmado |
| Limite diario | Nao confirmado |
| Limite por minuto | Nao confirmado |
| Custos | Nao confirmado |
| Restricoes | Nao confirmado |

## Licenciamento

| Pergunta | Resposta |
| --- | --- |
| Dados podem ser utilizados para pesquisa? | Nao confirmado |
| Dados podem ser armazenados? | Nao confirmado |
| Dados podem ser redistribuidos? | Nao confirmado |
| Existem restricoes contratuais? | Nao confirmado |

Risco juridico: sem contrato e politica de dados acessiveis, o TraderIA nao
pode tratar a Smart Trader API como fonte oficial de pesquisa quantitativa.

## Compatibilidade com o TraderIA

| Componente | Avaliacao sem implementar |
| --- | --- |
| `HistoricalDataProvider` | Nao aprovado: historico OHLCV/candles 1m nao confirmado. |
| `LiveDataProvider` | Potencialmente compativel em sprint futura, pois WebSocket de market data em tempo real foi confirmado. |
| Replay | Dependeria de candles historicos normalizados. Nao confirmado. |
| Research Lab | Dependeria de historico amplo, armazenavel e auditavel. Nao confirmado. |
| Validation Suite | Nao recomendado sem historico suficiente e licenca clara. |
| Benchmark | Nao recomendado sem dataset historico confiavel. |
| Portfolio | Nao recomendado sem cobertura multiativo e licenca clara. |

## Riscos

### Dependencia da Corretora

Se adotada, a Smart Trader API criaria dependencia direta de uma corretora.
Isso aumenta risco de lock-in, mudancas unilaterais de API, restricoes de
conta, bloqueio de acesso e acoplamento juridico/operacional.

### Dependencia da Plataforma

O TraderIA passaria a depender da disponibilidade e estabilidade de um portal
externo da Clear/XP. O acesso publico observado ja apresentou bloqueio por CDN,
o que e um sinal operacional relevante para auditoria.

### Lock-in Tecnologico

Sem documentacao aberta e padronizada, qualquer integracao futura pode ficar
fortemente acoplada a contratos proprietarios.

### Limitacoes Tecnicas

Foram confirmados REST e WebSocket para dados de mercado em tempo real.

Nao foram confirmados:

- historico OHLCV;
- WDO historico;
- WIN historico;
- candle de 1 minuto;
- tick data historico;
- limites de uso;
- permissao de armazenamento.

### Limitacoes Juridicas

Nao foram confirmados:

- permissao de armazenar dados;
- permissao de usar para pesquisa;
- permissao de redistribuir;
- regras de derivacao de datasets;
- custos e contrato.

## Tabela Comparativa

| Criterio | Smart Trader API Clear | B3 Market Data / UP2DATA | Cedro Market Data Cloud |
| --- | --- | --- | --- |
| Fonte | Corretora | Bolsa / fonte primaria | Distribuidor especializado |
| Documentacao publica auditavel | Parcial: acessivel via Chrome logado; rotas internas instaveis | Forte | Boa |
| Historico | Nao confirmado | UP2DATA Cloud com historico de 30 dias; series historicas oficiais para mercado a vista | Serie Historica, End of Day e Tick By Tick documentados como produtos |
| Tempo real | Confirmado para cotacoes e livro de ofertas | Sim, via Market Data B3/UMDF | Sim, via Rest/Socket/WebSocket |
| WebSocket | Confirmado: `WSSmarketdata` | Nao avaliado como API simples para TraderIA; infraestrutura institucional | Documentado |
| REST | Confirmado: detalhes, cotacoes, book e book agregado | B3 for Developers possui APIs e documentacao | Documentado |
| WDO/WIN | Nao confirmado | Derivativos e cambio pronto fazem parte do segmento BMF | Provavel por cobertura B3/BM&F, mas deve ser confirmado em contrato |
| Licenciamento | Nao confirmado | Politica comercial formal | Contratual com distribuidor |
| Armazenamento | Nao confirmado | Regras formais por produto/contrato | Contratual |
| Facilidade inicial | Indeterminada | Menor, por contrato e infraestrutura | Maior que B3 direta, por APIs prontas |
| Adequacao ao TraderIA | Nao recomendada agora | Alta para fonte primaria, com custo/complexidade | Alta para integracao via adapter futuro, se contrato permitir |

## Vantagens da Smart Trader API

- Portal oficial existe e foi acessado via Chrome logado.
- Confirma ambiente simulado e ambiente real.
- Confirma credenciais por `API_KEY`, `API_SECRET` e chaves RSA.
- Confirma REST e WebSocket.
- Confirma dados de mercado em tempo real: cotacoes e livro de ofertas.
- Pode ser candidata futura para `LiveDataProvider`, desde que haja missao
  especifica e travas contra envio de ordens.

## Desvantagens da Smart Trader API

- Funcionalidades historicas essenciais nao confirmadas.
- Historico de WDO 1m nao confirmado.
- Licenciamento para pesquisa e armazenamento nao confirmado.
- Possivel dependencia direta de corretora.
- Proximidade forte com execucao de ordens, o que exige bloqueio arquitetural
  absoluto no TraderIA.

## Limitacoes Identificadas

- Portal oficial bloqueado por CDN fora do Chrome; acessivel via Chrome logado.
- Area de credenciais indicada pela documentacao retornou pagina nao encontrada
  no portal atual da Clear durante a checagem.
- Ausencia de confirmacao sobre processo formal de homologacao, embora exista
  ambiente simulado.
- Ausencia de confirmacao sobre rate limits e custos.
- Ausencia de confirmacao sobre dados historicos/candles.

## Recomendacao Tecnica

**NAO**

A Smart Trader API nao pode ser adotada como fonte oficial de Market Data do
TraderIA neste momento.

Motivo: o TraderIA exige, nesta fase, fonte historica real, rastreavel,
licenciada, armazenavel, com suporte confirmado a WDO 1m e adequada para
pesquisa quantitativa. A documentacao oficial auditada confirmou market data em
tempo real, mas nao confirmou historico OHLCV/candles 1m nem direitos de
armazenamento para pesquisa.

## Condicoes Minimas Para Reavaliacao

A Smart Trader API so deve ser reavaliada se a Clear disponibilizar
documentacao oficial contendo:

- processo de acesso;
- ambiente de sandbox/homologacao;
- autenticacao;
- endpoints de market data;
- suporte a WDO e WIN;
- candles historicos;
- candles de 1 minuto;
- tick data ou times and trades, se disponivel;
- limites de requisicao;
- custos;
- regras de armazenamento;
- permissao de uso em pesquisa quantitativa;
- contrato de uso de dados.

## Proxima Missao Sugerida se Aprovada

Nao aplicavel, pois a API nao foi aprovada.

Caso futuramente seja aprovada, a proxima missao deveria ser:

`SMART_TRADER_API_CONTRACT_REVIEW.md`

Objetivo: revisar contrato, licenciamento, endpoints e limites antes de
qualquer desenho de adapter. Para uso live, essa missao tambem deveria separar
explicitamente dados de mercado de qualquer capacidade de envio de ordens.

## Proxima Missao Sugerida se Reprovada

`B3_CEDRO_MARKET_DATA_SOURCE_DECISION.md`

Objetivo: comparar oficialmente B3 Market Data/UP2DATA e Cedro Market Data
Cloud como fontes candidatas para expansao historica do WDO, com foco em:

- WDO 1m;
- historico minimo de 12 meses;
- permissao de armazenamento;
- custo;
- viabilidade de adapter futuro;
- aderencia ao `HistoricalDataProvider`.

## Status Final

`SMART_TRADER_API_NOT_APPROVED_AS_OFFICIAL_MARKET_DATA_SOURCE`.

Operacao real permanece proibida. Nenhuma integracao foi implementada.
