# MISSION_TIA-028 — Reparar ciclo do robô demo e efeitos colaterais do diagnóstico MT5

## Contexto

Após alteração do ciclo/auto-refresh para aproximadamente 10 segundos, o usuário relata que não consegue ligar o robô. Antes de acionar o ciclo, o robô aparecia offline.

No estado atual do GitHub, foram observados indícios de acoplamento indevido entre diagnóstico, ciclo Forex, thread de fundo e monitoramento online do robô demo.

## Problema observado no código

Em `dashboard_app.py`, o botão `Atualizar diagnostico MT5` ainda executa ações operacionais:

- chama `service.test_mt5_connection(...)`;
- em seguida chama `_load_mt5_forex_signals_locked(...)`;
- atualiza `data = service.get_light_dashboard_view_model()`;
- seta `st.session_state[MT5_FOREX_AUTO_CYCLE_UI_KEY] = True`;
- atualiza `MT5_FOREX_LAST_AUTO_LOAD_KEY`;
- chama `_start_mt5_forex_background_cycle_once(force=True)`;
- exibe mensagem dizendo que o ciclo automático foi ligado.

Isso transforma diagnóstico em gatilho operacional e pode criar concorrência com o ciclo do robô.

Além disso, `get_dashboard_service()` chama `_start_mt5_forex_background_cycle_once()` na criação/obtenção do serviço. Essa função pode iniciar thread se o auto-cycle UI estiver ativo.

O robô demo, por sua vez, depende de `st.session_state[MT5_DEMO_ROBOT_ONLINE_KEY]` e executa `service.run_online_demo_robot_cycle(...)` durante renderização da aba. Se o auto-refresh/rerun não estiver bem isolado, o robô pode ficar armado visualmente, mas sem ciclo online confiável.

## Objetivo

Restaurar a capacidade de ligar o robô demo e separar completamente:

1. Diagnóstico MT5;
2. Ciclo visual/Forex;
3. Ciclo online do robô demo;
4. Thread de fundo.

A correção NÃO deve alterar lógica de trading, Lab, decisão de entrada, stop móvel, saída dinâmica, ordem real ou estratégia.

---

# Tarefa 1 — Corrigir botão “Atualizar diagnóstico MT5”

O botão deve apenas diagnosticar.

Remover dele qualquer ação que:

- carregue Forex operacional;
- ligue `MT5_FOREX_AUTO_CYCLE_UI_KEY`;
- atualize `MT5_FOREX_LAST_AUTO_LOAD_KEY`;
- force `_start_mt5_forex_background_cycle_once(force=True)`;
- inicie thread de fundo;
- inicie ciclo automático;
- arme ou desarme robô.

Fluxo correto:

```python
if button_atualizar_diagnostico:
    diagnostic = service.test_mt5_connection(symbol=symbol, timeframe=timeframe)
    st.session_state[MT5_FOREX_MANUAL_DIAGNOSTIC_KEY] = diagnostic
    st.session_state[MT5_FOREX_MANUAL_DIAGNOSTIC_MESSAGE_KEY] = (
        "Diagnóstico MT5 atualizado. Nenhum ciclo automático foi iniciado."
    )
```

## Critério de aceite

Clicar em `Atualizar diagnostico MT5` não altera:

- `MT5_FOREX_AUTO_CYCLE_UI_KEY`;
- `MT5_DEMO_ROBOT_ONLINE_KEY`;
- estado do robô;
- thread de fundo;
- Position Manager;
- stop móvel.

---

# Tarefa 2 — Separar ciclo Forex do ciclo do robô demo

O ciclo Forex serve para atualizar leitura/sinais.

O ciclo do robô demo serve para monitorar gatilho e eventualmente enviar ordem demo.

Eles devem ter controles independentes:

- `MT5_FOREX_AUTO_CYCLE_UI_KEY`: apenas leitura/sinais Forex;
- `MT5_DEMO_ROBOT_ONLINE_KEY`: apenas monitoramento online do robô demo.

Nenhum botão de diagnóstico deve ligar qualquer um deles.

## Critério de aceite

O robô demo pode ser armado mesmo com ciclo Forex desligado, desde que os critérios de segurança do backend estejam satisfeitos.

---

# Tarefa 3 — Reparar fluxo de “Armar robô demo”

Ao clicar em `Armar robo demo`:

1. aplicar preferência de sessão Forex;
2. habilitar execução demo somente para a sessão local;
3. chamar `service.arm_demo_robot(pair=selected_pair, timeframe=timeframe)`;
4. obter estado atualizado do backend;
5. se o backend retornar status armável, setar `MT5_DEMO_ROBOT_ONLINE_KEY=True`;
6. se backend bloquear, manter False e exibir motivo claro.

