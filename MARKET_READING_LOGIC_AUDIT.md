# MARKET_READING_LOGIC_AUDIT

## 1. Resumo Executivo

Esta auditoria avaliou se o fluxo do Sprint 16 esta funcionando como pipeline real de pesquisa quantitativa:

```text
Dados -> Leitura do Mercado -> Contexto -> Setup -> Decisao -> Resultado
```

Classificacao final:

```text
MARKET_READING_PIPELINE_PARTIAL
```

O pipeline esta funcional como tela de leitura e replay sobre dados reais de PETR4, usando `DashboardService`, `HistoricalDataProvider`, `ReplayService`, `ReplayEngine`, `FeatureEngine`, `RegimeEngine`, `ResearchService`, estrategia e `DecisionPipeline`.

Entretanto, ele ainda nao pode ser classificado como OK porque:

- a Alpha efetiva continua sendo `Alpha001 - IORB`, incompatível com PETR4 diario;
- o seletor visual de Alpha no menu lateral nao altera a estrategia executada no Replay;
- varios indicadores de leitura de mercado ainda sao metricas simples ou proxies;
- o Market Profile ainda nao existe como componente conceitual completo;
- a decisao de risco usada no replay e uma autorizacao demonstrativa de pesquisa, nao uma avaliacao real de risco operacional;
- o Play automatico exige validacao visual manual adicional, pois em teste automatizado o loop de rerun do Streamlit causou timeout.

## 2. Mapa do Pipeline Real

### Dados

Status: REAL

O dataset PETR4 diario e carregado a partir do catalogo historico por meio da camada autorizada:

```text
Dashboard -> DashboardService -> HistoricalDataProvider -> HistoricalDataset
```

O dataset certificado contem 2491 candles e permanece classificado como dataset de pesquisa. WDO permanece como ativo operacional/configuracao.

### Replay

Status: REAL

O Replay utiliza `ReplayService` como fachada de aplicacao e `ReplayEngine` como simulador temporal. O avanco candle a candle e real e alimenta o pipeline com candles historicos normalizados.

Fluxo observado:

```text
ReplayService.load_historical_dataset()
ReplayEngine.load_candles()
ReplayService.next_candle()
ReplayEngine.next_candle()
ReplayService._update_feature_pipeline()
```

### Features

Status: REAL / PARCIAL

O `FeatureEngine` calcula features reais a partir de `CandleHistory`, incluindo:

- momentum;
- average_range;
- highest_high;
- lowest_low;
- direction;
- trend_strength;
- volatility_level.

As features sao reais, mas ainda simples. A volatilidade usa limites fixos que parecem calibrados para WDO e nao para PETR4 diario.

### Market Profile

Status: PARCIAL

Nao existe ainda um objeto formal completo de Market Profile para pesquisa. A leitura de mercado exibida no dashboard e composta por:

- features reais do `FeatureEngine`;
- analise de regime do `RegimeEngine`;
- calculos auxiliares feitos na interface.

Isso entrega valor visual, mas ainda nao constitui um Market Profile robusto.

### Contexto

Status: REAL / PARCIAL

O contexto vem principalmente do `RegimeEngine`, que avalia tendencia, volatilidade e liquidez. A analise e real, mas ainda usa thresholds genericos que podem gerar leitura pouco adequada para PETR4 diario.

### Setup

Status: PARCIAL

O painel de Setup nao usa um detector independente de setup. Ele deriva "setup encontrado" da decisao da estrategia:

```text
BUY ou SELL -> setup encontrado
WAIT -> setup nao encontrado
```

Portanto, o setup exibido e um proxy da decisao, nao uma camada propria de deteccao.

### Decisao

Status: REAL / PARCIAL

A decisao exibida vem de `StrategySignal` e passa pelo `DecisionPipeline`. A Alpha e de fato avaliada, mas a estrategia efetiva permanece `Alpha001 - IORB`.

Para PETR4 diario, a Alpha001 tende a retornar WAIT porque depende de janela intraday de opening range entre 09:00 e 09:15, inexistente em candles diarios.

### Resultado

Status: REAL / PARCIAL

As estatisticas sao calculadas a partir de paper trades e paper metrics. Como PETR4 diario com Alpha001 nao gera trades, as metricas permanecem zeradas.

Quando houver trades, o painel tende a refletir resultados reais do paper replay. No estado atual, ele confirma ausencia de operacoes em vez de performance quantitativa ativa.

## 3. Auditoria dos Indicadores

