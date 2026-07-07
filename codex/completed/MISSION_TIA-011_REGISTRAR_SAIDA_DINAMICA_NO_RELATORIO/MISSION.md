# MISSION_TIA-011_REGISTRAR_SAIDA_DINAMICA_NO_RELATORIO

## Objetivo

Registrar no Relatorio a politica original, recomendacao dinamica, motivo,
confianca, estado de mercado, acao executada e resultado final.

## Escopo autorizado

- Expandir contratos read-only de relatorio/auditoria.
- Transportar campos `dynamic_exit_*` ja calculados.
- Exibir os campos na tabela de auditoria MT5.
- Registrar acao executada como observacao, sem decisao operacional.
- Preservar compatibilidade com snapshots e registros antigos.
- Criar testes de contrato.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar provider demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo = true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- O Relatorio observa; nao decide saida.

## Criterios de aceite

- Relatorio registra politica original e recomendacao dinamica.
- Relatorio registra motivo, confianca, estado de mercado e stop candidato.
- Relatorio registra acao executada e resultado final observados.
- Testes focados passam.
- Processing fica vazio ao final.
