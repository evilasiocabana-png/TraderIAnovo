# TraderIA Architect GPT — Knowledge Files

Estes sao os arquivos que devem ser enviados como base de conhecimento para o
GPT especializado TraderIA Architect.

## Arquivos obrigatorios

- `TRADERIA_ARCHITECTURE_BIBLE.md`
- `ARCHITECTURE_RULES.md`
- `README.md`
- `TRADERIA_GPT_INSTRUCTIONS.md`
- `governance/execution/PROJECT_EXECUTION_CONTEXT.md`
- `governance/execution/EXECUTION_STATE.json`
- `governance/execution/MISSION_INDEX.md`
- `governance/cto/README.md`
- `governance/cto/MANIFEST.md`
- `governance/cto/CTO_RULES.md`
- `governance/cto/EXECUTION_PROTOCOL.md`
- `governance/cto/VALIDATION_PROTOCOL.md`
- `governance/cto/CODING_STANDARDS.md`

## Arquivos de conhecimento Alpha102

- `docs/RESEARCH_CATALOG.md`
- `docs/ALPHA_102_RESEARCH.md`
- `docs/ALPHA_102_FACTORY_APPROVAL.md`
- `docs/ALPHA_102_PLAYBOOK.md`
- `docs/ALPHA102_BENCHMARK.md`
- `docs/ALPHA102_PORTFOLIO.md`
- `docs/ALPHA102_KNOWLEDGE.md`

## Arquivos de governanca CTO e Inbox

- `codex/README.md`
- `codex/templates/MISSION_TEMPLATE.md`
- `codex/templates/EXECUTION_REPORT_TEMPLATE.md`
- `codex/templates/ERROR_REPORT_TEMPLATE.md`
- `governance/execution/NEXT_MISSION.md`
- `governance/execution/NEXT_BLOCK.md`
- `governance/execution/PROJECT_STATUS.md`
- `governance/execution/EXECUTION_LOG.md`
- `governance/execution/BLOCKED_ITEMS.md`
- `governance/cto/STATE.json`
- `governance/cto/SPRINT_TEMPLATE.md`
- `governance/cto/EXECUTION_REPORT_TEMPLATE.md`
- `governance/cto/ROADMAPS/01_GOVERNANCE.md`
- `governance/cto/ROADMAPS/02_HISTORICAL_DATA.md`
- `governance/cto/ROADMAPS/03_REPLAY.md`
- `governance/cto/ROADMAPS/04_RESEARCH_LAB.md`
- `governance/cto/ROADMAPS/05_ALPHA001.md`
- `governance/cto/ROADMAPS/06_VALIDATION.md`

## Finalidade de cada arquivo

### TRADERIA_ARCHITECTURE_BIBLE.md

Documento central da arquitetura do TraderIA_WDO. Define visao geral,
principios, camadas, fluxo do sistema, limites, roadmap e glossario.

### ARCHITECTURE_RULES.md

Arquivo com regras formais que protegem a arquitetura, especialmente dominio
puro, estrategias sem execucao de ordens, IA sem execucao de ordens e seguranca
antes de operacao real.

### README.md

Resumo operacional do projeto, com arquitetura, execucao, testes, dashboard e
estado atual das principais funcionalidades.

### TRADERIA_GPT_INSTRUCTIONS.md

Instrucoes de comportamento, responsabilidades, limites e fluxo de trabalho do
GPT TraderIA Architect.

### governance/execution/

Estado operacional do fluxo Codex Inbox. Define como uma missao entra em
`codex/inbox/`, passa por `processing/`, gera relatorio e termina em
`completed/` ou `failed/`, com registro de commit e quality gate.

### governance/cto/

Workspace documental do CTO importado para o repositorio principal. Contem
regras, protocolos, padroes de codificacao, templates e roadmaps que o GPT deve
usar para liberar uma unica proxima missao por vez.

### docs/ALPHA102_KNOWLEDGE.md

Registro institucional do conhecimento obtido com a Alpha102, incluindo
hipotese, resultados arquiteturais, licoes aprendidas, limitacoes e melhorias
futuras.

### docs/RESEARCH_CATALOG.md

Catalogo oficial de pesquisa com status, metricas, classe, familia e nivel de
confianca das Alphas acompanhadas pelo Research Lab.

## Observacao

O TraderIA Architect deve usar esses arquivos como base para revisar entregas
do Codex, aprovar ou solicitar correcoes e liberar apenas uma proxima missao por
vez.
