# Runtime Guard Evolution Report

## Escopo

Este relatorio documenta a evolucao do conceito de Runtime Guard no TraderIA Novo ate o estado atual do repositorio. A analise e arquitetural e nao altera comportamento operacional.

O Runtime Guard deve ser entendido como a camada de protecao que mantem o sistema utilizavel enquanto MT5, Forex, Lab, Relatorio e Robo Demo atualizam em ciclos leves. Ele tambem define o que pode ser limpo, pausado, preservado ou bloqueado sem danificar ordens, posicoes, planos do Lab ou gestao de stop.

## 1. Visao Inicial

O objetivo original era evitar que o runtime do TraderIA ficasse pesado, duplicado ou destrutivo durante o uso com MT5 aberto. A necessidade nasceu de problemas praticos:

- ciclos automaticos consumindo maquina;
- diagnostico MT5 misturado com leitura operacional;
- refresh total da pagina quebrando interacao;
- Relatorio nao acompanhando operacoes abertas;
- Robo Demo ligando/desligando visualmente;
- sessoes do Streamlit apagando dados bons com leituras temporariamente vazias;
- risco de duas instancias tentarem usar MT5 ao mesmo tempo;
- necessidade de limpar caches e filas sem apagar `.traderia`, historico, Lab ou posicoes.

Na ideia inicial, o Runtime Guard deveria ser uma protecao operacional: observar, limitar, preservar e diagnosticar. Ele nao deveria decidir entrada, saida, stop, alvo ou ordem MT5.

## 2. Evolucao Cronologica

| Missao | Evolucao | Impacto |
|---|---|---|
| TIA-023 Otimizar Dynamic Exit Runtime | Adicionou cache LRU pequeno e fallback fechado no motor de saida dinamica. | Primeira consolidacao explicita de runtime leve: cache, fallback e ausencia de execucao operacional automatica. |
| TIA-025 Diagnostico Lentidao e Reset Filas Runtime | Criou diagnostico de performance, limpeza segura de filas/caches temporarios e medicao de render. | Runtime Guard passou a ter interface operacional para investigar lentidao sem acionar MT5 nem Lab pesado. |
| TIA-026 Corrigir Gates Estruturais API Dashboard | Moveu acesso rapido MT5 para `DashboardService.get_fast_mt5_forex_snapshot()` e removeu leitura proibida do dashboard. | Reforcou que UI nao deve acessar MT5/posicoes diretamente; runtime passa pela fachada. |
| TIA-027 Execucao Assistida Demo Move SL | Criou fluxo assistido de SL demo com gates fortes e confirmacao manual. | Mostrou a fronteira entre Runtime Guard e execucao: guard pode autorizar contexto, mas nao deve mover SL automaticamente. |
| TIA-028 Reparar Ciclo Robo Demo e Diagnostico MT5 | Separou diagnostico MT5 de ciclo operacional, criou `RuntimeLockService`, limitou ciclo do robo e isolou ciclo Forex/Relatorio. | Runtime Guard ganhou lock ativo, controle de concorrencia, separacao de responsabilidades e robot cycle proprio. |
| TIA-029 UX Refresh Estavel MT5 sem Reload Total | Removeu reload total padrao, usou fragmentos de topo, adicionou grace period de interacao critica e indicador de refresh. | Runtime Guard ganhou politica de refresh leve e protecao de UX. |
| Ajustes pos-TIA-029 | Preservou snapshot Forex, estado visual do Robo Demo e sugestoes do Lab durante leituras vazias/transitorias. | Runtime Guard passou a incluir preservacao visual/operacional contra oscilacao de dados. |

## 3. Estado Atual

### Runtime Lock

Implementado em `core/runtime_lock_service.py`. O lock grava `.traderia/runtime/runtime_lock.json`, controla PID ativo, remove locks de PID morto e considera lock stale apos `TRADERIA_RUNTIME_LOCK_STALE_SECONDS` (padrao 90 segundos).

No dashboard, `_load_mt5_forex_signals_locked()` e `_load_mt5_trade_audit_report_locked()` usam `MT5_FOREX_CYCLE_LOCK` mais `MT5_RUNTIME_LOCK.acquire_active()` para evitar concorrencia em leituras MT5.

### MT5 Background Cycle

Existe em `_start_mt5_forex_background_cycle_once()` e `_mt5_forex_background_cycle()`. Por padrao fica desligado por flags:

- `TRADERIA_BACKGROUND_CYCLE_ENABLED`
- `TRADERIA_MT5_BACKGROUND_CYCLE_ENABLED`

Quando ligado, respeita horario/feriado Forex e chama leitura bloqueada por lock.

### Auto Cycle

`_mt5_forex_auto_cycle_enabled()` combina flag de ambiente, estado de UI e horario Forex. `_maybe_run_mt5_forex_auto_cycle()` executa leitura leve em intervalo `TRADERIA_MT5_FOREX_AUTO_REFRESH_SECONDS` e preserva snapshot valido se a leitura leve vier vazia.

