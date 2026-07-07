# APP_OPERATIONAL_DIAGNOSTIC.md

## Missao 219 - Diagnostico Operacional da Aplicacao Visual

Projeto: TraderIA  
Sprint 13 - Platform Observability Repair  
Data: 2026-06-28

---

## 1. Resumo Executivo

A aplicacao visual do TraderIA esta parcialmente operacional.

O painel principal em `dashboard_app.py` consegue exibir o dataset certificado da PETR4, listar o dataset no Replay e carregar candles reais via `DashboardService` e `HistoricalDataProvider`.

Entretanto, parte relevante da interface ainda esta em modo demonstrativo ou parcialmente desconectada do fluxo PETR4. O ponto mais importante: o dataset PETR4 esta visivel e carregavel, mas a aplicacao ainda mistura paineis reais de observabilidade com paineis legados/demo, especialmente em Market DNA, Research Lab, Eventos e `app.py`.

Classificacao honesta:

**PLATAFORMA VISUAL PARCIALMENTE OPERACIONAL PARA OBSERVABILIDADE.**

**PETR4 ESTA DISPONIVEL COMO DATASET DE PESQUISA.**

**RESEARCH COM PETR4 AINDA NAO PRODUZ RESULTADO QUANTITATIVO UTIL, POIS NAO EXISTE ALPHA COMPATIVEL COM PETR4 DIARIO.**

**OPERACAO REAL PERMANECE NAO AUTORIZADA.**

---

## 2. Escopo Avaliado

Foram avaliados:

- `app.py`
- `dashboard_app.py`
- `DashboardService`
- aba Home
- aba Market DNA
- aba Replay
- aba Research Lab
- aba Estrategias
- aba Eventos
- aba Sistema
- painel Dataset Ativo
- EventBus
- fluxo PETR4

---

## 3. O Que Funciona

### 3.1 Dashboard Streamlit

O arquivo `dashboard_app.py` sobe a aplicacao visual em Streamlit.

A aplicacao apresenta as abas principais:

- Home
- Market DNA
- Replay
- Research Lab
- Estrategias
- Eventos
- Sistema

Observacao: no Chrome com traducao automatica ativa, alguns nomes aparecem traduzidos, como `Home` para `Lar` e `Replay` para `Repeticao`.

### 3.2 Dataset Ativo

O painel de dataset ativo funciona.

O `DashboardService` retorna corretamente o dataset:

- Ativo: PETR4
- Timeframe: 1d
- Fonte: Yahoo Finance
- Provider: HistoricalDataProvider
- Dataset: `b3_petr4_1d_raw_yahoo_chart_20160628_20260628`
- Periodo: 2016-06-28 -> 2026-06-26
- Candles: 2491
- Status: CERTIFIED_WITH_WARNINGS
- Certificacao: PETR4_DATASET_CERTIFIED_FOR_QUANTITATIVE_RESEARCH
- Replay: Pronto para Replay
- Research Lab: Pronto para Research Lab
- Architecture: OK

### 3.3 Catalogo de Datasets

O `DashboardService` lista datasets disponiveis:

- PETR4 1d com 2491 candles via `HistoricalDataProvider`
- WDO 1m com 2 candles via `HistoricalDataProvider`

O dataset PETR4 aparece como dataset de pesquisa selecionado por padrao.

### 3.4 Replay com PETR4

O Replay consegue carregar o dataset PETR4 pelo `DashboardService`.

Evidencia operacional:

- status inicial apos carga: `ReplayStatus.READY`
- total de candles: 2491
- indice inicial: -1
- apos avancar um candle: indice 0
- contador de eventos apos primeiro candle: 6

Isso confirma que o fluxo basico de Replay com candles reais da PETR4 esta funcional na camada de aplicacao.

### 3.5 Research Lab com PETR4

O `DashboardService` consegue executar um experimento de pesquisa usando o dataset selecionado.

Resultado observado:

- experimento: `b3_petr4_1d_raw_yahoo_chart_20160628_20260628`
- estrategia: `alpha001_iorb`
- total de trades: 0
- net profit points: 0.0

Conclusao: o fluxo executa, mas o resultado nao e quantitativamente util para PETR4 diario porque a Alpha001 foi concebida para outro contexto operacional.

### 3.6 Auditoria Arquitetural

O Architecture Audit foi executado com sucesso.

Comando:

```bash
python scripts\architecture_audit.py
```

Resultado:

```text
Architecture audit status: OK
```

### 3.7 Testes Focados

Foram executados testes focados em dashboard, provider, replay e research.

Comando:

```bash
python -m unittest tests.test_dashboard_app_runtime tests.test_dashboard_historical_dataset tests.test_dashboard_historical_dataset_catalog tests.test_replay_historical_data tests.test_replay_market_data_provider tests.test_research_market_data_provider
```

Resultado:

```text
Ran 84 tests in 18.461s
OK
```

---

