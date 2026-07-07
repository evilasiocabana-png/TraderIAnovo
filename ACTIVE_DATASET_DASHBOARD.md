# ACTIVE_DATASET_DASHBOARD.md

## Missao

Missao 217 - Active Dataset Dashboard.

## Objetivo

Exibir no Dashboard institucional do TraderIA qual dataset historico esta ativo para pesquisa quantitativa, sem alterar logica de trading, Replay, Research Lab, EventBus, DecisionPipeline ou arquitetura operacional.

## Telas alteradas

- Home do Dashboard Streamlit.
- Aba Sistema do Dashboard Streamlit.

## Informacoes exibidas

O painel institucional `DATASET ATIVO` exibe:

- Ativo.
- Timeframe.
- Fonte.
- Provider.
- Dataset.
- Status.
- Periodo.
- Quantidade de candles.
- Ultima atualizacao.
- Checksum.
- Metadata Version.
- Dataset Certification.
- Replay Status.
- Research Status.
- Architecture Status.

Quando mais de um dataset esta disponivel, o Dashboard exibe tambem a tabela `DATASETS DISPONIVEIS`, com:

- Ativo.
- Timeframe.
- Candles.
- Status.
- Provider.
- Fonte.
- Selecionado.

## Dataset ativo identificado

- Ativo: PETR4.
- Timeframe: 1d.
- Fonte: Yahoo Finance.
- Provider: HistoricalDataProvider.
- Dataset: `b3_petr4_1d_raw_yahoo_chart_20160628_20260628`.
- Periodo: 2016-06-28 -> 2026-06-26.
- Candles: 2491.
- Status: CERTIFIED_WITH_WARNINGS.
- Dataset Certification: PETR4_DATASET_CERTIFIED_FOR_QUANTITATIVE_RESEARCH.
- Replay Status: READY.
- Research Status: READY.
- Architecture Status: OK.

## Origem das informacoes

As informacoes chegam ao Dashboard exclusivamente pela camada `application`, via `DashboardService`.

Fontes reutilizadas:

- `HistoricalDataProvider`.
- `metadata.json`.
- `checksum.sha256`.
- `DashboardService`.

O Dashboard nao acessa arquivos diretamente e nao instancia providers.

## Servicos reutilizados

- `application.dashboard_service.DashboardService`.
- `market_data.historical_data_provider.HistoricalDataProvider`.
- Catalogo estrutural de datasets historicos ja utilizado pelo provider.

Nenhum novo provider foi criado.

## Decisoes tecnicas

- Criado DTO imutavel `ActiveDatasetDashboardData` dentro da camada de aplicacao.
- O contrato publico congelado do `DashboardService` foi preservado: a nova composicao e exposta apenas por `DashboardData`.
- O dataset ativo e selecionado por metadados certificados, priorizando datasets com status `CERTIFIED`.
- O painel da Home e da aba Sistema reutiliza o mesmo helper visual, evitando divergencia entre telas.
- O label visual de quantidade foi mantido como `Candles Dataset` para nao colidir com a metrica `Candles` ja usada pelo Replay.

## Validacao arquitetural

- Dashboard continua consumindo apenas `DashboardService`.
- Dashboard nao acessa `metadata.json` diretamente.
- Dashboard nao acessa `checksum.sha256` diretamente.
- Replay nao foi alterado.
- Research Lab nao foi alterado.
- EventBus nao foi alterado.
- DecisionPipeline nao foi alterado.
- Estrategias nao foram alteradas.

## Testes executados

```bash
python -m unittest tests.test_dashboard_historical_dataset tests.test_dashboard_app_runtime
```

Resultado: OK - 10 testes.

```bash
python -m unittest tests.test_application_api
```

Resultado: OK - 8 testes.

```bash
python scripts\architecture_audit.py
```

Resultado: OK.

```bash
python -m unittest discover -s tests
```

Resultado: OK - 3155 testes.

```bash
python app.py
```

Resultado: executado com sucesso.

## Observacao sobre screenshot

Nao foi gerado screenshot automatizado porque o ambiente Python local nao possui Playwright instalado. A renderizacao do painel foi validada por `streamlit.testing.v1.AppTest`, que confirmou a presenca de `DATASET ATIVO` e `DATASETS DISPONIVEIS` no Dashboard.

## Conclusao

O Dashboard agora exibe institucionalmente o dataset ativo PETR4 certificado para pesquisa quantitativa, preservando o isolamento arquitetural e sem alterar qualquer funcionalidade operacional de trading.
