# BETA002 Lab vs Runtime Audit

Data: 2026-07-13

## Objetivo

Comparar o BETA002 escolhido/testado pelo Research Lab com o BETA002 que chega
na execucao, no Position Manager e no Relatorio.

Motivacao: o usuario observou sequencia recente de losses e solicitou auditoria
para entender se a saida BETA002 executada corresponde ao plano vencedor do Lab.

## Resumo Executivo

Ha divergencia entre o BETA002 do Lab e o BETA002 executado em parte do historico.

O Lab atualmente seleciona:

- `beta_id = BETA002`
- `beta_mode = ADAPTIVE_FULL_EXIT`
- `beta_version = M1_EMA14_MOMENTUM_VOLATILITY`

Mas varias ordens recentes foram gravadas como:

- `beta_id = BETA002`
- `beta_mode = PROTECT_ONLY`
- `exit_policy = BREAK_EVEN` ou `ATR_TRAILING_STOP`

Isso significa que parte relevante do historico recente chamado de BETA002 nao
representa fielmente o BETA002 adaptativo aprovado pelo Lab.

## Evidencias Coletadas

### Snapshot do Lab

Arquivo analisado:

```text
.traderia/mt5_research_snapshot.json
```

Resumo:

- `scenario_ranking`: 33.934 cenarios
- `candles_loaded`: 20.000
- BETA001: 16.987 cenarios, 7.525 aprovados
- BETA002: 16.947 cenarios, 7.989 aprovados

O Lab selecionou BETA002 em `best_scenarios_by_market` para os principais pares,
com `beta_mode = ADAPTIVE_FULL_EXIT`.

Exemplos observados:

| Par | TF | Alpha | Modelo | Beta | Modo | Plano inicial |
| --- | --- | --- | --- | --- | --- | --- |
| AUDUSD | H1 | ALPHA001 | TREND_MOMENTUM | BETA002 | ADAPTIVE_FULL_EXIT | ATR_TRAILING_STOP |
| EURJPY | M1 | ALPHA009 | ATR_VOLATILITY_REGIME | BETA002 | ADAPTIVE_FULL_EXIT | BREAK_EVEN |
| EURUSD | H1 | ALPHA001 | TREND_MOMENTUM | BETA002 | ADAPTIVE_FULL_EXIT | ATR_TRAILING_STOP |
| GBPUSD | M1 | ALPHA006 | ADX_TREND_STRENGTH | BETA002 | ADAPTIVE_FULL_EXIT | BREAK_EVEN |
| NZDUSD | M1 | ALPHA006 | ADX_TREND_STRENGTH | BETA002 | ADAPTIVE_FULL_EXIT | BREAK_EVEN |
| USDCAD | M1 | ALPHA006 | ADX_TREND_STRENGTH | BETA002 | ADAPTIVE_FULL_EXIT | BREAK_EVEN |
| USDCHF | M1 | ALPHA006 | ADX_TREND_STRENGTH | BETA002 | ADAPTIVE_FULL_EXIT | BREAK_EVEN |
| USDJPY | M1 | ALPHA009 | ATR_VOLATILITY_REGIME | BETA002 | ADAPTIVE_FULL_EXIT | BREAK_EVEN |

### Ordens Gravadas

Arquivo analisado:

```text
.traderia/mt5_demo_execution.jsonl
```

Foram encontrados registros recentes aceitos com:

```text
beta_id = BETA002
beta_mode = PROTECT_ONLY
exit_policy = BREAK_EVEN
```

Exemplo de ordem recente:

```text
USDCAD SELL
beta_id: BETA002
beta_version: M1_EMA14_MOMENTUM_VOLATILITY
beta_mode: PROTECT_ONLY
exit_policy: BREAK_EVEN
```

Isso diverge do Lab, que para BETA002 estava selecionando
`ADAPTIVE_FULL_EXIT`.

## Causa Tecnica Encontrada

Arquivo:

```text
research/mt5_research_trade_plan.py
```

No `MT5ResearchTradePlanInput`, existe:

```text
beta_id
beta_version
```

Mas nao existe campo `beta_mode`.

No `MT5ResearchTradePlanEngine.build_plan()`, o retorno do plano valido fixa:

```text
beta_mode="PROTECT_ONLY"
```

No `_empty_plan()`, tambem fixa:

```text
beta_mode="PROTECT_ONLY"
```

Impacto:

Mesmo quando o Lab escolhe `BETA002 / ADAPTIVE_FULL_EXIT`, o Trade Plan pode
materializar a operacao como `BETA002 / PROTECT_ONLY`.

Esse e o principal ponto de divergencia entre Lab e execucao.

## Resultado Historico Observado

No relatorio atual, o BETA002 aparece com desempenho ruim quando agrupado sem
separar corretamente o modo:

```text
BETA002: 119 trades fechados
Resultado aproximado: -107.84
Vitorias: 29
Perdas: 84
```

Ao separar por modo/plano:

| Grupo | Trades | Resultado aprox. | Observacao |
| --- | ---: | ---: | --- |
| BETA002 / PROTECT_ONLY / BREAK_EVEN | 48 | -71.33 | maior foco de perda |
| BETA002 / PROTECT_ONLY / ATR_TRAILING_STOP | 10 | -16.40 | perdas concentradas em EURUSD |
| BETA002 / ADAPTIVE_FULL_EXIT / DYNAMIC_POSITION_MANAGER | 27 | +73.97 | nao e o grupo que explica a sequencia recente de loss |

Conclusao: o loss recente esta mais associado ao BETA002 materializado como
`PROTECT_ONLY` com saidas legadas do que ao BETA002 adaptativo puro.

## Concentração Dos Losses

Por par, dentro do BETA002:

