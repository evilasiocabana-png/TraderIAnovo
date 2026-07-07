# PETR4 Dataset Plan

## 1. Objetivo

Definir oficialmente como o TraderIA_WDO devera obter, validar, organizar,
versionar e rastrear o primeiro dataset historico diario de `PETR4`.

Esta missao e exclusivamente documental. Nenhum dataset foi baixado, nenhum
provider foi criado, nenhuma arquitetura foi alterada e nenhuma pesquisa foi
executada.

Status:

`PETR4_DAILY_DATASET_PLAN_DEFINED`

## 2. Motivacao

O TraderIA ja possui infraestrutura certificada para pesquisa quantitativa com
dados historicos reais, mas o dataset institucional atual de WDO 1m possui
amostra minima. A trilha PETR4 diaria permite iniciar uma frente gratuita e
exploratoria de pesquisa com acoes brasileiras, reduzindo friccao de acesso a
dados e preservando a governanca do projeto.

Este plano nao substitui o WDO. Ele cria um padrao paralelo para datasets
diarios de acoes, com separacao explicita entre:

- `WDO_INTRADAY_RESEARCH`
- `EQUITY_DAILY_RESEARCH`
- `FREE_DATA_EXPLORATORY`
- `LICENSED_DATA_INSTITUTIONAL`

## 3. Fonte Principal

Fonte primaria planejada:

`YAHOO_FINANCE_PETR4_SA_DAILY_CSV`

Ativo esperado:

`PETR4.SA`

Justificativa:

- disponibiliza historico diario para acoes brasileiras via sufixo `.SA`;
- documenta download manual de historico em CSV;
- normalmente fornece OHLC, adjusted close e volume;
- e adequado para bootstrap gratuito e exploratorio;
- permite criacao de um arquivo bruto auditavel antes da normalizacao.

Regras:

- o download devera ser manual ou por procedimento aprovado em missao futura;
- o arquivo bruto deve ser preservado sem sobrescrita;
- a data do download deve ser registrada;
- a URL e o periodo selecionado devem ser documentados;
- o uso deve permanecer restrito a pesquisa exploratoria;
- termos de uso e licenca devem ser registrados antes de qualquer uso amplo.

## 4. Fonte Secundaria

Fonte secundaria planejada:

`INVESTING_PETR4_DAILY`

Uso:

- conferencia manual de precos;
- validacao pontual de divergencias;
- contingencia visual para OHLCV diario;
- apoio em auditoria de valores extremos.

Fonte CSV-friendly de contingencia:

`STOOQ_DAILY_CSV`

Uso:

- alternativa futura se PETR4 estiver disponivel com simbolo confirmado;
- referencia para fluxo baseado em arquivo CSV simples;
- contingencia caso Yahoo Finance fique indisponivel ou instavel.

Regra:

Nenhuma fonte secundaria deve sobrescrever a fonte primaria sem nova decisao
institucional do CTO.

## 5. Estrutura de Diretorios

Estrutura institucional planejada:

```text
historical_data/
  datasets/
    B3/
      PETR4/
        1d/
          data.csv
          metadata.json
          checksum.sha256
```

Estrutura recomendada para preservacao de bruto e versoes futuras:

```text
historical_data/
  datasets/
    B3/
      PETR4/
        1d/
          raw/
            yahoo_finance_petr4_sa_YYYYMMDD.csv
          versions/
            vYYYYMMDD/
              data.csv
              metadata.json
              checksum.sha256
          data.csv
          metadata.json
          checksum.sha256
```

Regra:

A estrutura minima exigida para a primeira missao de dataset e:

- `data.csv`
- `metadata.json`
- `checksum.sha256`

A pasta `raw/` e `versions/` deve ser usada quando a missao futura permitir
baixar e organizar arquivos fisicos.

## 6. Estrutura do CSV

Schema obrigatorio do CSV normalizado:

```csv
date,open,high,low,close,adjusted_close,volume
2025-01-02,36.10,36.80,35.90,36.50,34.92,50000000
```

Campos:

| Campo | Obrigatorio | Descricao |
| --- | --- | --- |
| `date` | Sim | Data do pregao no formato `YYYY-MM-DD`. |
| `open` | Sim | Preco de abertura. |
| `high` | Sim | Maxima do dia. |
| `low` | Sim | Minima do dia. |
| `close` | Sim | Fechamento nao ajustado quando disponivel. |
| `adjusted_close` | Condicional | Fechamento ajustado, quando fornecido pela fonte. |
| `volume` | Sim | Volume negociado. |

Regras de normalizacao:

- nomes de colunas em minusculo;
- separador CSV por virgula;
- ponto como separador decimal;
- sem separador de milhar;
- datas em `YYYY-MM-DD`;
- ordenacao cronologica crescente;
- uma linha por pregao;
- nenhum indice numerico extra;
- nenhuma coluna operacional do TraderIA no arquivo normalizado.

Caso `adjusted_close` nao exista:

