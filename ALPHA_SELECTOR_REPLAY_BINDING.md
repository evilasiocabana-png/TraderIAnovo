# ALPHA_SELECTOR_REPLAY_BINDING

## 1. Missao

MISSÃO 233 — ALPHA_SELECTOR_REPLAY_BINDING.md

Sprint 16 — Market Reading Replay MVP

Objetivo: conectar o seletor visual de Alpha no Dashboard ao `ReplayService`, garantindo que a Alpha selecionada seja a estrategia realmente avaliada durante o Replay.

## 2. Classificacao de Risco

Risco: ALTO.

Justificativa:

- alterou `dashboard_app.py`;
- alterou `DashboardService`;
- alterou `ReplayService`;
- alterou comportamento compartilhado consumido pelo Dashboard;
- alterou o estado funcional do Replay durante a selecao de estrategia.

## 3. Causa Raiz

O menu lateral do Research Workbench exibia um seletor de Alpha usando `st.sidebar.selectbox`, mas o valor escolhido ficava apenas no estado visual do Streamlit.

O `ReplayService` continuava usando a estrategia configurada internamente, por padrao `alpha001_iorb`.

Consequencia:

```text
Alpha selecionada no Dashboard != Alpha executada no Replay
```

## 4. Alteracao Aplicada

Foi criado um binding explicito entre Dashboard e Replay:

```text
Dashboard
  -> DashboardService
      -> ReplayService
          -> StrategyFactory
              -> Strategy registrada
```

O Dashboard continua consumindo apenas `DashboardService` como fachada.

## 5. Arquivos Alterados

- `application/replay_service.py`
- `application/dashboard_service.py`
- `dashboard_app.py`
- `tests/test_replay_service.py`
- `tests/test_dashboard_app_runtime.py`
- `tests/test_application_api.py`

## 6. Arquivo Criado

- `ALPHA_SELECTOR_REPLAY_BINDING.md`

## 7. ReplayService

O `ReplayService` passou a expor:

- `list_available_strategies()`
- `get_active_strategy_name()`
- `select_strategy(strategy_name)`

Tambem passou a incluir no `ReplayData`:

- `active_strategy_name`
- `active_strategy_label`
- `strategy_compatibility_warning`

Ao trocar a estrategia, o Replay e resetado para evitar que um `StrategySignal` antigo continue sendo exibido como se pertencesse a nova Alpha.

## 8. DashboardService

O `DashboardService` passou a expor pela fachada:

- `list_available_replay_strategies()`
- `get_active_replay_strategy_name()`
- `select_replay_strategy(strategy_name)`

Esses metodos mantem a regra arquitetural:

```text
dashboard_app.py nao acessa ReplayService diretamente.
```

## 9. Dashboard

O seletor de Alpha agora:

- lista apenas estrategias registradas pela `StrategyFactory`;
- usa a estrategia ativa como valor inicial;
- chama `DashboardService.select_replay_strategy()` quando o usuario altera a selecao;
- atualiza os dados do Dashboard apos a troca;
- mostra a Alpha realmente executada no painel;
- exibe aviso de incompatibilidade quando aplicavel.

## 10. Alphas Exibidas no Seletor

Alphas/estrategias registradas e validas exibidas:

```text
alpha001_iorb
alpha101
breakout
pullback
score_contexto
smart_money
```

Itens nao registrados nao aparecem no seletor.

## 11. Aviso de Incompatibilidade

Quando `alpha001_iorb` esta selecionada com PETR4 1D, o Dashboard exibe:

```text
Alpha001 IORB é incompatível com PETR4 1D. Esperado: WDO intraday.
```

Esse aviso aparece porque Alpha001 IORB depende de opening range intraday e nao e adequada para PETR4 diario.

## 12. Analise de Impacto

Componentes impactados:

- `ReplayService`;
- `DashboardService`;
- `dashboard_app.py`;
- testes de contrato da application layer;
- testes runtime do Streamlit.

Consumidores verificados:

- Dashboard;
- AppTest do Research Workbench;
- contrato congelado de API publica;
- testes de ReplayService;
- suite completa de testes.

Compatibilidade:

- nenhum metodo publico existente foi removido;
- assinaturas antigas foram preservadas;
- novos metodos foram adicionados e registrados no teste de API publica;
- `DashboardService` permanece a unica fachada consumida pelo Dashboard.

## 13. Testes Adicionados ou Ajustados

### ReplayService

Foram adicionados testes para:

- selecionar `breakout` e confirmar que ela e a estrategia executada;
- rejeitar estrategia nao registrada;
- exibir aviso de incompatibilidade Alpha001 IORB x PETR4 1D.

### Dashboard App Runtime

Foram adicionados/ajustados testes para:

- confirmar que `Alpha carregada` exibe `Alpha001 IORB`;
- confirmar aviso de incompatibilidade com PETR4 1D;
- selecionar `breakout` no menu e confirmar que o painel passa a exibir `Breakout`;
- avancar candle apos troca e confirmar ausencia de excecoes.

### Application API

O contrato congelado foi atualizado com os novos metodos publicos aditivos.

## 14. Validacoes Executadas

### PyCompile

```text
python -m py_compile application\replay_service.py application\dashboard_service.py dashboard_app.py
```

Resultado: OK.

### Testes Focados

```text
python -m unittest tests.test_replay_service tests.test_dashboard_app_runtime tests.test_application_api
```

Resultado:

```text
Ran 77 tests
OK
```

### App Principal

```text
python app.py
```

Resultado: OK.

### Architecture Audit

```text
python scripts\architecture_audit.py
```

Resultado:

```text
Architecture audit status: OK
```

### Suite Completa

```text
python -m unittest discover -s tests
```

Resultado:

```text
Ran 3163 tests in 124.679s
OK
```

### Streamlit

```text
python -m streamlit run dashboard_app.py --server.headless true --server.port 8504
```

Resultado:

```text
HTTP 200
```

### Validacao Funcional com AppTest

Fluxo validado:

- abrir Dashboard;
- carregar PETR4;
- confirmar 2491 candles;
- confirmar Alpha001 IORB inicial;
- confirmar aviso de incompatibilidade PETR4 1D;
- avancar Replay;
- confirmar decisao `WAIT`;
- selecionar `breakout`;
- confirmar que `Alpha carregada` muda para `Breakout`;
- confirmar ausencia de excecoes.

## 15. Confirmacoes Arquiteturais

- Nenhuma nova Strategy foi criada.
- Nenhuma nova Alpha foi criada.
- Nenhuma ordem real foi executada.
- Nenhuma corretora foi conectada.
- `HistoricalDataProvider` nao foi alterado.
- `ReplayEngine` nao foi alterado.
- `ResearchLab` nao foi alterado.
- `DecisionPipeline` nao foi alterado.
- Dashboard continua consumindo apenas `DashboardService`.

## 16. Declaracao Final

A selecao visual de Alpha agora esta conectada ao Replay.

```text
Alpha selecionada = Alpha executada
```

O seletor exibe apenas estrategias registradas e validas, o painel mostra o nome correto da Alpha executada, `StrategySignal` passa a vir da Alpha selecionada, e Alpha001 IORB com PETR4 1D exibe aviso claro de incompatibilidade.
