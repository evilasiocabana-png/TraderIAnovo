# EVENTBUS_VISUALIZATION.md

## Missao 224 - EventBus Visualization

Sprint 14 - TraderIA UX Consolidation  
Projeto: TraderIA  
Data: 2026-06-28

## Objetivo

Criar visualizacao real do EventBus no Dashboard.

## Implementacao

O `EventLogger` agora registra timestamp em cada `LoggedEvent`.

A aba Eventos e a secao Eventos do Replay exibem tabela com:

- timestamp;
- evento;
- payload resumido.

## Eventos Exibidos

- `NEW_CANDLE`
- `FEATURE_SNAPSHOT_CREATED`
- `REGIME_ANALYSIS_CREATED`
- `RESEARCH_ANALYSIS_CREATED`
- `STRATEGY_SIGNAL_CREATED`
- `DECISION_CREATED`
- `ORDER_CREATED`
- `ORDER_CLOSED`

## Eventos Solicitados Mas Nao Criados

Nao foram adicionados novos eventos oficiais como `REPLAY_STARTED`, `REPLAY_FINISHED`, `RESEARCH_STARTED` ou `RESEARCH_FINISHED`, porque isso altera o contrato oficial do EventBus e exige decisao arquitetural/baseline propria.

## Resultado

Eventos reais do Replay/EventBus passam a ser auditaveis visualmente.
