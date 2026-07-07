# MISSION_TIA-012_BACKTEST_SAIDA_DINAMICA_READ_ONLY

## Objetivo

Comparar saida original do Lab versus saida dinamica recomendada em modo
read-only.

## Escopo autorizado

- Criar contrato de backtest read-only para saida dinamica.
- Criar motor puro de comparacao de resultados.
- Calcular metricas comparativas.
- Documentar criterios e rastreabilidade.
- Criar testes focados.

## Metricas

- lucro liquido;
- drawdown;
- win rate;
- profit factor;
- expectancy;
- duracao media;
- RR medio;
- dominancia de break-even;
- ganho perdido por saida precoce;
- protecao contra perda.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar provider demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo = true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao substituir politica original do Lab.

## Criterios de aceite

- Motor apenas compara resultados.
- Resultado declara `read_only = true`.
- Nenhum componente operacional e chamado.
- Testes cobrem metricas principais e caso vazio.