| Indicador | Status | Origem | Observacao |
|---|---|---|---|
| Ativo | REAL | Dataset ativo via DashboardService | Exibe PETR4 corretamente |
| Timeframe | REAL | Metadata do dataset | Exibe 1d corretamente |
| Candle atual | REAL | ReplayService | Atualiza ao avancar candle |
| Data | REAL | Candle atual | N/D antes do primeiro candle |
| OHLC | REAL | Candle atual | Atualiza no replay |
| Volume | REAL | Candle atual | Atualiza no replay |
| Retorno do candle | REAL | Calculo sobre OHLC real | Simples e correto para o candle atual |
| Retorno acumulado | PARCIAL | Calculo UI / Dataset profile | Pode mostrar retorno total do dataset quando nao ha candle atual |
| Volatilidade simples | PARCIAL | Amplitude high-low | E uma amplitude simples, nao volatilidade estatistica |
| Drawdown de mercado | PARCIAL | Maximo dos closes processados | Util para visualizacao, mas ainda simplificado |
| Volume relativo | PARCIAL | Volume atual / media processada | Primeiro candle e forçado para 1.00x |
| Tendencia | REAL / PARCIAL | FeatureSnapshot.direction | Baseada no momentum acumulado do historico processado |
| Lateralidade | PARCIAL | Proxy por trend_strength | Nao e detector formal de range |
| Volatilidade alta/baixa | PARCIAL | FeatureSnapshot.volatility_level | Thresholds nao ajustados para PETR4 diario |
| Momentum | REAL | FeatureEngine | Calculado a partir dos candles processados |
| Alpha carregada | PARCIAL | Status Alpha001 | Seletor visual nao altera estrategia efetiva |
| Setup encontrado | PARCIAL | Derivado de BUY/SELL/WAIT | Nao ha detector independente de setup |
| Motivos | REAL / PARCIAL | StrategySignal.reasons | Motivos reais da Alpha001, mas ligados a estrategia inadequada para PETR4 diario |
| BUY/SELL/WAIT | REAL | StrategySignal | Alpha avalia e retorna WAIT para PETR4 diario |
| Confidence | REAL | StrategySignal | Calculado pela Alpha001DecisionEngine |
| Score | REAL | StrategySignal | Derivado da confidence |
| Trades | REAL | Paper metrics | Zera porque nao ha sinais executaveis |
| PnL | REAL | Paper metrics | Zera porque nao ha trades |
| Equity | REAL / PARCIAL | Paper equity curve | Sem valor informativo quando nao ha trades |
| Win Rate | REAL | Paper metrics | Zera porque nao ha trades |
| Profit Factor | REAL / PARCIAL | Paper metrics | Indefinido ou zero sem trades |
| Drawdown de resultado | REAL / PARCIAL | Paper metrics | Sem relevancia enquanto nao houver trades |
| Expectancy | PARCIAL | Calculo auxiliar UI | Depende de paper metrics |
| Sharpe | PARCIAL | Calculo auxiliar UI | N/D sem curva suficiente |

## 4. Auditoria da Strategy Engine

### Estrategia efetiva

Status: REAL / INADEQUADA PARA PETR4 1D

A estrategia efetiva no Replay e `alpha001_iorb`. Ela chama `Alpha001DecisionEngine.evaluate()` e retorna `StrategySignal`.

Isso significa que a Alpha nao e apenas um placeholder fixo. Ela avalia condicoes reais:

- opening range completo;
- breakout;
- momentum;
- regime;
- volatilidade;
- liquidez.

### Por que retorna WAIT

Status: ESPERADO PELO DESENHO ATUAL

PETR4 diario nao contem candles intraday entre 09:00 e 09:15. Portanto, o `OpeningRangeEngine` nao consegue formar opening range. Como a Alpha001 depende disso, o resultado pratico e WAIT persistente.

Teste empirico nos primeiros 30 candles:

```text
BUY: 0
SELL: 0
WAIT: 30
```

Conclusao:

```text
A Alpha esta realmente sendo avaliada, mas para PETR4 diario ela funciona na pratica como WAIT persistente por incompatibilidade de timeframe/mercado.
```

### Seletor de Alpha

Status: NAO IMPLEMENTADO COMO TROCA REAL

O menu lateral permite selecionar:

```text
alpha001_iorb
breakout
pullback
score_contexto
smart_money
```

Porem a selecao e apenas visual no estado atual. O `ReplayService` continua usando a estrategia configurada internamente, e o painel de Alpha carregada permanece vinculado ao status da Alpha001.

## 5. Teste Funcional do Painel

| Acao | Resultado |
|---|---|
| Abrir dashboard | FUNCIONA |
| Carregar PETR4 | FUNCIONA |
| Ver candles totais | FUNCIONA: 2491 candles |
| Avancar candle | FUNCIONA |
| Atualizar OHLC | FUNCIONA |
| Atualizar leitura de mercado | FUNCIONA PARCIALMENTE |
| Atualizar decisao | FUNCIONA, mas retorna WAIT |
| Atualizar resultado | FUNCIONA, mas sem trades |
| Reset | FUNCIONA |
| Voltar candle | FUNCIONA PARCIALMENTE; pode retornar para estado sem candle atual |
| Trocar Alpha | NAO FUNCIONA como troca efetiva de estrategia |
| Play automatico | FUNCIONA PARCIALMENTE; requer validacao visual manual adicional |

