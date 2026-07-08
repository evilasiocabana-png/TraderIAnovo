# Runtime Guard Implementation

## Status

Implementacao inicial criada na missao `MISSION_TIA-034_RUNTIME_GUARD_INFRASTRUCTURE_EXTRACTION`.

O Runtime Guard agora existe como camada propria de infraestrutura em:

```text
core/runtime_guard/
application/runtime_guard_service.py
```

## O Que Faz

Runtime Guard protege a operacao do aplicativo:

- controla lock de runtime;
- coordena ciclos leves por intervalo;
- preserva snapshots visuais validos;
- limpa somente estado temporario classificado;
- registra eventos de runtime;
- expoe health snapshot read-only;
- deduplica leituras MT5 por TTL.

## O Que Nunca Faz

Runtime Guard nao pode:

- decidir entrada;
- decidir saida operacional;
- abrir posicao;
- fechar posicao;
- mover stop;
- alterar alvo;
- recalcular Research Lab pesado automaticamente;
- substituir Position Manager;
- substituir DemoExecutionService.

## Componentes

### RuntimeLock

`core/runtime_guard/runtime_lock.py`

Fachada sobre o lock legado `core/runtime_lock_service.py`. Impede dois runtimes `ACTIVE` disputando leituras MT5 e permite limpar lock stale.

### RuntimeScheduler

`core/runtime_guard/runtime_scheduler.py`

Controla se um ciclo leve pode rodar pelo intervalo minimo. Tambem bloqueia execucao em grace period de UI e em modo diagnostico.

### RuntimeState

`core/runtime_guard/runtime_state.py`

Classifica estado em:

- `OPERACIONAL_PROTEGIDO`;
- `VISUAL_PRESERVAVEL`;
- `TEMPORARIO_LIMPAVEL`;
- `DIAGNOSTICO`;
- `PERSISTENTE`;
- `UNKNOWN`.

Chaves desconhecidas nao sao limpas.

### RuntimeStatePreserver

`core/runtime_guard/runtime_state_preserver.py`

Preserva ultimo snapshot valido quando a leitura nova vem vazia ou incompleta. Integrado inicialmente a:

- snapshot Forex;
- sugestoes de setup do Lab.

### RuntimeCleanupPolicy

`core/runtime_guard/runtime_cleanup_policy.py`

Remove somente `TEMPORARIO_LIMPAVEL`. Estado operacional protegido e chaves desconhecidas sao preservadas.

### RuntimeEventLog

`core/runtime_guard/runtime_event_log.py`

Log circular com limite de tamanho.

### RuntimeHealthSnapshot

`core/runtime_guard/runtime_health.py`

Snapshot read-only com modo, lock, ciclos, cache, recursos stale, alertas, eventos recentes e duracoes de renderizacao.

### MT5RuntimeQueue

`core/runtime_guard/mt5_runtime_queue.py`

Deduplicador TTL para futuras leituras MT5. Nesta fase ele nao altera chamadas existentes de MT5; fica disponivel para integracoes controladas.

## Integracao No Dashboard

`dashboard_app.py` consome `RuntimeGuardService` para:

- registrar eventos;
- limpar temporarios;
- preservar snapshots visuais;
- coordenar ciclos leves de Forex e Relatorio;
- expor health no diagnostico de performance.

O dashboard continua sendo camada de renderizacao. A decisao operacional permanece fora dele.

## Diferenca Entre Camadas

| Camada | Responsabilidade |
| --- | --- |
| Research Lab | Define Alpha, setup, entrada teorica, saida base e parametros. |
| Runtime Guard | Protege runtime, cache, scheduler, lock, health e limpeza segura. |
| Position Manager | Acompanha posicao aberta e calcula/move SL seguro quando autorizado. |
| DemoExecutionService | Envia/modifica ordens Demo por porta autorizada. |
| Dashboard | Renderiza estado e aciona fachadas de aplicacao. |

## Rollback

Para rollback:

1. Reverter commit da missao.
2. Remover `core/runtime_guard/`.
3. Remover `application/runtime_guard_service.py`.
4. Restaurar helpers locais anteriores em `dashboard_app.py`.
5. Rodar `python scripts/run_critical_ci.py`.

## Riscos Remanescentes

- A fila MT5 foi criada como infraestrutura, mas ainda nao substitui todas as leituras.
- Nem todos os snapshots visuais foram migrados para `RuntimeStatePreserver`.
- A observabilidade do Position Manager ainda sera integrada em missao propria.

## Proxima Missao Recomendada

`MISSION_TIA-035_RUNTIME_GUARD_POSITION_MANAGER_OBSERVABILITY`
