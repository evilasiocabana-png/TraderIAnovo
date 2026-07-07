# MARKET_READING_PIPELINE

## Missao

Missao 230 - Market Reading Pipeline.

## Sprint

Sprint 16 - Market Reading Replay MVP.

## Objetivo

Implementar o fluxo visual base do TraderIA durante o Replay:

```text
Dados -> Leitura do Mercado -> Contexto -> Setup -> Decisao -> Resultado
```

## Arquivos alterados

- `dashboard_app.py`
- `tests/test_dashboard_app_runtime.py`
- `tests/test_dashboard_facade.py`
- `MANIFEST.md`

## Componentes criados

No `dashboard_app.py` foram criados blocos visuais especificos para o pipeline:

- `exibir_market_reading_pipeline`
- `exibir_bloco_dados_pipeline`
- `exibir_bloco_leitura_pipeline`
- `exibir_bloco_contexto_pipeline`
- `exibir_bloco_setup_pipeline`
- `exibir_bloco_decisao_pipeline`
- `exibir_bloco_resultado_pipeline`

Foram adicionados tambem helpers de apresentacao para calculos simples de tela:

- posicao do candle atual;
- OHLC;
- retorno do candle;
- volatilidade simples;
- drawdown;
- volume relativo;
- tendencia;
- lateralidade;
- regime de volatilidade;
- momentum;
- setup encontrado;
- flags BUY, SELL e WAIT.

## Onde aparece no dashboard

O pipeline aparece na tela unica `TraderIA Research Workbench`, logo depois da area de grafico e controles de Replay.

A ordem visual e:

1. Grafico e Replay.
2. Market Reading Pipeline.
3. Alpha.
4. Estatisticas.

Essa ordem garante que, ao clicar em `Proximo candle`, o pipeline seja renderizado com o estado atualizado do Replay no mesmo ciclo de execucao.

## Metricas que ja funcionam

### Dados

- ativo;
- timeframe;
- candle atual;
- data;
- OHLC;
- volume.

### Leitura do Mercado

- retorno do candle;
- retorno acumulado;
- volatilidade simples;
- drawdown;
- volume relativo.

### Contexto

- tendencia;
- lateralidade;
- volatilidade;
- momentum.

### Setup

- Alpha avaliada;
- setup encontrado;
- motivo principal.

### Decisao

- BUY;
- SELL;
- WAIT;
- confidence;
- score.

### Resultado

- trades;
- PnL;
- drawdown;
- win rate;
- equity.

## Metricas ainda simplificadas

- Volatilidade simples usa amplitude do candle atual quando disponivel.
- Lateralidade e derivada de `trend_strength` do snapshot de features.
- Volume relativo usa media dos candles processados quando disponivel.
- Drawdown de mercado usa a sequencia processada no Replay, nao uma analise estatistica independente.
- Setup encontrado e derivado da decisao da Alpha atual: BUY ou SELL indicam setup; WAIT indica ausencia de setup acionavel.

## Restricoes preservadas

- Nenhuma engine nova foi criada.
- Nenhuma arquitetura nova foi criada.
- `HistoricalDataProvider` nao foi alterado.
- `ReplayEngine` nao foi alterado.
- `ResearchLab` nao foi alterado.
- O Dashboard continua consumindo dados apenas por `DashboardService`.
- Nao ha corretora.
- Nao ha envio de ordens.
- Nao ha uso de dados simulados no fluxo principal.
- Nao ha tabelas interativas instaveis.

## Validacoes

- `python scripts\architecture_audit.py`
- `python -m unittest tests.test_dashboard_app_runtime tests.test_dashboard_historical_dataset tests.test_application_api`
- `python -m unittest tests.test_dashboard_app_runtime tests.test_dashboard_facade`
- `python -m unittest discover -s tests`
- `python -m streamlit run dashboard_app.py`

## Resultado das validacoes

- Architecture Audit: OK.
- Testes obrigatorios focados: 21 testes OK.
- Testes de runtime/fachada: 11 testes OK.
- Suite completa: 3159 testes OK.
- Streamlit: respondeu em `http://localhost:8502` com status 200.

## Declaracao Final

O Market Reading Pipeline foi adicionado ao Dashboard. A operacao real continua proibida.
