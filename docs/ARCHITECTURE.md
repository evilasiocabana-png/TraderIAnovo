# Architecture

## Visao Geral

TraderIA Novo e uma aplicacao local Streamlit com camadas de aplicacao,
dominio, infraestrutura e pesquisa. O GitHub guarda o codigo e a governanca. A
execucao operacional com MT5 e Lab pesado permanece local.

## Camadas

### UI

Arquivo principal:

```text
dashboard_app.py
```

Responsabilidade:

- renderizar Streamlit;
- escolher abas;
- chamar apenas a fachada de aplicacao;
- evitar logica pesada na renderizacao.

### Application

Pasta principal:

```text
application/
```

Responsabilidade:

- orquestrar casos de uso;
- expor `DashboardService`;
- converter dados para ViewModels;
- isolar UI de infraestrutura.

### Domain

Pasta principal:

```text
domain/
```

Responsabilidade:

- contratos e dataclasses estaveis;
- objetos de decisao, risco, execucao e resultado;
- regras independentes de UI e infraestrutura.

### Research / Lab

Pastas principais:

```text
research/
alpha/
strategies/
```

Responsabilidade:

- motores de pesquisa;
- alphas;
- calibracao e ranking;
- calculo local a partir de `.traderia/`.

### MT5 / Infrastructure

Pastas principais:

```text
infrastructure/
mt5/
```

Responsabilidade:

- acesso externo;
- leitura MT5;
- provider de execucao demo;
- deteccao de caminho visual MT5.

## Runtime Local

Pasta:

```text
.traderia/
```

Conteudo esperado:

- snapshots do Lab;
- banco local SQLite;
- logs;
- jsonl de execucao demo;
- JSON visual MT5;
- arquivos de restauracao.

Essa pasta e ignorada pelo Git.

## Fluxo Das Abas

### MT5 Forex

- Abre com ultimo estado local/snapshot.
- Nao possui ciclo automatico bloqueante.
- Nao deve prender a UI em leitura MT5 longa.

### Lab

- Usa o motor local da TraderIA Novo.
- Lida com `.traderia/mt5_research_snapshot.json`.
- Usa `.traderia/traderia_mt5_history.sqlite` como banco local.
- Auditoria completa fica sob demanda.

### Relatorios

- Audita `.traderia/mt5_demo_execution.jsonl` contra historico MT5/local.
- Carrega uma vez, cacheia na sessao e atualiza por botao.

## Fronteiras Criticas

- `dashboard_app.py` nao deve importar providers diretamente.
- MT5 real nao roda no Codespaces.
- GitHub nao armazena runtime local.
- Recalculo pesado precisa ser explicito.
- Execucao real nao e autorizada por padrao.

