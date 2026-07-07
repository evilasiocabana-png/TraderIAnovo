# Execution Report

## Mission

`MISSION_TIA-027_EXECUCAO_ASSISTIDA_DEMO_MOVE_SL_SAIDA_DINAMICA`

## Status

`completed`

## Summary

Foi implementado o modo assistido para mover somente o SL de uma posicao existente em conta MT5 Demo, consumindo a decisao simulada aprovada da TIA-026.

O fluxo permanece desligado por padrao e exige confirmacao operacional explicita. Nenhuma ordem nova e aberta, nenhuma posicao e fechada e o TP e preservado.

## Implementado

- Criado contrato `DynamicExitDemoSLExecutionResult`.
- Criado servico `DynamicExitDemoSLExecutionService`.
- Adicionada flag `dynamic_exit_demo_sl_assisted_execution_enabled`, desligada por padrao.
- Adicionado metodo seguro `modify_demo_position_stop_loss` no `MT5DemoExecutionProvider`.
- Adicionado metodo de fachada `execute_dynamic_exit_demo_sl_assisted` no `DashboardService`.
- Adicionada auditoria em memoria para execucoes assistidas.
- Dashboard passou a exibir modo/gate/mensagem de SL assistido.
- Forex e Relatorio exibem o estado do modo assistido.
- API freeze e manifest arquitetural reconciliados.

## Gates Implementados

- Flag assistida precisa estar ligada.
- Usuario precisa confirmar explicitamente a acao.
- Robo Demo precisa estar armado.
- Ambiente precisa estar habilitado para Demo.
- Decisao simulada da TIA-026 precisa estar aprovada.
- Ticket MT5 precisa ser valido.
- BUY so aceita SL acima do stop atual e abaixo do preco atual.
- SELL so aceita SL abaixo do stop atual e acima do preco atual.
- Diferenca irrelevante e rejeitada.
- Execucao duplicada na mesma vela/janela e rejeitada.
- Provider revalida conta Demo antes de qualquer `TRADE_ACTION_SLTP`.
- Provider revalida posicao aberta, simbolo, ticket, lado e preco atual.
- TP e preservado exatamente no request SLTP.

## Guardrails

- Conta real permanece bloqueada.
- Nenhuma ordem nova foi aberta.
- Nenhuma posicao foi fechada.
- TP nao foi alterado.
- Nao houve execucao automatica por ciclo.
- Lab pesado nao foi recalculado.
- `.traderia` nao foi apagado.

## Validacao

Comandos executados:

```text
python -m unittest tests.test_dynamic_exit_demo_sl_execution_service tests.test_mt5_demo_execution_provider
python -m unittest tests.test_application_api.ApplicationApiFreezeTest tests.test_architecture_manifest.ArchitectureManifestTest
python -m compileall dashboard_app.py application domain infrastructure tests
python scripts\run_critical_ci.py
python scripts\architecture_audit.py
python scripts\architecture_health.py
python scripts\run_static_analysis.py
```

Resultados:

```text
test_dynamic_exit_demo_sl_execution_service + test_mt5_demo_execution_provider: OK, 21 testes
API/manifest tests: OK, 18 testes
compileall: OK
run_critical_ci.py: OK, 91 testes
architecture_audit.py: OK
architecture_health.py: BOM
run_static_analysis.py: OK_WITH_WARNINGS
```

Observacao: o unico warning de analise estatica e a ausencia opcional de `pyflakes`; nao houve erro de codigo.

## Arquivos Principais

- `domain/contracts/dynamic_exit_demo_sl.py`
- `application/dynamic_exit_demo_sl_execution_service.py`
- `infrastructure/execution/mt5_demo_execution_provider.py`
- `application/dashboard_service.py`
- `application/dashboard_view_model.py`
- `application/configuration_service.py`
- `core/configuration_manager.py`
- `dashboard_app.py`
- `tests/test_dynamic_exit_demo_sl_execution_service.py`
- `tests/test_mt5_demo_execution_provider.py`
- `tests/test_application_api.py`
- `architecture_manifest.json`

## Proxima Missao Recomendada

`MISSION_TIA-028_VALIDAR_SL_ASSISTIDO_DEMO_EM_AMBIENTE_CONTROLADO`

Objetivo: validar o modo assistido com MT5 Demo aberto, flag ligada manualmente e uma posicao demo real controlada, sem conta real.

## Commit

`PENDENTE`
