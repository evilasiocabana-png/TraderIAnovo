# Modelo 3 - Vencedores dos 17 Pares Forex

Data: 2026-08-05
Status: aposentado para novas entradas em 2026-08-11; somente historico
ID: `MODELO_3_LAB_ALL_FOREX_WINNERS`

## Objetivo

Este antigo M3 usava, em um unico portfolio, o vencedor individual produzido pelo Research
Lab para cada um dos 17 pares de moedas monitorados. O modelo nao possui uma
Alpha unica e nao recalcula pesquisa no runtime.

## Escopo

Pares originais: AUDUSD, EURJPY, EURUSD, GBPUSD, NZDUSD, USDCAD, USDCHF e
USDJPY.

Pares expandidos: AUDCAD, AUDJPY, CADCHF, EURNZD, GBPAUD, GBPCAD, GBPNZD,
NZDCAD e NZDJPY.

`XAUUSD` e `BTCUSD` sao excluidos estruturalmente do M3 e permanecem no M7.

## Fluxo

```text
snapshot MT5 compartilhado
  -> vencedor individual ja calculado pelo Lab
  -> Trade Plan do par e timeframe vencedor
  -> M3 preserva entrada, Alpha, timeframe, SL e TP
  -> gates leves do ciclo Forex
  -> Robo Demo
  -> Provider MT5 com comentario TraderIA M3
  -> Relatorio filtrado pelo ID novo
```

O ciclo de 10 segundos apenas consulta o snapshot e compara o ultimo candle
fechado. Backtest e pesquisa pesada continuam restritos aos comandos do Lab.

## Compatibilidade

`MODELO_3_LAB_ALL_FOREX_WINNERS`, `MODELO_3_LAB_ALPHA_SUGERIDA_2_PLUS` e
`MODELO_3_RR3` estao aposentados para novas entradas. Seus registros permanecem
no historico, mas nao entram na curva do M3 ativo
`MODELO_3_XAU_M5_RSI50_FLIP`.

## Guardrails

- nenhuma nova entrada;
- somente leitura e auditoria historica;
- uma posicao M3 por par;
- sem XAUUSD ou BTCUSD;
- sem reinterpretar o vencedor do Lab;
- SL/TP fixos conforme o Trade Plan;
- sem nova leitura MT5 exclusiva e sem Lab pesado no ciclo leve.
