# ADR-0006: EventBus como Mecanismo Oficial de Comunicação

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

O TraderIA_WDO possui módulos independentes que precisam comunicar eventos de
mercado, estratégia, decisão, ordem simulada, replay e pesquisa.

## Problema

Chamadas diretas entre publishers e subscribers criam acoplamento e dificultam
evolução modular.

## Alternativas Consideradas

- Comunicação direta entre módulos.
- Callbacks espalhados entre serviços.
- EventBus como distribuidor oficial.

## Decisão Adotada

`EventBus` é o mecanismo oficial de comunicação entre módulos.

## Justificativa

O EventBus desacopla produtores e consumidores e torna eventos oficiais
testáveis.

## Impactos Positivos

- Reduz dependência direta entre módulos.
- Permite auditoria de eventos oficiais.
- Facilita extensão futura de subscribers.

## Impactos Negativos

- Eventos precisam ser mantidos como contratos explícitos.

## Riscos

- Publicação por strings livres pode enfraquecer o contrato.

## Consequências Futuras

Novos eventos arquiteturais devem ser adicionados aos contratos oficiais e
testes correspondentes.

## Referências

- core/event_bus.py
- core/events.py
- tests/test_event_contracts.py

## Sprints Relacionadas

- SPRINT CTO 005
- SPRINT CTO 019
- SPRINT CTO 021
