# ADR-0001: Congelamento da Clean Architecture

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

O TraderIA_WDO evoluiu para uma estrutura com domínio, aplicação,
infraestrutura, replay, research, estratégias, risco e dashboard separados por
responsabilidade.

## Problema

Sem uma decisão formal, futuras sprints poderiam misturar regras de negócio,
interface, infraestrutura e execução operacional.

## Alternativas Consideradas

- Manter organização flexível por convenção.
- Formalizar Clean Architecture como regra obrigatória.
- Permitir acoplamentos locais caso acelerem entregas.

## Decisão Adotada

Congelar Clean Architecture como base arquitetural oficial do TraderIA_WDO.

## Justificativa

A separação por camadas reduz acoplamento, facilita testes e protege o domínio
contra dependências de infraestrutura.

## Impactos Positivos

- Domínio permanece puro.
- Testes arquiteturais ficam objetivos.
- Evoluções futuras passam a ter limites claros.

## Impactos Negativos

- Mudanças simples podem exigir mais disciplina documental.
- Novas integrações precisam respeitar portas e adapters.

## Riscos

- A arquitetura pode ser burlada por imports diretos se os testes forem
  enfraquecidos.

## Consequências Futuras

Toda mudança estrutural deve respeitar as regras de dependência entre camadas.

## Referências

- ARCHITECTURE_RULES.md
- TRADERIA_ARCHITECTURE_BIBLE.md
- architecture_manifest.json

## Sprints Relacionadas

- SPRINT CTO 001
- SPRINT CTO 006
- SPRINT CTO 021
