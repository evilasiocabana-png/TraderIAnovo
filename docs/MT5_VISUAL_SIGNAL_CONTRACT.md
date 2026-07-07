# Contrato do JSON Visual MT5

Este documento define a fronteira entre Python e o indicador MT5.

## Objetivo

O Python calcula e exporta sinais. O MetaTrader 5 apenas le o arquivo JSON e
desenha a informacao no grafico.

O indicador fonte fica em:

```text
mt5/indicators/TraderIAVisualSignals.mq5
```

O arquivo visual esperado e:

```text
traderia_visual_signals.json
```

## Responsabilidades

| Componente | Responsabilidade |
|---|---|
| `DashboardService` | Orquestra carga, view model e exportacao. |
| `MT5VisualSignalExporter` | Serializa sinais para JSON. |
| `MT5VisualSignalPathResolver` | Resolve caminho do arquivo em `MQL5/Files`. |
| `TraderIAVisualSignals.mq5` | Le JSON e desenha no grafico MT5. |

## Campos esperados

O JSON deve preservar pelo menos estes conceitos:

| Campo/conceito | Uso |
|---|---|
| `schema_version` | Permite evoluir contrato com seguranca. |
| `generated_at` | Momento em que Python exportou o arquivo. |
| `signals` | Lista de sinais por ativo/timeframe. |
| `symbol` | Ativo MT5. |
| `timeframe` | Timeframe decisor vindo do Lab. |
| `entry` / `direction` | BUY, SELL ou WAIT conforme contrato. |
| `entry_price` | Preco de referencia da entrada. |
| `stop_loss` | Stop atual ou inicial. |
| `take_profit` | Alvo quando aplicavel. |
| `setup` | Setup/modelo operacional. |
| `reason` | Motivo resumido. |
| `stop_management` | Tipo de saida/stop definido pelo Lab. |
| `position_open_time` | Candle/tempo da posicao aberta, quando houver. |
| `is_positioned` | Se ha posicao aberta naquele ativo. |

## Regra visual

- Ativos sem posicao aberta devem ficar limpos, salvo quando houver decisao
  explicita de exibir sinal pendente.
- Ativos com posicao aberta devem mostrar informacao suficiente para acompanhar
  entrada, stop, alvo e saida.
- Textos longos devem ser evitados no grafico.
- A marcacao do candle de entrada deve usar `position_open_time` quando
  disponivel.

## Compatibilidade

Qualquer mudanca no schema deve:

1. Manter leitura de campos antigos quando possivel.
2. Atualizar `schema_version` quando quebrar compatibilidade.
3. Ajustar testes do exporter.
4. Validar o indicador MT5 visualmente.

## O que nao pertence ao JSON

- Credenciais.
- Logs completos.
- Snapshot grande do Lab.
- Dados historicos brutos.
- Estado interno de Streamlit.
- Caminhos absolutos sensiveis, salvo quando indispensavel para diagnostico.
