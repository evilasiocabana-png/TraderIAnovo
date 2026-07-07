# MISSION_TIA-021_AUTORIZAR_PARABOLIC_SAR_DEMO

## Objetivo

Preparar a pre-autorizacao controlada de `PARABOLIC_SAR` em modo demo,
mantendo a fase read-only.

## Escopo autorizado

- Criar autorizador read-only para Parabolic SAR.
- Criar testes focados de elegibilidade e rejeicao.
- Criar documentacao e rastreabilidade.
- Atualizar governanca do inbox.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar Provider Demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo=true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao autorizar politica diferente de `PARABOLIC_SAR`.

## Criterios de aceite

- `PARABOLIC_SAR` pode ficar elegivel apenas em leitura de reversao rapida.
- Stop candidato deve melhorar a protecao e permanecer do lado correto do
  mercado.
- Momentum deve confirmar risco contra a posicao.
- Execucao demo permanece desligada.
- Testes cobrem casos elegiveis e rejeitados.
