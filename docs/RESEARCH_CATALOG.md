# Research Catalog

## 1. Objetivo

Catalogar oficialmente os ativos de pesquisa do TraderIA_WDO, registrando
status, metricas, classe, familia e nivel de confianca das Alphas avaliadas
pelo Research Lab.

Este catalogo nao executa pesquisas, nao recalcula metricas, nao altera
estrategias e nao aprova operacao real.

## 2. Alpha102

### Identificacao

- Alpha: `Alpha102`
- Nome institucional: `Swing Pullback Momentum Continuation`
- Classe: `Research Alpha`
- Familia: `Swing Trade`
- Mercado inicial: `WDO`
- Timeframe: `60m / 120m / diario como contexto`
- Status: `CATALOGED_FOR_RESEARCH`
- Nivel de confianca: `RESEARCH_CONFIDENCE_PENDING_NUMERICAL_VALIDATION`

### Status de Pesquisa

A Alpha102 esta catalogada como Alpha de pesquisa, com hipotese aprovada pela
Alpha Factory, playbook institucional criado, implementacao inicial concluida,
benchmark documental definido, avaliacao de portfolio documental definida e
registro de conhecimento atualizado.

A Alpha102 ainda nao esta aprovada para operacao real.

### Metricas Oficiais

As metricas oficiais da Alpha102 devem ser consumidas exclusivamente dos
componentes existentes do Research Lab:

- `total_trades`;
- `total_buy`;
- `total_sell`;
- `total_wait`;
- `gross_profit`;
- `gross_loss`;
- `net_profit`;
- `max_drawdown`;
- `win_rate`;
- `profit_factor`;
- `expectancy`;
- `robustness_score`;
- `reproducibility_score`;
- `scientific_score`;
- `similarity_score`;
- `diversification_score`;
- `portfolio_return`;
- `aggregate_drawdown`;
- `aggregate_risk_score`.

Nenhuma metrica numerica final deve ser registrada manualmente neste catalogo.
Os valores devem vir de `ResearchExecutionResult`, Validation Suite, Benchmark
e Portfolio Evaluation.

### Classe

`Research Alpha`

A Alpha102 pertence ao conjunto de estrategias candidatas que ja possuem
estrutura institucional suficiente para pesquisa, mas ainda dependem de
validacao numerica completa, robustez, reprodutibilidade, benchmark e avaliacao
de portfolio.

### Familia

`Swing Trade`

A familia Swing Trade exige avaliacao especifica de amostra, gaps, carregamento
entre sessoes, estabilidade de parametros, risco agregado e comportamento fora
da amostra.

### Nivel de Confianca

`PENDING_NUMERICAL_VALIDATION`

Justificativa:

- hipotese quantitativa clara;
- Alpha Factory aprovou a geracao do playbook;
- playbook institucional criado;
- estrategia implementada sem acesso operacional indevido;
- benchmark e portfolio definidos como especificacao;
- Knowledge Base atualizada;
- metricas numericas finais ainda nao registradas neste catalogo.

### Evidencias Documentais

- `docs/ALPHA_102_RESEARCH.md`
- `docs/ALPHA_102_FACTORY_APPROVAL.md`
- `docs/ALPHA_102_PLAYBOOK.md`
- `docs/ALPHA102_BENCHMARK.md`
- `docs/ALPHA102_PORTFOLIO.md`
- `docs/ALPHA102_KNOWLEDGE.md`

### Proxima Etapa Recomendada

Executar campanhas controladas de pesquisa para preencher o catalogo com
metricas oficiais produzidas pela arquitetura, sem recalculo manual e sem
execucao operacional real.
