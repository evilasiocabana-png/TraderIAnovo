# Historical Data Expansion Plan

## Objetivo

Definir o plano institucional para ampliar o dataset historico real do WDO no
TraderIA_WDO.

Este documento e apenas um plano. Ele nao implementa codigo, nao altera
providers, nao altera Research Lab, nao valida estrategia, nao conecta
corretora e nao autoriza operacao real.

## Estado Atual

| Campo | Valor |
| --- | --- |
| Dataset certificado atual | `wdo_1m_2025` |
| Ativo | `WDO` |
| Timeframe | `1m` |
| Caminho atual | `historical_data/datasets/WDO/1m/2025/` |
| Candles atuais | 2 |
| Provider atual | `HistoricalDataProvider` |
| Status atual | `MARKET_DATA_CERTIFIED_FOR_QUANTITATIVE_RESEARCH` |
| Limitacao atual | Amostra minima, suficiente para smoke test e certificacao da infraestrutura, insuficiente para validacao estatistica |

## Fonte dos Dados Historicos

Fonte recomendada:

- exportacao historica confiavel de candles do WDO;
- origem rastreavel e documentada;
- dados com timestamp, OHLC e volume;
- preferencialmente dados ja consolidados por candle fechado;
- timezone explicito, preferencialmente `America/Sao_Paulo`;
- calendario compatível com B3.

Fontes possiveis para avaliacao futura, sem integracao nesta missao:

- arquivo CSV exportado de plataforma autorizada;
- arquivo Parquet gerado a partir de fonte historica confiavel;
- base historica local previamente auditada;
- fornecedor de dados de mercado, somente por missao futura aprovada.

Qualquer fonte externa futura devera entrar por adapter/provider autorizado,
sem acesso direto por Replay, Research Lab, Dashboard, estrategias ou Domain.

## Periodo Minimo Recomendado

Periodo minimo para validacao quantitativa inicial:

- pelo menos 12 meses completos de candles de WDO;
- preferencialmente 24 meses para capturar mais regimes de mercado;
- idealmente 36 meses ou mais para validacoes robustas.

Janela minima por tipo de avaliacao:

| Uso | Periodo minimo recomendado |
| --- | --- |
| Smoke test de infraestrutura | 1 dia ou dataset minimo controlado |
| Replay funcional | 5 a 20 pregoes |
| Pesquisa exploratoria | 3 a 6 meses |
| Validacao estatistica inicial | 12 meses |
| Walk Forward | 18 a 24 meses |
| Monte Carlo e Stress Testing | 24 meses ou mais |
| Portfolio Evaluation | 24 a 36 meses |

## Granularidade

Granularidade principal recomendada:

- `1m` para WDO intraday.

Granularidades derivadas futuras:

- `5m`;
- `15m`;
- `30m`;
- `1h`;
- `1d`.

Regras:

- a granularidade original deve ser preservada;
- qualquer agregacao futura deve ser rastreavel;
- datasets derivados devem ter `dataset_id`, versao e metadados proprios;
- agregacoes nao devem sobrescrever o dataset bruto original.

## Formato Esperado

Formato inicial recomendado:

```csv
timestamp,open,high,low,close,volume
2025-01-01 09:00,100.0,102.0,99.5,101.0,1000
```

Campos obrigatorios:

- `timestamp`;
- `open`;
- `high`;
- `low`;
- `close`;
- `volume`.

Metadados obrigatorios:

- `dataset_id`;
- `symbol`;
- `timeframe`;
- `source`;
- `exchange`;
- `timezone`;
- `first_timestamp`;
- `last_timestamp`;
- `candle_count`;
- `format`;
- `version`;
- `file_path`;
- `description`;
- `tags`.

Formato fisico aceito nesta fase:

- CSV normalizado.

Formatos futuros possiveis, somente por missao aprovada:

- Parquet;
- DuckDB;
- PostgreSQL;
- outros adapters autorizados.

## Validacoes Obrigatorias

Todo dataset expandido deve passar por:

- existencia do arquivo fisico;
- leitura pelo adapter autorizado;
- schema obrigatorio presente;
- timestamps validos;
- timestamps ordenados;
- ausencia de duplicidades;
- volume nao negativo;
- OHLC consistente;
- candle completo;
- timezone documentado;
- periodo coerente com metadados;
- contagem de candles coerente entre arquivo, metadados e provider;
- readiness para Replay;
- readiness para Research;
- auditoria arquitetural;
- testes automatizados.

Validacoes minimas de OHLC:

- `high >= open`;
- `high >= close`;
- `high >= low`;
- `low <= open`;
- `low <= close`;
- `volume >= 0`.

## Criterios Minimos de Amostra

Para liberar uso em pesquisa estatistica inicial:

- minimo de 12 meses completos;
- minimo de 200 pregoes;
- minimo de 50.000 candles de 1 minuto, salvo justificativa do CTO;
- cobertura de diferentes regimes de mercado;
- gaps identificados e documentados;
- duplicidades removidas ou justificadas;
- qualidade geral aprovada pelo Data Lab;
- status `READY_FOR_REPLAY_AND_RESEARCH`.

Para liberar validacao cientifica mais forte:

- 24 meses ou mais;
- campanhas separadas por periodo;
- amostra suficiente para Walk Forward;
- amostra suficiente para Monte Carlo;
- cenarios de stress documentados;
- reproducibilidade por fingerprint ou metadados equivalentes.

