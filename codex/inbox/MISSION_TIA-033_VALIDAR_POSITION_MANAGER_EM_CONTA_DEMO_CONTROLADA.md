# MISSION_TIA-033_VALIDAR_POSITION_MANAGER_EM_CONTA_DEMO_CONTROLADA

## Tipo

Execucao unica para Codex no repositorio `TraderIAnovo`.

## Dependencia obrigatoria

Esta missao so deve ser executada depois da conclusao da TIA-032:

```text
MISSION_TIA-032_DYNAMIC_EXIT_AUTOMATIC_POLICIES_VIA_POSITION_MANAGER
```

Se a TIA-032 nao estiver concluida, mover esta missao para `codex/failed/` ou manter no inbox com status bloqueado, sem alterar codigo operacional.

## Objetivo

Validar em ambiente controlado de conta demo se o Position Manager consegue acompanhar uma posicao aberta e modificar Stop Loss automaticamente apenas quando todos os criterios de seguranca forem satisfeitos.

A validacao deve comprovar que:

```text
- o stop inicial continua sendo enviado na entrada;
- o Position Manager detecta posicao aberta;
- o Trade Plan valido e carregado;
- o SL e calculado dinamicamente;
- o SL so e movido se for mais protetivo;
- o sistema nunca afasta stop contra o trader;
- nenhuma nova entrada e feita pelo Position Manager;
- o Research Lab nao e recalculado para gerenciar posicao aberta;
- a flag dynamic_exit_demo_sl_assisted_execution_enabled controla a execucao;
- com a flag False, nada e modificado no MT5;
- com a flag True, apenas SL seguro pode ser modificado em demo.
```

## Escopo

Esta missao deve validar o funcionamento real/controlado do Position Manager em demo, sem liberar conta real e sem ampliar politicas perigosas.

Validar obrigatoriamente:

```text
BREAK_EVEN
ATR_TRAILING_STOP
MARKET_AWARE_STOP_PROTECTION
VOLATILITY_STOP_PROTECTION
MOMENTUM_WEAKNESS_STOP_TIGHTENING
STRUCTURE_BASED_STOP_PROTECTION
```

Acoes ainda bloqueadas nesta missao:

```text
FULL_EXIT
PARTIAL_EXIT
MOVE_TARGET
ADD_POSITION
INVERT_POSITION
REAL_ACCOUNT_EXECUTION
```

## Guardrails absolutos

Nao alterar:

```text
- regras de entrada;
- selecao de alpha;
- selecao de setup;
- timeframe vencedor;
- Research Lab pesado;
- credenciais;
- conta real;
- banco .traderia;
- historico persistente;
- Runtime Guard como nao decisor operacional.
```

O Position Manager nao pode:

```text
- abrir posicao;
- aumentar posicao;
- inverter posicao;
- remover stop;
- afastar stop;
- alterar TP nesta missao;
- fechar posicao automaticamente;
- executar se faltarem posicao, Trade Plan, preco atual ou dados minimos da politica.
```

## Plano de validacao

### 1. Validacao com flag desligada

Configurar:

```text
dynamic_exit_demo_sl_assisted_execution_enabled=False
```

Executar ciclo do Position Manager com posicao demo simulada ou real demo controlada.

Resultado esperado:

```text
- Position Manager calcula decisao;
- auditoria registra recomendacao;
- modify_position_sl NAO e chamado;
- nenhum SL e alterado no MT5;
- execution_status = BLOCKED_BY_CONFIG.
```

### 2. Validacao com flag ligada

Configurar:

```text
dynamic_exit_demo_sl_assisted_execution_enabled=True
```

Executar ciclo com posicao demo controlada.

Resultado esperado:

```text
- Position Manager calcula novo SL;
- valida que o novo SL e mais protetivo;
- chama DemoExecutionService;
- DemoExecutionService chama Provider MT5 Demo;
- Provider executa modify_position_sl;
- auditoria registra STOP_MOVED ou STOP_MOVE_FAILED.
```

### 3. Validacao BUY

Cenario:

```text
side=BUY
entry=1.1000
current_stop=1.0950
current_price=1.1060
```

Resultado esperado:

```text
novo_stop > current_stop
novo_stop nao pode ser menor que current_stop
se break-even for atingido, stop pode ir para entry ou acima, conforme regra.
```

### 4. Validacao SELL

Cenario:

```text
side=SELL
entry=1.1000
current_stop=1.1050
current_price=1.0940
```

Resultado esperado:

```text
novo_stop < current_stop
novo_stop nao pode ser maior que current_stop
se break-even for atingido, stop pode ir para entry ou abaixo, conforme regra.
```