## 4. O Que Esta Mockado ou Demo

### 4.1 app.py

O arquivo `app.py` nao representa a aplicacao visual principal.

Ele executa um fluxo legado/demonstrativo:

- cria um `MarketState` fixo;
- cria candles demonstrativos;
- usa `SimulatedBroker`;
- executa um fluxo com `TradingEngine`;
- salva um Market DNA em JSONL;
- gera um dashboard HTML estatico em `resultados/market_dna_dashboard.html`;
- registra eventos de exemplo.

Saida observada:

```text
Ativo: WDO
Operacao: Operacao(... status='ABERTA' ...)
Padroes similares: 3
MARKET DNA salvo em: data\market_dna\2026-06-25.jsonl
Dashboard salvo em: resultados\market_dna_dashboard.html
Eventos registrados: 5
```

Conclusao: `app.py` funciona como runner demo/legado, mas nao esta alinhado ao dashboard Streamlit nem ao fluxo PETR4.

### 4.2 Market DNA

A aba Market DNA ainda apresenta conteudo demonstrativo/legado.

Ela nao esta alimentada pelo dataset PETR4 diario e nao representa uma leitura real do fluxo PETR4.

### 4.3 Estrategias

A aba Estrategias mostra informacoes de estrategias e status institucional, mas nao e uma interface operacional completa de gerenciamento de estrategias.

Ela ainda funciona mais como painel informativo.

### 4.4 Eventos

A aba Eventos ainda nao apresenta uma trilha detalhada e auditavel do EventBus.

Ha contadores e mensagens institucionais, mas o usuario nao ve claramente uma lista completa de eventos emitidos pelo fluxo PETR4.

### 4.5 Research Lab

O Research Lab visual ainda esta parcialmente em modo demonstrativo.

Embora o servico consiga executar um experimento com PETR4, a interface ainda nao comunica com clareza que:

- PETR4 e dataset de pesquisa;
- Alpha001 nao e adequada para PETR4 diario;
- o resultado de 0 trades nao significa validacao da estrategia;
- ainda falta uma Alpha propria para PETR4 diario.

---

## 5. O Que Esta Desconectado ou Parcialmente Conectado

### 5.1 app.py vs dashboard_app.py

Existe uma desconexao conceitual entre:

- `app.py`: runner legado/demo;
- `dashboard_app.py`: aplicacao visual Streamlit atual.

Isso pode confundir o usuario, porque `python app.py` gera saidas e arquivos, mas nao altera a interface visual aberta no navegador.

### 5.2 Market DNA vs PETR4

O Market DNA nao esta conectado ao dataset PETR4 certificado.

O painel pode dar a impressao de funcionamento operacional, mas nao esta refletindo o dataset de pesquisa ativo.

### 5.3 Research Lab vs PETR4 Diario

O Research Lab consegue executar fluxo tecnico, mas ainda nao possui uma Alpha compativel com PETR4 diario.

Assim, a integracao existe em nivel de infraestrutura, mas nao ha pesquisa quantitativa significativa ainda.

### 5.4 EventBus vs Aba Eventos

O EventBus existe e eventos sao emitidos durante o Replay.

Porem a aba Eventos nao apresenta uma auditoria visual detalhada dos eventos gerados pelo fluxo PETR4.

### 5.5 Replay Visual

A aba Replay reconhece PETR4 e consegue operar com o dataset pela camada de servico.

Ainda assim, a experiencia visual precisa deixar mais claro:

- qual dataset esta selecionado;
- se o replay foi carregado;
- qual candle atual esta sendo exibido;
- quantos eventos foram emitidos;
- se o fluxo atual e apenas pesquisa, nao operacao.

---

## 6. Diagnostico por Aba

### 6.1 Home

Funciona para observabilidade institucional.

Mostra o dataset PETR4 como dataset de pesquisa ativo.

Ponto de atencao: precisa diferenciar ainda mais `Ativo operacional: WDO` de `Dataset de pesquisa: PETR4`.

### 6.2 Market DNA

Funciona como painel demonstrativo.

Nao esta comprovadamente conectado ao PETR4 diario.

Deve ser tratado como demo ate ser conectado a dados reais ou rotulado explicitamente como demonstrativo.

### 6.3 Replay

Funciona parcialmente.

Reconhece PETR4 1D, lista o dataset certificado e consegue carregar candles via `DashboardService`.

Precisa melhorar a clareza visual do estado do Replay e dos eventos emitidos.

### 6.4 Research Lab

Funciona tecnicamente, mas ainda nao entrega pesquisa quantitativa util para PETR4.

Motivo: o experimento observado executou Alpha001 sobre PETR4 diario e retornou 0 trades.

Isso nao e erro tecnico; e desalinhamento entre estrategia e dataset.

### 6.5 Estrategias

Funciona como painel informativo.

Nao executa estrategia real nem altera pipeline.

### 6.6 Eventos

Parcialmente funcional.

