# MISSION_TIA-010_EXIBIR_SAIDA_DINAMICA_NO_MT5_VISUAL

## Objetivo

Adicionar a recomendacao dinamica ao JSON visual e ao indicador MT5, mostrando
texto curto somente quando houver posicao aberta.

## Escopo autorizado

- Exportar texto visual curto de saida dinamica no payload MT5.
- Preservar compatibilidade com campos existentes.
- Atualizar indicador MT5 para ler o texto curto.
- Exibir somente em blocos com `robot_status = POSICAO_ABERTA_MT5`.
- Proteger graficos sem posicao contra poluicao visual.
- Criar testes de contrato.

## Guardrails

- Nao executar ordens.
- Nao mover SL/TP.
- Nao alterar provider demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo = true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao poluir grafico de ativo sem posicao.

## Criterios de aceite

- JSON visual preserva compatibilidade.
- MT5 visual mostra texto curto para posicao aberta.
- MT5 visual nao mostra texto dinamico quando nao houver posicao.
- Testes focados passam.
- Processing fica vazio ao final.
