# Position Manager MT5 Demo

## Objetivo

O Position Manager e a camada responsavel por acompanhar posicoes MT5 Demo ja abertas e avaliar se o stop loss pode ser tornado mais protetivo.

Ele nao abre posicao, nao fecha posicao, nao recalcula Lab e nao decide nova entrada.

## Fluxo Oficial

```text
Research Lab
  -> gera Trade Plan valido

MT5DemoRobotService
  -> abre a posicao com stop inicial e alvo

PositionManagerService
  -> detecta posicao aberta
  -> carrega plano salvo
  -> le preco atual e ATR
  -> calcula stop candidato
  -> preserva ou solicita modificacao de SL

DemoExecutionService / MT5DemoExecutionProvider
  -> modifica somente SL quando autorizado
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
- `dynamic_exit_demo_sl_assisted_execution_enabled=True`.

Com a configuracao default `False`, o sistema calcula e audita, mas nao envia modificacao ao MT5.

## Invariantes

- Stop inicial continua sendo enviado na entrada.
- Position Manager nunca abre ordem.
- Position Manager nunca fecha posicao.
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
- `READ_ERROR`
- `PLAN_ABSENT`
- `POSITION_ABSENT`
- `ATR_ABSENT`
- `EXECUTION_DISABLED`
- `MODIFY_REJECTED`
- `MARKET_DATA_ABSENT`
- `STRUCTURE_ABSENT`
- `POLICY_BLOCKED_UNSUPPORTED_ACTION`

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

