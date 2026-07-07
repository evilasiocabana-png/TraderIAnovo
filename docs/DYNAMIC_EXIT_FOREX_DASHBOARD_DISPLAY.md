# Dynamic Exit Forex Dashboard Display

## Status

Implementado em modo read-only pela `MISSION_TIA-009`.

## Objetivo

Exibir no Forex/Dashboard os campos da saida dinamica ja calculados pelas
camadas TIA-006, TIA-007 e TIA-008.

## Campos Exibidos

- `Politica Saida Lab`
- `Estado Mercado Saida`
- `Recomendacao Saida`
- `Motivo Saida Dinamica`
- `Confianca Saida Dinamica`
- `R Atual Saida`
- `Stop Candidato`
- `Execucao Saida Permitida`

## Guardrails

- Nenhuma ordem enviada.
- Nenhum SL/TP movido.
- Nenhum provider demo alterado.
- Nenhum recalculo pesado de Lab no ciclo leve Forex.
- Execucao permitida permanece `NAO`.

## Arquivo Principal

```text
dashboard_app.py
```

## Validacao

```text
python -m unittest tests.test_dashboard_app_runtime.DashboardAppRuntimeTest.test_forex_row_exibe_apenas_leitura_heuristica tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service tests.test_lab_forex_mt5_contract
```
