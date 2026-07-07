# MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY

## Tipo da Missao

Implementacao segura • Contrato read-only • Governanca operacional

---

## Objetivo

Implementar o contrato inicial de saida dinamica em modo **read-only**, permitindo que o TraderIA Novo transporte, exiba e audite recomendacoes de saida dinamica sem alterar a execucao real de SL/TP.

Esta missao deve preparar o sistema para futuras politicas dinamicas de saida, preservando a arquitetura atual e mantendo `dynamic_exit_allowed_to_execute_demo = false`.

---

## Contexto

A `MISSION_TIA-004_ANALISAR_STOPS_MOVEIS` confirmou que o Lab avalia 9 politicas canonicas de saida, mas o provider demo MT5 aplica gestao dinamica real somente para `BREAK_EVEN` e `ATR_TRAILING_STOP`.

A `MISSION_TIA-005_PROJETAR_SAIDA_DINAMICA_BASEADA_EM_LEITURA_DE_MERCADO` definiu que a saida dinamica deve comecar como camada de recomendacao auditavel, sem permitir execucao automatica de novas politicas.

Fluxo desejado nesta missao:

```text
Lab
  -> politica base e parametros
  -> contrato read-only de saida dinamica
  -> Forex Runtime transporta/observa
  -> MT5 Visual exibe recomendacao quando houver posicao
  -> Relatorio audita
  -> Provider demo NAO executa nova gestao de SL/TP
```

---

## Regras Obrigatorias

1. Nao alterar comportamento operacional de entrada.
2. Nao alterar envio de ordens reais.
3. Nao autorizar nova gestao real de SL/TP.
4. Nao fazer o MT5 escolher politica sozinho.
5. Nao recalcular Lab pesado no ciclo leve do Forex.
6. Nao substituir `stop_management` atual.
7. Preservar compatibilidade com planos e snapshots existentes.
8. Manter `dynamic_exit_allowed_to_execute_demo` como `false` nesta fase.

---

## Campos Read-only Esperados

Adicionar suporte contratual, quando tecnicamente adequado, para campos como:

```text
dynamic_exit_policy
dynamic_exit_action
dynamic_exit_reason
dynamic_exit_confidence
dynamic_exit_market_state
dynamic_exit_r_multiple
dynamic_exit_candidate_stop
dynamic_exit_allowed_to_execute_demo
dynamic_exit_source
```

Valor obrigatorio inicial:

```text
dynamic_exit_allowed_to_execute_demo = false
```

---

## Acoes Dinamicas Read-only

Catalogar acoes de recomendacao, sem execucao real:

```text
KEEP_ORIGINAL_PLAN
PROTECT_TO_BREAK_EVEN
TRAIL_BY_ATR
TRAIL_BY_STRUCTURE
TIGHTEN_BY_MOMENTUM_LOSS
TIME_DECAY_EXIT_WATCH
NO_ACTION_BAD_CONTEXT
```

---

## Estados de Mercado/Posicao

Suportar, documentar ou preparar os seguintes estados:

```text
NO_POSITION
NEW_POSITION
PROTECTED_POSITION
TREND_RUNNER
REVERSAL_RISK
TIME_DECAY
BAD_EXECUTION_CONTEXT
```

---

## Escopo Tecnico

O Codex deve inspecionar o codigo real e implementar apenas o minimo necessario para transportar os campos read-only pelo fluxo:

```text
Lab / TradePlan
-> Forex Runtime
-> Dashboard ViewModel
-> MT5 Visual JSON
-> Relatorio / Auditoria
```

A implementacao pode envolver, se confirmado no codigo real:

- contratos de dominio;
- dataclasses ou DTOs;
- serializacao JSON;
- view models;
- exportador visual MT5;
- relatorio/auditoria;
- testes de preservacao de contrato.

---

## Arquivos Provavelmente Impactados

O Codex deve confirmar no codigo real antes de alterar. Possiveis arquivos:

