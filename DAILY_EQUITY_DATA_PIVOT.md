# Daily Equity Data Pivot

## Objetivo

Definir um pivô documental para permitir pesquisa quantitativa gratuita com
acoes brasileiras em grafico diario, iniciando por `PETR4`, sem abandonar a
trilha institucional de WDO 1m.

Esta missao nao implementa codigo, nao altera arquitetura, nao conecta
corretora, nao importa dados e nao executa ordens.

## Decisao Institucional

Ativo inicial de teste:

`PETR4`

Timeframe inicial gratuito:

`1d`

Status:

`DAILY_EQUITY_RESEARCH_PIVOT_DEFINED`

O TraderIA podera usar PETR4 diario como trilha gratuita de pesquisa
exploratoria, prototipagem de datasets, smoke tests de Research Lab e
validacao inicial de contratos de dados diarios.

Essa trilha nao substitui o WDO 1m. O WDO permanece a referencia institucional
para pesquisa intraday e para a arquitetura principal de Market Data.

## Fontes Avaliadas

### Yahoo Finance

Fonte consultada:

- [PETR4.SA - Yahoo Finance](https://finance.yahoo.com/quote/PETR4.SA/)
- [Yahoo Help - Download historical data](https://help.yahoo.com/kb/SLN2311.html)

Resumo:

Yahoo Finance disponibiliza pagina historica para `PETR4.SA` e documenta
download manual de dados historicos em CSV pelo navegador, com selecao de
periodo, frequencia e tipo de dado.

Pontos fortes:

- suporte conhecido a acoes brasileiras pelo sufixo `.SA`;
- download CSV documentado;
- campos geralmente compativeis com OHLCV diario;
- boa facilidade para teste manual.

Limitacoes:

- nao deve ser tratado como feed institucional oficial;
- acesso automatizado pode ser instavel ou sujeito a mudancas;
- licenca de armazenamento e redistribuicao precisa ser tratada com cautela;
- nao atende WDO 1m;
- pode ter ajustes, eventos corporativos e diferencas metodologicas.

Uso recomendado:

`PRIMARY_FREE_TEST_SOURCE`

Yahoo Finance pode ser usado como fonte inicial manual para PETR4 diario,
desde que o arquivo CSV seja salvo, versionado e validado antes de entrar no
fluxo de pesquisa.

### Investing.com

Fonte consultada:

- [PETROBRAS PN Historical Data - Investing.com](https://www.investing.com/equities/petrobras-pn-historical-data)

Resumo:

Investing.com disponibiliza pagina de historico para PETR4, com dados diarios,
periodo selecionavel e opcao de download.

Pontos fortes:

- cobertura direta de `PETR4`;
- interface acessivel para consulta manual;
- dados diarios com preco, abertura, maxima, minima e volume;
- util como fonte comparativa secundaria.

Limitacoes:

- pode exigir cookies, sessao, captcha ou limitacoes de interface;
- nao deve ser usado como fonte automatizada sem revisao de termos;
- formato pode diferir do schema institucional;
- coluna principal aparece como `Price`, exigindo normalizacao para `close`;
- nao oferece `adjusted_close` de forma necessariamente padronizada no CSV.

Uso recomendado:

`SECONDARY_FREE_REFERENCE_SOURCE`

Investing.com deve ser usado como comparador manual ou contingencia de
validacao visual, nao como fonte principal automatizada.

### Stooq

Fonte consultada:

- [Free Historical Market Data - Stooq](https://stooq.com/db/h/)
- [Free Market Data - Stooq](https://stooq.com/db/)

Resumo:

Stooq disponibiliza base historica gratuita, com downloads e dados diarios.
Tambem apresenta estrutura de arquivos historicos e possibilidade de CSV para
varios ativos.

Pontos fortes:

- foco forte em historico gratuito;
- formato CSV simples;
- melhor aderencia conceitual a ingestao por arquivo;
- boa alternativa para testes de importacao e normalizacao.

Limitacoes:

- cobertura e simbolo exato para PETR4/Brasil devem ser confirmados antes do
  uso;
- pode nao oferecer `adjusted_close` no mesmo padrao do Yahoo;
- licenciamento e redistribuicao devem ser revisados;
- nao substitui fonte oficial da B3;
- nao atende WDO 1m institucional.

Uso recomendado:

`CSV_FRIENDLY_CONTINGENCY_SOURCE`

Stooq deve ser avaliada como contingencia gratuita para CSV diario, desde que
o ativo PETR4 seja confirmado e o layout final seja validado.

## Formato CSV Esperado

Schema institucional para a trilha diaria de acoes:

```csv
date,open,high,low,close,adjusted_close,volume
2025-01-02,36.10,36.80,35.90,36.50,34.92,50000000
```

Campos obrigatorios:

- `date`
- `open`
- `high`
- `low`
- `close`
- `adjusted_close`
- `volume`

Regras de normalizacao:

- `date` deve ser data de pregao, sem horario intraday;
- `open`, `high`, `low`, `close` e `adjusted_close` devem ser numericos;
- `volume` deve ser numerico inteiro ou decimal sem separador textual;
- se a fonte nao possuir `adjusted_close`, o campo deve ser preenchido com
  valor nulo controlado ou igual a `close`, desde que documentado;
- qualquer coluna extra deve ser ignorada ou mapeada explicitamente;
- o arquivo normalizado nao deve sobrescrever o dataset bruto.

## Comparacao Com WDO 1m

| Criterio | PETR4 Diario | WDO 1m |
| --- | --- | --- |
| Custo inicial | Gratuito ou baixo | Depende de fornecedor autorizado |
| Granularidade | Diario | Intraday 1 minuto |
| Volume de dados | Baixo | Alto |
| Facilidade de CSV | Alta | Media, depende da fonte |
| Licenca institucional | Limitada/precisa revisao | Deve ser contratual |
| Uso em pesquisa | Exploratorio | Institucional intraday |
| Replay | Mais simples e lento em frequencia | Mais proximo da operacao intraday |
| Alpha Factory | Bom para Swing/Position | Bom para Intraday |
| Validacao estatistica intraday | Nao aplicavel | Necessaria |
| Operacao real | Proibida | Proibida |

## Limitações Versus WDO 1m

PETR4 diario nao permite validar:

- microestrutura intraday;
- execucao em 1 minuto;
- slippage intraday realista;
- abertura/fechamento de candle intraday;
- comportamento do mini dolar;
- liquidez e volatilidade especificas de WDO;
- estrategias intraday como Alpha001 em sua forma original.

PETR4 diario permite validar:

- fluxo de ingestao de CSV;
- contratos de dados diarios;
- pesquisa exploratoria de Swing Trade;
- Alpha Factory para hipoteses de acoes;
- Research Lab com datasets mais longos e gratuitos;
- Validation Suite em horizonte diario;
- campanhas de baixa complexidade operacional.

## Impacto no Replay

Impacto esperado:

- Replay podera ser usado em modo diario apenas quando houver dataset
  normalizado e contrato de candle diario;
- nao deve reutilizar automaticamente premissas intraday de WDO;
- execucao deve considerar um candle por pregao;
- eventos intraday deixam de existir no dataset diario;
- qualquer comparacao com WDO 1m deve ser proibida sem camada explicita de
  contexto.

Restricao:

Nenhum ajuste no Replay esta autorizado nesta missao.

## Impacto no Research Lab

Impacto esperado:

- Research Lab podera receber experimentos diarios futuros;
- metricas estatisticas continuam reutilizaveis quando baseadas em resultados
  agregados;
- engines intraday especificos nao devem assumir que todo dataset e 1m;
- campanhas para PETR4 diario devem ser classificadas como `EQUITY_DAILY`;
- validacoes devem registrar a origem gratuita e suas limitacoes.

Restricao:

Nenhuma alteracao no Research Lab esta autorizada nesta missao.

## Impacto na Alpha Factory

Impacto esperado:

- Alpha Factory passa a poder propor hipoteses Swing/Position baseadas em
  acoes brasileiras;
- PETR4 diario deve ser o primeiro ativo de laboratorio gratuito;
- playbooks futuros devem declarar explicitamente:
  - ativo;
  - classe de ativo;
  - timeframe;
  - fonte de dados;
  - limitacoes do dataset;
  - se ha `adjusted_close`;
  - se a hipotese depende de dividendos, splits ou eventos corporativos.

Restricao:

Nao criar Alpha nova nesta missao.

## Governanca de Separacao

A trilha PETR4 diario deve permanecer separada da trilha WDO 1m.

Estados recomendados:

- `WDO_INTRADAY_RESEARCH`
- `EQUITY_DAILY_RESEARCH`
- `FREE_DATA_EXPLORATORY`
- `LICENSED_DATA_INSTITUTIONAL`

Regras:

- nao misturar datasets diarios com datasets intraday;
- nao comparar diretamente PETR4 diario com WDO 1m sem contexto;
- nao usar fonte gratuita como prova institucional de execucao;
- nao usar dataset gratuito para operacao real;
- nao promover resultado exploratorio para validacao operacional;
- sempre registrar fonte, data de download, periodo, colunas e licenca.

## Fonte Recomendada Para o Primeiro Teste

Fonte primaria gratuita de teste:

`YAHOO_FINANCE_PETR4_SA_DAILY_CSV`

Justificativa:

- Yahoo documenta download CSV de historico;
- `PETR4.SA` esta disponivel na plataforma;
- o formato historico costuma conter OHLC, adjusted close e volume;
- e a rota mais simples para iniciar um dataset diario exploratorio.

Fonte secundaria de conferencia:

`INVESTING_PETR4_DAILY`

Justificativa:

- possui pagina historica especifica para Petrobras PN;
- permite conferencia manual de OHLCV;
- util para divergencias pontuais.

Fonte CSV-friendly de contingencia:

`STOOQ_DAILY_CSV`

Justificativa:

- foco em historico gratuito e CSV;
- boa candidata para automacao futura, se PETR4 estiver disponivel e os termos
  forem aceitos.

## Criterios de Aceite Para Dataset PETR4 Diario Futuro

Antes de importar qualquer arquivo:

- ativo deve ser `PETR4`;
- timeframe deve ser `1d`;
- fonte deve ser registrada;
- arquivo bruto deve ser preservado;
- arquivo normalizado deve seguir o schema institucional;
- periodo inicial e final devem ser documentados;
- duplicidades devem ser verificadas;
- ordem cronologica deve ser validada;
- volume deve ser nao negativo;
- OHLC deve ser consistente;
- `adjusted_close` deve estar presente ou documentado como indisponivel;
- licenca/termos devem ser registrados;
- operacao real deve permanecer proibida.

## Proxima Missao Recomendada

`MISSAO 209 - PETR4_DAILY_DATASET_PLAN.md`

Objetivo sugerido:

- baixar manualmente ou localizar CSV diario de PETR4;
- registrar fonte e periodo;
- criar plano de normalizacao sem implementar provider novo;
- validar schema esperado;
- decidir se PETR4 diario pode virar dataset exploratorio oficial.

## Restricoes Preservadas

- WDO nao foi abandonado.
- Nenhuma arquitetura foi alterada.
- Nenhuma corretora foi conectada.
- Nenhuma ordem foi executada.
- Nenhum modulo novo foi criado.
- Nenhum provider foi implementado.
- Replay nao foi alterado.
- Research Lab nao foi alterado.
- Alpha Factory nao foi alterada.
- Pesquisa de acoes permanece separada de execucao operacional.
- Operacao real permanece proibida.
