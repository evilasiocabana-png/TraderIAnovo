# TraderIA_CTO

TraderIA_CTO e o workspace documental de governanca do projeto TraderIA.

Esta pasta nao contem funcionalidades operacionais do TraderIA_WDO. Ela existe
para organizar, controlar e registrar as futuras Sprints CTO.

## Finalidade

Centralizar o sistema operacional do CTO:

- estado atual da execucao;
- protocolos de sprint;
- regras arquiteturais;
- validacoes obrigatorias;
- templates oficiais;
- roadmaps por frente de evolucao;
- relatorios de execucao.

## Papel do TraderIA CTO

O TraderIA CTO define a direcao arquitetural, aprova sprints, protege contratos,
mantem governanca tecnica e decide quando uma entrega pode ser considerada
concluida.

## Papel do Codex

O Codex executa uma Sprint CTO por vez, seguindo o `STATE.json`, o roadmap
correspondente e os protocolos deste workspace.

O Codex nao deve executar duas sprints na mesma rodada.

## Funcionamento do Workspace

O fluxo oficial e:

1. Ler `STATE.json`.
2. Abrir o roadmap indicado.
3. Localizar a sprint atual.
4. Executar somente aquela sprint.
5. Rodar validacoes.
6. Atualizar `STATE.json`.
7. Gerar relatorio em `REPORTS/`.
8. Parar.