Revisar `_demo_robot_online_allowed(...)` para não bloquear indevidamente estados válidos de monitoramento.

Estados aceitáveis para manter online devem incluir, se existirem no backend:

- `ARMED`;
- `READY`;
- `ARMED_WAITING`;
- `AGUARDANDO_PLANO`, se representar robô armado aguardando plano;
- outro estado explicitamente documentado como armado/monitorando.

Estados bloqueados:

- `DISABLED`;
- `DISARMED`;
- `NOT_ARMED`;
- provider `MT5_DEMO_DISABLED`;
- conta real;
- env demo execution ausente quando backend exigir.

## Critério de aceite

Depois de clicar em `Armar robo demo`, a interface deve mostrar claramente:

- se armou;
- se ficou online;
- se foi bloqueado;
- qual motivo do bloqueio.

---

# Tarefa 4 — Auto-refresh/rerun seguro para robô online

Quando `MT5_DEMO_ROBOT_ONLINE_KEY=True`, o dashboard precisa reavaliar o robô em intervalo controlado.

Implementar mecanismo seguro:

- usar intervalo configurável `MT5_DEMO_ROBOT_INTERVAL_SECONDS`;
- evitar loop infinito;
- evitar rerun excessivo;
- não acionar ciclo Forex pesado desnecessário;
- não iniciar thread de fundo por causa do robô.

Se houver suporte a `st.rerun`, controlar por timestamp:

```python
last_cycle = st.session_state.get(MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY, 0.0)
now = time.monotonic()
if online_enabled and now - last_cycle >= MT5_DEMO_ROBOT_INTERVAL_SECONDS:
    run_online_demo_robot_cycle_once()
    st.session_state[MT5_DEMO_ROBOT_LAST_CYCLE_MONOTONIC_KEY] = now
```

Não executar várias vezes no mesmo render.

## Critério de aceite

Robô online executa no máximo um ciclo por intervalo configurado.

---

# Tarefa 5 — Não depender de thread de fundo para ligar robô

A thread de fundo Forex deve permanecer desligada por padrão.

Configuração esperada:

```text
TRADERIA_MT5_BACKGROUND_CYCLE_ENABLED=0
```

`get_dashboard_service()` não deve iniciar operação pesada automaticamente.

Se for necessário manter `_start_mt5_forex_background_cycle_once()`, ela deve continuar sem efeito quando:

- env estiver desligado;
- auto-cycle UI estiver desligado;
- usuário não pediu explicitamente ciclo Forex.

## Critério de aceite

Abrir a tela não cria ciclo operacional oculto.

---

# Tarefa 6 — Logs e mensagens

Adicionar mensagens claras:

- `MT5_DIAGNOSTIC_ONLY_COMPLETED`
- `MT5_DIAGNOSTIC_DID_NOT_START_CYCLE`
- `DEMO_ROBOT_ARM_REQUESTED`
- `DEMO_ROBOT_ARMED_ONLINE`
- `DEMO_ROBOT_ARM_BLOCKED`
- `DEMO_ROBOT_ONLINE_CYCLE_STARTED`
- `DEMO_ROBOT_ONLINE_CYCLE_COMPLETED`
- `DEMO_ROBOT_ONLINE_CYCLE_SKIPPED_INTERVAL`

---

# Tarefa 7 — Testes obrigatórios

Criar/ajustar testes para validar:

1. Diagnóstico MT5 não liga ciclo Forex.
2. Diagnóstico MT5 não inicia thread de fundo.
3. Diagnóstico MT5 não altera estado do robô.
4. Armar robô demo seta online quando backend permite.
5. Armar robô demo mostra bloqueio quando backend nega.
6. Robô online executa no máximo um ciclo por intervalo.
7. Auto-refresh Forex e monitoramento do robô são independentes.
8. Abrir dashboard não inicia thread pesada por padrão.

---

# Guardrails obrigatórios

Não alterar:

- regra de entrada;
- regra de saída;
- stop móvel;
- break-even;
- trailing stop;
- cálculo do Lab;
- envio de ordem real;
- proteção de conta demo/real;
- validação de risco;
- Position Manager.

---

# Resultado esperado

Após a correção:

- o botão de diagnóstico fica seguro e isolado;
- o robô demo volta a poder ser armado;
- o estado online/offline fica coerente com o backend;
- o ciclo de 10 segundos fica controlado e não bloqueia o robô;
- não há thread ou ciclo oculto iniciado pelo diagnóstico;
- o sistema fica mais leve e previsível.