## Riscos de Dados Incompletos

Riscos principais:

- falsa robustez estatistica;
- vies de selecao de periodo;
- ausencia de regimes relevantes;
- gaps intraday nao detectados;
- duplicidades gerando inflacao de sinais;
- timestamps em timezone incorreto;
- volume ausente ou inconsistente;
- dados com candle parcial tratado como candle fechado;
- mudancas de contrato, vencimento ou rolagem nao documentadas;
- conclusoes indevidas sobre estrategia.

Mitigacoes:

- documentar origem e periodo;
- manter metadados completos;
- validar contagem e ordenacao;
- medir gaps e duplicidades;
- separar datasets por versao;
- preservar dataset bruto;
- registrar dataset derivado separadamente;
- impedir aprovacao estatistica quando a amostra for insuficiente.

## Criterios Para Liberar Validacao Estatistica

Uma validacao estatistica so pode ser liberada quando:

- dataset estiver importado e catalogado;
- dataset estiver carregando via `HistoricalDataProvider`;
- Replay estiver `READY` com o dataset expandido;
- Research Lab executar com o dataset expandido;
- Data Quality aprovar integridade minima;
- Validation Suite nao estiver bloqueada por amostra insuficiente;
- periodo minimo recomendado estiver atendido;
- quantidade minima de candles estiver atendida;
- gaps e duplicidades estiverem documentados;
- Quality Gate estiver `PASSED`;
- Architecture Audit estiver `OK`;
- operacao real permanecer explicitamente proibida.

Estados recomendados:

- `NOT_VALIDATED`;
- `READY_FOR_REPLAY`;
- `READY_FOR_RESEARCH`;
- `READY_FOR_REPLAY_AND_RESEARCH`;
- `STATISTICAL_VALIDATION_ALLOWED`;
- `STATISTICAL_VALIDATION_BLOCKED`.

## Plano de Importacao Incremental

### Fase 1 - Coleta Inicial

- selecionar fonte historica confiavel;
- exportar WDO em candles de 1 minuto;
- documentar origem, periodo, timezone e formato;
- armazenar arquivo bruto fora do fluxo operacional.

### Fase 2 - Normalizacao

- converter para schema oficial;
- padronizar nomes de colunas;
- padronizar timestamp;
- garantir OHLCV numerico;
- preservar arquivo normalizado em estrutura de dataset versionada.

### Fase 3 - Importacao Controlada

- importar primeiro 1 dia;
- depois 1 semana;
- depois 1 mes;
- depois 3 meses;
- depois 12 meses;
- registrar metadados a cada etapa.

### Fase 4 - Validacao de Integridade

- executar validadores de candle;
- medir duplicidades;
- medir gaps;
- comparar contagem esperada e observada;
- registrar score de qualidade;
- bloquear datasets inconsistentes.

### Fase 5 - Ativacao em Replay

- carregar via `HistoricalDataProvider`;
- executar smoke test de Replay;
- confirmar status `READY`;
- confirmar quantidade de candles carregados;
- registrar primeiro e ultimo candle.

### Fase 6 - Ativacao em Research

- executar Research Lab com dataset expandido;
- registrar total de candles;
- registrar resultado do Research Runner;
- registrar Validation Suite;
- registrar Benchmark;
- registrar Portfolio Evaluation.

### Fase 7 - Liberacao Para Validacao Estatistica

- revisar criterios minimos de amostra;
- revisar qualidade do dataset;
- revisar cobertura temporal;
- revisar gaps e duplicidades;
- executar Quality Gate;
- registrar decisao institucional.

## Estrutura Recomendada de Datasets

```text
historical_data/
  datasets/
    WDO/
      1m/
        2025/
          data.csv
          metadata.json
        2024/
          data.csv
          metadata.json
        2023/
          data.csv
          metadata.json
```

Cada periodo deve ser independente, versionado e rastreavel.

## Criterio de Conclusao da Expansao

A expansao inicial sera considerada concluida quando:

- existir pelo menos 12 meses de WDO 1m catalogados;
- os arquivos estiverem normalizados;
- os metadados estiverem completos;
- `HistoricalDataProvider` carregar o dataset expandido;
- Replay executar com dados reais expandidos;
- Research Lab executar com dados reais expandidos;
- Validation Suite deixar de bloquear por amostra insuficiente;
- Quality Gate estiver `PASSED`;
- Architecture Audit estiver `OK`;
- relatorio institucional de expansao for produzido.

## Proibicoes

- Nao conectar corretora.
- Nao enviar ordens.
- Nao criar `LiveDataProvider`.
- Nao alterar Research Lab nesta etapa.
- Nao alterar provider nesta etapa.
- Nao validar estrategia ainda.
- Nao tratar dataset incompleto como evidencia estatistica.
- Nao usar dados demonstrativos para substituir dados reais.

## Decisao Institucional

Status: `HISTORICAL_DATA_EXPANSION_PLAN_DEFINED`.

O TraderIA_WDO deve ampliar o dataset historico real do WDO de forma
incremental, auditavel e rastreavel. A infraestrutura ja esta certificada para
pesquisa quantitativa com dados reais, mas a validacao estatistica de
estrategias permanece bloqueada ate que a amostra historica seja suficiente.

Operacao real permanece proibida.
