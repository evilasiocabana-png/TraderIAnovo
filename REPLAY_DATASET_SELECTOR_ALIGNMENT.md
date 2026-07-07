# REPLAY_DATASET_SELECTOR_ALIGNMENT.md

## Missao

Missao 219 - Replay Dataset Selector Alignment.

## Problema identificado

O painel `DATASET DE PESQUISA ATIVO` exibia corretamente o dataset certificado
da PETR4, mas a aba Replay continuava mostrando o catalogo legado vazio e a
mensagem de que nenhum dataset historico estava ativo.

Isso criava uma inconsistencia visual:

- Home e Sistema reconheciam PETR4 1D.
- Replay nao listava PETR4 no seletor antigo.
- O usuario via `Ativo WDO` e `PETR4` sem distincao clara entre ativo
  operacional e dataset de pesquisa.

## Causa raiz

O painel institucional usava a fonte estrutural do `HistoricalDataProvider`,
enquanto a aba Replay ainda consumia o catalogo simples legado por meio de
`DashboardService.list_historical_datasets()`.

O dataset PETR4 esta em:

```text
historical_data/datasets/B3/PETR4/1d/
```

Essa estrutura e descoberta pelo catalogo estrutural do provider, mas nao era
projetada para o contrato legado `HistoricalDatasetMetadata` consumido pela aba
Replay.

## Arquivos alterados

- `application/dashboard_service.py`
- `dashboard_app.py`
- `tests/test_dashboard_historical_dataset.py`
- `tests/test_dashboard_historical_dataset_catalog.py`
- `tests/test_dashboard_app_runtime.py`
- `tests/test_dashboard_service_persistence.py`

## Arquivo criado

- `REPLAY_DATASET_SELECTOR_ALIGNMENT.md`

## Servicos reutilizados

- `DashboardService`
- `HistoricalDataProvider`
- `metadata.json`
- `checksum.sha256`
- `ReplayService`

Nenhum provider novo foi criado.

## Como o Replay passou a listar PETR4

`DashboardService.list_historical_datasets()` passou a combinar:

1. datasets cadastrados no catalogo historico legado;
2. datasets descobertos pelo `HistoricalDataProvider`.

Os registros estruturais do provider sao projetados para
`HistoricalDatasetMetadata`, preservando a API publica ja congelada do
`DashboardService`.

PETR4 passa a aparecer no Replay como:

- Dataset: `b3_petr4_1d_raw_yahoo_chart_20160628_20260628`
- Ativo: `PETR4`
- Timeframe: `1d`
- Candles: `2491`
- Provider: `HistoricalDataProvider`

Quando nenhum dataset e selecionado manualmente, o dataset certificado PETR4 e
usado como selecao padrao de pesquisa.

## Correcoes de texto e encoding

Foram ajustados textos visiveis para reduzir ambiguidade:

- `DATASET ATIVO` passou a `DATASET DE PESQUISA ATIVO`.
- `Ativo` global passou a `Ativo operacional`.
- `Replay READY` passou a `Pronto para Replay`.
- `Research READY` passou a `Pronto para Research Lab`.
- Mensagens de operacao real passaram a exibir explicitamente:
  `NAO AUTORIZADA - PROIBIDA`.
- O warning de validacao passou a:
  `Operacao real: NAO AUTORIZADA. Envio de ordens reais proibido.`

A varredura do `dashboard_app.py` nao encontrou mojibake visivel remanescente
nos textos principais do dashboard.

## Validacoes executadas

```bash
python scripts\architecture_audit.py
```

Resultado: OK.

```bash
python -m unittest tests.test_dashboard_app_runtime tests.test_dashboard_historical_dataset tests.test_application_api
```

Resultado: OK - 19 testes.

```bash
python -m unittest discover -s tests
```

Resultado: OK - 3156 testes.

```bash
python -m streamlit run dashboard_app.py
```

Resultado: iniciado com sucesso em `http://localhost:8501/`.

## Validacao manual no Chrome

Abas verificadas:

- Home/Lar: PETR4 1D com 2491 candles exibido.
- Market DNA/DNA de mercado: sem erro, painel demonstrativo preservado.
- Replay/Repeticao: PETR4 listado, provider historico exibido, 2491 candles
  disponiveis, sem mensagem de dataset ativo ausente.
- Research Lab/Laboratorio de Pesquisa: sem erro, operacao real explicitamente
  nao autorizada.
- Estrategias: sem erro.
- Eventos: sem erro.
- Sistema: PETR4 1D com 2491 candles exibido e WDO identificado como ativo
  operacional.

## Limitacoes restantes

- O Chrome pode traduzir automaticamente alguns termos tecnicos, como
  `HistoricalDataProvider`, `Replay` e `Research Lab`.
- O Market DNA ainda exibe leitura demonstrativa do WDO; PETR4 permanece apenas
  dataset de pesquisa, nao ativo operacional.
- A convencao estrutural `B3/PETR4/1d` ainda e uma compatibilidade com o
  catalogo estrutural atual e deve ser tratada futuramente em uma missao de
  governanca de catalogo multi-mercado.

## Conclusao

A aba Replay agora esta alinhada ao painel `DATASET DE PESQUISA ATIVO`.

PETR4 e reconhecido como dataset de pesquisa certificado, WDO permanece como
ativo operacional configurado, e a operacao real continua proibida.
