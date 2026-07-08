# MISSION_TIA-032 - PART 3 - TESTS_ACCEPTANCE_AND_REPORT

## Objetivo desta parte

Definir testes obrigatorios, criterios de aceite, guardrails de nao alteracao e relatorio final da missao TIA-032.

## Testes obrigatorios

Criar testes automatizados para:

```text
1. BUY move SL para cima quando novo stop e mais protetivo.
2. SELL move SL para baixo quando novo stop e mais protetivo.
3. BUY nao afasta stop para baixo.
4. SELL nao afasta stop para cima.
5. Sem Trade Plan nao move.
6. Sem posicao aberta nao move.
7. Sem preco atual nao move.
8. Sem ATR em ATR_TRAILING_STOP nao move.
9. BREAK_EVEN calcula stop corretamente.
10. ATR_TRAILING_STOP calcula stop corretamente.
11. Flag False calcula mas nao executa.
12. Flag True executa modify_position_sl em demo.
13. Politica dinamica unsupported fica bloqueada.
14. MARKET_AWARE_STOP_PROTECTION so executa MOVE_STOP seguro.
15. STRUCTURE_BASED_STOP_PROTECTION bloqueia sem estrutura.
16. Position Manager nunca abre nova posicao.
17. Research Lab nao e chamado durante gestao de posicao aberta.
18. Runtime Guard nao move stop.
```

## Criterios de aceite

A missao sera aceita se:

```text
- O stop inicial continua sendo enviado na entrada.
- O Position Manager detecta posicao aberta.
- O Position Manager carrega Trade Plan valido salvo.
- O Position Manager calcula nova decisao operacional.
- BREAK_EVEN continua suportado.
- ATR_TRAILING_STOP continua suportado.
- Demais politicas dinamicas podem gerar acao padronizada.
- Politicas dinamicas seguras podem executar MOVE_STOP automaticamente em demo quando a flag estiver True.
- Com a flag False, nada e executado; apenas auditado/recomendado.
- O sistema nunca afasta stop contra o trader.
- O sistema nunca abre nova entrada pelo Position Manager.
- O sistema nunca recalcula Research Lab pesado para gerenciar posicao aberta.
- Safe Mode bloqueia execucao quando faltarem requisitos.
- Logs/auditoria registram todos os cenarios importantes.
- Testes automatizados passam.
```

## Guardrails de nao alterar

Nao alterar:

```text
- regras de entrada;
- selecao de alpha vencedora;
- selecao de setup;
- timeframe vencedor;
- stop inicial de entrada, exceto preservar compatibilidade;
- envio de ordem real;
- credenciais;
- banco .traderia;
- historico persistente;
- Research Lab pesado;
- Runtime Guard como executor de trade.
```

## Documentacao obrigatoria

Atualizar ou criar:

```text
docs/architecture/POSITION_MANAGER.md
docs/architecture/MARKET_AWARE_EXIT_PLAN.md
docs/architecture/DYNAMIC_EXIT_AUTOMATIC_POLICIES.md
```

A documentacao deve explicar:

```text
- diferenca entre entrada, gestao de posicao e runtime;
- quais politicas podem executar automaticamente;
- quais politicas continuam bloqueadas;
- como a flag dynamic_exit_demo_sl_assisted_execution_enabled controla execucao;
- por que o default continua False;
- como Safe Mode acompanha sem recalcular Lab;
- como auditoria registra decisoes;
- por que conta real permanece bloqueada.
```

## Relatorio esperado

Ao concluir, gerar:

```text
codex/completed/MISSION_TIA-032_DYNAMIC_EXIT_AUTOMATIC_POLICIES_VIA_POSITION_MANAGER/EXECUTION_REPORT.md
```

O relatorio deve informar:

```text
- arquivos criados;
- arquivos alterados;
- contratos implementados;
- politicas automatizadas;
- politicas ainda bloqueadas;
- configuracao usada;
- testes executados;
- resultado dos testes;
- riscos remanescentes;
- rollback;
- proxima missao recomendada.
```

## Rollback esperado

O rollback deve preservar:

```text
- entrada existente;
- Trade Plan salvo;
- banco .traderia;
- configuracoes persistentes;
- Provider Demo existente;
- logs anteriores;
- documentos de arquitetura anteriores.
```

Rollback sugerido:

```text
- remover novos modulos de Position Manager se causarem regressao;
- reverter alteracoes no DemoExecutionService/Provider que afetem execucao;
- manter docs se forem apenas explicativas, salvo contradicao;
- voltar ao comportamento anterior: BREAK_EVEN/ATR_TRAILING_STOP ou read-only conforme estado anterior.
```

## Proxima missao recomendada

Depois desta missao, recomendar uma das duas:

```text
MISSION_TIA-033_VALIDAR_POSITION_MANAGER_EM_CONTA_DEMO_CONTROLADA
```

ou

```text
MISSION_TIA-033_RUNTIME_GUARD_EXTRACTION_AFTER_POSITION_MANAGER_STABLE
```

A primeira deve ter prioridade se o Position Manager tiver sido implementado com execucao automatica demo.
