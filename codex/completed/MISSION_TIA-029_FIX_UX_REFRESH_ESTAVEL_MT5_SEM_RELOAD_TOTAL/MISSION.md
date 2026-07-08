# MISSION_TIA-029 — Corrigir UX do refresh MT5 sem recarregar a tela inteira

## Contexto

O usuário relata que a atualização automática do TraderIAnovo está abrindo/recarregando a tela do zero, fazendo a página subir para o topo e impedindo uma boa experiência de uso. Além disso, o refresh não dá tempo suficiente para ligar/armar o robô demo.

O objetivo é manter a tela parada e renovar somente as informações vindas do MT5, sem refresh total do navegador.

---

## Diagnóstico técnico encontrado

Em `dashboard_app.py`, a função `_inject_mt5_forex_auto_refresh()` injeta JavaScript com:

```javascript
setTimeout(function() { window.parent.location.reload(); }, interval_ms);
```

Isso força o navegador a recarregar a página inteira a cada intervalo.

Efeitos colaterais:

- a tela volta para o topo;
- a aba/posição visual fica instável;
- componentes são reconstruídos do zero;
- o usuário perde o contexto;
- o botão `Armar robo demo` pode ser interrompido pelo reload;
- a UX fica ruim;
- o ciclo visual passa a disputar com o ciclo do robô;
- a sensação é de “app reiniciando” em vez de painel atualizando.

O robô demo também depende de renderização da aba para executar `_run_demo_robot_online_cycle_if_due(...)`, então o refresh total interfere diretamente na experiência de armar e monitorar o robô.

---

## Objetivo

Eliminar o refresh total da página e substituir por atualização controlada de dados MT5, preservando o estado visual da interface.

A tela deve permanecer estável enquanto apenas os dados mudam.

---

# Tarefa 1 — Remover reload total do navegador

Remover ou desabilitar o uso de:

```python
window.parent.location.reload()
```

A função `_inject_mt5_forex_auto_refresh()` não deve mais recarregar a página inteira.

Se for mantida por compatibilidade, deve ficar desligada por padrão e protegida por flag explícita:

```text
TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED=0
```

## Critério de aceite

Nenhum fluxo padrão do MT5 Forex pode usar `window.parent.location.reload()`.

---

# Tarefa 2 — Atualizar apenas dados MT5

Criar ou ajustar um mecanismo de refresh interno que atualize somente os dados do MT5:

- `mt5_forex_signals`;
- status de conexão;
- candles recebidos;
- preços;
- decisões;
- status do robô;
- auditoria leve quando habilitada.

Sem reconstruir a tela inteira via reload do navegador.

O refresh deve ocorrer dentro do fluxo normal do Streamlit, com estado preservado em `st.session_state`.

---

# Tarefa 3 — Preservar posição da tela e interação do usuário

Durante atualização automática:

- não voltar para o topo;
- não trocar aba selecionada;
- não resetar selectbox do par monitorado;
- não perder estado do botão/robô;
- não apagar mensagens do usuário;
- não reabrir a tela como se fosse primeira carga.

Estados que devem ser preservados:

```text
dashboard_selected_tab
mt5_demo_robot_pair
mt5_demo_robot_online_enabled
mt5_demo_robot_last_cycle_monotonic
mt5_demo_robot_runtime_message
mt5_forex_auto_cycle_enabled_ui
mt5_report_audit_cache
```

---

# Tarefa 4 — Pausar refresh enquanto usuário opera controles críticos

Quando o usuário estiver em área de controle do robô:

- armar robô;
- desarmar robô;
- avaliar gatilho agora;
- selecionar par;
- confirmar SL assistido;

não deve ocorrer refresh automático agressivo no mesmo instante.

Implementar uma janela curta de proteção UX, por exemplo:

```text
TRADERIA_UI_INTERACTION_GRACE_SECONDS=20
```

Ao clicar em controle crítico, registrar:

```python
st.session_state["ui_last_critical_interaction_at"] = time.monotonic()
```

Durante esse período:

- não disparar reload;
- não disparar rerun automático pesado;
- permitir apenas atualização leve segura;
- não bloquear a ação do usuário.

---

# Tarefa 5 — Separar refresh visual, ciclo Forex e ciclo do robô

Manter três conceitos separados:

## 1. Refresh visual leve

Atualiza somente dados exibidos.

## 2. Ciclo Forex

Atualiza sinais/leituras MT5.

## 3. Ciclo do robô demo

Executa monitoramento online do robô.

Regras:

- refresh visual não arma robô;
- refresh visual não desarma robô;
- ciclo Forex não deve recarregar página inteira;
- ciclo do robô não depende de reload total da página;
- diagnóstico MT5 continua isolado.

---

# Tarefa 6 — Melhorar o fluxo de armar robô

Ao clicar em `Armar robo demo`, a ação deve ter prioridade sobre qualquer refresh.

Fluxo esperado:

1. usuário clica em armar;
2. app registra interação crítica;
3. app chama backend;
4. app mostra resultado;
5. app mantém a tela no mesmo local;
6. só depois retoma atualização leve.

Evitar `st.rerun()` desnecessário depois de armar, se for possível atualizar o `data` local e renderizar o estado novo no mesmo ciclo.

Se `st.rerun()` for indispensável, garantir que:

- aba selecionada seja preservada;
- par selecionado seja preservado;
- status do robô seja preservado;
- não volte ao topo por reload de navegador.

---

# Tarefa 7 — Criar indicador visual de atualização

Adicionar no topo ou no card MT5 uma informação discreta:

```text
Última atualização MT5: HH:MM:SS
Próxima atualização leve em: Ns
Refresh de página inteira: DESLIGADO
```

Isso ajuda o usuário a entender que o sistema está vivo sem precisar ver a tela recarregar.

---

# Tarefa 8 — Flags/configurações

Adicionar flags:

```text
TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED=0
TRADERIA_UI_LIGHT_REFRESH_ENABLED=1
TRADERIA_UI_INTERACTION_GRACE_SECONDS=20
TRADERIA_MT5_FOREX_AUTO_REFRESH_SECONDS=10
```

Observação: o intervalo de 10 segundos pode continuar, mas não pode recarregar a tela inteira.

---

# Tarefa 9 — Testes obrigatórios

Criar testes para validar:

1. `_inject_mt5_forex_auto_refresh()` não injeta `window.parent.location.reload()` por padrão.
2. Flag `TRADERIA_UI_FULL_PAGE_RELOAD_ENABLED=1` é necessária para permitir reload total, se a função for mantida.
3. Clicar em `Armar robo demo` registra interação crítica.
4. Durante janela de interação crítica, refresh automático pesado é bloqueado.
5. Estado `dashboard_selected_tab` é preservado.
6. Estado `mt5_demo_robot_pair` é preservado.
7. Estado `MT5_DEMO_ROBOT_ONLINE_KEY` não é resetado por refresh visual.
8. Diagnóstico MT5 continua sem iniciar ciclo automático.
9. Robô online continua executando ciclo controlado por intervalo.
10. Nenhuma lógica de trading, stop móvel ou envio real foi alterada.

---

## Guardrails obrigatórios

Não alterar:

- regra de entrada;
- regra de saída;
- stop móvel;
- break-even;
- trailing stop;
- Lab;
- Position Manager;
- envio de ordem real;
- bloqueio de conta real;
- validação de risco.

---

## Critérios de aceite

A missão estará concluída quando:

- a tela não recarregar inteira a cada 10 segundos;
- a página não voltar ao topo durante refresh;
- o usuário conseguir clicar em `Armar robo demo` sem ser interrompido;
- as informações MT5 continuarem atualizando;
- o ciclo do robô continuar funcionando quando online;
- o diagnóstico continuar isolado;
- o app preservar aba, par selecionado e estado online do robô;
- houver testes cobrindo a regressão.

---

## Resultado esperado

O TraderIAnovo deve se comportar como painel operacional estável: a tela fica parada, o usuário consegue operar os controles, e somente os dados MT5 são renovados de forma leve e previsível.