## 6. Consistencia Visual e Conceitual

O painel ja comunica a cadeia correta:

```text
Dados -> Leitura do Mercado -> Contexto -> Setup -> Decisao -> Resultado
```

Isso e positivo. O usuario consegue entender que o TraderIA esta lendo dados historicos e produzindo uma decisao quantitativa sem executar ordens reais.

O problema e que parte dos blocos ainda esta mais avancada visualmente do que logicamente:

- Market Profile ainda e uma composicao simples de features;
- Setup nao e uma deteccao independente;
- Alpha selector nao muda a Alpha efetiva;
- Resultado fica zerado porque a Alpha atual nao opera PETR4 diario;
- Confidence e Score existem, mas refletem principalmente a falha das pre-condicoes da Alpha001.

## 7. Problemas Encontrados

### Problema 1: Alpha001 incompatível com PETR4 diario

Impacto: alto.

A Alpha001 IORB foi desenhada para WDO intraday e depende de opening range. Com PETR4 1d, ela quase sempre retorna WAIT por desenho.

### Problema 2: Seletor de Alpha nao altera a estrategia real

Impacto: alto.

O usuario pode acreditar que esta testando outra Alpha, mas a estrategia efetiva do Replay permanece a configurada no `ReplayService`.

### Problema 3: Setup encontrado e derivado da decisao

Impacto: medio.

O painel mostra setup, mas nao ha uma camada independente de deteccao de setup.

### Problema 4: Market Profile ainda e simplificado

Impacto: medio.

Tendencia, volatilidade, lateralidade e contexto sao uteis, mas ainda baseados em heuristicas simples.

### Problema 5: Play automatico nao foi validado de forma robusta em teste automatizado

Impacto: medio.

O `AppTest` entrou em timeout ao acionar Play, provavelmente por causa do loop de rerun/sleep do Streamlit. Avanco manual candle a candle funciona sem excecoes.

## 8. Correcoes Prioritarias

### Prioridade 1: Conectar o seletor de Alpha ao ReplayService

O menu lateral deve trocar de fato a estrategia usada pelo Replay, preservando a arquitetura e mantendo `DashboardService` como fachada.

### Prioridade 2: Usar uma Alpha compatível com PETR4 diario

Para PETR4 1d, a direcao natural e ativar uma Alpha diaria/swing documentada, como a linha de `Alpha101`, em vez de usar Alpha001 IORB.

### Prioridade 3: Separar Setup Detection de Strategy Decision

O painel de Setup deve representar uma avaliacao propria de existencia de setup, sem depender apenas de `BUY/SELL/WAIT`.

### Prioridade 4: Formalizar o Market Profile

Criar uma leitura mais robusta de tendencia, volatilidade, volume, momentum e regime, sem misturar calculos de interface com raciocinio quantitativo.

### Prioridade 5: Estabilizar Play/Pause em modo testavel

O loop automatico deve ser previsivel, testavel e nao depender de reruns instaveis.

## 9. Validacoes Executadas

### Architecture Audit

Comando:

```text
python scripts\architecture_audit.py
```

Resultado:

```text
OK
```

### Testes completos

Comando:

```text
python -m unittest discover -s tests
```

Resultado:

```text
Ran 3159 tests in 128.480s
OK
```

### Streamlit

Comando:

```text
python -m streamlit run dashboard_app.py --server.headless true --server.port 8503
```

Resultado:

```text
HTTP 200
```

### AppTest funcional

Resultados observados:

- dashboard abriu sem excecoes;
- PETR4 carregou com 2491 candles;
- proximo candle funcionou;
- reset funcionou;
- troca visual de Alpha funcionou no seletor;
- troca visual de Alpha nao alterou a estrategia efetiva;
- Play automatico causou timeout em teste automatizado.

## 10. Conclusao CTO

O Market Reading Pipeline esta parcialmente funcional.

Ele ja entrega uma tela util para visualizar dados reais, avancar candles, ver OHLC, acompanhar leitura simples de mercado, observar decisao quantitativa e acompanhar estatisticas de paper replay.

Mas ainda nao e um MVP quantitativo completo porque a Alpha efetiva nao e apropriada para PETR4 diario, a troca de Alpha nao e operacional, o setup e apenas um proxy da decisao e parte do Market Profile ainda esta simplificada.

Classificacao final:

```text
MARKET_READING_PIPELINE_PARTIAL
```

Proxima correcao mais importante:

```text
Conectar o seletor de Alpha ao ReplayService e habilitar uma Alpha compatível com PETR4 diario, mantendo DashboardService como fachada e sem criar ordens reais.
```
