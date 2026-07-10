# Post Rollover Daily Open

## Objetivo

O evento `POST_ROLLOVER_DAILY_OPEN` representa a primeira oportunidade candidata
do novo dia operacional, depois da janela de protecao do rollover do servidor MT5.

Ele nao e uma Alpha fixa e nao substitui as Alphas existentes. E um evento
prioritario avaliado pelo Research Lab antes do fluxo normal.

## Separacao de responsabilidades

### RolloverGuard

Responsavel por bloquear operacao durante a janela de risco do rollover.

Fonte principal:

```text
research/forex_time_layer.py
```

O bloqueio usa preferencialmente o horario do servidor MT5, sem horario fixo de
Brasilia.

### PostRolloverAnalyzer

Responsavel por avaliar se, apos o fim da janela de protecao, existe edge
operacional.

Fonte principal:

```text
research/post_rollover_analyzer.py
```

Ele analisa:

- minutos apos rollover;
- spread atual;
- spread medio recente;
- normalizacao do spread;
- tick volume/liquidez;
- ATR;
- volatilidade;
- momentum;
- direcao dos primeiros candles;
- gap/tick gap estimado.

### Research Lab

Continua sendo o responsavel pela decisao operacional:

- par;
- timeframe;
- direcao;
- entrada;
- stop inicial;
- alvo;
- RR;
- justificativa.

## Contextos possiveis

```text
NO_TRADE
GAP_FILL_CANDIDATE
CONTINUATION_CANDIDATE
LOW_LIQUIDITY_SKIP
SPREAD_TOO_HIGH_SKIP
NO_EDGE_SKIP
```

## Modos exibidos

```text
POST_ROLLOVER_ANALYSIS
POST_ROLLOVER_TRADE_READY
POST_ROLLOVER_SKIPPED
NORMAL_LAB_FLOW
```

## Guardrails

- Nenhuma ordem abre durante a janela de rollover.
- A analise so comeca apos a janela de protecao.
- Nao existe regra fixa de compra/venda depois do rollover.
- O evento nao substitui as 15 Alphas existentes.
- O evento aparece como `EVENT_POST_ROLLOVER_DAILY_OPEN` no ranking.
- Se nao houver edge, o Lab segue o fluxo normal.
- Swap nao e rollover: rollover e evento temporal; swap e custo/credito financeiro.

## Metricas registradas

O ranking do Lab carrega os dados do evento em `parameters`:

- tipo do evento;
- modo;
- contexto;
- motivo de skip;
- minutos apos rollover;
- spread;
- spread medio;
- spread ratio;
- ATR;
- volatilidade;
- momentum;
- tick volume;
- entrada;
- stop;
- alvo;
- RR.
