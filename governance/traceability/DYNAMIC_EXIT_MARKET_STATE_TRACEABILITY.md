# Dynamic Exit Market State Traceability

## Missao

`MISSION_TIA-007_IMPLEMENTAR_MOTOR_DE_LEITURA_DE_MERCADO`

## Fluxo

```text
Lab/TradePlan
↓
Preco atual + posicao + stop + alvo + momentum + volatilidade + spread
↓
DynamicExitMarketReading
↓
DynamicExitMarketStateClassifier
↓
DynamicExitRecommendation read-only
↓
Forex / MT5 Visual / Relatorio
```

## Estados Rastreaveis

| Estado | Significado |
| --- | --- |
| `NO_POSITION` | Nao ha posicao aberta para gerir. |
| `NEW_POSITION` | Posicao existe, mas ainda sem confirmacao para ajuste. |
| `PROTECTED_POSITION` | Stop atual ja protege entrada ou lucro. |
| `TREND_RUNNER` | Posicao avancou pelo menos 1R em contexto favoravel. |
| `REVERSAL_RISK` | Posicao positiva com momentum contra. |
| `TIME_DECAY` | Tempo em posicao alto sem progresso suficiente. |
| `BAD_EXECUTION_CONTEXT` | Dado critico ausente/invalido ou spread ruim. |

## Garantia Operacional

Esta camada nao executa. Ela somente classifica e alimenta campos read-only.

Campo de seguranca:

```text
dynamic_exit_allowed_to_execute_demo = false
```

## Testes

Cobertura principal:

```text
tests/test_dynamic_exit_market_state_service.py
```

Suite focada executada:

```text
python -m unittest tests.test_dynamic_exit_market_state_service tests.test_lab_forex_mt5_contract tests.test_report_service tests.test_mt5_trade_audit_service tests.test_mt5_visual_signal_exporter
```

