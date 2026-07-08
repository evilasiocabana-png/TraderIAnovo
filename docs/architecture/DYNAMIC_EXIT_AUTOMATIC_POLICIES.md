# Dynamic Exit Automatic Policies

## Objetivo

Documentar quais politicas de saida dinamica podem gerar `MOVE_STOP` automatico controlado via Position Manager no TraderIA Novo.

## Regra Principal

Nenhuma politica pode aumentar risco.

Se faltar dado, se a acao for desconhecida ou se o stop candidato nao for mais protetivo:

```text
BLOCKED / STOP_MAINTAINED
```

## Configuracao De Execucao

Flag existente:

```text
dynamic_exit_demo_sl_assisted_execution_enabled
```

Default:

```text
False
```

Quando `False`, o Position Manager calcula e audita, mas nao chama `modify_position_sl`.

Quando `True`, o Position Manager pode executar somente `MOVE_STOP` em conta Demo, preservando TP e sem abrir nova ordem.

## Politicas Com MOVE_STOP Suportado

| Politica | Acao permitida | Dados obrigatorios | Bloqueio principal |
|---|---|---|---|
| `BREAK_EVEN` | Mover SL para entrada/offset | entrada, stop atual, preco atual, gatilho RR | gatilho nao atingido |
| `ATR_TRAILING_STOP` | Trailing por ATR | preco atual, stop atual, ATR, fator | `ATR_ABSENT` |
| `MARKET_AWARE_STOP_PROTECTION` | Protecao conservadora | posicao positiva e estrutura, momentum ou ATR | sem leitura segura |
| `VOLATILITY_STOP_PROTECTION` | Ajuste por volatilidade | ATR e volatilidade | `MARKET_DATA_ABSENT` |
| `MOMENTUM_WEAKNESS_STOP_TIGHTENING` | Apertar SL por momentum contra | momentum e posicao positiva | `MARKET_DATA_ABSENT` |
| `STRUCTURE_BASED_STOP_PROTECTION` | Stop por suporte/resistencia/swing | suporte/resistencia ou swing | `STRUCTURE_ABSENT` |

## Politicas Bloqueadas

Continuam bloqueadas nesta fase:

```text
FULL_EXIT
PARTIAL_EXIT
MOVE_TARGET
INVERT_POSITION
ADD_POSITION
```

Essas acoes sao mais destrutivas ou mudam o risco/posicionamento. Exigem missao propria, teste proprio e autorizacao explicita.

## Regras De Protecao

BUY:

```text
candidate_stop > current_stop
candidate_stop < current_price
```

SELL:

```text
candidate_stop < current_stop
candidate_stop > current_price
```

Se uma dessas regras falhar, o SL atual e preservado.

## Fontes De Dados

O Position Manager usa o Trade Plan/sinal salvo e as portas do provider:

```text
get_open_position(symbol)
get_current_price(symbol)
get_recent_candles(symbol, timeframe, limit)
get_atr(symbol, timeframe, period)
modify_position_sl(symbol, ticket, new_stop)
```

Ele nao recalcula o Research Lab pesado durante posicao aberta.

## Auditoria

Eventos esperados:

```text
POSITION_ABSENT
PLAN_ABSENT
READ_ERROR
ATR_ABSENT
MARKET_DATA_ABSENT
STRUCTURE_ABSENT
STOP_MAINTAINED
EXECUTION_DISABLED
STOP_MOVED
MODIFY_REJECTED
POLICY_BLOCKED_UNSUPPORTED_ACTION
```

Logs:

```text
.traderia/position_manager.jsonl
.traderia/mt5_stop_management.jsonl
```

