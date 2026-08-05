# Modelo 22 - Espelho Independente Do M9

Data: 2026-08-04
Status: operacional exclusivamente em MT5 Demo

## Identidade

```text
Modelo: M22
Identificador: MODELO_22_ESPELHO_M9
Comentario MT5: TraderIA M22
Origem: M9 / ALPHA_M9_TREND_PULLBACK_M15_M1
Cor visual: magenta claro
```

## Contrato De Entrada

O M22 usa exatamente os mesmos candles e o mesmo gatilho fechado do M9:

- contexto M15 pela EMA20/50;
- entrada M1 pela EMA9/21;
- ADX14 maior que 20;
- candle anterior tocando a faixa das medias;
- ultimo candle M1 fechado retomando a tendencia.

Somente depois de existir a decisao equivalente do M9 ocorre o espelho:

```text
BUY M9  -> SELL M22
SELL M9 -> BUY M22
TP M22  = SL M9
SL M22  = TP M9
```

## Risco E Alvo

O contrato M9 atual usa SL de 1,25 ATR e alvo de 2R, equivalente a 2,5 ATR.
A troca direta produz no M22:

```text
stop_factor M22 = 2,5 ATR
alvo M22        = 1,25 ATR
RR M22          = 0,5
```

Os fatores sao derivados do contrato M9 durante a materializacao. O M22 nao
mantem uma copia manual capaz de divergir silenciosamente da origem.

## Independencia E Seguranca

- M9 permanece inalterado;
- M22 pode ser selecionado e executado sem M9 estar selecionado;
- M9 e M22 possuem decisao, cache, Trade Plan, duplicidade e comentario proprios;
- ambos podem coexistir no mesmo par e no mesmo ciclo;
- permanece no maximo uma posicao por modelo/par e 22 posicoes totais por par;
- SL e TP sao fixos; Position Manager apenas audita este contrato;
- execucao continua exclusiva em Demo e conta real permanece bloqueada.

## Rastreabilidade

O snapshot e o historico M22 registram:

- `mirror_source_model=M9`;
- `mirror_swap_sl_tp=true`;
- `MIRROR_DIRECTION=INVERTED`;
- `SL M22` originado do `TP M9`;
- `TP M22` originado do `SL M9`;
- identidade `TraderIA M22` no MT5.

## Rollback

Remover M22 do mapa de modelos, conjuntos operacionais, seletor, provider,
monitor e Relatorio; recalcular o limite global a partir dos modelos restantes.
Nenhum parametro, cache, plano ou resultado do M9 deve ser alterado.
