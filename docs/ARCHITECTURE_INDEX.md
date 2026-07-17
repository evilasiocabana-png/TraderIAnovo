# Architecture Governance Index

Este é o índice oficial de governança arquitetural do TraderIA_WDO.

O objetivo deste documento é servir como ponto central de navegação para a
documentação, scripts, manifestos, baseline, ADRs e testes arquiteturais do
projeto. Ele não substitui a Architecture Bible, não controla comportamento da
aplicação e não duplica o conteúdo dos documentos referenciados.

## 1. Documentos Fundamentais

- [TRADERIA_ARCHITECTURE_BIBLE.md](../TRADERIA_ARCHITECTURE_BIBLE.md)
  - Documento central com visão arquitetural, princípios e decisões estruturais.
- [ARCHITECTURE_RULES.md](../ARCHITECTURE_RULES.md)
  - Regras formais de dependência, pureza do domínio e limites operacionais.
- [README.md](../README.md)
  - Entrada operacional do projeto, com execução, validação, quality gate,
    auditoria e política de baseline.

## 2. Governança

- [ARCHITECTURE_CHANGE_WORKFLOW.md](ARCHITECTURE_CHANGE_WORKFLOW.md)
  - Fluxo oficial para aprovar mudanças arquiteturais.
- [MARKET_DATA_ARCHITECTURE.md](MARKET_DATA_ARCHITECTURE.md)
  - Arquitetura oficial para ingestao de dados historicos e em tempo real,
    incluindo providers, contratos, eventos, Replay e Research Lab.
- [MARKET_DATA_VALIDATION.md](MARKET_DATA_VALIDATION.md)
  - Homologacao oficial da infraestrutura de dados historicos, cobrindo Replay,
    Research Lab, Dashboard, EventBus, performance e integridade.
- [MARKET_DATA_CERTIFIED.md](MARKET_DATA_CERTIFIED.md)
  - Certificacao oficial da plataforma para pesquisa quantitativa com dados
    historicos reais, mantendo operacao real proibida.
- [architecture/OPERATIONAL_MODEL_CREATION_PROTOCOL.md](architecture/OPERATIONAL_MODEL_CREATION_PROTOCOL.md)
  - Protocolo oficial para criar novos modelos operacionais, baseado na
    retrospectiva do M3 RR3, cobrindo snapshot, Trade Plan, gates, Robo Demo,
    Provider MT5, Position Manager, relatorio e testes.
- ARCHITECTURE_BASELINE.md
  - Não existe como arquivo separado no estado atual. A política de baseline
    está documentada em [README.md](../README.md), seção "Política de Baseline
    Arquitetural".
- ARCHITECTURE_AUDIT.md
  - Não existe como arquivo separado no estado atual. O uso da auditoria está
    documentado em [README.md](../README.md), seção "Auditoria Arquitetural
    Continua".
- QUALITY_GATE.md
  - Não existe como arquivo separado no estado atual. O fluxo oficial está
    documentado em [README.md](../README.md), seção "Quality Gate Local".

## 3. Manifestos

### [architecture_manifest.json](../architecture_manifest.json)

- Finalidade: descrever a arquitetura oficial em formato legível por máquina.
- Responsável pela atualização: CTO / TraderIA.
- Quando atualizar: após mudança arquitetural aprovada que altere camadas,
  serviços públicos, contratos, providers, adapters, eventos ou regras
  arquiteturais declaradas.

### [architecture_baseline.json](../architecture_baseline.json)

- Finalidade: registrar o snapshot arquitetural aprovado para detecção de drift.
- Responsável pela atualização: CTO / TraderIA.
- Quando atualizar: somente após Sprint aprovada, validação completa e
  autorização explícita do CTO.

## 4. Architectural Decision Records

Os ADRs oficiais ficam em [docs/adr/](adr/).

