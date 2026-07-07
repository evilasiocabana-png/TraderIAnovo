# MISSION_TIA-007 - IMPLEMENTAR_MOTOR_DE_LEITURA_DE_MERCADO

## Objetivo

Criar um motor read-only que leia o estado atual do mercado e da posicao para a
saida dinamica, sem alterar SL/TP e sem executar ordem.

## Escopo Autorizado

- Arquivos/pastas permitidos:
  - `domain/`
  - `application/`
  - `tests/`
  - `docs/`
  - `governance/traceability/`
  - `governance/execution/`
- Camadas permitidas:
  - contratos de dominio;
  - servicos de aplicacao read-only;
  - view models e relatorios de auditoria;
  - testes unitarios.
- Camadas proibidas:
  - `infrastructure/execution/`
  - `mt5/experts/`
  - `.traderia/`
  - qualquer codigo que use `order_send()`.

## Dependencias

- `MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY`
- `domain/contracts/dynamic_exit.py`
- `docs/DYNAMIC_EXIT_READ_ONLY_CONTRACT.md`

## Impacto Arquitetural

Esta missao cria a camada de leitura de estado de mercado para alimentar a saida
dinamica. Ela nao autoriza execucao demo, nao move stop e nao recalcula Lab
pesado durante o ciclo leve do Forex.

## Contexto

O contrato read-only `dynamic_exit_*` ja existe. A proxima camada deve calcular
um `MarketState` auditavel a partir de dados ja disponiveis no runtime, como
preco, stop, alvo, posicao, direcao, ATR quando disponivel e contexto de
timeframe do Lab.

## Tarefas

1. Criar contrato/estrutura para o estado de mercado da saida dinamica.
2. Criar motor read-only de classificacao de estado.
3. Cobrir os estados:
   - `NO_POSITION`
   - `NEW_POSITION`
   - `PROTECTED_POSITION`
   - `TREND_RUNNER`
   - `REVERSAL_RISK`
   - `TIME_DECAY`
   - `BAD_EXECUTION_CONTEXT`
4. Integrar a leitura ao fluxo `dynamic_exit_*` sem mudar execucao real.
5. Atualizar documentacao e rastreabilidade.
6. Atualizar ponteiros do ultimo inbox ao concluir.

## Validacao Obrigatoria

- `python -m unittest tests.test_lab_forex_mt5_contract tests.test_report_service tests.test_mt5_trade_audit_service tests.test_mt5_visual_signal_exporter`

Quando disponivel, executar tambem:

- `python scripts/run_critical_ci.py`

## Plano de Testes

- Testar cada estado de mercado com entradas controladas.
- Testar tolerancia a dados ausentes.
- Testar que `dynamic_exit_allowed_to_execute_demo` permanece `false`.
- Testar que nenhuma chamada operacional de MT5 foi criada.

## Plano de Rollback

- Reverter o commit da missao.
- Remover os novos contratos/readers se necessario.
- Manter intactos os contratos da TIA-006 e o comportamento operacional atual.

## Criterios de Aceite

- O motor apenas calcula estado.
- Nenhuma alteracao em SL/TP.
- Nenhuma ordem enviada.
- Todos os estados possuem cobertura de teste.
- O ciclo Forex continua leve e sem recalculo pesado de Lab.
- A governanca registra a proxima missao recomendada.

## Restricoes

- Nao enviar ordens reais.
- Nao usar `order_send()`.
- Preservar MT5 read-only salvo decisao formal.
- Nao alterar provider demo operacional.
- Nao forcar tudo para M1.

