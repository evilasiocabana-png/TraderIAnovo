# Modelo 7 - Trend Momentum Com Protecao Dinamica

Data: 2026-07-24
Status: operacional somente em MT5 Demo

## Objetivo

Preservar como modelo independente a variante historica do `ALPHA001` que
recebeu gestao dinamica. O M6 continua sendo a reproducao fixa do marco zero.
O M7 usa a mesma entrada congelada, mas possui identidade e saida proprias.

## Identidade

```text
Modelo: MODELO_7_TREND_MOMENTUM_DYNAMIC
Nome curto: M7
Alpha: ALPHA001
Versao Alpha: MARCO_ZERO_A3BC912
Beta: BETA007
Versao Beta: BETA007_DYNAMIC_PROTECT_ONLY_V1
Source: M7_DYNAMIC_MARCO_ZERO
Comentario MT5: TraderIA M7
Conta: Demo
```

## Entrada Congelada

```text
Timeframe: M1
Historico de referencia: 1.000 candles
Media rapida: 20
Media lenta: 50
Momentum: 10
Volatilidade: 20
Volatilidade minima: 0.00001
RSI: 14, limites 30/70
Tolerancia de lateralizacao: 0.00005
Confianca minima: 55%
```

O sinal usa o ultimo candle M1 fechado e o proximo preco vivo. A leitura de
entrada e compartilhada com o M6 no mesmo ciclo para evitar outra consulta ao
MT5, mas cada modelo materializa seu proprio Trade Plan.

## Plano Inicial

```text
SL inicial: maior distancia entre 2 ATR e 0,10% do preco
TP inicial: RR2 sobre o risco inicial
R inicial: abs(entry - initial_stop)
```

Entrada, SL inicial e TP nunca sao recalculados pelo Position Manager.

## Saida BETA007

| Faixa | Acao permitida |
|---|---|
| Abaixo de 1,50R | `HOLD_POSITION`; preservar SL inicial e TP |
| A partir de 1,50R | `HOLD_POSITION` ou `PROTECT_POSITION` |
| Protecao disponivel | Break-even ou ATR trailing com fator 2,0 |
| Fechamento antecipado | Proibido |

O candidato escolhido e o stop mais protetivo e valido. Para BUY, o novo SL
precisa ser maior que o SL atual e menor que o preco atual. Para SELL, precisa
ser menor que o SL atual e maior que o preco atual.

`EARLY_EXIT` e `FULL_EXIT` nunca sao emitidos pelo M7, mesmo que as flags globais
estejam ativas. O Position Manager nunca afasta o SL.

## Integracao Operacional

- seletor individual M7 e opcao `TODOS_MODELOS`;
- radar de entrada e monitor de indicadores na aba MT5 Forex;
- Trade Plan e snapshot com identidade M7/BETA007;
- Robo Demo abre a posicao, sem gerenciar saida;
- Provider aceita uma posicao M7 por par e grava `TraderIA M7`;
- Position Manager administra apenas posicoes abertas M7;
- Relatorio, historico e curva patrimonial reconhecem M7;
- limite global: sete posicoes por par, no maximo uma por modelo.

## Guardrails

- M6 nao e alterado e permanece com SL/TP fixos.
- M7 nao depende de M6 estar selecionado ou posicionado.
- A conta real continua bloqueada.
- O ciclo leve nao recalcula o Research Lab.
- O R de ativacao usa o stop inicial, mesmo depois de o SL ter sido movido.
- Snapshots antigos continuam compativeis.

## Rollback

O rollback operacional imediato e selecionar outro modelo no chaveamento. O
rollback de codigo deve remover M7 sem alterar M6, M1-M5 ou os dados em
`.traderia`. Posicoes M7 abertas devem continuar visiveis e auditadas ate o
fechamento; nunca devem ser apagadas por rollback de interface.