O sistema emite eventos, mas a aba ainda nao exibe uma trilha visual suficiente para auditoria.

### 6.7 Sistema

Funciona como painel institucional.

Mostra separacao entre plataforma, arquitetura e dataset.

Ponto de atencao: deve continuar reforcando que operacao real permanece nao autorizada.

---

## 7. O Que Precisa Ser Corrigido Primeiro

### Prioridade 1 - Separar claramente app.py e dashboard_app.py

O primeiro problema a corrigir e institucional.

`app.py` parece ser a aplicacao principal, mas na pratica e um runner demo/legado.

Acao recomendada:

- documentar `dashboard_app.py` como app visual oficial;
- rotular `app.py` como demo/legacy runner;
- evitar que `app.py` seja interpretado como fonte do dashboard atual.

### Prioridade 2 - Rotular Market DNA como demo ou conecta-lo ao PETR4

Hoje a aba Market DNA pode induzir leitura errada.

Acao recomendada:

- ou conectar Market DNA ao fluxo PETR4 real;
- ou exibir selo explicito: `DEMONSTRATIVO - NAO CONECTADO AO DATASET PETR4`.

### Prioridade 3 - Melhorar a aba Replay

A aba Replay deve deixar o estado do dataset e da execucao impossivel de confundir.

Acao recomendada:

- mostrar dataset carregado;
- mostrar candle atual;
- mostrar progresso;
- mostrar eventos emitidos;
- mostrar `Operacao real: NAO AUTORIZADA`.

### Prioridade 4 - Ajustar Research Lab para PETR4 diario

O Research Lab nao deve sugerir que Alpha001 valida PETR4 diario.

Acao recomendada:

- mostrar aviso quando a Alpha selecionada nao for compativel com o dataset;
- preparar Alpha propria para PETR4 diario antes de interpretar resultados;
- manter resultados de Alpha001/PETR4 como smoke test tecnico, nao pesquisa conclusiva.

### Prioridade 5 - Expor EventBus de forma auditavel

A aba Eventos precisa exibir os eventos relevantes emitidos pelo fluxo PETR4.

Acao recomendada:

- listar eventos recentes;
- mostrar tipo, timestamp, payload resumido e origem;
- diferenciar eventos de demo, replay e research.

---

## 8. Riscos Identificados

- Usuario interpretar `app.py` como aplicacao visual oficial.
- Usuario interpretar Market DNA como calculado sobre PETR4 quando ainda nao esta.
- Usuario interpretar Research Lab com 0 trades como falha da plataforma ou validacao da Alpha.
- Chrome Translate alterar termos tecnicos e gerar confusao visual.
- Mistura de WDO operacional e PETR4 pesquisa causar leitura equivocada.

---

## 9. Conclusao Tecnica

O TraderIA ja possui base funcional para observabilidade do dataset PETR4:

- dataset aparece no Dashboard;
- provider reconhece o dataset;
- Replay consegue carregar candles reais;
- Research Lab consegue executar smoke test tecnico;
- arquitetura permanece aprovada.

Mas a aplicacao visual ainda nao esta totalmente coerente do ponto de vista operacional.

O problema principal nao e o dataset.

O problema principal e a mistura de:

- componentes reais;
- componentes demo;
- paineis institucionais;
- runner legado;
- Research sem Alpha adequada para PETR4 diario.

---

## 10. Classificacao Final

| Area | Status |
|---|---|
| Dashboard Streamlit | FUNCIONA |
| Dataset Ativo PETR4 | FUNCIONA |
| HistoricalDataProvider PETR4 | FUNCIONA |
| Replay com PETR4 | FUNCIONA PARCIALMENTE |
| Research Lab com PETR4 | TECNICAMENTE EXECUTA, MAS NAO E UTIL AINDA |
| Market DNA | DEMO / PARCIALMENTE DESCONECTADO |
| EventBus visual | PARCIALMENTE DESCONECTADO |
| app.py | DEMO / LEGADO |
| Operacao real | NAO AUTORIZADA |

---

## 11. Recomendacao Imediata

A proxima missao deve corrigir a clareza operacional da interface antes de avancar em pesquisa quantitativa.

Missao recomendada:

**VISUAL_OPERATIONAL_ALIGNMENT**

Objetivo:

- rotular claramente paineis demo;
- separar WDO operacional de PETR4 pesquisa;
- melhorar Replay visual;
- expor eventos do EventBus;
- impedir interpretacao indevida do Research Lab com PETR4.

Essa correcao deve vir antes de qualquer nova Alpha ou certificacao visual.

---

## 12. Confirmacao de Escopo

Esta missao foi exclusivamente diagnostica.

Nenhum modulo operacional foi alterado.

Nenhuma estrategia foi alterada.

Nenhum provider foi criado.

Nenhum contrato foi alterado.

Nenhuma ordem foi executada.

Nenhuma conexao com corretora foi criada.

Operacao real permanece proibida.
