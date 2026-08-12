# Modelo Operacional M15 - XAUUSD M5 EMA Breakout

## Status

- Identidade: `MODELO_15_XAU_M5_EMA_BREAKOUT_TRAILING`
- Nome curto: `M15`
- Ambiente autorizado: MT5 Demo
- Ativo: `XAUUSD`
- Timeframe: `M5`
- Lab pesado no runtime: proibido
- Conta real: bloqueada

## Entrada

O M15 usa o ultimo candle M5 fechado como referencia e publica uma ordem
pendente para o candle M5 atual. Para XAUUSD, o contrato fixa `1 pip = 0,01`.

### Compra

1. EMA20 dos fechamentos M5 deve estar acima da EMA50.
2. Entrada: maxima do candle M5 anterior fechado + 0,01.
3. Stop inicial: minima exata do candle M5 anterior fechado.

### Venda

1. EMA20 dos fechamentos M5 deve estar abaixo da EMA50.
2. Entrada: minima do candle M5 anterior fechado - 0,01.
3. Stop inicial: maxima exata do candle M5 anterior fechado.

O modelo nao usa TP fixo. A ordem MT5 e enviada com `tp = 0`.

### Contrato da ordem pendente

- compra usa `TRADE_ACTION_PENDING` + `ORDER_TYPE_BUY_STOP`;
- venda usa `TRADE_ACTION_PENDING` + `ORDER_TYPE_SELL_STOP`;
- a pendencia expira no fechamento do candle M5 atual, usando o relogio do
  servidor MT5 exigido pela corretora;
- no candle seguinte, uma pendencia M15 anterior e cancelada antes da nova;
- se o gatilho ja foi rompido antes da leitura, o M15 nao entra a mercado;
- outros modelos continuam usando ordens a mercado sem alteracao.

## Gestao Da Posicao

Depois da abertura, somente o Position Manager administra o SL:

- BUY: candidato = minima exata do ultimo candle M5 fechado;
- SELL: candidato = maxima exata do ultimo candle M5 fechado;
- o novo SL so e enviado quando for mais protetivo que o SL atual;
- o SL nunca pode cruzar o preco atual;
- o SL nunca pode ser afastado contra o trader;
- `EARLY_EXIT` e `FULL_EXIT` nao fazem parte do M15;
- o encerramento ocorre pelo SL movel ou por intervencao externa/manual.

## Fronteiras

- `model15_xau_m5_breakout.py`: decisao pura de entrada e stop candidato.
- `DashboardService`: usa o snapshot MT5 compartilhado e materializa o plano.
- `MT5DemoRobotService`: valida e solicita somente a abertura.
- `DemoExecutionService`: transporta a ordem sem exigir TP para este modelo.
- `MT5DemoExecutionProvider`: envia ordem STOP pendente com `tp = 0`, substitui
  somente a pendencia M15 anterior e preserva o bloqueio de conta real.
- `PositionManagerService`: calcula e solicita apenas melhoria de SL.
- Dashboard/Relatorio: exibem identidade M15, Alpha, Beta, entrada e gestao.

## Desempenho

O ciclo leve nao recalcula Lab nem backtest. EMA e gatilho usam os candles M5 ja
mantidos no cache compartilhado. A gestao busca somente tres candles recentes,
o suficiente para identificar o ultimo candle fechado sem criar loops caros.

## Auditoria E Rollback

Cada ordem usa comentario `TraderIA M15`, Alpha
`ALPHAXAU15_EMA_BREAKOUT` e Beta
`BETAXAU15_PREVIOUS_CANDLE_TRAILING`. O ID historico antigo de M15 permanece
retirado e nao e reativado.

Rollback: remover somente o ID canonico M15 dos modelos ativos. Posicoes ja
abertas continuam identificadas e o Position Manager pode preservar o SL atual.
