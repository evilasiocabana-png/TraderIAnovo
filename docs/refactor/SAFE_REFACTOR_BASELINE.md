# Baseline da Refatoracao Segura

Data: 2026-08-13
Branch: `codex/safe-refactor-foundation`
Base operacional: `8ee6ed9`
Worktree isolado: `C:\Users\evcab\TraderIAnovo_Refactor_Safe`

## Pontos de restauracao

- Tag Git: `restore-traderia-20260813-2217`
- Pacote local: `.traderia/restore_points/20260813_221713`
- Aplicacao operacional preservada em `127.0.0.1:8532`.

## Escopo desta fundacao

- corrigir a ferramenta de auditoria para ler Python com BOM UTF-8;
- reconciliar o manifesto com contratos publicos ja existentes;
- registrar invariantes de equivalencia;
- estabelecer suites de caracterizacao e gates;
- nao alterar runtime, estrategia, MT5, Lab, modelos ou ordens.

## Estado encontrado

- O manifesto omitia `LabOperationalModelService`.
- O manifesto omitia `BetaDecision`, `BetaStrategy` e
  `BetaStrategyContext`.
- A auditoria falhava antes de gerar o relatorio ao encontrar BOM UTF-8.
- A baseline historica esta muito defasada: ela nao deve ser atualizada de
  forma automatica durante a refatoracao.
- Os caminhos de governanca declarados em `AGENTS.md` nao correspondiam aos
  arquivos existentes.

## Suites de caracterizacao

```text
tests/test_architecture_manifest.py
tests/test_architecture_baseline.py
tests/test_lab_forex_mt5_contract.py
tests/test_dashboard_view_model.py
tests/test_mt5_market_data_service.py
tests/test_mt5_demo_robot_service.py
tests/test_mt5_demo_execution_provider.py
tests/test_model23_basket_accumulator.py
tests/test_position_manager_service.py
tests/test_operational_indicator_window.py
tests/test_runtime_lock_service.py
tests/test_weekly_robot_schedule.py
```

## Limites

Os testes deste worktree nao conectam ao MT5 e nao enviam ordens. Validacao
viva permanece separada e somente observa o aplicativo operacional existente.

## Resultado inicial dos gates

- Auditoria arquitetural: manifesto `OK`.
- Baseline historica: `DRIFT` informativo preservado.
- Testes de manifesto e baseline: 22 aprovados.
- Caracterizacao operacional ampla: 270 aprovados e 10 falhas preexistentes.

As dez falhas nao foram ocultadas:

- sete testes de `MT5MarketDataService` ainda exigem 1.000 candles no ciclo
  leve, enquanto o contrato atual usa 200 fechados mais o candle corrente;
- tres testes do provider demonstram que IDs historicos de M8, M21 e M22 podem
  escapar da lista de aposentados pelo fallback numerico da politica.

O primeiro grupo exige reconciliacao dos testes de caracterizacao com o
contrato vigente. O segundo e uma falha operacional real e deve ser corrigido
em incremento proprio antes de qualquer refatoracao do executor.

## Sequencia segura

1. Tornar auditoria e manifesto confiaveis.
2. Congelar comportamento com testes de caracterizacao.
3. Medir ciclo e memoria antes de tocar runtime.
4. Refatorar um componente por commit.
5. Repetir todos os gates.
6. Integrar somente depois da revisao do diff e rollback confirmado.
