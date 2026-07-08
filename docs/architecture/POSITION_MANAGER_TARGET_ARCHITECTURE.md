# Arquitetura-Alvo do Position Manager Inteligente

Data: 2026-07-08
Projeto: TraderIA Novo
Status: proposta arquitetural, sem implementacao operacional

## Objetivo

Definir a arquitetura futura do gerenciamento de posicoes do TraderIA Novo.

Esta missao nao altera comportamento do sistema. Nao implementa novas regras, nao modifica execucao, nao altera Robo Demo, nao altera MT5 e nao muda o Position Manager atual.

O objetivo e estabelecer o contrato-alvo entre Research Lab, Trade Plan, Robo Demo, Position Manager e Relatorio para que futuras missoes implementem a evolucao com rastreabilidade e rollback.

## Principio Central

O Research Lab continua sendo a origem da decisao operacional.

O Position Manager nao substitui o Lab e nao recalcula a estrategia. Ele administra uma posicao que ja foi aberta com base no plano aprovado.

```text
Research Lab decide o plano.
Trade Plan materializa o plano.
Robo Demo executa a entrada.
Position Manager administra a vida da posicao.
Relatorio audita tudo.
```

## Filosofia-Alvo

O Position Manager deixa de ser apenas um modificador de Stop Loss.

Responsabilidade atual:

```text
Mover o Stop.
```

Responsabilidade-alvo:

```text
Maximizar a qualidade da saida da posicao aberta.
```

Isso significa acompanhar continuamente se a operacao ainda merece permanecer aberta, se deve ser protegida ou se deve ser encerrada antes do alvo original.

## Contrato de Responsabilidades

### Research Lab

O Research Lab continua responsavel por decidir:

- setup;
- modelo vencedor;
- timeframe;
- direcao;
- entrada;
- stop inicial;
- RR;
- alvo;
- politica de gestao pos-entrada;
- parametros da politica pos-entrada.

O Lab nao deve administrar a posicao em tempo real. Ele define o plano.

### Trade Plan

O Trade Plan deve representar fielmente o plano produzido pelo Lab.

Responsabilidades-alvo:

- transportar `entry`;
- transportar `initial_stop`;
- transportar `initial_rr`;
- transportar `initial_target`;
- transportar `post_entry_exit_policy`;
- transportar `post_entry_exit_parameters`;
- transportar `post_entry_activation_condition`;
- nao distorcer o racional do Lab;
- nao trocar stop inicial por politica movel;
- nao acoplar stop inicial e gestao pos-entrada.

O Trade Plan pode materializar calculos desde que os campos indiquem claramente a origem e a regra usada.

### Robo Demo

O Robo Demo permanece simples.

Responsabilidades-alvo:

- abrir a posicao;
- enviar direcao;
- enviar volume;
- enviar entrada ou preco operacional;
- enviar stop inicial;
- enviar alvo inicial.

Fora de escopo para o Robo Demo:

- decidir saida;
- mover SL;
- fechar posicao por leitura de mercado;
- recalcular Lab;
- escolher politica de saida sozinho.

### Position Manager

O Position Manager passa a ser o gerente da posicao aberta.

Ele so atua depois de existir posicao aberta.

Responsabilidades-alvo:

- detectar posicao aberta;
- carregar Trade Plan valido salvo;
- ler preco atual;
- ler candle atual;
- ler ATR;
- ler momentum;
- ler volatilidade;
- ler estrutura;
- calcular estado da posicao;
- avaliar saude do trade;
- decidir se mantem, protege ou encerra;
- auditar toda decisao;
- executar apenas acoes autorizadas por contrato e configuracao.

O Position Manager nao deve:

- abrir nova ordem;
- escolher setup;
- recalcular Lab pesado;
- alterar TP sem politica especifica futura;
- atuar em conta real;
- ignorar o plano original.

## Estados-Alvo da Posicao

Estados sugeridos:

```text
NO_POSITION
NEW_POSITION
HEALTHY_POSITION
PROTECTED_POSITION
TREND_RUNNER
MOMENTUM_WEAKNESS
REVERSAL_RISK
TIME_DECAY
STRUCTURE_BREAK_RISK
VOLATILITY_RISK
LOW_PROBABILITY_TO_TARGET
BAD_EXECUTION_CONTEXT
EXIT_REQUIRED
POSITION_CLOSED
```

## Acoes-Alvo do Position Manager

Acoes sugeridas:

