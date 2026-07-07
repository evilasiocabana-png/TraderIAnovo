# MISSAO 220 - STREAMLIT_DOM_DEBUG

## Objetivo

Descobrir qual componente do Dashboard do TraderIA pode produzir o erro de frontend do Streamlit:

```text
NotFoundError:
Failed to execute 'removeChild' on 'Node':
The node to be removed is not a child of this node.
```

Este documento registra a investigacao estatica inicial. Ele nao altera codigo, nao corrige o Replay e nao cria novas funcionalidades.

## Conclusao Executiva

A causa raiz mais provavel nao esta no motor de Replay em si. O ponto de risco esta no fluxo de renderizacao do Dashboard Streamlit, especialmente na aba `Replay`, quando o usuario troca ou carrega um dataset historico enquanto a mesma renderizacao continua reconstruindo tabelas, graficos e controles.

O codigo analisado nao usa `st.data_editor` nem `st.dataframe` em `dashboard_app.py`. A hipotese inicial de conflito com `st.data_editor` nao se confirma para este arquivo. O problema se concentra em:

- mutacao do estado de Replay durante a renderizacao;
- troca de dataset sem uma fronteira limpa de rerun;
- tabelas e graficos reconstruidos apos a mudanca de dataset;
- `st.rerun()` executado pelo auto-run depois que parte da tela ja foi renderizada.

## Arquivo Principal

```text
dashboard_app.py
```

## Componentes Mapeados

| Componente | Localizacao | Achado | Risco |
|---|---:|---|---|
| `st.data_editor` | Nao encontrado | Nao e usado em `dashboard_app.py`. | Baixo para este arquivo. |
| `st.dataframe` | Nao encontrado | Nao e usado em `dashboard_app.py`. | Baixo para este arquivo. |
| `st.empty` | Nao encontrado | Nao ha placeholder manual sendo esvaziado. | Baixo para este arquivo. |
| `st.container` | `dashboard_app.py:106` | Container usado na barra de status. | Baixo. |
| `st.columns` | `dashboard_app.py:895`, `dashboard_app.py:961` e outros | Usado em controles de Replay e acoes de dataset. | Medio. |
| `st.tabs` | `dashboard_app.py:2048` | A aba `Replay` contem arvore dinamica grande. | Medio. |
| `st.session_state` | `dashboard_app.py:12-15` | Mantem `DashboardService` persistente. | Medio. |
| `st.rerun` | `dashboard_app.py:64`, `dashboard_app.py:1797` | O helper em `64` nao aparece referenciado; o auto-run chama `st.rerun()` em `1797`. | Alto. |
| `st.table` | `dashboard_app.py:942`, `dashboard_app.py:1753` | Tabelas mudam quando o dataset/replay muda. | Alto. |
| `st.line_chart` | `dashboard_app.py:1756` | Grafico muda conforme candles processados. | Alto. |

## Fluxo Suspeito

O fluxo de maior risco e:

```text
Usuario clica "Carregar Replay do Dataset"
        |
dashboard_app.py:962
        |
service.load_selected_historical_dataset_to_replay()
        |
dashboard_app.py:964
        |
estado interno do Replay e candles carregados mudam
        |
a mesma renderizacao continua
        |
st.table / st.line_chart / tabs / columns sao reconstruidos
        |
se auto-run estiver ativo, st.rerun() pode ocorrer em dashboard_app.py:1797
        |
frontend React do Streamlit tenta remover elemento antigo
        |
removeChild falha porque a arvore DOM ja mudou
```

## Quem Modifica o Dataframe ou Dados Renderizados

Nao foi encontrado `dataframe` explicito em `dashboard_app.py`.

Os dados tabulares sao montados como listas/dicionarios e renderizados com `st.table`. Os pontos mais relevantes sao:

- `dashboard_app.py:942`: renderiza a tabela de datasets historicos com `_historical_datasets_table(datasets)`;
- `dashboard_app.py:1753`: renderiza a tabela de candles carregados com `_candles_table(candles_loaded, len(candles_processed))`;
- `dashboard_app.py:1756`: renderiza o grafico de fechamentos processados com `_close_values(candles_processed)`.

Esses dados mudam quando o dataset selecionado e carregado para o Replay.

## Quem Chama Rerun

Foram encontrados dois pontos:

- `dashboard_app.py:64`: `st.rerun()` dentro de `rerender_dashboard()`;
- `dashboard_app.py:1797`: `st.rerun()` dentro de `executar_auto_run()`.

O ponto de maior risco e `dashboard_app.py:1797`, porque o auto-run avanca candle depois de parte da aba Replay ja ter sido renderizada.

## Quem Troca o Dataset

Os pontos que alteram o dataset/replay sao:

