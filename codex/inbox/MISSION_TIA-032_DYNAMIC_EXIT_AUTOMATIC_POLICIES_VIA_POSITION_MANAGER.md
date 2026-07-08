# MISSION_TIA-032_DYNAMIC_EXIT_AUTOMATIC_POLICIES_VIA_POSITION_MANAGER

## Tipo

Execucao unica para Codex no repositorio `TraderIAnovo`.

## Objetivo

Evoluir o TraderIAnovo para que as politicas de saida dinamica que hoje estao em modo `read-only`, `simulado` ou `assistido` possam tambem operar em modo automatico controlado, da mesma forma que `BREAK_EVEN` e `ATR_TRAILING_STOP`, sempre via Position Manager central, auditavel e com guardrails de seguranca.

## Arquivos desta missao

Esta missao foi dividida em 4 arquivos no inbox:

```text
codex/inbox/MISSION_TIA-032_DYNAMIC_EXIT_AUTOMATIC_POLICIES_VIA_POSITION_MANAGER.md
codex/inbox/MISSION_TIA-032_PART1_CONTEXT_AND_ARCHITECTURE.md
codex/inbox/MISSION_TIA-032_PART2_POLICIES_AND_PROVIDER_PORTS.md
codex/inbox/MISSION_TIA-032_PART3_TESTS_ACCEPTANCE_AND_REPORT.md
```

O Codex deve ler este arquivo primeiro e depois executar os arquivos PART1, PART2 e PART3 como uma unica missao coesa.

## Contexto

O ultimo inbox registrou:

```text
MISSION_TIA-031_AUDIT_SAFE_MODE_E_STOP_MOVEL
Status: completed
```

Conclusao importante:

```text
O stop management automatico do Provider Demo suporta hoje BREAK_EVEN e ATR_TRAILING_STOP, enquanto outras politicas dinamicas permanecem read-only/simuladas/assistidas ate autorizacao explicita.
```

Esta missao e a autorizacao explicita para desenhar e implementar a evolucao controlada das demais politicas de saida dinamica para execucao automatica, desde que todas passem pelos gates de seguranca.

## Fluxo alvo

```text
Posicao aberta
  -> Trade Plan valido
  -> leitura de mercado minima
  -> politica de saida selecionada
  -> Position Manager calcula acao
  -> valida guardrails
  -> executa ou bloqueia conforme modo configurado
  -> audita tudo
```

## Principio arquitetural obrigatorio

O Runtime Guard nao decide trade e nao move stop.

Responsabilidades:

```text
Research Lab
  Define plano inicial, setup, TF, entrada, stop inicial, alvo e politica de saida base.

Position Manager
  Acompanha posicao aberta, le mercado atual, aplica politica de saida e decide a melhor acao operacional permitida.

DemoExecutionService
  Executa/modifica ordens quando autorizado.

Provider MT5 Demo
  Faz a chamada MT5 de leitura e modificacao.

Runtime Guard
  Protege ciclo, lock, preservacao de estado, diagnostico e performance. Nao decide nem executa saida.
```

## Regra central

Nenhuma politica automatica pode aumentar risco.

Se houver duvida, a decisao obrigatoria e:

```text
BLOCKED
```

## Configuracao obrigatoria

Preservar a configuracao existente:

```text
dynamic_exit_demo_sl_assisted_execution_enabled
```

O default deve continuar:

```text
False
```

Com a flag `False`, o Position Manager pode calcular, recomendar e auditar, mas nao pode modificar SL/TP ou ordem.

Com a flag `True`, o Position Manager pode executar automaticamente apenas acoes seguras e permitidas em conta demo, principalmente `MOVE_STOP` mais protetivo.

## Proibicoes absolutas

```text
- nao executar em conta real;
- nao abrir nova posicao;
- nao aumentar posicao;
- nao inverter posicao;
- nao remover stop;
- nao afastar stop contra o trader;
- nao trocar alpha/setup/timeframe durante posicao aberta;
- nao recalcular Research Lab pesado para gerenciar posicao aberta;
- nao usar Runtime Guard como decisor ou executor operacional.
```

## Relatorio esperado

Ao concluir, gerar:

```text
codex/completed/MISSION_TIA-032_DYNAMIC_EXIT_AUTOMATIC_POLICIES_VIA_POSITION_MANAGER/EXECUTION_REPORT.md
```

O relatorio deve informar arquivos criados/alterados, contratos, politicas automatizadas, politicas bloqueadas, configuracao usada, testes executados, resultado dos testes, riscos remanescentes, rollback e proxima missao recomendada.
