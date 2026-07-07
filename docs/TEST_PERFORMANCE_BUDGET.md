# Test Performance Budget

Este documento define como medir e interpretar o orcamento de performance da
suite de testes do TraderIA_WDO.

O budget e informativo e serve para evitar degradacao progressiva da
produtividade. Ele nao autoriza remocao de testes, enfraquecimento de validacao
arquitetural ou mudanca de comportamento da aplicacao.

## Como Executar

```powershell
python scripts/test_performance_budget.py
```

## Arquivo Gerado

```text
reports/test_performance_budget.json
```

## O Que o Relatorio Mostra

- tempo total da suite medida arquivo por arquivo;
- tempo por arquivo de teste;
- suites mais lentas;
- avisos;
- violacoes;
- status geral;
- data e hora da execucao;
- tendencia quando houver relatorio anterior disponivel.

## Como Interpretar

Avisos nao bloqueiam entrega automaticamente. Eles indicam suites que merecem
observacao, como arquivos lentos ou aumento de tempo em relacao a uma medicao
anterior.

Falha indica degradacao extrema, falha de suite durante a medicao ou estouro de
limite maximo definido no script. Nesse caso, a causa deve ser investigada antes
de considerar a Sprint concluida.

Pequenas variacoes de tempo sao normais. Elas nao devem gerar reescrita de
testes nem mudancas apressadas. O objetivo e detectar tendencia relevante, nao
ruido de maquina.

Otimizacoes devem preservar clareza, cobertura, determinismo e independencia.

## Politica CTO

- Nunca remover teste apenas para reduzir tempo.
- Nunca enfraquecer teste arquitetural.
- Otimizar primeiro setup, duplicacao e fixtures.
- Manter determinismo e independencia da suite.
- Nao mascarar falhas de testes para cumprir budget.
- Nao transformar variacao pequena de tempo em refatoracao desnecessaria.

## Prioridade de Otimizacao

Quando uma suite ficar lenta, investigar nesta ordem:

1. setup repetido desnecessario;
2. fixtures duplicadas;
3. chamadas caras que podem ser substituidas por mocks controlados;
4. escrita em disco fora de diretorios temporarios;
5. dependencia acidental de Streamlit, banco ou arquivos grandes;
6. excesso de verificacoes redundantes no mesmo arquivo.

## Limites

Os limites iniciais ficam definidos em `scripts/test_performance_budget.py` para
serem ajustados pelo CTO quando a suite crescer.

O budget nao faz parte da autorizacao de operacao real. O TraderIA_WDO continua
restrito a pesquisa, replay, simulacao e paper trading visual.