### Auto Refresh

`_inject_mt5_forex_auto_refresh()` nao faz reload total por padrao. Reload total so ocorre com `TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED=1`. O fluxo padrao usa fragmentos Streamlit em `exibir_mt5_forex_dashboard()` e `exibir_relatorios_dashboard()`.

### Runtime Cleanup

`_clear_runtime_queues_and_temporary_caches()` limpa somente chaves temporarias e caches Streamlit. Ele preserva configuracoes persistentes, Lab, `.traderia`, banco local, snapshots validos de tela e dados operacionais.

### Runtime Diagnostics

`_runtime_performance_snapshot()` mostra latencia, refresh id, ultima leitura MT5, lock busy, tamanho de session state, cache de relatorio e status do robo. A UI aparece em `Sistema Forex` no expander de performance.

### Runtime Events

`_record_runtime_event()` mantem os ultimos eventos em `RUNTIME_EVENT_LOG_KEY`. Eventos registram solicitacoes de armar robo, ciclos online, skips por intervalo, bloqueios e conclusoes.

### Demo Robot Online Cycle

`_run_demo_robot_online_cycle_if_due()` roda separado do ciclo Forex, limitado por `MT5_DEMO_ROBOT_INTERVAL_SECONDS`. A UI preserva estado visual com `MT5_DEMO_ROBOT_LAST_VISIBLE_SNAPSHOT_KEY`; leituras transitorias do backend nao apagam o ultimo card valido. O botao Desarmar e a acao explicita que limpa o estado.

Regra consolidada apos auditoria operacional:

- quando `.traderia/mt5_demo_robot_online_state.json` indicar `online=true`, o
  motor automatico de entrada deve ficar no ciclo de fundo do TraderIA Novo;
- a UI Streamlit nao deve ser a dona da execucao automatica, porque render,
  reload, troca de aba ou navegador dormindo podem interromper ou duplicar
  tentativas;
- com o ciclo de fundo ativo, as abas `MT5 Forex` e `Relatorios` apenas exibem
  o estado, preservam o ultimo snapshot visual e permitem comandos manuais;
- o heartbeat do ciclo fica em
  `.traderia/mt5_demo_robot_background_state.json`;
- qualquer futura mudanca no robo demo deve preservar essa separacao:
  background executa, UI observa.

Essa regra evita dois problemas ja observados em producao local:

1. robo marcado como online, mas sem novas entradas porque a aba parou de
   renderizar;
2. dupla tentativa no mesmo candle quando UI e ciclo de fundo avaliam ao mesmo
   tempo.

Regra de Modelo 1 + Modelo 2:

- em `TODOS_MODELOS`, Modelo 1 e Modelo 2 sao avaliados no mesmo ciclo, sem
  prioridade entre eles;
- se ambos estiverem prontos no mesmo candle, ambos podem enviar ordem;
- a trava operacional fica no provider: no maximo uma posicao por modelo no
  mesmo par;
- Modelo 2 nao pode ser vetado pelo regime direcional usado pelo Modelo 1,
  porque sua propria tese e espelhada e ja exige ADX < 20;
- demais guardrails continuam ativos: horario, plano valido, risco, provider,
  duplicidade por modelo e consistencia de stop/alvo.

### Runtime Health

Runtime health e composto por lock busy, status de MT5, status do Robo Demo, historico de eventos, duracoes de render e mensagens de diagnostico. Ainda nao existe um modulo unico `RuntimeHealthService`; hoje isso esta distribuido no `dashboard_app.py`.

### Runtime Cache e Session State

O estado atual depende de `st.session_state` para:

- service singleton;
- ultima leitura MT5;
- ultimo snapshot Forex valido;
- ultimo snapshot visual do Robo Demo;
- ultimas sugestoes validas do Lab;
- cache de auditoria MT5;
- grace period de interacao;
- mensagens e eventos temporarios.

### MT5 Queue

Nao ha uma fila MT5 formal unica. O comportamento equivalente hoje e composto por locks, intervalo de ciclo, deduplicacao curta no provider/servico MT5 e caches de auditoria. Isso resolve parte do problema, mas ainda nao e uma arquitetura permanente de fila.

## 4. Diagrama Textual

