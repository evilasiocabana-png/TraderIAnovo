# MISSION_TIA-045 — CONTINUATION M24 apos TP da REENTRY

Status: completed

Data: 2026-08-19

Branch: `codex/multi-ea-trading-lab`

Commit funcional: `ae5268c`

## Objetivo

Remover o descarte da primeira reentrada apos saida RSI 70/30 e criar a entrada
`CONTINUATION` depois que uma `REENTRY` zerar no TP estrutural.

## Contrato implementado

- a primeira reentrada valida apos Full Exit RSI 70/30 e liberada;
- a `CONTINUATION` so e armada por uma `REENTRY` aceita com TP;
- o historico read-only do MT5 precisa confirmar encerramento por TP;
- BUY exige preco acima do TP anterior e RSI14 maior que 70;
- SELL exige preco abaixo do TP anterior e RSI14 menor que 30;
- ordem a mercado, volume `0,40`, SL um pip alem do micro-pivo 1+1 anterior e
  nenhum TP individual;
- BUY faz Full Exit no retorno abaixo de 70; SELL no retorno acima de 30;
- comentario MT5 e estado persistido usam o papel `CONTINUATION`;
- no maximo uma posicao aberta por papel e lados opostos continuam bloqueados.

## Protecoes

- confirmacao do TP falha fechado sem historico auditavel;
- watch e consumido somente apos aceite do provider Demo;
- conta real permanece bloqueada;
- testes nao enviam ordens ao MT5;
- contrato promovido para `M24_SETUP_V3_20260819`.

## Contrato vigente

`M24_CONTRACT=M24_SETUP_V3_20260819; SHA256=4caa2af5fb100fbf7631fbaf2655b0ab9006f4afbc55ebcf7543590d176eb60b`
