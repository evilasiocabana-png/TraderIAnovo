# PETR4 Dataset Validation

## 1. Resumo Executivo

Esta validacao avaliou o dataset historico diario da PETR4 obtido a partir do
Yahoo Finance Chart API e preservado como arquivo bruto em:

`historical_data/datasets/B3/PETR4/1d/raw/yahoo_finance_petr4_sa_20160628_20260628_chart.csv`

Resultado final:

`CERTIFIED_WITH_WARNINGS`

O dataset possui schema correto, encoding UTF-8, delimitador CSV por virgula,
ordenacao cronologica crescente, 2.491 candles diarios, `adjusted_close`
presente, ausencia de duplicidades, ausencia de valores nulos e ausencia de
inconsistencias OHLC.

A certificacao plena fica condicionada a uma validacao futura contra calendario
oficial da B3 e revisao dos registros com volume zero.

## 2. Origem do Dataset

| Campo | Valor |
| --- | --- |
| Ativo | `PETR4` |
| Simbolo de origem | `PETR4.SA` |
| Fonte | Yahoo Finance Chart API |
| Arquivo validado | `historical_data/datasets/B3/PETR4/1d/raw/yahoo_finance_petr4_sa_20160628_20260628_chart.csv` |
| Periodo solicitado | `2016-06-28` a `2026-06-28` |
| Primeiro candle retornado | `2016-06-28` |
| Ultimo candle retornado | `2026-06-26` |
| Timeframe | `1d` |
| Classe de ativo | Acoes brasileiras |
| Exchange institucional | B3 |
| Uso autorizado nesta fase | Pesquisa quantitativa exploratoria |

Observacao: o endpoint CSV direto do Yahoo Finance retornou `401 unauthorized`.
O arquivo validado foi gerado a partir do endpoint publico de chart do proprio
Yahoo, preservando os campos OHLCV e `adjusted_close`.

## 3. Estrutura do CSV

Schema esperado:

```csv
date,open,high,low,close,adjusted_close,volume
```

Schema encontrado:

```csv
date,open,high,low,close,adjusted_close,volume
```

| Verificacao | Resultado |
| --- | --- |
| Encoding | `UTF-8` |
| Delimitador | `,` |
| Header presente | Sim |
| Schema obrigatorio | Aprovado |
| Colunas extras | Nenhuma |
| Datas no formato `YYYY-MM-DD` | Aprovado |
| `adjusted_close` presente | Sim |

## 4. Estatisticas

| Metrica | Valor |
| --- | --- |
| Total de candles | 2.491 |
| Pregoes unicos | 2.491 |
| Periodo coberto | `2016-06-28` a `2026-06-26` |
| Primeiro candle | `2016-06-28, 9.100000381469727, 9.279999732971191, 9.069999694824219, 9.199999809265137, 2.377040386199951, 45291700` |
| Ultimo candle | `2026-06-26, 38.06999969482422, 38.25, 37.93000030517578, 38.060001373291016, 38.060001373291016, 23383000` |
| Media de volume | 57.280.646,49 |
| Maior volume | 490.230.400 |
| Menor volume | 0 |
| Maxima historica | 50,689998626708984 |
| Minima historica | 8,949999809265137 |
| Registros validos | 2.491 |
| Registros invalidos | 0 |
| Percentual valido | 100,0% |
| Percentual invalido | 0,0% |
| SHA-256 do CSV | `a3fd3442f26bc0716463425c9f654c7561907d27e5413c1c762a70383dcfa21e` |

### Distribuicao Anual

| Ano | Candles |
| --- | ---: |
| 2016 | 129 |
| 2017 | 254 |
| 2018 | 246 |
| 2019 | 248 |
| 2020 | 248 |
| 2021 | 247 |
| 2022 | 250 |
| 2023 | 248 |
| 2024 | 251 |
| 2025 | 250 |
| 2026 | 120 |

## 5. Validacoes Executadas

| Validacao | Resultado |
| --- | --- |
| Arquivo existe | Aprovado |
| Leitura UTF-8 | Aprovado |
| Delimitador CSV por virgula | Aprovado |
| Schema completo | Aprovado |
| Tipos numericos | Aprovado |
| Datas validas | Aprovado |
| Ordem cronologica crescente | Aprovado |
| Datas duplicadas | 0 |
| Valores nulos | 0 |
| Precos negativos | 0 |
| Volume negativo | 0 |
| `open <= high` | Aprovado |
| `low <= close` | Aprovado |
| `high >= close` | Aprovado |
| `high >= open` | Aprovado |
| `low <= open` | Aprovado |
| `low <= close` | Aprovado |
| `adjusted_close` presente | Aprovado |
| Registros em finais de semana | 0 |
| Quebras cronologicas | 0 |
| Gaps de calendario | 566 |
| Gaps de dias uteis | 96 |
| Gaps anormais com 3 ou mais dias uteis ausentes | 0 |
| Registros com volume zero | 10 |

## 6. Problemas Encontrados

### Estrutura Local do Dataset

Durante a execucao dos testes relacionados ao `HistoricalDataProvider`, a suite
identificou que a nova pasta `historical_data/datasets/B3/PETR4/1d/` precisava
conter `metadata.json` para respeitar a estrutura documental exigida para
datasets locais.

Acao corretiva documental executada:

- criado `historical_data/datasets/B3/PETR4/1d/metadata.json`;
- criado `historical_data/datasets/B3/PETR4/1d/checksum.sha256`;
- o CSV bruto validado nao foi alterado.

