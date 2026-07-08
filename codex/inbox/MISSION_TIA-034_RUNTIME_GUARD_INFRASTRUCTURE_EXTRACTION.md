# MISSION_TIA-034_RUNTIME_GUARD_INFRASTRUCTURE_EXTRACTION

## Tipo

Execucao unica para Codex no repositorio `TraderIAnovo`.

## Objetivo

Retomar o conceito de Runtime Guard e transforma-lo em uma camada real de infraestrutura, separada do `dashboard_app.py`, para proteger desempenho, estado visual, locks, ciclos leves, limpeza segura, eventos e diagnostico.

Esta missao NAO implementa decisao operacional de trade.

## Regra principal

Runtime Guard e infraestrutura de protecao do aplicativo.

Ele pode:

```text
- controlar lock de runtime;
- organizar ciclos leves;
- preservar ultimo snapshot valido;
- evitar reload total;
- limpar somente recursos temporarios;
- registrar eventos;
- expor health snapshot;
- reduzir concorrencia de leituras;
- deixar dashboard mais leve.
```

Ele nao pode:

```text
- decidir trade;
- alterar posicao;
- alterar stop;
- alterar alvo;
- abrir ou fechar operacao;
- recalcular Research Lab pesado automaticamente;
- substituir papel do Position Manager;
- substituir DemoExecutionService;
- apagar estado operacional protegido.
```

## Arquitetura alvo

Criar ou consolidar:

```text
core/runtime_guard/
  __init__.py
  runtime_lock.py
  runtime_scheduler.py
  runtime_state.py
  runtime_state_preserver.py
  runtime_cleanup_policy.py
  runtime_health.py
  runtime_event_log.py
  mt5_runtime_queue.py

application/runtime_guard_service.py
```

Se ja existirem modulos equivalentes, reaproveitar sem quebrar compatibilidade.

## Extracao do dashboard

Auditar `dashboard_app.py` e extrair apenas responsabilidades de runtime:

```text
- locks;
- auto-cycle leve;
- auto-refresh;
- cleanup temporario;
- diagnostico de performance;
- eventos de runtime;
- preservacao de snapshots;
- health snapshot;
- controle de intervalo;
- grace period de interacao;
- deduplicacao de leituras.
```

O dashboard deve ficar como camada de renderizacao e chamada de servicos.

## Runtime State

Separar estado em categorias:

```text
OPERACIONAL_PROTEGIDO
VISUAL_PRESERVAVEL
TEMPORARIO_LIMPAVEL
DIAGNOSTICO
PERSISTENTE
UNKNOWN
```

Regras:

```text
TEMPORARIO_LIMPAVEL -> pode limpar
VISUAL_PRESERVAVEL -> substituir somente por nova leitura valida
OPERACIONAL_PROTEGIDO -> nunca limpar automaticamente
PERSISTENTE -> nunca limpar automaticamente
DIAGNOSTICO -> pode atualizar sem side effect
UNKNOWN -> nao limpar
```

## State Preserver

Preservar ultimo snapshot valido quando leitura nova vier vazia, offline ou incompleta:

```text
- Forex snapshot;
- Robo Demo visual snapshot;
- Lab setup suggestions;
- relatorio/auditoria visual;
- aba selecionada;
- mensagens recentes de runtime.
```

Quando nova leitura for valida, substituir o snapshot preservado.

## Cleanup Policy

Implementar:

```text
cleanup_temporary()
cleanup_expired()
dry_run_cleanup()
```

A limpeza deve ser classificada e segura. Se a classificacao for desconhecida, nao limpar.

## Scheduler

Criar scheduler leve para coordenar ciclos de interface e leitura leve:

```text
- Forex light read;
- Relatorio refresh leve;
- Robo Demo visual refresh;
- diagnosticos opcionais;
- health snapshot.
```

Obrigatorio:

```text
- respeitar intervalos configuraveis;
- evitar loops caros no Streamlit;
- aplicar grace period durante interacao critica;
- nao disparar calculo pesado do Lab;
- nao usar diagnostico como ciclo operacional.
```