```text
HOLD_POSITION
PROTECT_POSITION
MOVE_TO_BREAK_EVEN
ATR_TRAILING
STRUCTURE_PROTECTION
VOLATILITY_PROTECTION
MOMENTUM_PROTECTION
EARLY_EXIT
FULL_EXIT
NO_ACTION_BAD_CONTEXT
```

Cada acao deve ter:

- motivo;
- dados usados;
- confianca;
- permissao de execucao;
- modo de execucao;
- resultado;
- log auditavel.

## Decisoes-Alvo

### Manter Posicao

Usar quando:

- o setup original continua valido;
- o movimento ainda tem potencial;
- o momentum segue favoravel;
- o risco nao aumentou;
- o preco ainda tem condicao razoavel de buscar o alvo.

Saida esperada:

```text
action = HOLD_POSITION
execution = NONE
```

### Proteger Posicao

Usar quando:

- a posicao ja andou a favor;
- existe ganho suficiente para reduzir risco;
- o stop pode ser melhorado sem sufocar a operacao;
- a protecao nao piora o risco;
- o stop candidato fica do lado correto do mercado.

Exemplos:

- break-even;
- ATR trailing;
- protecao por estrutura;
- protecao por volatilidade;
- protecao por perda de momentum.

Saida esperada:

```text
action = PROTECT_POSITION | MOVE_TO_BREAK_EVEN | ATR_TRAILING
execution = MODIFY_SL_ONLY
```

### Encerrar Antecipadamente

Usar quando o mercado perdeu potencial de atingir o alvo original.

Exemplos de motivo:

- perda de momentum;
- enfraquecimento do movimento;
- reversao provavel;
- exaustao;
- falha de continuacao;
- deterioracao do contexto;
- aumento do risco operacional;
- baixa probabilidade de atingir TP.

Importante: fechamento antecipado nao significa erro do Lab. Significa adaptacao dinamica depois que o mercado mudou.

Saida esperada futura:

```text
action = EARLY_EXIT | FULL_EXIT
execution = CLOSE_POSITION
```

Essa capacidade ainda nao existe no contrato operacional atual e deve ser implementada apenas em missao futura, com gates especificos.

## Contratos Novos Propostos

### PositionLifecyclePlan

Contrato derivado do Trade Plan e usado pelo Position Manager.

Campos sugeridos:

```text
symbol
timeframe
side
entry_price
initial_stop
initial_target
initial_rr
initial_risk
post_entry_exit_policy
post_entry_exit_parameters
activation_condition
lab_model
lab_alpha
lab_setup
created_at
plan_version
```

### PositionStateSnapshot

Leitura atual da posicao.

Campos sugeridos:

```text
symbol
ticket
side
volume
entry_price
current_price
current_stop
current_target
floating_profit
r_multiple
time_in_position
atr
momentum
volatility
spread
support
resistance
market_structure
last_candle_time
```

### PositionManagerDecision

Decisao auditavel do Position Manager.

Campos sugeridos:

```text
symbol
ticket
state
action
reason
confidence
allowed_to_execute
execution_mode
requested_stop
requested_close_volume
requested_close_reason
final_exit_reason
source
created_at
```

### PositionManagerExecutionResult

Resultado da acao operacional.

Campos sugeridos:

```text
symbol
ticket
action
submitted
success
provider_status
provider_message
old_stop
new_stop
close_price
closed_volume
final_exit_reason
created_at
```

## Motivos de Encerramento-Alvo

Taxonomia sugerida para o Relatorio:

```text
TAKE_PROFIT
STOP_LOSS
BREAK_EVEN
TRAILING_STOP
EARLY_EXIT_MOMENTUM_LOSS
EARLY_EXIT_REVERSAL
EARLY_EXIT_TIME_DECAY
EARLY_EXIT_STRUCTURE_BREAK
EARLY_EXIT_LOW_PROBABILITY
MANUAL_EXIT
PROVIDER_REJECTED
UNKNOWN
```

## Relatorio-Alvo

O Relatorio deve exibir e registrar:

```text
Plano inicial
  -> Estado do mercado
  -> Estado da posicao
  -> Decisao do Position Manager
  -> Motivo da decisao
  -> Acao solicitada
  -> Resultado operacional
  -> Resultado final da posicao
```

Campos importantes:

- stop inicial;
- alvo inicial;
- RR inicial;
- politica pos-entrada;
- stop atual;
- stop candidato;
- estado da posicao;
- decisao do Position Manager;
- motivo da decisao;
- acao executada;
- motivo final de encerramento.

## Impacto nos Modulos Existentes

### `research/mt5_research_trade_plan.py`

Impacto futuro:

