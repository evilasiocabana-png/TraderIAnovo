# Position Manager Demo Validation

## Objetivo

Registrar a validacao controlada do Position Manager para acompanhamento de posicao aberta e modificacao segura de Stop Loss em conta Demo.

## Estado Validado

Dependencia confirmada:

```text
MISSION_TIA-032_DYNAMIC_EXIT_AUTOMATIC_POLICIES_VIA_POSITION_MANAGER
```

## Modo De Validacao

A validacao automatizada foi feita com provider demo simulado/controlado, sem conexao com conta real.

Isso permite comprovar:

- calculo de SL candidato;
- bloqueio por configuracao;
- chamada a `modify_position_sl` apenas quando autorizada;
- ausencia de abertura de nova ordem pelo Position Manager;
- auditoria dos eventos obrigatorios.

## Flags

### Flag desligada

```text
dynamic_exit_demo_sl_assisted_execution_enabled=False
```

Resultado esperado e validado:

```text
execution_status = BLOCKED_BY_CONFIG
modify_position_sl nao e chamado
SL real nao e alterado
```

### Flag ligada

```text
dynamic_exit_demo_sl_assisted_execution_enabled=True
```

Resultado esperado e validado:

```text
novo SL mais protetivo -> modify_position_sl chamado
novo SL nao protetivo -> bloqueado
```

## Politicas Validadas

| Politica | Resultado |
|---|---|
| `BREAK_EVEN` | move SL para entrada quando gatilho RR e atingido |
| `ATR_TRAILING_STOP` | move SL com ATR quando ATR existe |
| `MARKET_AWARE_STOP_PROTECTION` | move SL por estrutura segura quando disponivel |
| `VOLATILITY_STOP_PROTECTION` | move SL por volatilidade/ATR quando dados existem |
| `MOMENTUM_WEAKNESS_STOP_TIGHTENING` | move SL para entrada quando momentum enfraquece contra posicao positiva |
| `STRUCTURE_BASED_STOP_PROTECTION` | bloqueia sem estrutura; move somente com estrutura valida |

## Bloqueios Validados

Eventos:

```text
POSITION_ABSENT
TRADE_PLAN_ABSENT
MARKET_DATA_ABSENT
ATR_ABSENT
STRUCTURE_ABSENT
STOP_MOVE_BLOCKED_BY_CONFIG
STOP_MOVE_BLOCKED_NOT_PROTECTIVE
POLICY_BLOCKED_UNSUPPORTED_ACTION
```

## Auditoria

Arquivo operacional:

```text
.traderia/position_manager.jsonl
```

Campos obrigatorios validados por teste:

```text
timestamp
symbol
ticket
side
policy
entry
current_price
old_stop
new_stop
action
execution_mode
execution_status
message
missing_data
provider_result
```

## Guardrails Confirmados

- Position Manager nao abre nova posicao.
- Position Manager nao fecha posicao.
- Position Manager nao altera TP.
- Position Manager nao aumenta risco.
- Position Manager nao recalcula Research Lab.
- Conta real permanece bloqueada pelo Provider Demo.
- Acoes destrutivas continuam bloqueadas.

## Riscos Remanescentes

- Validacao ainda nao foi feita contra uma conta Demo real conectada ao MT5 nesta missao.
- Politicas de estrutura dependem da qualidade dos campos de suporte/resistencia/swing recebidos no sinal/plano.
- `FULL_EXIT`, `PARTIAL_EXIT`, `MOVE_TARGET`, inversao e aumento de posicao permanecem fora de execucao.

## Criterio Para Proxima Liberacao

Antes de ampliar execucao:

1. rodar validacao em conta Demo real com volume minimo;
2. confirmar logs `.traderia/position_manager.jsonl` e `.traderia/mt5_stop_management.jsonl`;
3. comparar SL antes/depois no terminal MT5;
4. validar que TP nao muda;
5. manter conta real bloqueada.

