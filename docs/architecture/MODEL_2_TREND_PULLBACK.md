# Modelo 2 - Trend Pullback M15/H1

Data: 2026-07-29
Status: operacional em MT5 Demo

## Objetivo

O Modelo 2 e um fluxo independente aplicado aos oito pares Forex monitorados.
Ele nao reutiliza a direcao, o stop ou o alvo dos demais modelos.

## Contrato

```text
H1 fechado define direcao pela EMA20/EMA50
  -> M15 fechado confirma EMA9/EMA21 na mesma direcao
  -> ADX14 precisa ser maior que 20
  -> candle anterior precisa sobrepor a faixa EMA9/EMA21
  -> ultimo M15 fechado precisa retomar a direcao
  -> entrada no preco vivo seguinte
  -> SL fixo em 1,25 ATR14
  -> TP fixo em 2R
```

Pares:

```text
AUDUSD
EURJPY
EURUSD
GBPUSD
NZDUSD
USDCAD
USDCHF
USDJPY
```

## Compra

Todos os gates precisam estar alinhados:

- EMA20 H1 acima da EMA50 H1;
- EMA9 M15 acima da EMA21 M15;
- ADX14 M15 maior que 20;
- candle M15 anterior cruza ou toca a faixa entre EMA9 e EMA21;
- ultimo candle M15 fechado e positivo e fecha acima da EMA9.

## Venda

A regra e o inverso exato:

- EMA20 H1 abaixo da EMA50 H1;
- EMA9 M15 abaixo da EMA21 M15;
- ADX14 M15 maior que 20;
- candle M15 anterior cruza ou toca a faixa entre EMA9 e EMA21;
- ultimo candle M15 fechado e negativo e fecha abaixo da EMA9.

## Risco

```text
distancia_stop = max(ATR14_M15 * 1,25; preco * 0,05%)
target = entrada +/- distancia_stop * 2
```

O SL e o TP nascem fixos. O Position Manager apenas audita esse contrato e nao
move o SL nem executa FULL_EXIT para posicoes M2.

## Rastreabilidade

O monitor Forex MT5 publica a cada ciclo:

- `M15_EMA9`;
- `M15_EMA21`;
- `ADX14`;
- `ATR14`;
- `PULLBACK_TOUCH`;
- `CONFIRM_BULLISH`;
- `CONFIRM_BEARISH`;
- `H1_EMA20`;
- `H1_EMA50`;
- `H1_TREND`;
- `M15_TREND`;
- `M2_SIGNAL`.

O sinal so permanece executavel nos primeiros 120 segundos do novo candle M15.
Essa janela usa o relogio do servidor MT5 quando disponivel.

## Camadas Alteradas

```text
research/alpha_suggested/model2_trend_pullback.py
  -> application/lab_operational_model_service.py
  -> application/dashboard_service.py
  -> application/mt5_demo_robot_service.py
  -> provider MT5 Demo
  -> Relatorio/Historico
```

O `DashboardService` materializa a decisao em um `Trade Plan` completo. O robo
recebe apenas direcao, entry, SL, TP, RR e identidade M2. O provider nao decide
indicadores.

## Guardrails

- somente MT5 Demo;
- uma posicao por modelo e par;
- coexistencia independente com M1 e M3-M7;
- sem recalculo pesado do Lab no ciclo;
- somente candles fechados decidem;
- sem evidencia falsa: o contrato esta liberado operacionalmente, mas replay e
  forward test por par continuam identificados como pendentes;
- rollback pelo commit anterior.

## Testes

`tests/test_model2_trend_pullback.py` cobre:

- contrato nos oito pares;
- carregamento M15/H1;
- BUY;
- SELL;
- stop 1,25 ATR;
- alvo 2R;
- cache por candle fechado.
