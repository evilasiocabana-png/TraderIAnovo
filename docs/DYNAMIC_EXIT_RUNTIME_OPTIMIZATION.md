# Dynamic Exit Runtime Optimization

## Status

Read-only.

## Objetivo

Manter o `DynamicExitUnifiedEngine` leve para uso em ciclo de Forex sem
recalcular Lab pesado.

## Otimizacoes implementadas

- cache LRU pequeno para leituras identicas;
- cache desligavel com `max_cache_entries=0`;
- recomendacoes externas nao entram no cache;
- fallback seguro em excecao inesperada;
- resultado de erro sempre bloqueia execucao demo.

## Guardrails

- nao envia ordem;
- nao move SL/TP;
- nao altera Provider Demo;
- nao altera Dashboard, MT5 visual ou Relatorio;
- `allowed_to_execute_demo=false` em todos os caminhos.
