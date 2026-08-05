# Modelo 21 - Espelho Independente Do M19

Data: 2026-08-04
Status: operacional exclusivamente em MT5 Demo

## Identidade

```text
Modelo: M21
Identificador: MODELO_21_ESPELHO_M19
Comentario MT5: TraderIA M21
Origem: M19 / ALPHA015 / LIQUIDITY_SPREAD_FILTER
Cor visual: cinza azulado
```

## Contrato

O M21 avalia exatamente o mesmo candle M1, gate de spread, tick volume,
EMA20/50 e momentum do M19. A transformacao ocorre somente depois que o sinal
M19 equivalente existe:

```text
BUY M19  -> SELL M21
SELL M19 -> BUY M21
TP M21   = SL M19
SL M21   = TP M19
```

Com o contrato M19 atual (`stop_factor=2 ATR`, `RR=2`), a troca direta produz:

```text
stop_factor M21 = 4 ATR
alvo M21        = 2 ATR
RR M21          = 0,5
```

Esses valores sao derivados dos parametros M19 durante a materializacao; nao
sao uma segunda configuracao independente que possa divergir silenciosamente.

## Independencia

- M19 nao e alterado;
- M21 possui decisao, cache, Trade Plan, duplicidade e comentario proprios;
- M19 e M21 podem coexistir no mesmo par;
- em `TODOS_MODELOS`, ambos podem enviar no mesmo ciclo;
- o limite continua uma posicao por modelo/par e acompanha o inventario global;
- Position Manager apenas audita; SL e TP permanecem fixos;
- conta real continua bloqueada.

## Rastreabilidade

O Trade Plan M21 registra:

- `mirror_source_model=M19`;
- `mirror_source_alpha=ALPHA015`;
- `mirror_direction=INVERTED`;
- `SL M21` originado do `TP M19`;
- `TP M21` originado do `SL M19`.

## Rollback

Remover M21 do mapa de modelos, seletor, provider e relatorio; recalcular o
limite pelos modelos restantes. Nenhum estado, plano ou resultado do M19 deve
ser alterado.
