# Modelos M8-M12 — XAUUSD/M5 SMA/RSI com filtros de lateralidade

Data: 2026-08-10  
Status: contratos manuais aprovados para MT5 Demo  
Protocolo: `OPERATIONAL_MODEL_CREATION_PROTOCOL.md`

## Contrato compartilhado

- ativo exclusivo: XAUUSD;
- timeframe exclusivo: M5;
- SMA20 e SMA50 simples definem somente a direção;
- BUY enquanto RSI14 > 50 e SMA20 > SMA50;
- SELL enquanto RSI14 < 50 e SMA20 < SMA50;
- entrada a mercado depois do candle M5 fechado;
- SL `0,01` além do último pivô M5 confirmado 2+2;
- sem take profit fixo;
- Full Exit de BUY quando candle M5 fechado confirmar RSI14 de `>= 70` para `< 70`, ou SMA20 <= SMA50;
- Full Exit de SELL quando candle M5 fechado confirmar RSI14 de `<= 30` para `> 30`, ou SMA20 >= SMA50;
- após saída extrema, BUY reentra por Buy Stop exatamente no topo do último candle fechado, com RSI14 > 50 e direção BUY válida;
- após saída extrema, SELL reentra por Sell Stop exatamente no fundo do último candle fechado, com RSI14 < 50 e direção SELL válida;
- posição reentrada BUY faz Full Exit adicional ao cruzar 50 para baixo em candle M5 fechado; posição reentrada SELL faz o inverso;
- execução exclusivamente em conta MT5 Demo.

## Variantes

| Modelo | Setup | Filtro adicional de entrada |
|---|---|---|
| M8 | A | nenhum; contrato-base |
| M9 | B | ADX14 estritamente maior que 25 |
| M10 | C | `abs(SMA20-SMA50) / ATR14 >= 0,25` |
| M11 | D | inclinação direcional da SMA50 em 1 candle, normalizada pelo ATR14, `>= 0,05` |
| M12 | E | exige simultaneamente os filtros de M9, M10 e M11 |

M12 é a combinação congelada inicial, não uma alegação de superioridade
estatística. Comparações futuras do Lab podem criar uma nova versão, mas não
podem reescrever silenciosamente estes limites.

## Identidade e isolamento

```text
M8  MODELO_8_XAU_M5_SMA_RSI_REENTRY
M9  MODELO_9_XAU_M5_SMA_RSI_ADX
M10 MODELO_10_XAU_M5_SMA_RSI_MA_DISTANCE_ATR
M11 MODELO_11_XAU_M5_SMA_RSI_SMA50_SLOPE
M12 MODELO_12_XAU_M5_SMA_RSI_TREND_FILTERS
```

Cada contrato possui Alpha, Beta, fonte do plano, comentário MT5 e política de
saída próprios. IDs anteriores que utilizaram os números M8-M12 continuam
aposentados e aparecem somente no histórico.

## Auditoria e rollback

### Contrato da interface MT5 Forex

- O monitor deve rotular estas linhas exclusivamente como `M8`, `M9`, `M10`,
  `M11` e `M12`, nesta ordem.
- Todos os cinco modelos usam somente `XAUUSD` e timeframe `M5`.
- Eles nao podem herdar pares Forex nem timeframe H1 das linhas-base do M1.
- A tela consome a mesma decisao calculada pelo executor sobre o snapshot
  compartilhado XAUUSD/M5; ela nao possui um avaliador paralelo.
- Durante aquecimento, a linha XAUUSD/M5 permanece visivel e informa a falta
  de candles, sem ser substituida por linhas M1/H1.

Falha corrigida em 2026-08-10: o fallback do rotulo devolvia `MODELO 1` para
IDs sem caso explicito, e o adaptador visual generico do Lab fazia M8-M12
herdarem as linhas Forex/H1. A protecao de regressao exige casos explicitos de
rotulo e fonte XAUUSD/M5 nos testes da interface.

Plano e relatório registram SMA20, SMA50, RSI14, ADX14, ATR14, distância/ATR,
inclinação SMA50/ATR, filtros aprovados/reprovados, pivô do SL e motivo final.
O runtime solicita somente 52 registros MT5: 50 candles úteis para a SMA50,
um fechado para comparação e o candle atual, que é excluído dos indicadores.
O rollback desativa somente o ID novo afetado na política central, preservando
posições e operações históricas identificadas por contrato.
