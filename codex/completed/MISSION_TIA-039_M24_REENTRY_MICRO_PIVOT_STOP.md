# MISSION_TIA-039_M24_REENTRY_MICRO_PIVOT_STOP

Status: completed

Data: 2026-08-17

## Objetivo

Usar micro pivo confirmado como Stop Loss das duas reentradas do Modelo 24.

## Implementacao

- Reentrada estrutural Stop usa microfundo 1+1 no BUY ou microtopo 1+1 no SELL.
- Reentrada RSI50 a mercado usa a mesma regra.
- O micro pivo precisa estar confirmado e pertencer aos ultimos cinco M5
  fechados.
- Sem micro pivo valido, a reentrada fica bloqueada.
- O Position Manager atualiza o SL somente para novo micro pivo favoravel e
  nunca afrouxa a protecao.
- Variantes M24 passaram a ser reconhecidas explicitamente pelo gestor.

## Seguranca

Validacao feita com candles sinteticos e provider local. Nenhuma ordem foi
aberta, fechada ou modificada no MT5 real.

## Validacao

- `python -m pytest tests/test_model24_xau_basket.py tests/test_position_manager_service.py -q`:
  53 testes aprovados;
- `python scripts/run_critical_ci.py`: 188 testes aprovados;
- `python -m py_compile`: aprovado.

## Commit funcional

`ca590f0` em `codex/multi-ea-trading-lab`.