```text
Streamlit UI
  |
  +-- Fragment MT5 Forex (10s)
  |     |
  |     +-- _maybe_run_mt5_forex_auto_cycle
  |     |     |
  |     |     +-- MT5_FOREX_CYCLE_LOCK
  |     |     +-- RuntimeLockService (.traderia/runtime/runtime_lock.json)
  |     |     +-- DashboardService.load_mt5_forex_signals
  |     |
  |     +-- Stable Forex Snapshot
  |     +-- Demo Robot Panel
  |           |
  |           +-- Demo Robot Online Cycle
  |           +-- Stable Robot Snapshot
  |
  +-- Fragment Relatorios (10s)
  |     |
  |     +-- _maybe_refresh_mt5_trade_audit_report
  |     +-- MT5 trade audit cache
  |
  +-- Lab
  |     |
  |     +-- DashboardService.suggest_mt5_lab_setups
  |     +-- Stable Lab Suggestions Snapshot
  |
  +-- Sistema Forex
        |
        +-- Runtime Performance Snapshot
        +-- Cleanup temporario
        +-- Pause auto-cycle UI
```

## 5. Problemas Encontrados

### Resolvidos

- Diagnostico MT5 deixou de iniciar ciclo operacional.
- Refresh total deixou de ser padrao.
- Robo Demo saiu do ciclo Forex.
- Relatorio passou a ter ciclo leve proprio.
- Snapshot Forex valido passou a ser preservado.
- Card do Robo Demo passou a ser estavel durante polling.
- Sugestoes do Lab passaram a preservar ultimo snapshot valido.
- UI deixou de depender de leituras diretas proibidas de MT5.

### Ainda frageis

- Runtime Guard esta concentrado demais em `dashboard_app.py`.
- Session state mistura caches, flags de UI, snapshots operacionais e mensagens.
- Nao ha uma fila MT5 formal com prioridade, TTL e deduplicacao centralizada.
- Runtime Health ainda e uma agregacao de helpers, nao um contrato.
- O lock ativo protege leitura, mas nao e um orquestrador completo de recursos.
- Preservacao de estado visual foi adicionada em pontos separados; precisa virar politica unificada.
- Relatorio, Forex, Lab e Robo compartilham o mesmo periodo de refresh, mas nao ha scheduler central.

## 6. Comparacao

| Ideia inicial | Implementacao atual | Diferencas | Beneficios | Riscos | Recomendacao |
|---|---|---|---|---|---|
| Evitar maquina travada por ciclos | Intervalos, flags, fragments, cleanup e lock | Ainda sem scheduler unico | Menos reload e menos carga | Logica dispersa | Criar `RuntimeSchedulerService` |
| Separar diagnostico de operacao | Diagnostico MT5 read-only e sem ciclo | Ainda renderizado no dashboard | Evita disparos acidentais | UI ainda conhece demais | Criar `RuntimeDiagnosticsService` |
| Proteger MT5 contra concorrencia | `RuntimeLockService` com PID/stale | Lock nao modela prioridade | Evita duas instancias ativas | Lock pode ficar stale em casos raros | Adicionar heartbeat explicito |
| Manter UI estavel | Snapshots validos preservados | Feito por helpers locais | Reduz pisca/some | Politica espalhada | Criar `RuntimeStatePreserver` |
| Limpar sem destruir | Cleanup temporario restrito | Lista manual de chaves | Ajuda em lentidao | Pode esquecer novas chaves | Classificar chaves por tipo |
| Nao recalcular Lab pesado | Ciclo leve nao chama pesquisa pesada | Lab ainda renderiza sugestoes | Preserva performance | Falta cache formal de Lab UI | Criar cache TTL por aba |
| Robo demo controlado | Ciclo proprio por intervalo | Estado visual e operacional ainda acoplados | Menos oscilacao | Risco de confundir snapshot antigo com estado atual | Mostrar timestamp do snapshot preservado |

## 7. Problemas Introduzidos

- Fragmentos Streamlit reduziram reload, mas expuseram erros frontend `removeChild` quando a arvore visual muda demais.
- A preservacao de snapshots melhora UX, mas exige indicar que o dado e ultimo estado valido.
- O lock reduz concorrencia, mas pode bloquear leituras se processo antigo parecer vivo.
- O uso de `session_state` como barramento aumentou a necessidade de politica formal de chaves.

## 8. O Que Ainda Falta

- Extrair Runtime Guard para modulos fora do dashboard.
- Criar contrato `RuntimeState`.
- Criar scheduler leve para Forex, Relatorio, Robo e diagnosticos.
- Criar fila MT5 formal com deduplicacao e prioridades.
- Criar politica declarativa de chaves preservaveis/limpaveis.
- Registrar timestamps para snapshots preservados.
- Criar painel unico de Runtime Health.
- Criar testes de regressao para oscilacao de UI em Forex, Robo e Lab.

## 9. O Que Deve Virar Arquitetura Permanente

- Lock ativo por repositorio.
- Separacao diagnostico vs operacao.
- Refresh leve por fragmento ou scheduler, sem reload total padrao.
- Preservacao de ultimo snapshot operacional valido.
- Cleanup estritamente temporario.
- Runtime events auditaveis.
- Robo Demo em ciclo proprio, separado do Forex.
- Relatorio como observador, nao decisor.
- Lab pesado somente sob comando explicito.