- registrar a ausencia no `metadata.json`;
- preencher `adjusted_close` com `null` somente se o adapter futuro suportar;
- alternativamente preencher com o mesmo valor de `close`, desde que o campo
  `adjusted_close_policy` registre `MIRRORED_FROM_CLOSE`;
- nunca inferir ajuste sem fonte explicita.

## 7. Metadata

Arquivo previsto:

`metadata.json`

Campos minimos:

```json
{
  "dataset_id": "b3_petr4_1d_vYYYYMMDD",
  "asset": "PETR4",
  "symbol": "PETR4.SA",
  "exchange": "B3",
  "asset_class": "STOCKS",
  "timeframe": "1d",
  "source": "YAHOO_FINANCE_PETR4_SA_DAILY_CSV",
  "secondary_source": "INVESTING_PETR4_DAILY",
  "first_date": "YYYY-MM-DD",
  "last_date": "YYYY-MM-DD",
  "record_count": 0,
  "imported_at": "YYYY-MM-DDTHH:MM:SS",
  "version": "vYYYYMMDD",
  "dataset_hash": "sha256",
  "timezone": "America/Sao_Paulo",
  "date_format": "YYYY-MM-DD",
  "schema_version": "daily_equity_ohlcv_v1",
  "adjusted_close_available": true,
  "adjusted_close_policy": "SOURCE_PROVIDED",
  "license_notes": "free exploratory research only",
  "quality_status": "NOT_VALIDATED",
  "readiness_status": "NOT_READY",
  "metadata_version": "1.0"
}
```

Regras:

- `dataset_hash` deve ser o hash SHA-256 do `data.csv`;
- `record_count` deve bater com a quantidade de linhas de dados do CSV;
- `first_date` e `last_date` devem bater com o primeiro e ultimo registro;
- `source` deve indicar a fonte efetiva do arquivo normalizado;
- qualquer alteracao no arquivo deve gerar nova versao.

## 8. Criterios de Qualidade

Quantidade minima recomendada:

- minimo exploratorio: 252 candles diarios, aproximadamente 1 ano de pregoes;
- recomendado para pesquisa inicial: 756 candles, aproximadamente 3 anos;
- recomendado para validacao mais robusta: 1.260 candles ou mais,
  aproximadamente 5 anos;
- ideal para regimes variados: 2.520 candles ou mais, aproximadamente 10 anos.

Qualidade minima:

- schema completo;
- datas validas;
- ordenacao cronologica crescente;
- ausencia de duplicidades por `date`;
- OHLC consistente;
- volume nao negativo;
- pelo menos 95% dos pregoes esperados no periodo escolhido, salvo
  justificativa documentada;
- `adjusted_close` presente ou politica documentada;
- hash calculado;
- metadados completos;
- origem registrada;
- timezone oficial registrado como `America/Sao_Paulo`.

Validacoes OHLC:

- `high >= open`;
- `high >= close`;
- `high >= low`;
- `low <= open`;
- `low <= close`;
- `volume >= 0`.

## 9. Criterios de Rejeicao

O dataset deve ser rejeitado se:

- fonte nao for identificavel;
- arquivo nao possuir `date`, `open`, `high`, `low`, `close` e `volume`;
- `adjusted_close` estiver ausente e nao houver politica documentada;
- houver datas invalidas;
- houver registros duplicados sem tratamento;
- houver ordem cronologica quebrada;
- houver valores OHLC impossiveis;
- houver volume negativo;
- houver lacunas extensas sem justificativa;
- periodo coberto for inferior a 252 candles para uso exploratorio;
- `metadata.json` estiver incompleto;
- `checksum.sha256` nao bater com `data.csv`;
- licenca/termos forem incompatíveis com armazenamento local para pesquisa;
- houver tentativa de usar o dataset para operacao real.

## 10. Processo de Validacao

Fluxo institucional:

```text
Fonte
  |
  v
Download
  |
  v
Validacao
  |
  v
HistoricalDataProvider
  |
  v
Replay
  |
  v
Research Lab
  |
  v
Validation Suite
  |
  v
Benchmark
  |
  v
Portfolio
```

Etapas:

1. registrar fonte, URL, periodo e data de download;
2. preservar arquivo bruto;
3. normalizar para schema oficial;
4. calcular `checksum.sha256`;
5. criar `metadata.json`;
6. validar schema;
7. validar datas;
8. validar OHLCV;
9. validar duplicidades;
10. validar lacunas;
11. validar contagem entre CSV e metadados;
12. validar hash;
13. classificar qualidade;
14. liberar apenas quando `quality_status` e `readiness_status` permitirem.

Estados recomendados:

- `NOT_VALIDATED`
- `VALIDATION_FAILED`
- `VALIDATED_WITH_WARNINGS`
- `VALIDATED`
- `READY_FOR_REPLAY`
- `READY_FOR_RESEARCH`
- `READY_FOR_REPLAY_AND_RESEARCH`

## 11. Processo de Versionamento

