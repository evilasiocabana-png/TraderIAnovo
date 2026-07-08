# Runtime Guard Target Architecture

## Objetivo

Definir a arquitetura permanente recomendada para o Runtime Guard do TraderIA Novo. Esta proposta parte do estado atual do repositorio e organiza os componentes hoje dispersos em uma camada clara, testavel e segura.

## Estado Da Implementacao

A missao `MISSION_TIA-034_RUNTIME_GUARD_INFRASTRUCTURE_EXTRACTION` criou a primeira implementacao real em `core/runtime_guard/` e a fachada `application/runtime_guard_service.py`.

O alvo permanece evolutivo: novos ciclos podem migrar para o scheduler central em missoes futuras, mas a camada base ja existe, com lock, scheduler, state preserver, cleanup, health, event log e fila MT5.

## Principios

1. Runtime Guard protege o sistema; nao decide trade.
2. Lab continua definindo plano, setup, entrada, saida base e parametros.
3. MT5 executa apenas comandos explicitamente autorizados.
4. Relatorio observa e audita; nao decide.
5. Dashboard renderiza; nao acessa MT5 diretamente.
6. Estado operacional valido nao pode ser apagado por leitura vazia transitoria.
7. Limpeza automatica so pode atuar em recursos temporarios.
8. Reload total da pagina deve ser excecao, nunca padrao.

## Modulos Recomendados

```text
core/runtime_guard/
  runtime_lock.py
  runtime_scheduler.py
  runtime_state.py
  runtime_state_preserver.py
  runtime_cleanup_policy.py
  runtime_health.py
  runtime_event_log.py
  mt5_runtime_queue.py
```

### `runtime_lock.py`

Responsabilidade:

- manter lock ativo por repositorio;
- controlar PID, heartbeat e stale lock;
- impedir dois runtimes ACTIVE disputando MT5.

Origem atual:

- `core/runtime_lock_service.py`.

### `runtime_scheduler.py`

Responsabilidade:

- coordenar ciclos leves;
- respeitar horario Forex e feriados;
- controlar intervalos por tarefa;
- impedir loops caros no Streamlit;
- aplicar grace period de interacao.

Tarefas previstas:

- Forex light read;
- Relatorio audit refresh;
- Robo Demo online cycle;
- diagnosticos opcionais;
- health snapshot.

### `runtime_state.py`

Responsabilidade:

- manter contrato declarativo do estado runtime;
- separar estado operacional, visual, temporario e persistente.

Campos sugeridos:

```text
forex_last_valid_snapshot
demo_robot_last_visible_snapshot
lab_last_valid_suggestions
mt5_trade_audit_cache
runtime_events
render_durations
last_auto_load_at
last_report_load_at
last_critical_interaction_at
```

### `runtime_state_preserver.py`

Responsabilidade:

- aplicar politica de preservacao de estado;
- substituir leituras vazias por ultimo snapshot valido;
- registrar timestamp de preservacao;
- expor se o dado e atual ou preservado.

Casos atuais:

- Forex panel;
- Robo Demo panel;
- Lab setup suggestions;
- Relatorio com snapshot Forex preservado.

### `runtime_cleanup_policy.py`

Responsabilidade:

- classificar chaves e recursos;
- limpar somente temporarios;
- impedir remocao de estado operacional.

Deve oferecer:

```text
cleanup_temporary()
cleanup_expired()
cleanup_orphan_processes()
dry_run_cleanup()
```

### `runtime_health.py`

Responsabilidade:

- consolidar status do Runtime Guard;
- expor diagnostico sem acionar MT5;
- informar lock, ciclos, caches, eventos e memoria.

Saida sugerida:

```text
RuntimeHealth(
  mode,
  lock_status,
  forex_cycle_status,
  report_cycle_status,
  demo_robot_cycle_status,
  mt5_connection_status,
  cache_status,
  stale_resources,
  warnings
)
```

### `runtime_event_log.py`

Responsabilidade:

- registrar eventos do runtime em memoria e, opcionalmente, arquivo;
- manter tamanho limitado;
- permitir auditoria de ciclos e bloqueios.

Eventos canonicos:

