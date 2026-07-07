# Architecture Change Workflow

Este documento define o fluxo oficial de aprovação para mudanças arquiteturais
no TraderIA_WDO.

O objetivo é impedir alterações estruturais sem avaliação de impacto,
justificativa técnica e aprovação explícita do CTO.

## Quando o Workflow é Obrigatório

Este workflow é obrigatório sempre que a mudança afetar:

- camadas da arquitetura;
- contratos públicos;
- serviços da camada `application`;
- providers;
- adapters;
- EventBus;
- `DashboardService`;
- Replay;
- Research Lab;
- Decision Pipeline;
- Risk Engine;
- `ConfigurationManager`;
- `OperationSession`;
- manifesto arquitetural;
- baseline arquitetural.

## Fluxo Obrigatório

Toda alteração arquitetural deve seguir esta sequência:

1. Definição do problema.
2. Justificativa arquitetural.
3. Avaliação de impacto.
4. Avaliação de riscos.
5. Alternativas consideradas.
6. Aprovação do CTO.
7. Implementação.
8. Atualização dos testes.
9. Atualização da documentação.
10. Atualização do manifesto, quando aplicável.
11. Atualização da baseline, somente após aprovação.

## Checklist Antes da Implementação

Antes de implementar, a mudança deve responder:

- O domínio continua puro?
- Há aumento de acoplamento?
- Existe alternativa mais simples?
- Há quebra de contratos públicos?
- Os testes existentes continuam válidos?
- A mudança afeta Replay?
- Afeta Research Lab?
- Afeta Dashboard?
- Afeta providers?
- Afeta EventBus?
- Afeta Configuration?
- Afeta Session?
- Exige atualização do manifesto?
- Exige atualização da baseline?

## Critérios de Reprovação

A alteração deve ser rejeitada quando:

- aumentar acoplamento sem necessidade;
- violar Clean Architecture;
- quebrar contratos públicos;
- mover lógica para a UI;
- permitir acesso direto à infraestrutura;
- permitir operação real;
- reduzir cobertura arquitetural.

## Critérios de Aprovação

A alteração pode ser aprovada quando:

- reduzir complexidade;
- preservar contratos;
- aumentar testabilidade;
- melhorar isolamento entre camadas;
- manter compatibilidade;
- atualizar documentação;
- atualizar testes.

## Regras de Manifesto e Baseline

O manifesto arquitetural deve ser atualizado quando a mudança aprovada alterar a
estrutura oficial declarada do projeto.

A baseline arquitetural só pode ser atualizada após:

- Sprint aprovada;
- validação completa;
- autorização explícita do CTO.

A baseline nunca deve ser atualizada para esconder drift indevido.

## Limites Operacionais

Este workflow não autoriza operação real.

Mudanças arquiteturais não podem:

- integrar corretora sem autorização específica;
- habilitar MT5;
- permitir envio de ordens reais;
- permitir que IA execute ordens;
- contornar Replay, Research Lab, Paper Trading visual ou os gates existentes.

O TraderIA_WDO permanece restrito a pesquisa, replay, simulação e paper trading
visual até aprovação formal em sentido contrário.
