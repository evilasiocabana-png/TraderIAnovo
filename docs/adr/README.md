# Architectural Decision Records

Este diretório contém os Architectural Decision Records (ADRs) oficiais do
TraderIA_WDO.

Cada ADR registra uma decisão arquitetural relevante, o contexto da decisão, as
alternativas consideradas, os impactos esperados e as consequências futuras.

## Regras

- Toda decisão arquitetural importante deve possuir um ADR próprio.
- ADRs são documentos históricos e não devem ser apagados.
- Quando uma decisão mudar, um novo ADR deve ser criado.
- O ADR anterior deve ser marcado como substituído, mantendo o histórico.
- ADRs dependem de aprovação do CTO.

## Numeração

Use o formato:

```text
ADR-0001-titulo-curto.md
```

## Status Permitidos

- Proposto
- Aprovado
- Substituído
- Rejeitado

## Relação com Outros Artefatos

- Architecture Bible: descreve a visão geral e regras centrais.
- Architecture Manifest: registra a arquitetura oficial em formato legível por máquina.
- Architecture Baseline: registra o snapshot aprovado para detectar drift.
- ADRs: explicam por que decisões arquiteturais foram tomadas.

## ADRs Iniciais

- ADR-0001: Congelamento da Clean Architecture
- ADR-0002: DashboardService como fachada única da UI
- ADR-0003: ReplayService como orquestrador do Replay
- ADR-0004: ResearchLabService como fachada do laboratório quantitativo
- ADR-0005: HistoricalDataProvider como ponto autorizado para datasets históricos
- ADR-0006: EventBus como mecanismo oficial de comunicação
- ADR-0007: Estratégias retornam apenas StrategySignal
- ADR-0008: IA não executa ordens
- ADR-0009: Operação real permanece desabilitada
