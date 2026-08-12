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
Janela operacional: exatamente as ultimas 52 velas M5, incluindo a vela atual
Pesquisa pesada no runtime: proibida
Métricas históricas: diagnóstico, não gate operacional
```

## Entrada

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
