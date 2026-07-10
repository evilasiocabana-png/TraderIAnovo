# EXECUTION REPORT — INVESTIGACAO_CONTRATO_POSITION_MANAGER

Data: 2026-07-09
Status: completed
Responsavel: Codex
Tipo: auditoria documental

## Escopo

Executar a missão pendente em `codex/inbox/INVESTIGACAO_CONTRATO_POSITION_MANAGER.md`.

A missão pedia investigação, sem alteração de código, sobre o contrato atual entre:

- Research Lab;
- Trade Plan;
- Robo Demo;
- Position Manager;
- Relatorio.

## Resultado

A investigação está consolidada nos documentos oficiais já produzidos no projeto:

- `docs/architecture/TRADE_ENTRY_EXIT_CONTRACT_AUDIT.md`
- `docs/architecture/POSITION_MANAGER_TARGET_ARCHITECTURE.md`
- `docs/architecture/POSITION_MANAGER_OFFICIAL_CONTRACT.md`
- `docs/architecture/POSITION_MANAGER.md`

## Resumo Executivo

O contrato atual ficou definido assim:

```text
Research Lab
  decide setup, timeframe, direção, parâmetros de entrada, risco inicial e RR

Trade Plan
  materializa entrada, stop inicial e alvo inicial

Robo Demo
  executa somente abertura da posição em MT5 Demo

Position Manager
  atua somente após posição aberta
  protege por SL mais protetivo
  não recalcula Lab
  não altera TP
  não abre nova ordem
  não executa EARLY_EXIT/FULL_EXIT no fluxo operacional normal

Relatório
  audita plano inicial, execução, Position Manager, stop móvel e resultado
```

## Pontos Confirmados

- `stop_management` é hint legado/compatibilidade, não aprovação de saída.
- A entrada não depende da escolha de melhor saída.
- O Lab não deve pré-definir a saída executada.
- O Position Manager decide dinamicamente apenas depois da posição aberta.
- A fase operacional atual é conservadora: proteger SL, não fechar antecipadamente.
- O stop móvel só pode mover se for mais protetivo e após confirmação mínima de avanço da posição.

## Validação

Esta execução não alterou código operacional.

Validações recentes relacionadas ao contrato:

```text
tests.test_position_manager_service: OK
tests.test_mt5_demo_robot_service: OK
tests.test_mt5_demo_execution_provider: OK
tests.test_dashboard_app_runtime: OK nos testes focados de relatório
tests.test_forex_time_layer: OK
```

## Guardrails

Nenhuma alteração feita por este inbox:

- não abriu ordem;
- não fechou posição;
- não moveu SL/TP;
- não recalculou Lab;
- não alterou execução MT5;
- não apagou `.traderia`.

## Status Final

Missão concluída como auditoria documental.

Próxima ação recomendada: manter a fila `codex/inbox` apenas com missões executáveis. Arquivos de ponteiro, como `RESULTADO_DO_ULTIMO_INBOX.md`, devem ser tratados como material informativo, não como missão.
