# RESEARCH_WORKBENCH_MVP

## Missao

Missao 220 - Research Workbench MVP.

## Objetivo

Transformar o Dashboard do TraderIA em uma tela unica utilizavel para pesquisa quantitativa, sem criar novos modulos, engines, contratos ou abas.

## Arquivos alterados

- `dashboard_app.py`
- `tests/test_dashboard_app_runtime.py`
- `tests/test_dashboard_facade.py`
- `MANIFEST.md`

## Componentes removidos da experiencia principal

- Navegacao por abas no `main()`.
- Renderizacao principal em telas separadas de Home, Market DNA, Replay, Research Lab, Estrategias, Eventos e Sistema.
- Tabelas Streamlit diretas na experiencia operacional principal.
- Componentes demonstrativos como fluxo central do usuario.

As funcoes antigas permanecem no arquivo para compatibilidade auxiliar, mas deixam de ser o fluxo principal renderizado pelo `main()`.

## Componentes reutilizados

- `DashboardService`
- `ReplayService`, exclusivamente via fachada
- `ResearchLabService`, exclusivamente via fachada
- `HistoricalDataProvider`, exclusivamente via `DashboardService`
- DTOs existentes de `DashboardData`
- Estado de Replay ja existente
- Alpha 001 ja registrada
- Paper metrics ja produzidas pelo Replay
- Dataset PETR4 ja catalogado

## Tela entregue

A tela principal foi reorganizada em quatro regioes:

1. Grafico
   - Candlestick via Vega-Lite nativo do Streamlit.
   - Zoom e pan por selecao de intervalo vinculada as escalas.
   - Tooltip com data, OHLC e volume.
   - Volume em grafico separado.

2. Replay
   - Candle anterior.
   - Proximo candle.
   - Play.
   - Pause.
   - Ir para data.
   - Candle atual.
   - Numero do candle.
   - Progresso.
   - OHLC e volume.

3. Alpha
   - Alpha carregada.
   - Status.
   - Decisao BUY, SELL ou WAIT.
   - Confidence.
   - Score.
   - Explicacao e motivos.
   - Aviso explicito de que nenhuma ordem real e executada.

4. Estatisticas
   - Trades.
   - PnL.
   - Equity Curve.
   - Win Rate.
   - Profit Factor.
   - Drawdown.
   - Expectancy.
   - Quantidade de operacoes.
   - Sharpe.
   - Retorno acumulado.

## Menu lateral

O menu lateral permite:

- selecionar dataset;
- selecionar Alpha;
- ajustar velocidade;
- Play;
- Pause;
- Reset.

## Como utilizar

1. Executar `python -m streamlit run dashboard_app.py`.
2. Selecionar o dataset na lateral.
3. Observar o grafico candlestick carregado com dados reais.
4. Avancar candle a candle ou usar Play.
5. Acompanhar decisao da Alpha.
6. Acompanhar estatisticas e curva de equity.

## Fluxo do usuario

O usuario nao precisa abrir arquivos do projeto. O Dashboard carrega o dataset selecionado via `DashboardService`, exibe o grafico, permite replay visual e mostra decisao quantitativa e estatisticas em uma unica tela.

## Limitacoes atuais

- O botao Candle anterior reconstrui o estado por reset e reavanco, pois a fachada atual ainda nao possui operacao nativa de retrocesso.
- O grafico usa Vega-Lite nativo do Streamlit, sem Plotly ou nova dependencia.
- A selecao de Alpha e visual; a Alpha efetiva permanece a estrategia ja integrada ao Replay.
- O MVP continua estritamente paper/simulacao; operacao real permanece proibida.

## Proximas evolucoes

- Criar suporte nativo de retrocesso no Replay somente se aprovado por contrato arquitetural.
- Melhorar selecao efetiva de Alpha quando o roadmap autorizar multiplas alphas executaveis.
- Adicionar persistencia controlada de sessoes de pesquisa, sem misturar com execucao real.

## Validacoes executadas

- `python scripts\architecture_audit.py`
- `python -m unittest tests.test_dashboard_app_runtime`
- `python -m unittest tests.test_dashboard_facade`
- `python -m unittest tests.test_dashboard_app_runtime tests.test_dashboard_historical_dataset tests.test_dashboard_historical_dataset_catalog tests.test_replay_historical_data tests.test_replay_market_data_provider tests.test_dashboard_facade tests.test_dashboard_service_contract`
- `python -m unittest discover -s tests`
- `python -m streamlit run dashboard_app.py`

## Resultado

O Architecture Audit retornou OK. Os testes focados de Dashboard, fachada, datasets historicos e Replay passaram. A suite completa executou 3159 testes com resultado OK. O Streamlit respondeu em `http://localhost:8501` com status 200.

## Declaracao Final

O TraderIA agora possui um MVP utilizavel para Pesquisa Quantitativa.
