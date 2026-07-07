# MISSION_TIA-022_UNIFICAR_DYNAMIC_EXIT_ENGINE

## Objetivo

Consolidar leitura de mercado, recomendacao dinamica e pre-autorizacao de
politicas de saida em um motor unico auditavel.

## Escopo autorizado

- Criar contrato de entrada e resultado do motor unificado.
- Criar orquestrador read-only para saida dinamica.
- Reusar classificacao, recomendacao e autorizadores existentes.
- Criar testes focados de fluxo unico, fallback e politica sem autorizador.
- Atualizar documentacao, rastreabilidade e governanca.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar Provider Demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo=true` por padrao.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao quebrar compatibilidade com contratos existentes.

## Criterios de aceite

- Uma entrada unica produz uma saida unica auditavel.
- O motor sempre retorna leitura, recomendacao e autorizacao.
- Politicas conhecidas sao roteadas para seus autorizadores.
- Politicas sem autorizador usam fallback seguro.
- Execucao demo permanece desligada.