Convencao de versao:

`vYYYYMMDD`

Convencao de dataset:

`b3_petr4_1d_vYYYYMMDD`

Convencao de arquivos brutos:

`yahoo_finance_petr4_sa_YYYYMMDD.csv`

Regras:

- toda atualizacao gera nova versao;
- versoes anteriores devem ser preservadas quando possivel;
- `data.csv` pode apontar para a versao ativa;
- `metadata.json` deve declarar a versao ativa;
- `checksum.sha256` deve ser recalculado a cada versao;
- mudancas de fonte exigem nova versao e registro em `source`;
- mudancas de politica de `adjusted_close` exigem nova versao;
- datasets derivados nao devem sobrescrever o dataset bruto.

## 12. Processo de Atualizacao

Politica de atualizacao:

- bootstrap inicial: uma carga historica completa;
- atualizacao manual mensal durante fase exploratoria;
- atualizacao semanal somente se aprovada por missao futura;
- atualizacao diaria nao autorizada nesta fase.

Fluxo de atualizacao:

1. baixar novo arquivo bruto;
2. preservar arquivo bruto antigo;
3. normalizar nova versao;
4. comparar periodo e contagem com a versao anterior;
5. validar integridade;
6. recalcular hash;
7. atualizar metadados;
8. promover nova versao somente se aprovada;
9. manter registro de diferencas.

Politica para dados ausentes:

- nao preencher datas ausentes automaticamente;
- registrar gaps detectados;
- diferenciar feriados/pregoes inexistentes de falhas de dado;
- usar calendario B3 apenas quando houver componente aprovado;
- bloquear validacao estatistica se gaps relevantes nao forem explicados.

Tratamento de duplicidades:

- duplicidade por `date` deve bloquear o dataset bruto;
- remocao de duplicidade so pode ocorrer no arquivo normalizado;
- toda remocao deve ser registrada em metadados ou relatorio de importacao;
- se houver divergencia entre linhas duplicadas, o dataset deve ser rejeitado
  ate revisao manual.

## 13. Riscos

- licenca de fonte gratuita nao permitir armazenamento amplo;
- Yahoo Finance mudar formato ou disponibilidade;
- Investing exigir sessao, cookies ou captcha;
- Stooq nao disponibilizar PETR4 no simbolo esperado;
- dados ajustados divergirem entre fontes;
- eventos corporativos alterarem interpretacao de retornos;
- volume divergente por criterio de fonte;
- uso indevido de PETR4 diario como substituto de WDO 1m;
- falsa confianca estatistica por misturar horizontes diferentes;
- pesquisa diaria ser confundida com validacao operacional.

## 14. Limitacoes

PETR4 diario nao valida:

- estrategias intraday de WDO;
- microestrutura;
- slippage intraday;
- book de ofertas;
- times and trades;
- volatilidade minuto a minuto;
- comportamento de futuros;
- execucao real.

PETR4 diario pode apoiar:

- pesquisa exploratoria de acoes;
- hipoteses Swing e Position;
- teste de pipeline com CSV diario;
- prototipagem de Alpha Factory;
- comparacao de fontes gratuitas;
- validacao institucional de processo de dataset.

## 15. Proximos Passos

Missao recomendada:

`MISSAO 210 - PETR4_DAILY_DATASET_BOOTSTRAP.md`

Objetivo sugerido:

- obter manualmente o CSV historico de PETR4.SA;
- preservar arquivo bruto;
- normalizar para schema oficial;
- criar `metadata.json`;
- criar `checksum.sha256`;
- validar integridade;
- executar smoke test controlado via infraestrutura existente;
- manter operacao real proibida.

## Decisoes Arquiteturais

- PETR4 diario sera uma trilha exploratoria separada de WDO 1m.
- Fonte primaria: Yahoo Finance.
- Fonte secundaria: Investing.com.
- Contingencia CSV-friendly: Stooq.
- Estrutura institucional: `historical_data/datasets/B3/PETR4/1d/`.
- CSV normalizado deve seguir `daily_equity_ohlcv_v1`.
- Toda fonte fisica futura deve entrar por fluxo autorizado de dados
  historicos, sem acesso direto por Replay, Research Lab ou Dashboard.

## Restricoes Preservadas

- Nenhum dataset foi baixado.
- Nenhum dado foi importado.
- Nenhum provider foi criado.
- Replay nao foi alterado.
- Research Lab nao foi alterado.
- Validation Suite nao foi alterada.
- Benchmark nao foi alterado.
- Portfolio nao foi alterado.
- Arquitetura nao foi alterada.
- Contratos nao foram alterados.
- Nenhuma pesquisa foi executada.
- Nenhum backtest foi executado.
- Nenhuma estrategia foi criada.
- Nenhuma corretora foi conectada.
- Nenhuma ordem foi executada.
- Operacao real permanece proibida.

## Status Final

`PETR4_DAILY_DATASET_PLAN_READY_FOR_MISSION_210`
