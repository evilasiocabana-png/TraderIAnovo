# MISSION_TIA-009 - EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_DASHBOARD

## Objetivo

Mostrar no Dashboard/Forex a politica original do Lab, estado atual do mercado,
recomendacao dinamica, motivo, confianca, R atual, stop candidato e execucao
permitida sempre `false`.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar provider demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo=true`.
- Nao recalcular Lab pesado no ciclo leve Forex.

## Validacao

- `python -m unittest tests.test_dashboard_app_runtime tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service tests.test_lab_forex_mt5_contract`
