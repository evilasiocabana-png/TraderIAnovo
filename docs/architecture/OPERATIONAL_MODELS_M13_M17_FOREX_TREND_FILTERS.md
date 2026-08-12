# Modelos M13-M17 — 17 pares Forex/M5 SMA/RSI

Data: 2026-08-10  
Status: contratos manuais aprovados exclusivamente para MT5 Demo  
Protocolo: `OPERATIONAL_MODEL_CREATION_PROTOCOL.md`

## Escopo e contrato

Operam separadamente os 17 pares de `domain/market_universe.py`, sempre em M5.
XAUUSD e BTCUSD ficam excluídos. BUY inicial ocorre a mercado com SMA20>SMA50
e RSI14>50; SELL usa o inverso. O SL fica um pip além do pivô M5 confirmado
2+2 (`0,0001`, ou `0,01` nos pares JPY), sem TP fixo.

Full Exit BUY exige candle M5 fechado confirmando RSI14 de `>=70` para `<70`;
SELL exige `<=30` para `>30`. Inversão SMA20/SMA50 também encerra. Após saída
extrema, a reentrada usa Buy Stop exatamente no topo anterior ou Sell Stop
exatamente no fundo anterior, mantendo RSI50 e direção SMA válidos.
Depois de executada a reentrada, BUY também faz Full Exit se o RSI fechar
cruzando de `>=50` para `<50`; SELL faz o inverso, de `<=50` para `>50`.

| Modelo | Setup | Filtro adicional |
|---|---|---|
| M13 | A | nenhum |
| M14 | B | ADX14 > 25 |
| M15 | C | `abs(SMA20-SMA50)/ATR14 >= 0,25` |
| M16 | D | inclinação direcional SMA50/ATR14 >= 0,05 |
| M17 | E | os três filtros simultaneamente |

Estado, posição, ordem, Alpha, Beta e auditoria são independentes por
modelo/par. IDs históricos M13-M16 continuam aposentados e auditáveis.
