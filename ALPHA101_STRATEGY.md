# ALPHA101_STRATEGY

## Missao

MISSÃO 241 — ALPHA101_STRATEGY.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Implementar Alpha101 como Strategy de pesquisa baseada no playbook `ALPHA101_PLAYBOOK.md`.

## Status

```text
IMPLEMENTED_FOR_RESEARCH
```

## Arquivos Alterados

- `strategies/alpha101/alpha101_config.py`
- `strategies/alpha101/alpha101_strategy.py`
- `strategies/strategy_factory.py`
- `application/replay_service.py`
- `tests/test_alpha101_strategy.py`
- `tests/test_strategy_factory_alpha001.py`
- `tests/test_strategies.py`
- `tests/test_replay_service.py`

## Implementação

Alpha101 foi implementada como:

```text
alpha101
```

Nome visual no Replay:

```text
Alpha101 Volume Momentum Breakout
```

## Contrato

A Strategy:

- implementa `Strategy`;
- retorna `StrategySignal`;
- não acessa Broker;
- não acessa RiskEngine;
- não acessa Dashboard;
- não acessa arquivos;
- não executa ordens;
- não altera posição diretamente.

## Regra de Sinal

Retorna `BUY` quando:

- histórico >= 200 candles;
- `ret_5d > 0`;
- `volume_ratio_20 >= 1.2`;
- `donchian_pos20 >= 0.80`;
- `atr14_pct <= 0.08`;
- `dist_ma_200 <= 0.50`.

Caso contrário:

```text
WAIT
```

## Features Calculadas

- retorno de 5 dias;
- volume relativo de 20 dias;
- posição Donchian de 20 dias;
- ATR14 percentual;
- distância da média móvel de 200 dias.

## Integração com Replay

Alpha101 foi registrada na `StrategyFactory`, o que permite seleção pelo Dashboard após a missão 233.

Fluxo:

```text
Dashboard
  -> DashboardService
      -> ReplayService
          -> StrategyFactory
              -> alpha101
                  -> StrategySignal
```

## Integração com Research Lab

A Strategy foi registrada na factory oficial. O Research Lab continua preservado e pode consumir estratégias registradas pelos contratos existentes.

Nenhuma engine nova de Research foi criada.

## Testes

Testes adicionados/ajustados:

- Alpha101 retorna `BUY` quando a tese é satisfeita;
- Alpha101 retorna `WAIT` com histórico insuficiente;
- Alpha101 retorna `WAIT` sem volume;
- Alpha101 retorna `WAIT` sem momentum;
- Alpha101 implementa interface base;
- StrategyFactory cria `alpha101`;
- ReplayService seleciona `alpha101`;
- contrato geral de estratégias inclui Alpha101.

## Restrições Preservadas

- Nenhuma ordem real.
- Nenhuma corretora.
- Nenhum MT5.
- Nenhum Broker.
- Nenhuma alteração em `HistoricalDataProvider`.
- Nenhuma alteração em `ReplayEngine`.
- Nenhuma alteração estrutural em `ResearchLab`.

## Declaração Final

Alpha101 foi implementada como Strategy de pesquisa, integrada ao seletor de Alpha e ao Replay por contratos existentes, retornando exclusivamente `StrategySignal`.
