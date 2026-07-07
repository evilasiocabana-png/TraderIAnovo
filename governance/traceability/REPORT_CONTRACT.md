# TraderIA Novo - Contract Report

Este contrato rastreia o papel da aba Relatorio no fluxo operacional.

## Fonte

```text
dashboard_app.py
  exibir_relatorios_dashboard()

application/dashboard_service.py
  get_mt5_trade_audit_report()
  _read_mt5_demo_execution_jsonl()
  _load_mt5_trade_history()
```

## Responsabilidade

Relatorio e auditoria. Ele confronta registros locais de execucao demo com o
historico MT5 read-only.

## Dados rastreaveis

| Dado | Origem |
| --- | --- |
| registros locais | `.traderia/mt5_demo_execution.jsonl` |
| aceitos localmente | registros com `accepted=true` |
| historico MT5 | `MetaTrader5.history_deals_get` quando disponivel |
| saldo/equity | `MetaTrader5.account_info` quando disponivel |
| status da auditoria | comparacao local x MT5 |

## Regras

- Relatorio nao decide Alpha.
- Relatorio nao decide setup.
- Relatorio nao decide timeframe.
- Relatorio nao recalcula Lab pesado.
- Relatorio pode acionar auditoria sob demanda.

## Ligacao com Alpha/setup

Quando o registro local tiver metadados de Lab, a auditoria deve preservar:

- Alpha;
- setup/modelo;
- timeframe;
- stop management;
- direcao;
- entrada;
- stop;
- alvo;
- ticket/horario quando existir.

## Missao que tocar Relatorio

Deve declarar impacto em:

- `REPORT_AUDIT`;
- `LAB_TO_FOREX_CONTRACT`, se consumir parametros do Lab;
- `FOREX_TO_MT5_CONTRACT`, se depender de JSON/posicao;
- testes de fallback sem MT5.
