# TraderIA Novo - Traceability Index

Este diretorio registra a trilha oficial:

```text
Alpha -> setup -> entrada -> saida -> timeframe -> Forex -> MT5 -> Relatorio
```

## Indices

- `ALPHA_INDEX.md`: catalogo Alpha001-Alpha015.
- `SETUP_INDEX.md`: modelos/setups e suas fontes de decisao.
- `LAB_TO_FOREX_CONTRACT.md`: como o Lab entrega parametros ao Forex.
- `FOREX_TO_MT5_CONTRACT.md`: como o Forex vira JSON/visual/execucao demo.
- `REPORT_CONTRACT.md`: como o Relatorio audita sem virar fonte de decisao.
- `TRACEABILITY_MATRIX.md`: matriz de ponta a ponta.
- `STOP_LOGIC_TRACEABILITY.md`: trilha das politicas de saida/stop management
  do Lab ate MT5 e Relatorio.
- `DYNAMIC_EXIT_TRACEABILITY.md`: desenho de rastreabilidade para futura saida
  dinamica read-only por leitura de mercado.
- `DYNAMIC_EXIT_CONTRACT_TRACEABILITY.md`: contrato read-only implementado da
  saida dinamica.
- `DYNAMIC_EXIT_MARKET_STATE_TRACEABILITY.md`: leitura de estado de mercado
  implementada para a saida dinamica read-only.
- `DYNAMIC_EXIT_RECOMMENDATION_TRACEABILITY.md`: motor read-only que transforma
  estado de mercado em recomendacao dinamica auditavel.
- `DYNAMIC_EXIT_DASHBOARD_DISPLAY_TRACEABILITY.md`: exibicao da saida dinamica
  no Forex/Dashboard sem decisao operacional.
- `DYNAMIC_EXIT_MT5_VISUAL_TRACEABILITY.md`: exibicao curta da saida dinamica
  no MT5 visual apenas quando ha posicao aberta.
- `DYNAMIC_EXIT_REPORT_TRACEABILITY.md`: registro da saida dinamica na aba
  Relatorio como auditoria read-only.
- `DYNAMIC_EXIT_BACKTEST_TRACEABILITY.md`: comparacao read-only entre saida
  original do Lab e saida dinamica recomendada.
- `DYNAMIC_EXIT_PAPER_SIMULATION_TRACEABILITY.md`: simulacao paper read-only
  que registra recomendacoes dinamicas sem executar no Provider Demo.
- `DYNAMIC_EXIT_BREAK_EVEN_DEMO_TRACEABILITY.md`: pre-autorizacao read-only de
  break-even dinamico demo sem ligar execucao operacional.
- `DYNAMIC_EXIT_ATR_TRAILING_DEMO_TRACEABILITY.md`: pre-autorizacao read-only
  de ATR trailing dinamico demo sem ligar execucao operacional.
- `DYNAMIC_EXIT_CHANDELIER_DEMO_TRACEABILITY.md`: pre-autorizacao read-only de
  Chandelier Exit demo sem ligar execucao operacional.
- `DYNAMIC_EXIT_DONCHIAN_DEMO_TRACEABILITY.md`: pre-autorizacao read-only de
  Donchian Channel Stop demo sem ligar execucao operacional.
- `DYNAMIC_EXIT_VOLATILITY_DEMO_TRACEABILITY.md`: pre-autorizacao read-only de
  Volatility Stop demo sem ligar execucao operacional.
- `DYNAMIC_EXIT_TIME_STOP_DEMO_TRACEABILITY.md`: pre-autorizacao read-only de
  Time Stop demo sem ligar execucao operacional.
- `DYNAMIC_EXIT_MOVING_AVERAGE_DEMO_TRACEABILITY.md`: pre-autorizacao read-only
  de Moving Average Exit demo sem ligar execucao operacional.
- `DYNAMIC_EXIT_PARABOLIC_SAR_DEMO_TRACEABILITY.md`: pre-autorizacao read-only
  de Parabolic SAR demo sem ligar execucao operacional.
- `DYNAMIC_EXIT_UNIFIED_ENGINE_TRACEABILITY.md`: motor unificado read-only que
  consolida leitura, recomendacao e pre-autorizacao sem executar.
- `DYNAMIC_EXIT_RUNTIME_OPTIMIZATION_TRACEABILITY.md`: otimizacao de runtime
  com cache LRU pequeno e fallback seguro sem executar.

## Regra de uso

Toda missao que alterar Alpha, setup, timeframe, entrada, saida, stop
management, visual MT5 ou relatorio deve atualizar o indice correspondente.

## Fonte de verdade

O codigo continua sendo a fonte executavel. Estes indices sao a fonte de
rastreabilidade para revisao no GitHub e para o GPT criar missoes seguras.
