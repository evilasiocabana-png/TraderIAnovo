# MISSION_TIA-023_OTIMIZAR_DYNAMIC_EXIT_RUNTIME

## Objetivo

Otimizar o runtime da saida dinamica, mantendo o motor leve, tolerante a dados
ausentes e sem recalcular Lab pesado.

## Escopo autorizado

- Adicionar cache LRU pequeno no motor unificado read-only.
- Criar fallback seguro para excecoes inesperadas.
- Garantir que recomendacoes externas nao sejam cacheadas indevidamente.
- Criar testes focados de cache, tolerancia e limites.
- Atualizar documentacao, rastreabilidade e governanca.

## Guardrails

- Nao executar ordem.
- Nao mover SL/TP.
- Nao alterar Provider Demo operacional.
- Nao permitir `dynamic_exit_allowed_to_execute_demo=true`.
- Nao recalcular Lab pesado no ciclo leve Forex.
- Nao alterar Dashboard, MT5 visual ou Relatorio.

## Criterios de aceite

- Leituras identicas sem recomendacao externa reutilizam resultado cacheado.
- Cache tem limite e descarta entradas antigas.
- Erros inesperados retornam resultado seguro `REJECTED`.
- Execucao demo permanece desligada.
