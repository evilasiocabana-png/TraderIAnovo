# MISSION_TIA-040_M24_SKIP_FIRST_POST_EXTREME_REENTRY

Status: completed

Data: 2026-08-17

## Objetivo

Ignorar a primeira oportunidade de reentrada M24 depois de um Full Exit por
retorno do RSI14 abaixo de 70 no BUY ou acima de 30 no SELL, liberando somente
a segunda oportunidade valida.

## Implementacao

- O Position Manager arma a trava apenas depois de Full Exit RSI 70/30 executado.
- A primeira reentrada valida do mesmo lado e persistida como bloqueada.
- Repeticoes do ciclo leve na mesma vela M5 continuam bloqueadas.
- Uma oportunidade valida identificada por nova vela M5 e tratada como segunda
  e pode ser liberada.
- A regra e simetrica para BUY/SELL e cobre reentrada Stop e RSI50 a mercado.
- Estado isolado por fonte M24, sem compartilhar contagem entre M8, M10 e M18-M22.

## Seguranca

Testes usam estado temporario e provider local. Nenhuma operacao MT5 real foi
aberta, fechada ou modificada.

## Validacao

- testes direcionados M24 e Position Manager: 56 aprovados;
- `python scripts/run_critical_ci.py`: 188 testes aprovados;
- compilacao dos modulos alterados: aprovada.

## Commit funcional

`33c7d02` em `codex/multi-ea-trading-lab`.
