# TraderIA Novo - Rastreabilidade da Logica de Setup

Este documento mapeia entrada, saida, stop management e consumo operacional do
setup calculado pelo Lab.

## Conceito

No TraderIA Novo, setup nao e apenas direcao BUY/SELL. Um setup operacional e a
combinacao de:

- par;
- timeframe decisor;
- Alpha/modelo;
- parametros de entrada;
- decisao teorica;
- evidencia historica;
- stop inicial;
- alvo/RR;
- politica de stop management;
- motivo e status.

## Fluxo do setup

```text
Lab calcula cenarios
  |
  v
Seleciona linha vencedora por par/timeframe
  |
  v
final_configuration
  |
  +--> Forex MT5 usa timeframe/setup no ciclo leve
  +--> TradePlan deriva entrada, stop e alvo
  +--> Exportador visual envia JSON ao indicador MT5
  +--> Relatorio audita execucoes locais contra MT5
```

## Entrada

Fonte principal:

```text
application/dashboard_service.py
  _mt5_parameterized_candidate()
  _find_theoretical_entry_trigger()
  _mt5_research_trade_plan_for_data()
```

Regra operacional atual:

```text
Pode considerar entrada quando:
  Lab/Forex produz BUY ou SELL
  ha plano valido do Research Lab
  ativo nao esta bloqueado pela politica temporal
  nao existe posicao aberta conflitante no papel
  ciclo demo esta armado/habilitado conforme politica local
```

## Saida e stop management

Fonte principal:

```text
application/dashboard_service.py
  _mt5_exit_management_variants()

research/mt5_research_trade_plan.py
  SUPPORTED_STOP_MANAGEMENT_POLICIES
  MT5ResearchTradePlanEngine.build_plan()
```

Politicas suportadas:

| Politica | Parametros principais |
| --- | --- |
| FIXED_STOP | nenhum parametro adicional |
| ATR_TRAILING_STOP | `atr_trailing_factor`, `atr_trailing_activation_rr` |
| BREAK_EVEN | `break_even_trigger_rr`, `break_even_offset_pips` |
| CHANDELIER_EXIT | `chandelier_period`, `chandelier_atr_factor` |
| PARABOLIC_SAR | `sar_step`, `sar_max_step` |
| DONCHIAN_CHANNEL_STOP | `donchian_stop_period` |
| MOVING_AVERAGE_EXIT | `exit_ma_period`, `exit_ma_type` |
| TIME_STOP | `max_bars_in_trade`, `max_minutes_in_trade` |
| VOLATILITY_STOP | `volatility_window`, `volatility_multiplier` |

Regra de governanca:

A saida deve vir do Lab assim como a entrada. O sistema nao deve forcar
`FIXED_STOP` para todos se o Lab tiver selecionado outra politica.

## Onde aparece no app

| Area | Campo/uso |
| --- | --- |
| Lab | tabela de setups sugeridos e auditoria de cenarios |
| Forex MT5 | linha por par, plano, stop, alvo, motivo e envio MT5 |
| MT5 Visual | texto/linhas no grafico quando aplicavel |
| Relatorio | auditoria de execucao e historico |

## Rastreabilidade minima por setup

Toda alteracao de setup deve declarar:

- Alpha/modelo;
- par/timeframe afetado;
- parametros de entrada;
- parametros de saida;
- impacto no `DashboardMT5ScenarioViewModel`;
- impacto no `DashboardMT5HeuristicResearchRowViewModel`;
- impacto no `MT5ResearchTradePlan`;
- impacto no JSON visual MT5;
- teste/validacao;
- rollback.

## Anti-regressoes conhecidas

Missoes futuras devem proteger contra:

- todos os pares voltarem a M1 por fallback;
- calculo pesado do Lab rodar no ciclo leve Forex;
- grafico MT5 ficar poluido em ativo sem posicao;
- stop management virar `FIXED_STOP` para todos;
- Relatorio virar fonte de decisao;
- UI alterar regra quantitativa diretamente.