### Volume Zero

Foram encontrados 10 registros com volume igual a zero:

| Data | Observacao |
| --- | --- |
| 2017-05-29 | OHLC constante e volume zero |
| 2017-06-15 | OHLC constante e volume zero |
| 2017-09-07 | OHLC constante e volume zero |
| 2017-10-12 | OHLC constante e volume zero |
| 2017-11-02 | OHLC constante e volume zero |
| 2017-11-15 | OHLC constante e volume zero |
| 2017-11-20 | OHLC constante e volume zero |
| 2017-12-25 | OHLC constante e volume zero |
| 2017-12-29 | OHLC constante e volume zero |
| 2018-01-25 | OHLC constante e volume zero |

Esses registros nao violam a regra de volume nao negativo, mas devem ser
tratados como alerta de qualidade. Varias datas parecem ser feriados ou dias
sem negociacao, mas a validacao desta missao nao carregou calendario oficial da
B3.

### Gaps de Dias Uteis

Foram identificados 96 gaps contendo dias uteis entre candles consecutivos. Os
exemplos encontrados incluem datas tipicas de feriados nacionais ou periodos
sem pregao, como `2016-09-07`, `2016-10-12`, `2016-11-02`, `2016-11-15`,
`2017-02-27`, `2017-02-28`, `2017-04-14`, `2017-04-21` e `2018-01-01`.

Nao foram encontrados gaps anormais com 3 ou mais dias uteis ausentes.

Limitacao: a validacao final dos gaps deve ser feita contra calendario oficial
da B3 em missao futura.

## 7. Riscos

- Yahoo Finance e fonte gratuita, nao fonte institucional oficial da B3.
- O endpoint CSV direto exigiu sessao logada; o arquivo validado veio do
  endpoint Chart API.
- Registros com volume zero podem representar feriados, suspensoes ou
  inconsistencias da fonte.
- Gaps de dias uteis precisam ser reconciliados contra calendario oficial B3.
- `adjusted_close` pode refletir metodologia propria do Yahoo.
- Eventos corporativos podem afetar comparacoes historicas.
- O dataset e adequado para pesquisa exploratoria, nao para operacao real.

## 8. Limitacoes

- Nao foi utilizado calendario oficial da B3.
- Nao houve conferencia cruzada com Investing.com ou Stooq.
- Nao houve validacao de eventos corporativos.
- Nao houve validacao juridica dos termos de armazenamento da fonte gratuita.
- Nao houve execucao de Replay.
- Nao houve execucao de Research Lab.
- Nao houve backtest.
- Nao houve alteracao no `HistoricalDataProvider`.

## 9. Classificacao Final

`CERTIFIED_WITH_WARNINGS`

Justificativa:

- aprovado em schema, encoding, tipos, datas, ordenacao, duplicidades,
  nulidade, valores negativos, OHLC e `adjusted_close`;
- possui amostra suficiente para pesquisa exploratoria diaria;
- nao possui erros estruturais bloqueantes;
- exige warning por volume zero e por ausencia de calendario oficial B3 para
  validar gaps de pregao.

## 10. Recomendacoes

1. Manter este arquivo como dataset bruto validado.
2. Na Missao 212, verificar compatibilidade com `HistoricalDataProvider` sem
   alterar codigo.
3. Antes de promover para `data.csv` institucional, criar `metadata.json` e
   `checksum.sha256`.
4. Validar gaps contra calendario oficial B3 quando houver componente ou fonte
   aprovada.
5. Marcar registros de volume zero como warning em qualquer relatorio de
   qualidade futuro.
6. Nao utilizar este dataset para operacao real.
7. Nao misturar resultados de PETR4 diario com WDO 1m sem contexto
   institucional explicito.

## Validacoes de Projeto

Comandos obrigatorios executados:

```bash
python scripts\architecture_audit.py
```

Resultado: `OK`.

```bash
python -m unittest tests.test_architecture_manifest tests.test_architecture_baseline tests.test_dependency_rules
```

Resultado: `30 OK`.

Testes relacionados ao `HistoricalDataProvider` executados:

```bash
python -m unittest tests.test_historical_data_provider_contract tests.test_market_data_provider tests.test_historical_data_source_compatibility tests.test_historical_dataset_structure tests.test_historical_importer tests.test_replay_market_data_provider tests.test_research_market_data_provider tests.test_provider_architecture
```

Primeira execucao: `63 tests`, `1 failure`, por ausencia de `metadata.json` no
novo diretorio local `historical_data/datasets/B3/PETR4/1d/`.

Apos criacao documental de `metadata.json` e `checksum.sha256`, a suite foi
executada novamente.

Resultado final: `63 OK`.

## Confirmacao de Escopo

- O dataset nao foi alterado.
- O CSV nao foi modificado.
- Nenhum provider foi criado.
- `HistoricalDataProvider` nao foi alterado.
- Replay nao foi alterado.
- Research Lab nao foi alterado.
- Validation Suite nao foi alterada.
- Benchmark nao foi alterado.
- Portfolio nao foi alterado.
- EventBus nao foi alterado.
- Arquitetura nao foi alterada.
- Nenhuma estrategia foi criada.
- Nenhum Replay foi executado.
- Nenhuma pesquisa foi executada.
- Nenhum backtest foi executado.
- Nenhum dado artificial foi criado.
- Operacao real permanece proibida.
