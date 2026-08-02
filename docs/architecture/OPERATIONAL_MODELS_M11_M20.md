# Modelos Operacionais M11-M20

Data: 2026-08-01
Status: implementacao Demo validada

## Objetivo

Promover, em sequencia, as dez Alphas oficiais ainda sem modelo operacional
proprio. Cada modelo nasce independente, cobre os oito pares Forex e segue o
protocolo `OPERATIONAL_MODEL_CREATION_PROTOCOL.md`.

## Registro Oficial

| Modelo | Alpha | Familia | TF | Evidencia-base | Risco inicial |
|---|---|---|---|---|---|
| M11 | ALPHA001 | TREND_MOMENTUM | H1 | EURUSD, 145 amostras, ICT 61,72 | 1,5 ATR / 1,5R |
| M12 | ALPHA005 | DONCHIAN_BREAKOUT | M30 | AUDUSD, 102 amostras, ICT 52,71 | 1,5 ATR / 1,5R |
| M13 | ALPHA006 | ADX_TREND_STRENGTH | M15 | USDCAD, 57 amostras, ICT 61,31 | 2,5 ATR / 2R |
| M14 | ALPHA007 | MACD_MOMENTUM_SHIFT | M30 | NZDUSD, 213 amostras, ICT 47,08 | 1,5 ATR / 1,5R |
| M15 | ALPHA011 | PIVOT_REJECTION | M30 | EURUSD, 241 amostras, ICT 49,11 | 1,5 ATR / 2R |
| M16 | ALPHA012 | VWAP_MEAN_REVERSION | M30 | EURJPY, 82 amostras, ICT 61,10 | 2 ATR / 2R |
| M17 | ALPHA013 | SUPPORT_RESISTANCE_REACTION | H1 | NZDUSD, 107 amostras, ICT 62,25 | 2,5 ATR / 2R |
| M18 | ALPHA014 | MULTI_TIMEFRAME_ALIGNMENT | M30 + H4 | USDCAD, 71 amostras, ICT 66,41 | 2 ATR / 2R |
| M19 | ALPHA015 | LIQUIDITY_SPREAD_FILTER | M1 | hipotese Demo sem amostra robusta propria | 2 ATR / 2R |
| M20 | ALPHA016 | BETA002_REVERSAL_SIGNAL | M30 | USDCAD, 63 amostras, ICT 57,97 | 2,5 ATR / 2R |

Evidencia-base documenta a origem da configuracao; nao promete resultado
futuro. M19 fica marcado como hipotese Demo nao certificada porque ALPHA015 e
originalmente um filtro. EMA20/50 e momentum fornecem sua direcao operacional,
enquanto spread e volume continuam sendo o gate de liquidez.

## Contrato Operacional

- execucao exclusiva em conta Demo;
- uma posicao por modelo/par;
- ate vinte posicoes por par em `TODOS_MODELOS`;
- entrada calculada no ultimo candle fechado e enviada no proximo preco vivo;
- SL e TP fixos conforme o contrato de cada Alpha;
- Position Manager observa e audita, sem mover SL nem executar `FULL_EXIT`;
- cada ordem usa comentario proprio `TraderIA M11` ate `TraderIA M20`;
- selecao persistida, funil visual e historico distinguem todos os modelos.

## Runtime Leve

O ciclo coleta um unico lote de candles MT5. Indicadores derivados sao
calculados uma vez por `par + timeframe + candle fechado` e compartilhados
entre os modelos. Cada decisao continua separada por
`modelo + par + timeframe + candle fechado`.

O runtime nao executa pesquisa, backtest ou ranking do Lab. Entre fechamentos
de candle, o ciclo de 10 segundos apenas reutiliza os indicadores congelados e
reavalia os gates vivos necessarios, como preco e spread.

Teste de desempenho sintetico em 2026-08-01:

```text
10 modelos x 8 pares = 80 avaliacoes
tempo observado = 1,35 s
limite de aceite = 3,00 s
```

## Rastreabilidade

```text
OFFICIAL_ALPHA_MODEL_SPECS
  -> official_alpha_operational_results
  -> LabOperationalModelService.evaluate
  -> DashboardService / Trade Plan
  -> Robo Demo
  -> DemoExecutionService
  -> Provider MT5 Demo
  -> comentario TraderIA M11-M20
  -> Historico e Relatorio
```

## Rollback

O rollback consiste em remover M11-M20 de seletores e listas operacionais,
restaurar o limite do provider e retirar o adaptador de Alpha oficial. Nenhum
snapshot existente, arquivo `.traderia` ou modelo M1-M10 precisa ser apagado.
