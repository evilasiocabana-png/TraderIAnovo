# Execution Report

## Mission

`MISSION_TIA-026_EXECUCAO_SIMULADA_SAIDA_DINAMICA_STOP_MANAGEMENT`

## Status

`completed`

## Summary

Foi implementada a camada de simulacao/paper da saida dinamica para stop management.

A missao cria uma decisao auditavel de stop dinamico sem executar ordem real, sem fechar posicao e sem modificar SL/TP no MT5. O Provider Demo operacional permanece inalterado.

## Implementado

- Criado contrato `DynamicExitSimulationDecision`.
- Criado servico `DynamicExitSimulationService`.
- Adicionada flag `dynamic_exit_simulation_enabled`, desligada por padrao.
- Integrado o resultado da simulacao ao `DashboardService`.
- Adicionados campos de simulacao ao `DashboardMT5ForexSignalRowViewModel`.
- Exibidos campos de simulacao na aba Forex e no relatorio/auditoria.
- Adicionados testes unitarios para gates de simulacao.
- Reconciliados `tests/test_application_api.py` e `architecture_manifest.json`.

## Gates Implementados

- Simulacao so ocorre com flag ligada.
- Simulacao exige robo armado.
- Simulacao exige posicao aberta/snapshot posicionado.
- Simulacao exige plano `PLANO_VALIDO`.
- `TIME_DECAY_EXIT_WATCH` permanece observacional.
- Somente as acoes abaixo podem simular stop:
  - `PROTECT_TO_BREAK_EVEN`
  - `TRAIL_BY_ATR`
  - `TRAIL_BY_STRUCTURE`
  - `TIGHTEN_BY_MOMENTUM_LOSS`
- BUY nao aceita stop que piore risco nem stop acima do preco atual.
- SELL nao aceita stop que piore risco nem stop abaixo do preco atual.
- Diferenca irrelevante de stop e rejeitada.
- Simulacao duplicada na mesma chave/candle e rejeitada.
- Spread excessivo bloqueia simulacao.

## Guardrails

- Nenhuma ordem real foi enviada.
- Nenhum SL/TP foi movido no MT5.
- Nenhuma posicao foi fechada.
- Provider Demo operacional nao foi alterado.
- Lab pesado nao foi recalculado no ciclo leve.
- `.traderia` nao foi apagado.

## Ajuste Corretivo Durante Validacao

Durante o `run_critical_ci.py`, foram detectadas duas regressoes nos gates do Dashboard e depois uma falha de continuidade de regime.

Correcoes aplicadas:

- A linha Forex pronta nao e mais recarregada via provider quando nao ha linha ativa do Lab exigindo timeframe especifico.
- Candles em cache continuam disponiveis para marcar entrada teorica.
- Decisao `WAIT` volta a aparecer como `FORA_DA_ZONA_DE_INTERESSE`.
- Continuidade de regime `TREND_MOMENTUM` continua autorizando entrada teorica quando tendencia, momentum e RSI estao alinhados.

## Validacao

Comandos executados:

```text
python -m unittest tests.test_dynamic_exit_simulation_service
python -m compileall dashboard_app.py application domain research tests
python -m unittest tests.test_application_api.ApplicationApiFreezeTest tests.test_architecture_manifest.ArchitectureManifestTest
python scripts\run_critical_ci.py
python scripts\architecture_audit.py
python scripts\architecture_health.py
python scripts\run_static_analysis.py
```

Resultados:

```text
tests.test_dynamic_exit_simulation_service: OK, 8 testes
compileall: OK
API/manifest tests: OK, 18 testes
run_critical_ci.py: OK, 88 testes
architecture_audit.py: OK
architecture_health.py: BOM
run_static_analysis.py: OK_WITH_WARNINGS
```

Observacao: o unico warning de analise estatica e a ausencia opcional de `pyflakes`; nao houve erro de codigo.

## Arquivos Principais

- `domain/contracts/dynamic_exit_simulation.py`
- `application/dynamic_exit_simulation_service.py`
- `application/dashboard_service.py`
- `application/dashboard_view_model.py`
- `application/configuration_service.py`
- `core/configuration_manager.py`
- `dashboard_app.py`
- `tests/test_dynamic_exit_simulation_service.py`
- `tests/test_application_api.py`
- `architecture_manifest.json`

## Proxima Missao Recomendada

`MISSION_TIA-027_ATUALIZAR_BASELINE_ARQUITETURAL_INFORMATIVO`

Motivo: a implementacao adicionou contrato e servico novos; os gates passaram, mas o baseline informativo deve ser reconciliado formalmente.

## Commit

`PENDENTE`
