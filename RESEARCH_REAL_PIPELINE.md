# RESEARCH_REAL_PIPELINE.md

## Missao 222 - Research Real Pipeline

Sprint 14 - TraderIA UX Consolidation  
Projeto: TraderIA  
Data: 2026-06-28

## Objetivo

Eliminar o Research demonstrativo da experiencia principal do Dashboard.

## Implementacao

A aba Research Lab passou a expor apenas acoes ligadas ao dataset selecionado:

- executar Research do Dataset;
- comparar benchmarks existentes;
- validar benchmarks existentes;
- limpar experimentos.

Foram removidos da experiencia principal:

- executar experimento demo;
- executar benchmarks demo;
- executar grid demo;
- ranking demo;
- Alpha001 experiment demo.

## Estado Sem Experimentos

Quando nao ha experimento real, a interface exibe explicitamente:

```text
Nenhum experimento executado.
```

## Limite Cientifico

O pipeline executa PETR4 tecnicamente, mas ainda nao existe Alpha propria para PETR4 diario.

Portanto, resultados de Alpha001 sobre PETR4 devem ser tratados como smoke test tecnico, nao como validacao estatistica.

## Resultado

Research Lab visual deixou de sugerir resultados demonstrativos como se fossem pesquisas reais.
