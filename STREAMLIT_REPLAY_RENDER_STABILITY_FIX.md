# MISSAO 221 - STREAMLIT_REPLAY_RENDER_STABILITY_FIX

## Objetivo

Corrigir a instabilidade visual do Streamlit na aba Replay associada ao erro:

```text
NotFoundError: Failed to execute 'removeChild' on 'Node'
```

A correcao estabiliza a fronteira entre acoes de dataset/replay, estado de `st.session_state` e renderizacao dos componentes visuais.

## Causa Raiz Confirmada

A causa raiz confirmada foi a mutacao do estado do Replay durante a mesma passada de renderizacao da aba `Replay`.

Antes da correcao, botoes da interface chamavam diretamente:

```text
service.load_selected_historical_dataset_to_replay()
service.select_historical_dataset(...)
```

enquanto a mesma renderizacao continuava reconstruindo tabelas, metricas, graficos e controles. Isso criava uma arvore visual instavel para o frontend React do Streamlit, especialmente quando existiam dois datasets disponiveis e o usuario carregava PETR4 no Replay.

## Arquivos Alterados

- `dashboard_app.py`
- `tests/test_dashboard_app_runtime.py`
- `MANIFEST.md`

## Arquivos Criados

- `STREAMLIT_REPLAY_RENDER_STABILITY_FIX.md`

## Alteracao Aplicada

### 1. Fila de acao de Replay em `st.session_state`

Foram adicionadas chaves especificas para controlar acoes pendentes:

```text
replay_pending_action
replay_pending_dataset_id
replay_pending_message
```

Os botoes de Replay agora registram uma intencao de acao e encerram a passada atual com rerun controlado, sem carregar dataset no meio do desenho da tela.

### 2. Aplicacao da acao antes da renderizacao

A aba Replay passou a aplicar a acao pendente no inicio de `exibir_replay()`, antes de desenhar tabelas, graficos e controles dinamicos.

Com isso, o dataset e o estado do Replay ja estao consistentes quando os componentes visuais sao criados.

### 3. Auto Replay protegido durante troca de dataset

Ao carregar dataset no Replay, o auto-run e desabilitado antes da carga. Isso evita que `st.rerun()` do auto replay concorra com a troca do dataset.

### 4. Keys estaveis para botoes dinamicos

Foram adicionadas chaves explicitas aos botoes da aba Replay e acoes de dataset historico:

- `replay_start`
- `replay_next_candle`
- `replay_stop`
- `replay_reset`
- `select_historical_dataset`
- `load_selected_historical_dataset_replay`
- `run_selected_historical_dataset_research`
- `analyze_selected_historical_dataset_quality`
- `enable_replay_auto_run`
- `disable_replay_auto_run`

### 5. Remocao de renderizacao duplicada do dataset ativo

A selecao do dataset deixou de redesenhar `exibir_dataset_historico_ativo()` no meio da mesma passada. O dataset ativo passa a ser renderizado uma unica vez, depois da atualizacao de estado.

## Antes

```text
Clique em Carregar Replay do Dataset
  -> service.load_selected_historical_dataset_to_replay()
  -> estado interno muda
  -> renderizacao continua na mesma passada
  -> tabelas/graficos/controles sao recriados com estado novo
  -> frontend pode gerar removeChild
```

## Depois

```text
Clique em Carregar Replay do Dataset
  -> registra acao pendente no session_state
  -> rerun controlado
  -> nova passada inicia
  -> acao pendente e aplicada antes da renderizacao
  -> componentes sao desenhados com estado consistente
```

## Validacoes Executadas

### Architecture Audit

Comando:

```bash
python scripts\architecture_audit.py
```

Resultado:

```text
Architecture audit status: OK
```

### Testes focados obrigatorios

Comando:

```bash
python -m unittest tests.test_dashboard_app_runtime tests.test_dashboard_historical_dataset tests.test_dashboard_historical_dataset_catalog tests.test_replay_historical_data tests.test_replay_market_data_provider
```

Resultado:

```text
Ran 80 tests in 17.962s
OK
```

### Suite completa

Comando:

```bash
python -m unittest discover -s tests
```

Resultado:

```text
Ran 3158 tests in 89.940s
OK
```

### Runner legado

Comando:

```bash
python app.py
```

Resultado:

```text
Executado com sucesso.
Ativo: WDO.
Eventos registrados: 5.
```

### Streamlit manual

Comando:

```bash
python -m streamlit run dashboard_app.py --server.port 8507 --server.headless true
```

Resultado:

```text
Streamlit iniciado com sucesso em http://localhost:8507.
```

Validacao manual no navegador:

- Home: OK.
- Replay: OK.
- Research Lab: OK.
- Sistema: OK.
- PETR4 carregado no Replay: OK.
- Total de candles PETR4 no Replay: 2491.
- Botoes da aba Replay testados: `Iniciar`, `Proximo Candle`, `Resetar`.
- Erro `removeChild`: nao observado.
- Logs de erro relacionados a `removeChild`, `NotFoundError` ou `Failed to execute`: nenhum.

## Confirmacoes Arquiteturais

- `DashboardService` continua sendo a fachada consumida pelo Dashboard.
- `HistoricalDataProvider` nao foi alterado.
- `ReplayEngine` nao foi alterado.
- `ResearchLab` nao foi alterado.
- Nenhuma strategy foi criada.
- Nenhuma ordem real foi executada.
- Nenhuma corretora foi conectada.
- PETR4 permanece dataset de pesquisa.
- WDO permanece ativo operacional/configuracao.
- Operacao real permanece nao autorizada.

## Limitacoes Restantes

- A validacao manual confirmou ausencia do erro no fluxo reproduzido localmente, mas o erro era de frontend e pode depender de velocidade de clique, navegador, cache e estado previo da sessao.
- O auto replay ainda utiliza `time.sleep()` e `st.rerun()` para avancar ciclos; isso nao foi redesenhado nesta missao para evitar mudanca maior de comportamento.
- A aba Replay ainda renderiza tabelas grandes quando PETR4 e carregado; a otimizacao visual dessas tabelas deve ser tratada em missao separada, se necessario.

## Declaracao Final

A Missao 221 estabilizou a renderizacao da aba Replay ao impedir que dataset e estado de Replay sejam modificados no meio da construcao visual. O fluxo PETR4 foi validado com 2491 candles, os botoes principais da aba Replay funcionaram sem quebrar a tela, o Architecture Audit passou, a suite completa passou com 3158 testes e a operacao real permanece proibida.
