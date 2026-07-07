# ADR-0003: ReplayService como Orquestrador do Replay

- Status: Aprovado
- Data: 2026-06-26
- Autor: CTO / TraderIA

## Contexto

O Replay simula execução candle a candle para análise e validação, sem operar
mercado real.

## Problema

Misturar ReplayEngine, carregamento físico de dados, UI e execução operacional
criaria acoplamento e risco operacional.

## Alternativas Consideradas

- ReplayEngine carregando dados diretamente.
- Dashboard controlando internamente o replay.
- ReplayService orquestrando o fluxo e ReplayEngine focado em simulação.

## Decisão Adotada

`ReplayService` é o orquestrador de aplicação do Replay.

## Justificativa

O serviço separa controle de aplicação da simulação candle a candle e mantém o
ReplayEngine sem dependência de UI, arquivos físicos ou corretora.

## Impactos Positivos

- Replay permanece testável.
- ReplayEngine recebe apenas candles e estado de simulação.
- Dashboard chama apenas DashboardService.

## Impactos Negativos

- Novos fluxos de replay precisam passar por serviços de aplicação.

## Riscos

- Acesso direto a provider físico no Replay quebraria a arquitetura.

## Consequências Futuras

Replay não deve executar ordens reais nem acessar Broker, MT5 ou corretora.

## Referências

- application/replay_service.py
- replay/replay_engine.py
- tests/test_replay_service.py
- tests/test_replay_market_data_provider.py

## Sprints Relacionadas

- SPRINT MARKET DATA 002
- SPRINT MARKET DATA 004
- SPRINT CTO 009