- separar stop inicial de politica pos-entrada;
- adicionar campos explicitos de `initial_stop` e `post_entry_exit_policy`;
- preservar compatibilidade com snapshots antigos.

### `application/mt5_demo_robot_service.py`

Impacto futuro:

- continuar abrindo posicao com o plano inicial;
- garantir que nao existe inteligencia de saida nesta camada;
- consumir somente `initial_stop` e `initial_target` na abertura.

### `application/position_manager_service.py`

Impacto futuro:

- evoluir de gestor de SL para gerenciador de ciclo de vida;
- continuar suportando `modify_position_sl`;
- adicionar contrato futuro para fechamento controlado;
- separar decisao de execucao;
- registrar decisao mesmo quando nao executa.

### `application/demo_execution_service.py`

Impacto futuro:

- manter `submit_order` para entrada;
- manter `modify_position_sl` para protecao;
- adicionar porta futura de fechamento apenas se aprovada por missao especifica.

### `infrastructure/execution/mt5_demo_execution_provider.py`

Impacto futuro:

- manter `TRADE_ACTION_SLTP` para mover SL;
- adicionar fechamento via ordem oposta somente em contrato futuro;
- bloquear conta real;
- preservar TP quando a acao for apenas protecao.

### `application/mt5_trade_audit_service.py`

Impacto futuro:

- diferenciar motivo final de saida;
- registrar decisao do Position Manager;
- registrar se foi hold, protect ou exit;
- separar resultado de TP/SL/trailing/early/manual.

## Guardrails

Qualquer implementacao futura deve respeitar:

- nao operar conta real;
- nao fechar posicao sem flag especifica;
- nao mover SL para piorar risco;
- nao mover SL para lado errado do mercado;
- nao alterar TP em missoes de protecao;
- nao recalcular Lab pesado em ciclo leve;
- nao apagar `.traderia`;
- manter rollback documentado;
- manter testes antes de ativar execucao.

## Plano de Implementacao em Missoes Futuras

### TIA-PM-001 - Formalizar contratos read-only

Criar contratos `PositionLifecyclePlan`, `PositionStateSnapshot`, `PositionManagerDecision` e `PositionManagerExecutionResult`.

Sem execucao.

### TIA-PM-002 - Separar stop inicial de politica pos-entrada

Atualizar Trade Plan para expor explicitamente:

- `initial_stop`;
- `initial_rr`;
- `initial_target`;
- `post_entry_exit_policy`;
- `post_entry_exit_parameters`.

Sem alterar envio real ainda.

### TIA-PM-003 - Exibir contrato novo no Forex e Relatorio

Mostrar plano inicial e politica pos-entrada separadamente.

Sem alterar MT5.

### TIA-PM-004 - Aplicar ativacao explicita da politica pos-entrada

Implementar estados:

- pendente;
- ativa;
- bloqueada;
- executada.

Exemplo: trailing so ativa depois de +1R ou condicao definida.

### TIA-PM-005 - Unificar gestao de SL no Position Manager

Garantir que apenas o Position Manager decide movimento de SL.

### TIA-PM-006 - Criar contrato read-only de early exit

Criar decisao de fechamento antecipado apenas como recomendacao auditavel.

Sem fechar posicao.

### TIA-PM-007 - Simular early exit em paper

Comparar:

- manter ate TP/SL;
- proteger;
- sair antecipadamente.

Sem execucao MT5.

### TIA-PM-008 - Autorizar early exit demo assistido

Permitir fechamento manual/assistido em conta demo, com confirmacao e gates.

### TIA-PM-009 - Autorizar early exit demo automatico controlado

Somente apos validacao estatistica, logs, testes e rollback.

## Criterio de Conclusao da Arquitetura

Esta arquitetura sera considerada pronta para implementacao quando:

- Research Lab continuar sendo a origem do plano;
- Trade Plan separar plano inicial e gestao pos-entrada;
- Robo Demo abrir posicao sem inteligencia adicional;
- Position Manager tiver contrato para hold/protect/exit;
- Relatorio distinguir o motivo final de saida;
- testes cobrirem nascimento, protecao e encerramento;
- execucao real permanecer bloqueada ate missao especifica.

## Conclusao

O Position Manager deve evoluir para um Gerenciador Inteligente de Posicao, mas a evolucao precisa ocorrer por camadas.

O primeiro passo nao e fechar posicao. O primeiro passo e criar contratos claros para separar:

```text
plano inicial
gestao pos-entrada
decisao de permanencia
decisao de protecao
decisao de encerramento
resultado final
```

Somente depois disso o sistema deve receber execucao controlada de fechamento antecipado.
