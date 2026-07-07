# Alpha102 Benchmark

## 1. Objetivo

Registrar o benchmark institucional da Alpha102 contra os benchmarks internos
do TraderIA_WDO, com foco em comparacao com a Alpha001, avaliacao de
consistencia estatistica, vantagens, limitacoes e criterios de continuidade da
pesquisa.

Este documento nao executa pesquisas, nao recalcula metricas e nao altera
estrategias. Ele define o escopo oficial de interpretacao dos resultados que
devem ser produzidos pela infraestrutura existente de Research, Validation,
Benchmark e Portfolio.

## 2. Escopo

O benchmark da Alpha102 deve comparar:

- metricas estruturais da Alpha102;
- metricas financeiras produzidas pelos engines oficiais;
- consistencia estatistica da amostra;
- robustez cientifica da validacao;
- reprodutibilidade;
- dominancia frente a Alpha001;
- similaridade e diversificacao frente ao portfolio;
- vantagens e limitacoes da hipotese Swing Pullback Momentum Continuation.

## 3. Fontes Institucionais

O benchmark deve ser alimentado apenas por resultados oficiais ja produzidos
pela arquitetura:

- `ResearchExecutionResult`;
- `Alpha102ScientificValidationResult`;
- `ValidationSuiteReport`;
- `ValidationCertificationResult`;
- `AlphaBenchmarkReport`;
- `AlphaDominanceResult`;
- `AlphaSimilarityResult`;
- `PortfolioEvaluation`;
- `PortfolioOptimizationReport`, quando disponivel.

Nao devem ser usados valores manuais, planilhas externas, simulacoes fora da
arquitetura ou metricas calculadas diretamente neste documento.

## 4. Alpha102

A Alpha102 e uma estrategia candidata da familia Swing Trade baseada em
continuidade direcional apos pullback controlado.

A hipotese central e que, em mercados liquidos e direcionais, uma tendencia
mensuravel seguida de recuo saudavel, preservacao estrutural e retomada de
momentum pode oferecer assimetria positiva em horizonte Swing Trade.

Caracteristicas esperadas:

- menor frequencia operacional que estrategias intraday;
- maior dependencia de qualidade do contexto de mercado;
- maior exposicao a risco de carregamento entre sessoes;
- necessidade de amostra historica adequada ao horizonte Swing;
- dependencia de filtros de tendencia, pullback, momentum, liquidez e
  volatilidade.

## 5. Benchmark Primario: Alpha001

A Alpha001 e o benchmark interno inicial do TraderIA_WDO, ja integrada ao
Research Lab, Replay, Benchmark Comparator e Dashboard por meio das camadas
oficiais da arquitetura.

A comparacao com a Alpha001 deve ser interpretada como comparacao entre uma
Alpha historicamente consolidada dentro da plataforma e uma candidata Swing em
fase de validacao cientifica.

A Alpha102 nao precisa superar a Alpha001 em todas as metricas para justificar
continuidade. Ela pode agregar valor se demonstrar:

- melhor diversificacao;
- menor similaridade operacional;
- comportamento positivo em regimes diferentes;
- risco agregado aceitavel;
- robustez e reprodutibilidade suficientes;
- contribuicao incremental ao portfolio.

## 6. Metricas Comparativas

As metricas obrigatorias para comparacao sao:

- total_trades;
- net_profit;
- gross_profit;
- gross_loss;
- max_drawdown;
- profit_factor;
- win_rate;
- expectancy;
- robustness_score;
- reproducibility_score;
- scientific_score;
- similarity_score;
- diversification_score.

Nenhuma metrica deve ser recalculada durante o benchmark. Todos os valores
devem vir dos engines e reports oficiais.

## 7. Consistencia Estatistica

A consistencia estatistica da Alpha102 deve ser avaliada pelos seguintes
criterios:

- tamanho minimo de amostra;
- distribuicao de trades por periodo;
- dependencia de poucos outliers;
- estabilidade em Walk Forward;
- estabilidade em Monte Carlo;
- resiliencia em Stress Testing;
- compatibilidade de dataset e replay;
- reprodutibilidade do fingerprint;
- ausencia de degradacao extrema fora da amostra.

Uma Alpha102 com resultado financeiro positivo, mas com baixa amostra,
dependencia excessiva de outliers ou baixa reprodutibilidade, deve permanecer
em pesquisa e nao deve avancar para portfolio.

## 8. Comparacao Qualitativa com Alpha001

| Dimensao | Alpha001 | Alpha102 |
| --- | --- | --- |
| Papel institucional | Benchmark interno inicial | Candidata Swing |
| Horizonte | Validacao historica da plataforma | Swing Trade |
| Tese central | Estrategia proprietaria ja integrada | Pullback em tendencia com retomada de momentum |
| Principal exigencia | Manter consistencia como baseline | Provar robustez e diversificacao |
| Risco critico | Dependencia dos dados e thresholds historicos | Gaps, baixa amostra e falso pullback |
| Criterio de continuidade | Permanecer referencia interna | Agregar valor estatistico e de portfolio |

## 9. Vantagens Potenciais da Alpha102

A Alpha102 pode apresentar vantagens se:

- capturar movimentos direcionais sem perseguir rompimentos tardios;
- reduzir entradas em preco esticado por exigir pullback controlado;
- operar em horizonte complementar ao da Alpha001;
- aumentar diversificacao do portfolio;
- apresentar baixa similaridade com Alphas intraday;
- manter expectancy positiva em regimes direcionais;
- preservar drawdown aceitavel em testes de estresse.

## 10. Limitacoes Identificadas

As principais limitacoes da Alpha102 sao:

- menor quantidade de trades por ser uma estrategia Swing;
- maior risco de gaps entre sessoes;
- sensibilidade a parametros de tendencia e profundidade do pullback;
- possibilidade de falso pullback em mercado lateral;
- risco de redundancia com outras Alphas de momentum;
- dependencia de qualidade superior do dataset historico;
- necessidade de validacao fora da amostra antes de qualquer promocao.

## 11. Criterios de Decisao

A Alpha102 deve ser classificada conforme os resultados oficiais:

- `PORTFOLIO_CANDIDATE`: domina benchmarks relevantes e agrega diversificacao;
- `NEUTRAL`: apresenta desempenho competitivo, mas ainda sem vantagem clara;
- `UNDER_REVIEW`: perde para benchmarks internos ou apresenta fragilidade
  estatistica;
- `REJECTED_FOR_PORTFOLIO`: falha em validacao cientifica, robustez ou
  reprodutibilidade.

Esta classificacao nao aprova operacao real. Ela orienta apenas a continuidade
da pesquisa quantitativa.

## 12. Resultado Institucional

Status deste documento:

`BENCHMARK_SPECIFICATION_READY`

A Alpha102 esta preparada para ser comparada contra a Alpha001 e demais Alphas
internas usando exclusivamente a infraestrutura oficial existente.

Nenhuma estrategia foi alterada.
Nenhuma metrica foi recalculada manualmente.
Nenhuma decisao operacional foi aprovada.
