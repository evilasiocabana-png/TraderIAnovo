# MANIFEST - TraderIA_CTO

Este manifesto descreve a estrutura documental do workspace TraderIA_CTO.

## Estrutura

| Caminho | Finalidade |
| --- | --- |
| `README.md` | Apresenta o workspace CTO e seu funcionamento |
| `MANIFEST.md` | Documenta a estrutura e o fluxo de execucao |
| `STATE.json` | Registra o estado atual da fila CTO |
| `EXECUTION_PROTOCOL.md` | Define o protocolo obrigatorio de execucao |
| `CTO_RULES.md` | Centraliza regras arquiteturais e operacionais |
| `VALIDATION_PROTOCOL.md` | Lista validacoes obrigatorias |
| `CODING_STANDARDS.md` | Define padroes de codificacao |
| `SPRINT_TEMPLATE.md` | Template oficial de Sprint CTO |
| `EXECUTION_REPORT_TEMPLATE.md` | Template oficial de relatorio de execucao |
| `ROADMAPS/` | Roadmaps por frente de trabalho |
| `REPORTS/` | Relatorios gerados ao final de cada sprint |

## Fluxo de Execucao

1. Ler `STATE.json`.
2. Abrir o roadmap informado em `current_roadmap`.
3. Localizar a sprint informada em `current_sprint`.
4. Executar somente a sprint localizada.
5. Rodar as validacoes obrigatorias.
6. Atualizar `STATE.json`.
7. Gerar relatorio de execucao.
8. Parar.

## Regra Central

O TraderIA_CTO controla a execucao das futuras Sprints CTO. Ele nao substitui o
codigo do TraderIA_WDO e nao autoriza alteracoes fora do escopo aprovado.