- `dashboard_app.py:950`: `service.select_historical_dataset(dataset_id)`;
- `dashboard_app.py:901`: `service.load_selected_historical_dataset_to_replay()`;
- `dashboard_app.py:964`: `service.load_selected_historical_dataset_to_replay()`.

O ponto mais suspeito para o erro relatado e `dashboard_app.py:964`, acionado pelo botao:

```text
Carregar Replay do Dataset
```

## Quem Recria Containers

Os containers principais sao recriados naturalmente a cada renderizacao do Streamlit:

- `dashboard_app.py:2048`: cria as abas principais com `st.tabs`;
- `dashboard_app.py:895`: cria colunas dos controles de Replay;
- `dashboard_app.py:961`: cria colunas das acoes do dataset historico;
- `dashboard_app.py:106`: cria container da barra de status.

Nao ha uso de `st.empty()` neste arquivo.

## Causa Raiz Provavel

A causa raiz provavel e a troca de estado do Replay/dataset no meio da renderizacao da aba `Replay`, seguida por reconstrucao de componentes dinamicos e, em alguns casos, por `st.rerun()` disparado pelo auto-run.

Em outras palavras: a interface renderiza uma arvore antiga, muda o dataset/replay durante a mesma passada, tenta continuar renderizando uma arvore nova e o frontend do Streamlit pode falhar ao reconciliar os nos React.

## Como Reproduzir

Fluxo recomendado para reproducao:

1. Abrir o Dashboard Streamlit do TraderIA.
2. Entrar na aba `Replay`.
3. Garantir que existam pelo menos dois datasets historicos disponiveis.
4. Selecionar um dataset no seletor `Dataset historico de pesquisa`.
5. Clicar em `Carregar Replay do Dataset`.
6. Se o erro nao aparecer, iniciar o Replay ou ativar auto-run.
7. Alternar rapidamente entre datasets e recarregar o Replay.
8. Observar se o frontend mostra `removeChild` / `Node` / `NotFoundError`.

## Correcao Recomendada

A correcao deve estabilizar a fronteira de renderizacao do Streamlit. Nao se deve continuar renderizando a aba Replay depois que o dataset foi trocado ou carregado.

Recomendacoes:

1. Transformar clique de carregamento em uma intencao de acao.
2. Processar a acao no inicio da renderizacao da aba Replay.
3. Depois de `load_selected_historical_dataset_to_replay()`, executar `st.rerun()` e interromper a renderizacao atual com `st.stop()`.
4. Adicionar `key` explicita aos botoes de dataset historico que ainda nao possuem chave.
5. Evitar renderizar `exibir_dataset_historico_ativo()` duas vezes na mesma passada.
6. Desabilitar ou pausar auto-run durante troca de dataset.
7. Evitar `time.sleep()` seguido de `st.rerun()` depois que tabelas e graficos ja foram renderizados.
8. Registrar logs temporarios de ciclo de renderizacao, dataset ativo, replay carregado, auto-run e chamadas de rerun.

## Correcao Que Nao Deve Ser Feita

Nao se recomenda:

- alterar o motor de Replay sem evidencia;
- trocar arquitetura de dados;
- remover tabs ou tabelas sem diagnostico;
- introduzir nova camada de estado paralela ao `DashboardService`;
- misturar logica operacional com interface;
- corrigir adicionando sleeps extras.

## Proxima Missao Recomendada

```text
MISSAO 221 - STREAMLIT_REPLAY_RENDER_STABILIZATION.md
```

Objetivo sugerido:

Estabilizar a renderizacao da aba Replay, criando uma fronteira clara entre acao de troca/carregamento de dataset e reconstrucao dos componentes visuais.

Escopo sugerido:

- adicionar chaves explicitas aos botoes dinamicos;
- separar intencao de carregamento da renderizacao;
- executar rerun controlado apos troca de dataset;
- impedir renderizacao parcial apos mutacao de Replay;
- adicionar teste ou checklist manual de reproducao.

## Risco Arquitetural

Risco atual: alto para estabilidade do Dashboard.

Enquanto este erro existir, novas funcionalidades de interface podem parecer instaveis mesmo quando os servicos internos estiverem corretos. Por isso, a correcao deve ter prioridade antes de novos incrementos visuais no Dashboard.

## Criterios de Aceite Desta Missao

- causa raiz provavel documentada;
- arquivo principal identificado;
- linhas relevantes registradas;
- componentes Streamlit mapeados;
- fluxo de reproducao descrito;
- correcao recomendada documentada;
- nenhuma alteracao de codigo realizada.

## Declaracao Final

A Missao 220 conclui que o erro `removeChild` deve ser tratado como instabilidade de renderizacao do Dashboard Streamlit, nao como falha primaria do motor de Replay. A proxima intervencao deve estabilizar a fronteira entre mudanca de dataset, reconstrucao visual e rerun antes de qualquer nova funcionalidade de interface.