| Número | Título | Status | Data | Arquivo |
| --- | --- | --- | --- | --- |
| ADR-0001 | Congelamento da Clean Architecture | Aprovado | 2026-06-26 | [ADR-0001-congelamento-clean-architecture.md](adr/ADR-0001-congelamento-clean-architecture.md) |
| ADR-0002 | DashboardService como Fachada Única da UI | Aprovado | 2026-06-26 | [ADR-0002-dashboardservice-fachada-unica-ui.md](adr/ADR-0002-dashboardservice-fachada-unica-ui.md) |
| ADR-0003 | ReplayService como Orquestrador do Replay | Aprovado | 2026-06-26 | [ADR-0003-replayservice-orquestrador-replay.md](adr/ADR-0003-replayservice-orquestrador-replay.md) |
| ADR-0004 | ResearchLabService como Fachada do Laboratório Quantitativo | Aprovado | 2026-06-26 | [ADR-0004-researchlabservice-fachada-laboratorio.md](adr/ADR-0004-researchlabservice-fachada-laboratorio.md) |
| ADR-0005 | HistoricalDataProvider como Ponto Autorizado para Datasets Históricos | Aprovado | 2026-06-26 | [ADR-0005-historicaldataprovider-datasets.md](adr/ADR-0005-historicaldataprovider-datasets.md) |
| ADR-0006 | EventBus como Mecanismo Oficial de Comunicação | Aprovado | 2026-06-26 | [ADR-0006-eventbus-comunicacao-oficial.md](adr/ADR-0006-eventbus-comunicacao-oficial.md) |
| ADR-0007 | Estratégias Retornam Apenas StrategySignal | Aprovado | 2026-06-26 | [ADR-0007-estrategias-retornam-strategysignal.md](adr/ADR-0007-estrategias-retornam-strategysignal.md) |
| ADR-0008 | IA Não Executa Ordens | Aprovado | 2026-06-26 | [ADR-0008-ia-nao-executa-ordens.md](adr/ADR-0008-ia-nao-executa-ordens.md) |
| ADR-0009 | Operação Real Permanece Desabilitada | Aprovado | 2026-06-26 | [ADR-0009-operacao-real-desabilitada.md](adr/ADR-0009-operacao-real-desabilitada.md) |

## 5. Scripts Arquiteturais

- [scripts/run_quality_gate.py](../scripts/run_quality_gate.py)
  - Executa o fluxo oficial de validação local: `app.py`, suíte completa de
    testes e auditoria arquitetural.
- [scripts/architecture_audit.py](../scripts/architecture_audit.py)
  - Gera relatórios de auditoria comparando arquitetura atual, manifesto e
    baseline.
- [scripts/create_architecture_baseline.py](../scripts/create_architecture_baseline.py)
  - Gera explicitamente `architecture_baseline.json`. Não é executado
    automaticamente pelo quality gate.

## 6. Testes Arquiteturais

- [test_application_contracts.py](../tests/test_application_contracts.py)
  - Protege contratos entre camadas de aplicação e dependências arquiteturais.
- [test_event_contracts.py](../tests/test_event_contracts.py)
  - Protege EventBus, eventos oficiais, publishers e subscribers.
- [test_dependency_rules.py](../tests/test_dependency_rules.py)
  - Valida regras de dependência entre camadas e pureza arquitetural.
- [test_domain_contracts.py](../tests/test_domain_contracts.py)
  - Protege DTOs e contratos públicos do domínio.
- [test_application_api.py](../tests/test_application_api.py)
  - Congela APIs públicas dos serviços de aplicação.
- test_replay_contracts.py
  - Não existe como arquivo separado no estado atual. Proteções de Replay estão
    distribuídas em suítes como `test_replay_service.py`,
    `test_replay_engine.py`, `test_replay_market_data_provider.py` e
    `test_architecture_regression.py`.
- [test_research_contracts.py](../tests/test_research_contracts.py)
  - Protege contratos, métricas e acoplamentos proibidos do Research Lab.
- [test_provider_architecture.py](../tests/test_provider_architecture.py)
  - Protege provider autorizado, registry, catálogo e adapters físicos.
- [test_configuration_contracts.py](../tests/test_configuration_contracts.py)
  - Protege ConfigurationManager, ConfigurationService e acesso via fachada.
- [test_session_contracts.py](../tests/test_session_contracts.py)
  - Protege OperationSession, SessionManager, SessionService e fluxo de sessão.
- [test_dashboard_facade.py](../tests/test_dashboard_facade.py)
  - Protege DashboardService como fachada única consumida pela UI.
- [test_architecture_regression.py](../tests/test_architecture_regression.py)
  - Consolida proteções contra regressões arquiteturais críticas.
- [test_architecture_manifest.py](../tests/test_architecture_manifest.py)
  - Valida manifesto, consistência com o projeto e integração com auditoria.
- [test_architecture_baseline.py](../tests/test_architecture_baseline.py)
  - Valida baseline, determinismo e detecção de drift.

## 7. Fluxo Oficial de Governança

1. Alteração proposta.
2. ADR.
3. Aprovação CTO.
4. Implementação.
5. Testes.
6. Auditoria.
7. Baseline.
8. Quality Gate.
9. Documentação.
10. Merge.

## Observações

- Este índice é apenas documental.
- Este índice não autoriza operação real.
- Este índice não substitui Architecture Bible, manifesto, baseline ou ADRs.
- Drift arquitetural deve ser revisado pelo CTO antes de qualquer atualização de
  baseline.