```text
research/mt5_research_trade_plan.py
application/dashboard_service.py
application/forex_mt5_service.py
application/dashboard_view_model.py
application/mt5_visual_signal_exporter.py
application/report_service.py
domain/contracts/forex_signal.py
domain/contracts/report_row.py
domain/contracts/trade_audit.py
tests/test_lab_forex_mt5_contract.py
tests/test_mt5_visual_signal_exporter.py
tests/test_report_service.py
```

---

## Arquivos Proibidos ou Sensiveis

Nao alterar comportamento operacional em:

```text
infrastructure/execution/mt5_demo_execution_provider.py
mt5/experts/
.traderia/
```

O provider demo pode ser lido para garantir compatibilidade, mas nao deve passar a executar novas politicas nesta missao.

---

## Entregaveis

1. Contrato read-only implementado ou preparado no fluxo correto.
2. Campos dinamicos transportados sem quebrar contratos atuais.
3. Exportacao JSON capaz de incluir os campos quando disponiveis.
4. Relatorio/auditoria capaz de registrar a recomendacao read-only.
5. Testes cobrindo preservacao Lab -> Forex -> MT5 -> Relatorio.
6. Documentacao de rastreabilidade atualizada.

Atualizar ou criar, conforme necessario:

```text
docs/DYNAMIC_EXIT_READ_ONLY_CONTRACT.md
governance/traceability/DYNAMIC_EXIT_CONTRACT_TRACEABILITY.md
governance/execution/EXECUTION_LOG.md
governance/execution/MISSION_INDEX.md
governance/execution/PROJECT_STATUS.md
governance/execution/NEXT_MISSION.md
governance/execution/EXECUTION_STATE.json
codex/completed/MISSION_TIA-006_IMPLEMENTAR_CONTRATO_DE_SAIDA_DINAMICA_READ_ONLY/EXECUTION_REPORT.md
```

---

## Testes Obrigatorios

Criar ou atualizar testes para garantir:

1. Campos read-only sao preservados no contrato.
2. `dynamic_exit_allowed_to_execute_demo` permanece `false`.
3. Exportacao JSON nao quebra sinais antigos.
4. MT5 visual recebe campos opcionais sem exigir posicao aberta.
5. Relatorio registra recomendacao sem decidir saida.
6. Forex nao recalcula Lab pesado no ciclo leve.
7. Falta de campos dinamicos nao quebra planos antigos.
8. Provider demo nao executa nova politica por causa destes campos.

Executar, se possivel:

```bash
pytest
```

Se nao for possivel executar, registrar o motivo no relatorio.

---

## Criterios de Aceite

A missao so sera aceita se:

- nenhum comportamento operacional de ordem/SL/TP for alterado;
- a saida dinamica existir apenas como recomendacao read-only;
- `dynamic_exit_allowed_to_execute_demo` estiver sempre `false` nesta fase;
- o fluxo Lab -> Forex -> MT5 Visual -> Relatorio preservar os campos dinamicos;
- snapshots e contratos antigos continuarem compativeis;
- os testes relevantes forem criados/atualizados;
- a documentacao de governanca for atualizada;
- o relatorio de execucao for salvo em `codex/completed/`.

---

## Resultado Esperado

Ao final, o TraderIA Novo deve conseguir transportar uma recomendacao dinamica de saida de forma auditavel, sem executar nenhuma nova gestao real de stop.

O sistema devera estar pronto para a proxima etapa:

```text
MISSION_TIA-007_EXIBIR_SAIDA_DINAMICA_NO_FOREX_E_RELATORIO
```

ou, se o Codex julgar que a exibicao ja foi parcialmente coberta, recomendar a proxima missao segura com base no estado real do codigo.

---

## Rollback

O rollback deve remover apenas campos/contratos/documentacao read-only. Nao deve haver impacto operacional esperado, pois nenhuma execucao real de SL/TP deve ser adicionada nesta missao.