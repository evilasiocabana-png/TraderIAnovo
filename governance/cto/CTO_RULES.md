# CTO Rules

Regras centrais para todas as Sprints CTO do TraderIA.

## Arquitetura

- Preservar Clean Architecture.
- Preservar SOLID.
- Preservar DDD quando aplicavel.
- Preservar comunicacao Event Driven quando definida.
- Manter dominio independente de infraestrutura.
- Manter contratos explicitos entre modulos.

## Dashboard

- Dashboard deve atuar como camada de apresentacao.
- Dashboard deve consumir fachadas autorizadas.
- Dashboard nao deve acessar dominio interno, providers, adapters ou persistencia diretamente.

## Replay

- Replay deve permanecer restrito a simulacao e pesquisa.
- Replay nao executa ordens reais.
- Replay nao acessa formatos fisicos de dados fora das portas autorizadas.

## Research

- Research Lab deve permanecer restrito a pesquisa quantitativa.
- Research Lab nao executa ordens reais.
- Research Lab nao acessa broker real, MT5 ou corretora.

## Provider e Adapter

- Providers expõem portas estaveis.
- Adapters isolam infraestrutura e formatos fisicos.
- Novas fontes devem entrar como adapters/providers autorizados.

## IA

- IA nunca executa ordens.
- IA nao contorna Risk Engine.
- IA nao envia comandos para broker, MT5 ou corretora.

## Operacao Real

- Operacao real e proibida.
- Broker real nao autorizado.
- MT5 nao autorizado.
- Qualquer evolucao operacional exige aprovacao arquitetural explicita.
