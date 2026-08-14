# Modelo 8 — XAUUSD/M5 SMA20/50 com RSI14 e reentrada

Data: 2026-08-10  
Status: contrato manual aprovado para MT5 Demo  
Protocolo: `OPERATIONAL_MODEL_CREATION_PROTOCOL.md`

## Identidade

```text
Nome: Modelo 8 — XAUUSD SMA/RSI Reentry
Identificador: MODELO_8_XAU_M5_SMA_RSI_REENTRY
Nome curto: M8
Comentario MT5: TraderIA M8
Cor visual: azul-ciano
Ativo: XAUUSD
Timeframe: M5
Execucao: somente MT5 Demo
```

Os IDs anteriores que usaram o número M8 continuam aposentados e preservados
no histórico. O novo ID não herda entrada ou gestão desses contratos.

## Fonte e seleção

```text
Origem do plano: regra manual aprovada pelo usuário
Fonte preferencial: último candle M5 fechado e snapshot M5 compartilhado
Fonte fallback: nenhuma; ausência de candles falha fechado
Janela operacional: 200 velas M5 fechadas mais a vela atual em formacao
Pesquisa pesada no runtime: proibida
Métricas históricas: diagnóstico, não gate operacional
```

## Entrada

### Primeira entrada versus reentrada

- M7 nao participa desta regra e permanece inalterado.
- Do M8 em diante, somente os modelos que reutilizam SMA20/50 + RSI50 seguem este
  contrato.
- A primeira entrada BUY exige cruzamento novo da SMA20 de baixo para cima da SMA50
  no ultimo candle M5 fechado, com RSI14 acima de 50 e filtros do modelo aprovados.
- A primeira entrada SELL exige o cruzamento oposto, com RSI14 abaixo de 50.
- Se as medias ja estavam cruzadas quando o robo foi ligado, nao existe primeira
  entrada a mercado: o movimento e tratado como candidato a reentrada.
- As reentradas sao ilimitadas enquanto a tendencia e os filtros permanecerem
  validos. Cada reentrada exige que a posicao anterior esteja encerrada, recuo
  estrutural de dois candles e retomada por BUY_STOP/SELL_STOP no extremo correto.
- O mesmo candle/plano nao pode ser executado duas vezes.

- médias aritméticas simples SMA20 e SMA50;
- RSI de Wilder com 14 períodos;
- BUY a mercado enquanto RSI14 estiver acima de 50 e SMA20 estiver acima da SMA50;
- SELL a mercado enquanto RSI14 estiver abaixo de 50 e SMA20 estiver abaixo da SMA50;
- SMA20/SMA50 definem direção, mas não o preço de entrada;
- após Full Exit por RSI, reentrada por BUY STOP exatamente no topo do último
  candle M5 fechado, se RSI14 > 50 e SMA20 > SMA50;
- para SELL, reentrada por SELL STOP exatamente no fundo do último candle M5
  fechado, se RSI14 < 50 e SMA20 < SMA50;
- uma posição M8 por XAUUSD.

## Stop e alvo

- BUY: SL `0,01` abaixo do último fundo confirmado M5;
- SELL: SL `0,01` acima do último topo confirmado M5;
- fundo/topo confirmado: pivô mais recente com dois candles de cada lado;
- não existe take profit fixo.

## Saída

- BUY fecha integralmente quando um candle M5 fechado confirmar RSI14 saindo de
  `>= 70` para `< 70`;
- SELL fecha integralmente quando um candle M5 fechado confirmar RSI14 saindo de
  `<= 30` para `> 30`;
- depois da saída pelo RSI, o nível RSI50 e a direção das médias autorizam a
  colocação da ordem Stop de reentrada no extremo do candle anterior;
- se uma reentrada BUY confirmar depois RSI14 de `>=50` para `<50` no fechamento
  M5, executa Full Exit; para reentrada SELL, o inverso (`<=50` para `>50`);
- inversão SMA20/SMA50 encerra integralmente a posição e invalida reentrada;
- toda decisão usa candle M5 fechado;
- a saída é executável somente em Demo e precisa ser persistida por ticket.

## Auditoria e rollback

Plano, ordem, histórico e saída registram SMA20, SMA50, RSI14, último pivô,
estado do RSI50, tipo de sinal e motivo final. O rollback consiste em retirar
somente `MODELO_8_XAU_M5_SMA_RSI_REENTRY` do conjunto ativo; contratos M8
históricos permanecem inalterados.

## Reentrada estrutural M5 (2026-08-13)

A primeira entrada e todos os demais contratos permanecem inalterados. Somente
a reentrada passou a exigir recuo oposto confirmado nos dois ultimos candles
M5 fechados:

- SELL: maxima e minima ascendentes; arma SELL STOP na minima do ultimo candle;
- BUY: maxima e minima descendentes; arma BUY STOP na maxima do ultimo candle.

O SL, os filtros SMA/RSI, o Full Exit e a gestao posterior continuam iguais.
Uma tendencia reta, sem o recuo estrutural, nao autoriza mais reentrada.

O alvo estrutural complementar e calculado na mesma janela fechada:

- SELL: ultimo fundo M5 confirmado por pivo 2+2, abaixo do gatilho;
- BUY: ultimo topo M5 confirmado por pivo 2+2, acima do gatilho.

Esse alvo nao altera o contrato individual do M8. Ele e transportado como
evidencia para que a copia XAU do M23 possa materializar seu TP individual.
