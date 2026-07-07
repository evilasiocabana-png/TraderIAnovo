# ADR-0007: Estratégias Retornam Apenas StrategySignal

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

Estratégias como Alpha001 avaliam mercado e produzem sinal para o pipeline de
decisão.

## Problema

Se estratégias executarem ordens, acessarem corretora ou pularem o pipeline, o
sistema perde controle de risco e rastreabilidade.

## Alternativas Consideradas

- Estratégias retornando dicionários livres.
- Estratégias chamando execução diretamente.
- Estratégias retornando apenas `StrategySignal`.

## Decisão Adotada

Estratégias retornam apenas `StrategySignal`.

## Justificativa

`StrategySignal` preserva contrato explícito entre estratégia, decisão, risco e
execução simulada.

## Impactos Positivos

- Estratégias permanecem intercambiáveis.
- Decision Pipeline mantém autoridade sobre decisão final.
- Risk Engine continua no fluxo obrigatório.

## Impactos Negativos

- Estratégias precisam adaptar informações ao DTO oficial.

## Riscos

- Adicionar campos sem atualizar contratos pode quebrar consumidores.

## Consequências Futuras

Toda nova estratégia deve respeitar o contrato `StrategySignal`.

## Referências

- domain/contracts/strategy_signal.py
- strategies/
- alpha/
- tests/test_domain_contracts.py

## Sprints Relacionadas

- SPRINT ALPHA 001
- SPRINT CTO 007
- SPRINT CTO 021
