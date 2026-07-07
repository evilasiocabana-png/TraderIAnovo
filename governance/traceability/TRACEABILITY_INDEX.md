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

## Regra de uso

Toda missao que alterar Alpha, setup, timeframe, entrada, saida, stop
management, visual MT5 ou relatorio deve atualizar o indice correspondente.

## Fonte de verdade

O codigo continua sendo a fonte executavel. Estes indices sao a fonte de
rastreabilidade para revisao no GitHub e para o GPT criar missoes seguras.
