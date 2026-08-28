# Modelo 27 - Espelho Independente do M26

## Escopo

O M27 opera exclusivamente `XAUUSD/M5`, em conta Demo, e reutiliza cada sinal
validado do M26 sem alterar o M26. As rotas `CONTINUATION`, `LATERALIZATION` e
`EXHAUSTION` permanecem independentes.

## Transformacao

- `BUY` do M26 vira `SELL` no M27.
- `SELL` do M26 vira `BUY` no M27.
- O preco de entrada e preservado.
- `TP_M27 = SL_M26`.
- O `SL_M27` fica a mesma distancia da entrada, no lado oposto ao TP.
- O risco-retorno do M27 e sempre `1:1`.
- Todas as entradas usam lote fixo `0,03`.

## Tipos de ordem

| M26 | M27 |
|---|---|
| `MARKET` | `MARKET` oposta |
| `BUY_STOP` | `SELL_LIMIT` |
| `SELL_STOP` | `BUY_LIMIT` |
| `BUY_LIMIT` | `SELL_STOP` |
| `SELL_LIMIT` | `BUY_STOP` |

Essa transformacao conserva o mesmo preco-gatilho sem enviar uma ordem
pendente geometricamente invalida ao MT5.

## Guardrails

- Conta Real permanece bloqueada no provider.
- M27 precisa estar explicitamente selecionado para abrir novas ordens.
- M27 nao alimenta a cesta M23.
- Uma posicao ou pendencia por rota M27 e simbolo; rotas diferentes podem
  coexistir.
- O provider valida simbolo, timeframe, SL, TP, distancia minima, selecao,
  duplicidade e conta Demo imediatamente antes do `order_send`.
- O M27 nao usa o Position Manager do M26; seu SL e TP sao fixos.

## Rastreabilidade

- Modelo: `MODELO_27_ESPELHO_M26`
- Alpha: `ALPHA027_M26_MIRROR`
- Beta: `BETA027_FIXED_RR1`
- Fonte: `MODEL_27_MIRROR_M26`
- Comentarios MT5: `TraderIA M27 CONT`, `TraderIA M27 LAT` ou
  `TraderIA M27 EXH`.