### 5. Validacao de bloqueios

Testar e auditar:

```text
- sem posicao aberta -> POSITION_ABSENT;
- sem Trade Plan -> TRADE_PLAN_ABSENT;
- sem preco atual -> MARKET_DATA_ABSENT;
- sem ATR em ATR_TRAILING_STOP -> ATR_ABSENT;
- sem estrutura em STRUCTURE_BASED_STOP_PROTECTION -> STRUCTURE_ABSENT;
- novo stop pior que atual -> STOP_MOVE_BLOCKED_NOT_PROTECTIVE;
- politica nao suportada -> POLICY_BLOCKED_UNSUPPORTED_ACTION.
```

## Testes automatizados obrigatorios

Garantir que os testes criados na TIA-032 continuem passando e adicionar testes de integracao controlada quando possivel:

```text
1. Flag False bloqueia execucao real e apenas audita.
2. Flag True permite modify_position_sl em demo.
3. BUY move SL para cima.
4. SELL move SL para baixo.
5. BUY nao afasta stop.
6. SELL nao afasta stop.
7. Sem Trade Plan nao move.
8. Sem posicao nao move.
9. Sem ATR nao move.
10. Sem estrutura nao move.
11. DemoExecutionService e chamado somente pelo fluxo autorizado.
12. Provider Real nao e chamado.
13. Position Manager nao abre nova ordem.
14. Research Lab pesado nao e chamado.
15. Auditoria registra evento correto para cada resultado.
```

## Auditoria obrigatoria

Registrar arquivo ou estrutura de auditoria contendo:

```text
timestamp
symbol
ticket
side
policy
entry
current_price
current_stop
proposed_stop
action
execution_mode
execution_status
reason
missing_data
provider_result
```

Eventos obrigatorios:

```text
VALIDATION_STARTED
VALIDATION_COMPLETED
VALIDATION_FAILED
STOP_HELD
STOP_MOVED
STOP_MOVE_FAILED
STOP_MOVE_BLOCKED_BY_CONFIG
STOP_MOVE_BLOCKED_NOT_PROTECTIVE
POSITION_ABSENT
TRADE_PLAN_ABSENT
MARKET_DATA_ABSENT
ATR_ABSENT
STRUCTURE_ABSENT
REAL_ACCOUNT_BLOCKED
```

## Documentacao obrigatoria

Atualizar:

```text
docs/architecture/POSITION_MANAGER.md
docs/architecture/DYNAMIC_EXIT_AUTOMATIC_POLICIES.md
docs/architecture/MARKET_AWARE_EXIT_PLAN.md
```

Criar, se fizer sentido:

```text
docs/validation/POSITION_MANAGER_DEMO_VALIDATION.md
```

A documentacao deve registrar:

```text
- como validar em demo;
- quais flags ligar/desligar;
- quais cenarios foram testados;
- quais politicas executaram;
- quais politicas permaneceram bloqueadas;
- riscos remanescentes;
- criterio para futura liberacao assistida/automatica ampliada.
```

## Criterios de aceite

A missao sera aceita se:

```text
- TIA-032 estiver concluida;
- testes automatizados passarem;
- com flag False nada for executado no MT5;
- com flag True o SL for modificado apenas em demo e apenas quando mais protetivo;
- nenhum fluxo de conta real for acionado;
- nenhuma nova posicao for aberta pelo Position Manager;
- nenhuma saida total/parcial for executada;
- logs de auditoria forem gerados;
- documentacao de validacao for criada/atualizada;
- houver relatorio final em codex/completed.
```

## Relatorio esperado

Ao concluir, gerar:

```text
codex/completed/MISSION_TIA-033_VALIDAR_POSITION_MANAGER_EM_CONTA_DEMO_CONTROLADA/EXECUTION_REPORT.md
```

O relatorio deve conter:

```text
- status;
- data/hora;
- dependencia TIA-032 confirmada ou nao;
- arquivos alterados;
- testes executados;
- resultado dos testes;
- cenarios validados;
- politicas validadas;
- eventos de auditoria gerados;
- riscos remanescentes;
- rollback;
- proxima missao recomendada.
```

## Proxima missao recomendada

Se a validacao demo for bem-sucedida:

```text
MISSION_TIA-034_OPERATIONAL_DECISION_ENGINE_FULL_POSITION_ACTIONS_READ_ONLY
```

Objetivo futuro: ampliar o motor para avaliar `PARTIAL_EXIT`, `FULL_EXIT`, `MOVE_TARGET` e outras acoes, inicialmente em modo read-only/auditoria antes de qualquer execucao.
