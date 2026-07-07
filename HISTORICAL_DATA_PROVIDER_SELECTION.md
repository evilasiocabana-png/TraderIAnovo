# Historical Data Provider Selection

## Objetivo

Selecionar a fonte oficial candidata para expansao do dataset historico real do
TraderIA_WDO, com foco em WDO 1m, pesquisa quantitativa, rastreabilidade e
governanca institucional.

Esta missao e exclusivamente documental. Nenhum codigo foi implementado,
nenhum provider foi alterado, nenhuma API foi conectada e nenhum dado foi
importado.

## Documentos Institucionais Consultados

- `MANIFEST.md`
- `TRADERIA_ARCHITECTURE_BIBLE.md`
- `ARCHITECTURE_RULES.md`
- `docs/MARKET_DATA_ARCHITECTURE.md`
- `docs/MARKET_DATA_CERTIFIED.md`
- `HISTORICAL_DATA_EXPANSION_PLAN.md`
- `HISTORICAL_DATASET_REPORT.md`
- `SMART_TRADER_API_AUDIT.md`

## Fontes Oficiais Consultadas

### B3

- [B3 for Developers](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/b3-for-developers/)
- [Market Data B3 - Perguntas frequentes](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/distribuidores/perguntas-frequentes/)
- [UP2DATA Cloud - B3](https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/perguntas-frequentes/acesso-ao-up2data-cloud.htm)
- [Politica Comercial de Market Data B3](https://www.b3.com.br/data/files/6D/77/9D/65/0AB929106EEC8429AC094EA8/Politica%20Comercial%20de%20Market%20Data%20v3.0.4.1.pdf)

### Cedro / Market Data Cloud

- [Documentacao Market Data Cloud](https://www.marketdatacloud.com.br/documentacao/)
- [Arquivo Serie Historica - Market Data Cloud](https://www.marketdatacloud.com.br/serie-historica/)
- [Precos - Market Data Cloud](https://www.marketdatacloud.com.br/precos/)
- [API Market Data - Cedro Technologies](https://www.cedrotech.com/blog/api-market-data/)

## Estado Atual do TraderIA

| Item | Estado |
| --- | --- |
| Dataset certificado atual | `wdo_1m_2025` |
| Candles atuais | 2 |
| Timeframe | `1m` |
| Ativo | `WDO` |
| Status institucional | `MARKET_DATA_CERTIFIED_FOR_QUANTITATIVE_RESEARCH` |
| Limitacao | amostra insuficiente para validacao estatistica |
| Necessidade imediata | expandir para pelo menos 12 meses de WDO 1m |

## Criterios de Selecao

- WDO disponivel.
- Candles de 1 minuto.
- Historico suficiente para pesquisa quantitativa.
- Formato exportavel.
- Licenca clara para armazenamento e uso em pesquisa.
- Custo compativel com fase institucional.
- Rastreabilidade da origem dos dados.
- Facilidade de integracao futura com `HistoricalDataProvider`.

## Avaliacao Comparativa

| Criterio | B3 / UP2DATA / Market Data B3 | Cedro Market Data Cloud | Smart Trader API Clear |
| --- | --- | --- | --- |
| Natureza | Fonte primaria / bolsa | Distribuidor especializado | API de corretora |
| WDO / BM&F | Sim, Market Data B3 cobre mercado futuro e cambio | Sim para BM&F; WDO deve ser confirmado em contrato | Nao confirmado para historico |
| Candles 1m | Nao confirmado publicamente no UP2DATA Cloud como historico amplo | Confirmado em Serie Historica intraday de 1 minuto ou 15 minutos | Nao confirmado |
| Historico suficiente | UP2DATA Cloud publico informa 30 dias corridos; historico maior depende de produto/contrato | Serie Historica e planos com candles 1m; escopo exato deve ser contratado | Nao confirmado |
| Formato exportavel | CSV, TXT, JSON e XML no UP2DATA Cloud | Arquivo Serie Historica via FTP e APIs/documentacao | Nao confirmado para historico |
| Licenca de armazenamento | Formal pela B3, mas exige enquadramento contratual | Contratual com distribuidor; precisa confirmar armazenamento para pesquisa | Nao confirmado |
| Custo | Maior complexidade comercial e operacional | Planos e contato comercial; custo mais previsivel para uso inicial | Nao aplicavel para historico |
| Rastreabilidade | Maxima, por ser fonte primaria | Alta, se contrato comprovar origem B3 e permissao de uso | Insuficiente para historico |
| Facilidade de integracao | Media/baixa: contrato, cloud, certificado, SAS e formatos por canal | Alta/media: arquivo historico, FTP/API e menor complexidade de entrada | Nao aprovado |
| Adequacao ao TraderIA agora | Excelente para auditoria e contingencia; limitado como fonte operacional imediata pelo historico publico de 30 dias no UP2DATA Cloud | Melhor candidata pratica para dataset historico WDO 1m, condicionada a contrato | Rejeitada para historico |

## Analise B3 / UP2DATA

A B3 e a fonte primaria natural para rastreabilidade institucional. A
documentacao do Market Data B3 confirma distribuicao via UMDF, dados em tempo
real ou com atraso, niveis L1/L2 e cobertura do segmento de mercado futuro e
cambio.

O UP2DATA Cloud documenta arquivos em nuvem, download em CSV, TXT, JSON e XML,
credenciais, certificado e chaves SAS. Entretanto, a documentacao publica
consultada informa 30 dias corridos de dados historicos no UP2DATA Cloud. Esse
periodo e suficiente para validacoes operacionais curtas, mas nao atende ao
criterio institucional de pelo menos 12 meses para pesquisa estatistica inicial.

A Politica Comercial de Market Data B3 define dados historicos como
informacoes de sessoes anteriores geradas pelas plataformas de Market Data B3 e
define regras contratuais de distribuicao. Isso torna a B3 a melhor referencia
de auditoria, mas nao a escolha mais simples para a primeira expansao pratica
do dataset, salvo se uma proposta comercial especifica entregar WDO 1m com
periodo historico suficiente.

## Analise Cedro Market Data Cloud

A Cedro documenta Market Data Cloud para B3, BM&F, derivativos, moedas,
indices e outros mercados. A pagina de Serie Historica informa dados
historicos intraday em periodos de 1 minuto ou 15 minutos, com entrega de
candles e campos compativeis com normalizacao OHLCV.

A pagina de precos tambem indica cobertura de Mercado BM&F e candles de 1
minuto em planos superiores. Para o TraderIA, o ponto mais forte e a combinacao
de:

- entrega historica em arquivo;
- granularidade intraday de 1 minuto;
- cobertura BM&F;
- menor complexidade de integracao inicial;
- possibilidade de selecionar ativos;
- adequacao natural ao fluxo de importacao CSV institucional.

Pontos que ainda exigem confirmacao comercial antes de qualquer importacao:

- suporte explicito ao simbolo WDO;
- periodo historico minimo de 12, 24 ou 36 meses;
- permissao formal de armazenamento local para pesquisa quantitativa;
- proibicao ou permissao de redistribuicao;
- custo final;
- layout final do arquivo;
- timezone;
- tratamento de vencimentos/rolagem do contrato futuro.

## Outras Fontes Avaliadas

### Smart Trader API Clear

Status: `REJEITADA_PARA_HISTORICO`.

A auditoria da Missao 205 concluiu que a documentacao oficial confirma dados
de mercado em tempo real, mas nao confirma candles historicos, WDO 1m,
profundidade historica nem permissao de armazenamento. Pode ser reavaliada
futuramente apenas para `LiveDataProvider`, com separacao absoluta de qualquer
capacidade de envio de ordens.

### Plataformas de Trading

Plataformas como Profit, Tryd e similares nao devem ser usadas como fonte
oficial enquanto nao houver:

- contrato claro;
- permissao de armazenamento;
- exportacao auditavel;
- origem documentada;
- cobertura WDO 1m;
- rastreabilidade do arquivo.

### Fontes Publicas, Scrapers e Dados Informais

Status: `REJEITADAS`.

Nao atendem a governanca institucional por risco de licenciamento,
inconsistencia, ausencia de rastreabilidade e baixa auditabilidade.

## Fonte Principal Candidata

**Cedro Market Data Cloud - Arquivo Serie Historica**

Status: `PRIMARY_CANDIDATE_PENDING_CONTRACT_CONFIRMATION`.

Justificativa tecnica:

- documenta Serie Historica intraday de 1 minuto;
- documenta cobertura BM&F;
- permite entrega em arquivo, alinhada ao plano de importacao incremental;
- reduz complexidade inicial em comparacao com acesso direto B3/UP2DATA;
- e mais adequada ao objetivo imediato: obter WDO 1m historico suficiente para
  Replay, Research Lab, Validation Suite, Benchmark e Portfolio Evaluation.

Condicao obrigatoria:

A Cedro so podera ser declarada fonte oficial ativa apos confirmacao formal de:

- WDO disponivel;
- candles 1m historicos;
- minimo de 12 meses, preferencialmente 24 a 36 meses;
- permissao de armazenamento local para pesquisa;
- formato exportavel compativel com CSV institucional;
- origem/rastreabilidade B3;
- timezone e calendario B3;
- contrato sem autorizacao para operacao real.

## Fonte Secundaria de Contingencia

**B3 / UP2DATA / Market Data B3**

Status: `SECONDARY_AUTHORITATIVE_CONTINGENCY`.

Justificativa tecnica:

- e a fonte primaria e mais rastreavel;
- documenta mercado futuro e cambio;
- possui politica comercial formal;
- fornece base juridica mais forte para auditoria;
- deve servir como referencia de validacao e contingencia institucional.

Limitacao:

O UP2DATA Cloud publico indica 30 dias corridos de historico. Portanto, para
atender ao TraderIA, seria necessario contratar produto/canal B3 ou distribuidor
autorizado que entregue periodo historico maior em WDO 1m.

## Requisitos Minimos Para Contratacao Futura

Antes de qualquer missao de importacao, o CTO deve exigir do fornecedor:

- especificacao do ativo `WDO`;
- granularidade `1m`;
- periodo historico ofertado;
- amostra de arquivo;
- schema de campos;
- timezone;
- regra para contratos/vencimentos/rolagem;
- permissao de armazenamento local;
- permissao de uso para pesquisa quantitativa;
- proibicao de redistribuicao, se aplicavel;
- custo total;
- SLA ou prazo de entrega;
- declaracao de origem dos dados;
- canal de suporte tecnico.

## Decisao Institucional

Fonte principal candidata:

`CEDRO_MARKET_DATA_CLOUD_SERIE_HISTORICA`

Fonte secundaria de contingencia:

`B3_UP2DATA_MARKET_DATA_B3`

Status final:

`HISTORICAL_DATA_PROVIDER_SELECTED_PENDING_COMMERCIAL_VALIDATION`

## Conclusao

A fonte principal candidata para a expansao historica do TraderIA deve ser a
Cedro Market Data Cloud, especificamente o Arquivo Serie Historica, porque e a
opcao que melhor combina WDO/BM&F, candles intraday de 1 minuto, entrega em
arquivo e facilidade de integracao futura ao fluxo CSV institucional.

A B3/UP2DATA deve permanecer como fonte secundaria de contingencia e referencia
autoritativa de auditoria, especialmente para validacao de origem, licenca e
politica comercial.

Nenhuma fonte esta autorizada para importacao ate que a confirmacao comercial e
juridica seja registrada em missao futura.

## Proxima Missao Recomendada

`MISSÃO 207 - CEDRO_MARKET_DATA_CONTRACT_CHECK.md`

Objetivo sugerido:

- solicitar confirmacao formal de WDO 1m;
- obter amostra do arquivo historico;
- confirmar periodo disponivel;
- confirmar licenca de armazenamento e uso em pesquisa;
- validar custo e formato;
- decidir se a Cedro pode passar de candidata para fonte oficial ativa.

## Restricoes Preservadas

- Nenhum codigo foi implementado.
- Nenhum modulo foi criado.
- Nenhuma API foi conectada.
- Nenhum dado foi importado.
- Nenhuma arquitetura foi alterada.
- `HistoricalDataProvider` nao foi alterado.
- Replay nao foi alterado.
- Research Lab nao foi alterado.
- Validation Suite nao foi alterada.
- Benchmark nao foi alterado.
- Portfolio nao foi alterado.
- Dashboard nao foi alterado.
- Estrategias nao foram alteradas.
- Nenhuma corretora foi conectada.
- Nenhuma ordem foi executada.
- Operacao real permanece proibida.
