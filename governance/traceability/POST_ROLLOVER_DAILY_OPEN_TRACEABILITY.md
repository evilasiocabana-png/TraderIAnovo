# POST_ROLLOVER_DAILY_OPEN Traceability

## Evento

```text
POST_ROLLOVER_DAILY_OPEN
```

## Identidade no ranking

```text
EVENT_POST_ROLLOVER_DAILY_OPEN
```

## Fluxo

```text
MT5 server time
↓
ForexTimeLayer / RolloverGuard
↓
PostRolloverAnalyzer
↓
Research Lab scenario ranking
↓
Dashboard / Relatorio
↓
Fluxo normal das Alphas se nao houver edge
```

## Arquivos

```text
research/forex_time_layer.py
research/post_rollover_analyzer.py
application/dashboard_service.py
application/dashboard_view_model.py
dashboard_app.py
docs/POST_ROLLOVER_DAILY_OPEN.md
```

## Guardrails

- Nao abre operacao durante rollover.
- Nao hardcoda horario de Brasilia.
- Usa horario do servidor MT5 quando disponivel.
- Nao substitui as 15 Alphas.
- Nao cria Alpha 16.
- Se nao houver edge, volta para `NORMAL_LAB_FLOW`.
- Rollover e evento temporal; swap e custo/credito financeiro.

## Estados visiveis

```text
POST_ROLLOVER_ANALYSIS
POST_ROLLOVER_TRADE_READY
POST_ROLLOVER_SKIPPED
NORMAL_LAB_FLOW
```

## Contextos

```text
NO_TRADE
GAP_FILL_CANDIDATE
CONTINUATION_CANDIDATE
LOW_LIQUIDITY_SKIP
SPREAD_TOO_HIGH_SKIP
NO_EDGE_SKIP
```
