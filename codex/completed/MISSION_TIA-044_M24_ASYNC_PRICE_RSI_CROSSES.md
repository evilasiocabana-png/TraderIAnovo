# MISSION_TIA-044 — Cruzamentos assincronos obrigatorios na INITIAL M24

Status: completed

Data: 2026-08-19

Branch: `codex/multi-ea-trading-lab`

Commit funcional: `ae5268c`

## Objetivo

Corrigir a entrada inicial M24 para exigir novo cruzamento do preco pela SMA20
e novo cruzamento do RSI14 pelo nivel 50, sem exigir simultaneidade.

## Contrato implementado

- BUY: preco cruza e permanece acima da SMA20; RSI14 cruza e permanece acima
  de 50;
- SELL: preco cruza e permanece abaixo da SMA20; RSI14 cruza e permanece abaixo
  de 50;
- os dois eventos podem ocorrer em candles M5 diferentes, mas ambos devem ter
  ocorrido e permanecer validos na mesma direcao;
- a distancia atual `abs(SMA20-SMA50)/ATR14` deve ser `>= 0,25`;
- micro-pivo inicial continua dispensado;
- SL, trailing SMA20, reentrada, TP, saidas RSI e cesta nao foram alterados.

## Protecoes

- contrato promovido para `M24_SETUP_V2_20260819`;
- interface e documentos usam o novo fingerprint canonico;
- teste bloqueia RSI apenas no lado correto sem novo cruzamento;
- teste comprova cruzamentos em M5 diferentes;
- teste comprova a fronteira inclusiva de `0,25 ATR`.

## Contrato vigente

`M24_CONTRACT=M24_SETUP_V2_20260819; SHA256=08fe79a4213cdc1d249fa6e588b6406b03fe869d2faaf4f9c9515157d8eba51d`