| Par | Resultado aprox. | Observacao |
| --- | ---: | --- |
| USDCHF | -73.22 | maior foco negativo |
| GBPUSD | -37.70 | 9 perdas em 9 trades analisados |
| EURUSD | -16.40 | concentrado em ATR_TRAILING_STOP |
| NZDUSD | -11.80 | negativo |
| USDCAD | -10.83 | negativo |
| USDJPY | +143.31 | positivo, compensa parte dos losses |

Por setup de entrada:

| Setup entrada | Resultado aprox. | Observacao |
| --- | ---: | --- |
| ADX_TREND_STRENGTH | -128.19 | principal foco negativo |
| TREND_MOMENTUM | -16.40 | negativo |
| MACD_MOMENTUM_SHIFT | +80.43 | positivo |
| ATR_VOLATILITY_REGIME | +16.87 | positivo |

Isso sugere que a combinacao `ADX_TREND_STRENGTH + BETA002 materializado como
PROTECT_ONLY/BREAK_EVEN` merece bloqueio ou revisao antes de nova execucao.

## Problema No Relatorio

O relatorio cruza trades fechados com o `position_manager_current.json` por
ticket e, se nao acha ticket, cai para chave por simbolo:

```text
symbol:EURUSD
symbol:GBPUSD
...
```

Risco:

Um trade fechado pode receber no historico uma mensagem atual do Position
Manager, como:

```text
POSITION_ABSENT
TRADE_PLAN_ABSENT
STOP_MAINTAINED
```

Isso pode nao ser o motivo real do fechamento daquele trade.

Conclusao: o relatorio pode estar atribuindo estado atual ao passado.

## Diferenca Conceitual Lab vs Runtime

O Lab nao simula o BETA002 real candle a candle.

No ranking, o Lab usa uma funcao de ajuste estatistico:

```text
_exit_adjusted_scenario_return()
```

Esse calculo aplica fatores de captura/perda por `stop_management` e bonus para
`BETA002`, mas nao reproduz integralmente:

- EMA14 em candle fechado;
- momentum14;
- ATR relativo;
- estrutura;
- persistencia;
- confirmacoes;
- prioridade de PROTECT antes de FULL_EXIT;
- bloqueios por dados ausentes;
- estado real da posicao no MT5.

Portanto, o Lab chama BETA002 de vencedor por aproximacao estatistica, nao por
backtest fiel do motor runtime.

## Riscos Atuais

1. Lab aprova `ADAPTIVE_FULL_EXIT`, mas Trade Plan grava `PROTECT_ONLY`.
2. Historico mistura BETA002 adaptativo com BETA002 legado/protetivo.
3. Relatorio atribui estado atual do Position Manager a trades fechados.
4. Loss recente fica concentrado em um modo que nao corresponde ao modo vencedor
   do Lab.
5. Backtest do Lab nao representa exatamente a execucao real do BETA002.

## Recomendacoes

### 1. Corrigir contrato do Trade Plan

Adicionar `beta_mode` ao `MT5ResearchTradePlanInput` e preservar o valor vindo
do Lab.

Regra esperada:

```text
Lab seleciona BETA002 / ADAPTIVE_FULL_EXIT
↓
Trade Plan preserva BETA002 / ADAPTIVE_FULL_EXIT
↓
Robo Demo grava ordem com BETA002 / ADAPTIVE_FULL_EXIT
↓
Position Manager executa conforme modo recebido
```

### 2. Separar no Relatorio

Adicionar/usar campos distintos:

- Beta aprovado pelo Lab;
- Beta enviado na ordem;
- Beta observado pelo Position Manager;
- modo Beta;
- motivo real de fechamento MT5;
- motivo de auditoria atual.

E evitar fallback por simbolo para trades fechados quando nao houver ticket
correspondente do Position Manager.

### 3. Criar backtest fiel do BETA002

O Lab deve ter uma fase especifica que rode o BETA002 real candle a candle,
com a mesma classe/contrato usada no runtime.

### 4. Bloqueio preventivo recomendado

Enquanto a divergencia nao for corrigida, evitar interpretar losses de
`BETA002 / PROTECT_ONLY / BREAK_EVEN` como prova contra
`BETA002 / ADAPTIVE_FULL_EXIT`.

### 5. Revisar ADX_TREND_STRENGTH

O maior foco de perda observado foi:

```text
BETA002 + ADX_TREND_STRENGTH
```

Recomenda-se auditar esse par Alpha/Beta antes de novas mudancas de estrategia.

## Estado Final Da Auditoria

O BETA002 do Lab e o BETA002 executado nao estavam totalmente alinhados.

A causa tecnica mais importante e o `beta_mode` ser perdido/forcado para
`PROTECT_ONLY` durante a materializacao do Trade Plan.

Antes de concluir que BETA002 adaptativo da loss, e necessario corrigir a
rastreabilidade e garantir que o modo testado pelo Lab seja o mesmo modo enviado
na ordem e auditado no relatorio.

## Decisao Operacional 2026-07-13

Apos auditoria dos trades fechados, o BETA002 em modo `FULL_EXIT` mostrou perda
recente concentrada em fechamentos antecipados pequenos, sem deixar as operacoes
alcancarem nem o TP cheio nem o SL cheio.

Regra operacional aplicada:

- BETA002 continua lendo M1 por EMA14, momentum e volatilidade.
- BETA002 continua podendo proteger a posicao com movimento de SL.
- `allow_full_exit = false`.
- A protecao de SL so pode iniciar quando a posicao tiver pelo menos `1.0R`.
- Antes de `1.0R`, o BETA002 deve preservar o plano original do Lab.

Objetivo:

- deixar o trade respirar;
- preservar o alvo original;
- reduzir saidas ansiosas;
- manter o Position Manager como camada de protecao, nao como camada de
  fechamento antecipado nesta fase.
