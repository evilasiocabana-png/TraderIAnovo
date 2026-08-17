# MISSION_TIA-042 — M24 principal sem saída por inversão SMA20/50

Status: completed

Data: 2026-08-17

Branch: `codex/multi-ea-trading-lab`

Commit funcional: `1bdfaf1`

## Objetivo

Remover a saída por inversão SMA20/SMA50 exclusivamente das posições principais
do M24, mantendo as proteções das reentradas e todas as demais saídas.

## Implementação

- o avaliador M8 recebeu uma chave explícita para habilitar ou desabilitar a
  saída por inversão SMA, com padrão compatível com os modelos existentes;
- o Position Manager desabilita essa chave somente quando o contrato é M24 e o
  papel persistido é `INITIAL`/`PRINCIPAL`;
- reentradas M24, M8-M22 diretos e modelos Forex preservam o comportamento
  anterior;
- a evidência operacional registra
  `M24_INITIAL_NO_SMA_INVERSION_EXIT=True` na posição principal.

## Critérios comprovados

- principal BUY não fecha apenas porque SMA20 ficou abaixo da SMA50;
- principal SELL não fecha apenas porque SMA20 ficou acima da SMA50;
- retorno RSI 70/30 ainda produz Full Exit principal;
- reentrada ainda permite Full Exit por inversão SMA;
- testes usam providers simulados e não enviam ordens ao MT5.

## Validação

- suíte focada M8/M24/Position Manager: 92 testes aprovados;
- `python scripts/run_critical_ci.py`: 188 testes aprovados;
- `python scripts/architecture_audit.py`: OK;
- `python scripts/architecture_health.py`: CRITICO por débito preexistente de
  UI desacoplada; drift atual classificado como informativo.
