# MISSION_TIA-013_PAPER_SIMULATION_SAIDA_DINAMICA

## Objetivo

Rodar a saida dinamica em modo simulado/paper, registrando cada recomendacao e
comparando com o resultado real da politica original.

## Escopo autorizado

- Criar contrato de simulacao paper da saida dinamica.
- Registrar cada recomendacao dinamica recebida.
- Comparar resultado original observado contra resultado dinamico paper.
- Reutilizar o backtest read-only da TIA-012 para consolidacao.
- Criar testes focados.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar provider demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo = true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao executar recomendacao dinamica no Provider Demo.

## Criterios de aceite

- Simulacao registra cada recomendacao.
- Resultado final declara `read_only = true`.
- Resultado final declara `execution_allowed = false`.
- Relatorio compara politica original versus saida dinamica paper.
- Testes cobrem recomendacoes, comparacao e caso vazio.
