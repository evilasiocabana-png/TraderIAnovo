# MISSION_TIA-038_SHOW_ENTRY_TYPE_IN_OPEN_TRADES

Status: completed

Data: 2026-08-17

## Objetivo

Exibir na tabela `Em negociacao` se a posicao veio de entrada principal ou de
reentrada, posicionando a informacao antes de `Alvo`.

## Implementacao

- Criada classificacao a partir do snapshot persistido do Trade Plan.
- `INITIAL` e exibido como `PRINCIPAL`.
- `REENTRY` e `STRUCTURAL_REENTRY` sao exibidos como `REENTRADA`.
- Ausencia de contrato explicito retorna `N/D`, sem inferencia pelo preco.

## Seguranca

Mudanca exclusivamente visual e read-only. Nenhuma ordem, stop, alvo, setup ou
estado operacional foi alterado.

## Validacao

- testes direcionados de classificacao e ordem das colunas: aprovados;
- compilacao do dashboard: aprovada;
- snapshot atual M24 classificado como `REENTRADA`;
- `python scripts/run_critical_ci.py`: 188 testes aprovados.
