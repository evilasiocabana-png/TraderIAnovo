# TraderIA Novo - Contract Forex -> MT5

Este contrato rastreia como a linha Forex vira JSON visual e informacao no MT5.

## Fonte Forex

```text
DashboardMT5ForexSignalRowViewModel
```

Campos relevantes:

- `pair`
- `timeframe`
- `lab_timeframe`
- `lab_alpha_id`
- `lab_parameters`
- `active_model`
- `decision`
- `theoretical_entry_status`
- `theoretical_entry_price`
- `research_plan_stop`
- `research_plan_target`
- `research_plan_risk_reward`
- `research_plan_stop_management`
- `research_plan_stop_management_parameters`
- `research_plan_stop_management_reason`

## Exportacao

```text
DashboardService.export_mt5_visual_signals()
  -> MT5VisualSignalExporter.export()
  -> traderia_visual_signals.json
  -> mt5/indicators/TraderIAVisualSignals.mq5
```

## Campos JSON rastreaveis

| Campo JSON | Origem |
| --- | --- |
| `symbol` | `row.pair` |
| `timeframe` | timeframe operacional/Lab |
| `mt5_source_timeframe` | timeframe lido no MT5 |
| `decision` | decisao Forex/Lab |
| `entry` | entrada teorica ou preco de posicao |
| `stop` | `research_plan_stop` |
| `target` | `research_plan_target` |
| `rr` | `research_plan_risk_reward` |
| `stop_management` | `research_plan_stop_management` |
| `lab_alpha_id` | Alpha consolidada |
| `lab_configuration` | pacote de parametros do Lab |
| `is_positioned` | posicao aberta no MT5 |
| `position_open_time` | horario da posicao aberta |
| `trigger_candle` | candle de gatilho teorico |

## Regras visuais

- Sem posicao aberta: grafico limpo por padrao.
- Com posicao aberta: mostrar entrada, stop, alvo/saida e candle de entrada.
- Textos longos devem ser reduzidos antes de chegar ao indicador.
- `stop_management` deve ser preservado no JSON.

## Indicador MT5

Fonte:

```text
mt5/indicators/TraderIAVisualSignals.mq5
```

Campos de atencao:

- leitura de `stop_management`;
- filtro por `symbol` e `timeframe`;
- desenho de linhas de entrada/stop/alvo;
- resumo de saida.