- `FOREX_AUTO_CYCLE_STARTED`
- `FOREX_AUTO_CYCLE_SKIPPED_INTERVAL`
- `MT5_DIAGNOSTIC_ONLY_COMPLETED`
- `DEMO_ROBOT_ARM_REQUESTED`
- `DEMO_ROBOT_ONLINE_CYCLE_STARTED`
- `DEMO_ROBOT_ONLINE_CYCLE_COMPLETED`
- `RUNTIME_CLEANUP_REQUESTED`

### `mt5_runtime_queue.py`

Responsabilidade:

- centralizar requisicoes MT5;
- deduplicar chamadas identicas;
- aplicar prioridade e TTL;
- impedir chamadas concorrentes caras.

Fila sugerida:

| Prioridade | Tipo | Exemplo |
|---|---|---|
| 1 | operacao demo autorizada | mover SL assistido confirmado |
| 2 | leitura robo | checar posicao/estado para robo demo |
| 3 | Forex light read | atualizar pares |
| 4 | Relatorio audit | atualizar auditoria |
| 5 | diagnostico manual | teste conexao MT5 |

## Fluxo Alvo

```text
Dashboard
  |
  +-- RuntimeScheduler
        |
        +-- RuntimeLock
        +-- MT5RuntimeQueue
        +-- DashboardService facade
        |
        +-- RuntimeStatePreserver
              |
              +-- Forex Snapshot
              +-- Demo Robot Snapshot
              +-- Lab Suggestions Snapshot
              +-- Report Cache
```

## Politicas de Preservacao Operacional

Preservar quando uma leitura nova vier vazia, offline ou incompleta:

- ultimo snapshot Forex com pares;
- ultimo card do Robo Demo com plano/precos/status visivel;
- ultimas sugestoes do Lab;
- ultima auditoria MT5 valida;
- estado de aba selecionada;
- grace period de interacao.

Substituir imediatamente quando a leitura nova vier valida:

- pares Forex com `pairs` nao vazio;
- sugestoes Lab nao vazias;
- Robo Demo com plano/status visivel;
- auditoria MT5 com registros validos.

Limpar somente por acao explicita:

- snapshot visual do Robo Demo ao desarmar;
- caches temporarios por botao de limpeza;
- runtime lock stale;
- eventos antigos por limite de tamanho.

## Recursos Que Podem Ser Limpos Automaticamente

- caches temporarios de UI;
- logs temporarios em memoria;
- filas expiradas;
- locks stale;
- subprocessos orfaos confirmados;
- threads orfas confirmadas;
- snapshots visuais sem valor operacional;
- mensagens antigas de diagnostico;
- duracoes de render antigas.

## Recursos Que Nunca Podem Ser Alterados Pelo Runtime Guard

- posicao aberta;
- stop movel;
- trailing stop;
- break-even;
- alvo;
- entrada;
- plano do Lab;
- estado persistente do Robo Demo;
- Position Manager;
- ordens MT5;
- estrategia;
- historico local;
- banco `.traderia`;
- configuracoes persistentes.

## Roadmap Tecnico

1. Criar `core/runtime_guard/runtime_state.py` com tipos e chaves canonicas.
2. Extrair preservacao de snapshot do `dashboard_app.py` para `runtime_state_preserver.py`.
3. Extrair limpeza para `runtime_cleanup_policy.py`.
4. Promover `RuntimeLockService` para pacote `core/runtime_guard`.
5. Criar `RuntimeHealthService`.
6. Criar `RuntimeSchedulerService` com tarefas registradas.
7. Criar `MT5RuntimeQueue` com prioridade, TTL e deduplicacao.
8. Atualizar Dashboard para consumir somente contratos de Runtime Guard.
9. Adicionar testes de regressao de UI para leituras vazias/transitorias.
10. Documentar rollback por modulo.

## Criterio de Arquitetura Pronta

O Runtime Guard definitivo estara pronto quando:

- nenhum helper de preservacao critica ficar solto no dashboard;
- todos os ciclos passarem por scheduler;
- toda leitura MT5 passar por queue/lock;
- todo cleanup for dirigido por politica declarativa;
- o painel Runtime Health mostrar estado real sem acionar MT5;
- os testes cobrirem oscilacao de Forex, Lab, Relatorio e Robo Demo;
- rollback de cada modulo for documentado.