## Event Log

Criar log de eventos de runtime com limite de tamanho.

Eventos sugeridos:

```text
RUNTIME_STARTED
RUNTIME_LOCK_ACQUIRED
RUNTIME_LOCK_BUSY
RUNTIME_LOCK_STALE_CLEARED
FOREX_AUTO_CYCLE_STARTED
FOREX_AUTO_CYCLE_SKIPPED_INTERVAL
FOREX_AUTO_CYCLE_COMPLETED
REPORT_REFRESH_STARTED
REPORT_REFRESH_COMPLETED
DIAGNOSTIC_ONLY_COMPLETED
RUNTIME_CLEANUP_REQUESTED
RUNTIME_CLEANUP_COMPLETED
SNAPSHOT_PRESERVED
SNAPSHOT_REPLACED_BY_VALID_READ
```

## Health Snapshot

Criar snapshot consolidado:

```text
mode
lock_status
forex_cycle_status
report_cycle_status
demo_robot_cycle_status
cache_status
stale_resources
warnings
last_events
render_durations
```

Health nao pode ter efeito colateral operacional.

## MT5 Runtime Queue

Se viavel, criar uma fila simples/deduplicador para leituras MT5.

Objetivo:

```text
- evitar leituras duplicadas;
- aplicar TTL;
- reduzir concorrencia;
- registrar skips;
- melhorar desempenho.
```

Se nao for seguro implementar agora, documentar como pendencia sem alterar comportamento.

## Testes obrigatorios

Criar testes para:

```text
1. Runtime Guard nao altera estado operacional protegido.
2. Cleanup remove somente temporarios.
3. Cleanup nao remove OPERACIONAL_PROTEGIDO.
4. Snapshot valido e preservado quando leitura vem vazia.
5. Snapshot e substituido quando leitura nova e valida.
6. Lock impede duas instancias ativas.
7. Lock stale pode ser limpo.
8. Scheduler respeita intervalo minimo.
9. Scheduler nao dispara Lab pesado.
10. Diagnostico nao inicia ciclo operacional.
11. Queue deduplica leituras identicas, se implementada.
12. Health snapshot nao tem side effect.
13. Event log respeita limite de tamanho.
14. Dashboard consegue consumir RuntimeGuardService.
```

## Documentacao obrigatoria

Atualizar ou criar:

```text
docs/architecture/RUNTIME_GUARD_IMPLEMENTATION.md
docs/architecture/RUNTIME_GUARD_TARGET_ARCHITECTURE.md
docs/architecture/RUNTIME_PRESERVATION_POLICY.md
```

A documentacao deve explicar:

```text
- o que Runtime Guard faz;
- o que Runtime Guard nunca faz;
- diferenca entre Runtime Guard, Position Manager, Research Lab e Dashboard;
- como lock, scheduler, state preserver, cleanup, health e event log se conectam;
- rollback.
```

## Criterios de aceite

```text
- Runtime Guard existe como camada propria fora do dashboard_app.py;
- dashboard_app.py fica mais leve;
- nenhuma regra operacional e alterada;
- cleanup e classificado e seguro;
- health snapshot consolidado existe;
- event log existe;
- scheduler leve existe;
- state preserver existe;
- testes passam;
- documentacao e atualizada;
- relatorio final e gerado.
```

## Relatorio esperado

Gerar:

```text
codex/completed/MISSION_TIA-034_RUNTIME_GUARD_INFRASTRUCTURE_EXTRACTION/EXECUTION_REPORT.md
```

O relatorio deve conter:

```text
- status;
- arquivos criados;
- arquivos alterados;
- helpers extraidos do dashboard;
- modulos criados;
- testes executados;
- resultado dos testes;
- riscos remanescentes;
- rollback;
- proxima missao recomendada.
```

## Proxima missao recomendada

```text
MISSION_TIA-035_RUNTIME_GUARD_POSITION_MANAGER_OBSERVABILITY
```

A proxima missao deve integrar observabilidade entre Runtime Guard e Position Manager, sem transferir decisao operacional para o Runtime Guard.
