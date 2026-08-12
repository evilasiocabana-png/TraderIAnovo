# Modelos 6 e 7 - Expansao do Lab

Data: 2026-08-04
Status: operacional em MT5 Demo
Protocolo: `OPERATIONAL_MODEL_CREATION_PROTOCOL.md`

## Fronteira

M6 e M7 reutilizam o mesmo motor, grade de Alphas, selecao de timeframe e
materializacao de Trade Plan do M1. Eles nao copiam o vencedor dos oito pares
originais: cada mercado novo foi baixado e pesquisado individualmente em M1,
M5, M15, M30 e H1, com 5.000 candles por timeframe.

```text
snapshot MT5 compartilhado
  -> Lab pesado manual
  -> vencedor individual por mercado
  -> Trade Plan fixo do Lab
  -> gates leves no ciclo Forex
  -> Robo Demo
  -> Provider MT5
  -> relatorio por M6 ou M7
```

O calculo pesado roda somente pelos comandos da aba Lab. O ciclo de 10 segundos
le o snapshot pronto e nao recalcula indicadores historicos.

A primeira pintura da interface nao executa uma segunda sonda MT5 sincrona. O
ciclo de fundo e o unico dono da atualizacao inicial, evitando duplicacao de
leitura e travamento ao abrir o app com 19 mercados.

## M6

- ID: `MODELO_6_LAB_FOREX_EXPANSION`
- comentario MT5: `TraderIA M6`
- escopo exclusivo: AUDCAD, AUDJPY, CADCHF, EURNZD, GBPAUD, GBPCAD, GBPNZD,
  NZDCAD e NZDJPY
- entrada: Alpha e timeframe vencedores de cada par
- risco e saida: SL/TP fixos do Trade Plan vencedor, sem herdar o antigo M6
- coexistencia: uma posicao M6 por par, independente dos demais modelos

| Par | Alpha | TF | Setup | ATR SL | RR | Confirmacao | ICT |
|---|---|---:|---|---:|---:|---:|---|
| AUDCAD | ALPHA013 | H1 | SUPPORT_RESISTANCE_REACTION | 2.5 | 2.0 | 43.81% | D |
| AUDJPY | ALPHA002 | M30 | TREND_PULLBACK | 2.0 | 2.5 | 37.84% | D |
| CADCHF | ALPHA004 | M15 | RSI_REVERSAL | 1.5 | 2.5 | 41.96% | D |
| EURNZD | ALPHA002 | M30 | TREND_PULLBACK | 2.0 | 2.5 | 38.39% | D |
| GBPAUD | ALPHA004 | H1 | RSI_REVERSAL | 2.5 | 1.5 | 46.00% | D |
| GBPCAD | ALPHA006 | M30 | ADX_TREND_STRENGTH | 2.0 | 2.0 | 39.00% | E |
| GBPNZD | ALPHA004 | H1 | RSI_REVERSAL | 2.0 | 2.0 | 42.48% | D |
| NZDCAD | ALPHA013 | H1 | SUPPORT_RESISTANCE_REACTION | 1.5 | 2.0 | 44.24% | D |
| NZDJPY | ALPHA002 | H1 | TREND_PULLBACK | 2.0 | 2.5 | 36.27% | E |

## M7

- ID: `MODELO_7_LAB_XAU_BTC`
- comentario MT5: `TraderIA M7`
- escopo exclusivo: XAUUSD e BTCUSD
- mapeamento: o ativo `BITCOIN` do CSV usa o simbolo executavel `BTCUSD`
- entrada: Alpha e timeframe vencedores de cada ativo
- risco e saida: SL/TP fixos do Trade Plan vencedor
- coexistencia: uma posicao M7 por ativo, independente dos demais modelos

| Ativo | Alpha | TF | Setup | ATR SL | RR | Confirmacao | ICT |
|---|---|---:|---|---:|---:|---:|---|
| XAUUSD | ALPHA001 | H1 | TREND_MOMENTUM | 1.5 | 2.5 | 37.84% | D |
| BTCUSD | ALPHA002 | H1 | TREND_PULLBACK | 2.5 | 1.5 | 46.73% | D |

## Gates e evidencias

O ICT permanece diagnostico, como no M1, e nao substitui a regra de entrada.
Uma linha com ICT E continua identificada como melhor cenario disponivel, mas a
tela deve mostrar a classificacao sem promover a evidencia a certificacao.
Para enviar ordem, ainda sao obrigatorios: candle fechado, sinal vivo, zona,
plano valido, robo armado, MT5 Demo apto, ausencia de duplicidade e simbolo
executavel.

## Compatibilidade

Os IDs `MODELO_6_TREND_MOMENTUM_ORIGINAL`, `MODELO_6_ESPELHO_M5` e
`MODELO_7_TREND_MOMENTUM_DYNAMIC` ficam aposentados para novas entradas. Eles
continuam reconhecidos no historico e pelo Position Manager de posicoes antigas.
Isso impede que a antiga saida dinamica do M7 contamine o novo M7 do Lab.
