# Position Manager MT5 Demo

## Objetivo

O Position Manager e a camada responsavel por acompanhar posicoes MT5 Demo ja abertas e administrar o ciclo de vida da posicao.

Ele nao abre posicao, nao recalcula Lab e nao decide nova entrada.

Ele pode decidir entre:

- `HOLD_POSITION`;
- protecao por SL mais protetivo;
- `EARLY_EXIT`/`FULL_EXIT` permanecem fora do fluxo operacional normal nesta fase.

## Fluxo Oficial

```text
Research Lab
  -> gera Trade Plan valido

MT5DemoRobotService
  -> abre a posicao com stop inicial e alvo

PositionManagerService
  -> detecta posicao aberta
  -> carrega plano salvo
  -> le preco atual, ATR, momentum, volatilidade, estrutura e contexto
  -> classifica o estado da posicao
  -> decide HOLD ou PROTECT
  -> preserva ou solicita modificacao de SL

DemoExecutionService / MT5DemoExecutionProvider
  -> modifica SL demo quando autorizado
```

## Implementacao

Arquivo principal:

```text
application/position_manager_service.py
```

Portas usadas:

```text
get_open_position(symbol)
get_current_price(symbol)
modify_position_sl(symbol, ticket, new_stop)
close_position(symbol, ticket, side, volume, reason)
```

Essas portas foram adicionadas ao contrato do `DemoExecutionService` e implementadas pelo `MT5DemoExecutionProvider`.

## Politicas Suportadas

### BREAK_EVEN

Move o SL para a entrada, com offset opcional, somente quando o preco andou a favor pelo RR minimo configurado.

Parametros:

```text
break_even_trigger_rr
break_even_offset_pips
```

### ATR_TRAILING_STOP

Move o SL usando distancia baseada em ATR.

Parametros:

```text
atr_trailing_factor
```

Se ATR estiver ausente, o stop e preservado e o evento e registrado como `ATR_ABSENT`.

### Politicas Dynamic Exit Conservadoras

O Position Manager tambem reconhece politicas dinamicas que so podem executar `MOVE_STOP` seguro:

- `MARKET_AWARE_STOP_PROTECTION`
- `VOLATILITY_STOP_PROTECTION`
- `MOMENTUM_WEAKNESS_STOP_TIGHTENING`
- `STRUCTURE_BASED_STOP_PROTECTION`

Essas politicas nunca executam `FULL_EXIT`, `PARTIAL_EXIT`, `MOVE_TARGET`, inversao ou aumento de posicao nesta fase.

### Regua Conservadora De Acionamento

Para evitar que a gestao dinamica sufoque a entrada do Lab, o Position Manager usa uma trava minima por R:

```text
R atual < 0.50
  -> HOLD_POSITION
  -> preserva stop inicial

0.50 <= R atual < 1.00
  -> HOLD_POSITION
  -> monitora, mas nao move SL

R atual >= 1.00
  -> pode gerar stop candidato
  -> executa somente se o novo SL for mais protetivo e estiver do lado correto do mercado
```

Essa regra separa a avaliacao da entrada do Lab da protecao pos-entrada. O plano inicial tem espaco para respirar antes de qualquer interferencia operacional do Position Manager.

### EARLY_EXIT / FULL_EXIT

Capacidade arquitetural futura para encerramento antecipado em Demo quando houver evidencias compostas de deterioracao do contexto.

Evidencias usadas:

- perda de momentum;
- time decay;
- baixa probabilidade de atingir alvo;
- risco de volatilidade;
- risco de quebra estrutural;
- R negativo relevante.

Regra atual: `EARLY_EXIT` e `FULL_EXIT` nao fazem parte da operacao normal. O Position Manager opera como camada de protecao de SL, nao como camada de fechamento antecipado.

## Gates De Seguranca

O Position Manager so solicita modificacao de SL quando:

- existe posicao aberta no simbolo;
- existe plano valido do Lab;
- existe ticket MT5;
- existe stop atual;
- existe preco atual;
- a politica e suportada;
- o stop candidato melhora o risco;
- o stop candidato nao cruza nem encosta no preco atual;
- o trade ja atingiu pelo menos `1.00R` a favor;
- `dynamic_exit_demo_sl_assisted_execution_enabled=True`.

Com `dynamic_exit_demo_sl_assisted_execution_enabled=True`, o sistema pode enviar somente modificacao de SL demo quando todos os gates forem aprovados.

## Invariantes

- Stop inicial continua sendo enviado na entrada.
- Position Manager nunca abre ordem.
- Position Manager nao fecha posicao no fluxo operacional normal desta fase.
- Position Manager nunca altera TP.
- Position Manager nunca afasta stop contra o trader.
- Position Manager nunca recalcula Research Lab.
- Safe Mode so acompanha stop se houver preco atual, posicao aberta e Trade Plan valido.

## Auditoria

Log principal:

```text
.traderia/position_manager.jsonl
```

Eventos esperados:

- `STOP_MAINTAINED`
- `STOP_MOVED`
- `TRADE_PLAN_ABSENT`
- `MARKET_DATA_ABSENT`
- `POSITION_ABSENT`
- `ATR_ABSENT`
- `EXECUTION_DISABLED`
- `STOP_MOVE_BLOCKED_BY_CONFIG`
- `STOP_MOVE_BLOCKED_NOT_PROTECTIVE`
- `MODIFY_REJECTED`
- `MARKET_DATA_ABSENT`
- `STRUCTURE_ABSENT`
- `POLICY_BLOCKED_UNSUPPORTED_ACTION`
- `POSITION_HELD`
- `EARLY_EXIT_CANDIDATE`
- `POSITION_CLOSED`
- `CLOSE_REJECTED`

O provider MT5 tambem preserva o log historico:

```text
.traderia/mt5_stop_management.jsonl
```

## Testes

Suite principal:

```text
tests/test_position_manager_service.py
```

Cenarios cobertos:

- BUY move stop para cima;
- SELL move stop para baixo;
- nao afasta stop;
- sem plano nao move;
- sem posicao nao move;
- sem ATR nao move;
- break-even;
- ATR trailing;
- default de execucao assistida permanece `False`.
- HOLD_POSITION;
- trava conservadora abaixo de `0.50R`;
- trava conservadora entre `0.50R` e `1.00R`;
- EARLY_EXIT/FULL_EXIT preservam posicao no fluxo normal.

