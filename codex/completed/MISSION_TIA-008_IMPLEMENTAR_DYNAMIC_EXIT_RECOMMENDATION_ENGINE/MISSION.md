# MISSION_TIA-008 - IMPLEMENTAR_DYNAMIC_EXIT_RECOMMENDATION_ENGINE

## Objetivo

Criar o motor que transforma `DynamicExitMarketReading`/estado de mercado em
recomendacao dinamica read-only.

## Escopo Autorizado

- Arquivos/pastas permitidos:
  - `domain/`
  - `application/`
  - `tests/`
  - `docs/`
  - `governance/traceability/`
  - `governance/execution/`
- Camadas permitidas:
  - contratos de dominio;
  - servicos de aplicacao read-only;
  - view models e relatorios de auditoria;
  - testes unitarios.
- Camadas proibidas:
  - `infrastructure/execution/`
  - `mt5/experts/`
  - `.traderia/`
  - qualquer codigo que use `order_send()`.

## Dependencias

- `MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY`
- `MISSION_TIA-007_IMPLEMENTAR_MOTOR_DE_LEITURA_DE_MERCADO`
- `domain/contracts/dynamic_exit.py`
- `application/dynamic_exit_market_state_service.py`

## Tarefas

1. Criar motor read-only de recomendacao dinamica.
2. Mapear estados de mercado para acoes dinamicas:
   - `KEEP_ORIGINAL_PLAN`
   - `PROTECT_TO_BREAK_EVEN`
   - `TRAIL_BY_ATR`
   - `TRAIL_BY_STRUCTURE`
   - `TIGHTEN_BY_MOMENTUM_LOSS`
   - `TIME_DECAY_EXIT_WATCH`
   - `NO_ACTION_BAD_CONTEXT`
3. Exigir motivo e confianca em toda recomendacao.
4. Garantir `dynamic_exit_allowed_to_execute_demo = false`.
5. Integrar ao fluxo existente sem alterar execucao real.
6. Cobrir com testes unitarios.
7. Atualizar documentacao, rastreabilidade e ponteiros do ultimo inbox.

## Criterios de Aceite

- Recomendacao auditavel.
- Motivo obrigatorio.
- Confianca obrigatoria.
- Nenhuma execucao real.
- Nenhum movimento de SL/TP.
- Nenhuma alteracao no provider demo operacional.
- Ciclo Forex continua leve e sem recalculo pesado de Lab.

## Validacao Obrigatoria

- `python -m unittest tests.test_dynamic_exit_recommendation_service tests.test_dynamic_exit_market_state_service tests.test_lab_forex_mt5_contract tests.test_report_service tests.test_mt5_trade_audit_service tests.test_mt5_visual_signal_exporter`

Quando possivel:

- `python scripts/run_critical_ci.py`

## Rollback

Reverter o commit da missao para voltar ao estado da TIA-007.
