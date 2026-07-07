# MISSAO 221 - DATASET_PROFILE_VALUE_PANEL

## Objetivo

Criar o painel visual `PERFIL DO DATASET` para transformar o dataset PETR4 em informacoes quantitativas uteis ao usuario logo na abertura do Dashboard.

## Contexto

O Dashboard ja exibia que PETR4 estava disponivel como dataset de pesquisa, mas ainda faltava traduzir esse dataset em leitura quantitativa direta:

- retorno;
- volatilidade;
- drawdown;
- melhores e piores dias;
- volume;
- curvas visuais.

Esta missao adicionou esse valor visual sem criar Strategy, Alpha, ordem, corretora, provider novo, alteracao de Research Lab ou alteracao de Replay Engine.

## Fonte dos Dados

Fonte fisica usada pela cadeia autorizada:

```text
historical_data/datasets/B3/PETR4/1d/data.csv
```

A interface nao acessa o arquivo diretamente. O fluxo preservado e:

```text
dashboard_app.py
  -> DashboardService
      -> HistoricalDataProvider
          -> data source/adapter historico existente
```

## Arquivos Alterados

- `application/dashboard_service.py`
- `dashboard_app.py`
- `tests/test_dashboard_historical_dataset.py`
- `tests/test_dashboard_app_runtime.py`
- `MANIFEST.md`

## Arquivos Criados

- `DATASET_PROFILE_VALUE_PANEL.md`

## Alteracao Aplicada

### Camada Application

Foram adicionados DTOs imutaveis:

- `DatasetProfileData`
- `DatasetProfilePoint`

O `DashboardService` passou a montar privadamente o perfil quantitativo do dataset ativo, sem criar metodo publico novo e sem alterar o contrato congelado da API publica.

### Dashboard

A Home passou a exibir o painel:

```text
PERFIL DO DATASET
```

O painel aparece logo apos o bloco `DATASET DE PESQUISA ATIVO`, para que o usuario veja valor quantitativo real ao abrir o Dashboard.

## Metricas Exibidas

Com base no PETR4 1d:

| Metrica | Valor |
|---|---:|
| Ativo | PETR4 |
| Timeframe | 1d |
| Periodo | 2016-06-28 00:00:00 -> 2026-06-26 00:00:00 |
| Candles | 2491 |
| Preco inicial | 9.20 |
| Preco final | 38.06 |
| Retorno acumulado | 313.70% |
| Retorno anualizado | 15.45% |
| Volatilidade anualizada | 41.96% |
| Drawdown maximo | 63.55% |
| Melhor dia | 2020-03-13 00:00:00 |
| Retorno do melhor dia | 22.22% |
| Pior dia | 2020-03-09 00:00:00 |
| Retorno do pior dia | -29.70% |
| Dias positivos | 1303 |
| Dias negativos | 1153 |
| Volume medio | 57.280.646 |
| Volume maximo | 490.230.400 |
| Status de qualidade | APPROVED |

## Graficos Adicionados

Foram adicionados quatro graficos simples:

- curva de preco;
- curva de retorno acumulado;
- histograma de retornos diarios;
- volume ao longo do tempo.

## Decisoes Tecnicas

- O dashboard continua consumindo somente `DashboardService`.
- O calculo do perfil fica na camada `application`.
- O `DashboardService` nao ganhou metodo publico novo, preservando o contrato congelado.
- O provider existente foi apenas reutilizado.
- O drawdown maximo foi calculado como queda percentual a partir do pico de preco.
- O retorno anualizado usa 252 pregoes como base anual.
- A volatilidade anualizada usa desvio-padrao amostral dos retornos diarios multiplicado por raiz de 252.

## Validacoes Executadas

### Testes focados obrigatorios

Comando:

```bash
python -m unittest tests.test_dashboard_app_runtime tests.test_dashboard_historical_dataset tests.test_application_api
```

Resultado:

```text
Ran 21 tests in 9.626s
OK
```

### Architecture Audit

Comando:

```bash
python scripts\architecture_audit.py
```

Resultado:

```text
Architecture audit status: OK
```

### Suite completa

Comando:

```bash
python -m unittest discover -s tests
```

Resultado:

```text
Ran 3159 tests in 97.359s
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
python -m streamlit run dashboard_app.py --server.port 8508 --server.headless true
```

Resultado:

```text
Streamlit iniciado com sucesso em http://localhost:8508.
```

Validacao no navegador:

- `PERFIL DO DATASET`: visivel;
- PETR4: visivel;
- 2491 candles: visivel;
- retorno acumulado: visivel;
- volatilidade anualizada: visivel;
- drawdown maximo: visivel;
- curva de preco: visivel;
- curva de retorno acumulado: visivel;
- histograma de retornos diarios: visivel;
- volume ao longo do tempo: visivel;
- erro `removeChild`: nao observado;
- logs de erro relacionados a `removeChild`, `NotFoundError` ou `Failed to execute`: nenhum.

## Confirmacoes Arquiteturais

- Nenhuma Strategy foi criada.
- Nenhuma Alpha foi criada.
- Nenhuma ordem foi executada.
- Nenhuma corretora foi conectada.
- Nenhum dado simulado foi usado no perfil.
- `HistoricalDataProvider` nao foi alterado.
- `ResearchLab` nao foi alterado.
- `ReplayEngine` nao foi alterado.
- `DashboardService` continua sendo a fachada do Dashboard.
- PETR4 permanece dataset de pesquisa.
- WDO permanece ativo operacional/configuracao.
- Operacao real permanece proibida.

## Limitacoes Restantes

- Os graficos sao simples e usam a renderizacao nativa do Streamlit.
- O eixo temporal nao foi customizado nesta missao para evitar introduzir biblioteca ou complexidade visual fora do escopo.
- O painel e descritivo; ele nao interpreta estrategia, nao valida Alpha e nao recomenda operacao.

## Declaracao Final

A missao `DATASET_PROFILE_VALUE_PANEL` transformou o dataset PETR4 em leitura visual quantitativa real na Home do Dashboard. O usuario agora ve retorno, volatilidade, drawdown, melhores e piores dias, volume e graficos reais antes de qualquer execucao de Replay ou Research Lab, preservando a arquitetura e mantendo a operacao real proibida.
