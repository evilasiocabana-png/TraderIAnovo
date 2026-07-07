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

## Regra de uso

Toda missao que alterar Alpha, setup, timeframe, entrada, saida, stop
management, visual MT5 ou relatorio deve atualizar o indice correspondente.

## Fonte de verdade

O codigo continua sendo a fonte executavel. Estes indices sao a fonte de
rastreabilidade para revisao no GitHub e para o GPT criar missoes seguras.
