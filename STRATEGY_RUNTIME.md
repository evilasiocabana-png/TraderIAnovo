# STRATEGY_RUNTIME.md

## Missao 225 - Strategy Runtime

Sprint 14 - TraderIA UX Consolidation  
Projeto: TraderIA  
Data: 2026-06-28

## Objetivo

Mostrar estado runtime da strategy carregada.

## Implementacao

A aba Estrategias passou a exibir:

- strategy carregada;
- status;
- versao;
- market;
- timeframe;
- quantidade de sinais na sessao;
- ultima execucao;
- ultima decisao.

## Fonte dos Dados

Os dados sao obtidos por `DashboardService`, `ReplayData`, `StrategySignal` e dataset ativo.

## Resultado

A aba Estrategias deixou de ser apenas placeholder futuro e passou a representar o runtime visivel da strategy em uso.

## Restricao

Nenhuma strategy foi alterada. Nenhuma ordem real foi autorizada.
