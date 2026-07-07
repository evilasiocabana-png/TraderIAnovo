# Dynamic Exit Market State Engine

## Status

Implementado em modo read-only pela `MISSION_TIA-007`.

## Objetivo

Classificar o estado atual de mercado/posicao para alimentar a futura saida
dinamica, sem mover SL/TP e sem enviar ordens.

## Contrato

Entrada principal:

```text
DynamicExitMarketReading
```

Campos principais:

- `symbol`
- `side`
- `is_positioned`
- `current_price`
- `entry_price`
- `stop_price`
- `target_price`
- `atr`
- `volatility`
- `momentum`
- `spread`
- `time_in_position_minutes`

Saida:

```text
NO_POSITION
NEW_POSITION
PROTECTED_POSITION
TREND_RUNNER
REVERSAL_RISK
TIME_DECAY
BAD_EXECUTION_CONTEXT
```

## Motor

O classificador fica em:

```text
application/dynamic_exit_market_state_service.py
```

Ele e deterministico, leve e nao acessa MT5 diretamente. O motor apenas usa
dados que ja chegaram ao runtime.

## Guardrails

- Nao executa ordem.
- Nao chama `order_send()`.
- Nao move SL/TP.
- Nao recalcula Lab pesado.
- Nao altera provider demo operacional.
- Nao forca timeframe M1.
- Mantem `dynamic_exit_allowed_to_execute_demo = false`.

## Integracao Atual

- `application/forex_mt5_service.py`: classifica leitura leve do Forex quando
  ha dados de posicao disponiveis.
- `application/dashboard_service.py`: usa o estado de mercado para preencher
  `DynamicExitRecommendation` read-only sem autorizar execucao.

## Limitacao Atual

Quando a posicao nao traz stop atual, o estado retorna
`BAD_EXECUTION_CONTEXT`, porque o motor nao deve inventar risco nem R-multiple.

