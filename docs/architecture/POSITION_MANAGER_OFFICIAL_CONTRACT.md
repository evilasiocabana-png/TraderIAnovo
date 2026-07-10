# Contrato Oficial do Position Manager

Data: 2026-07-08
Projeto: TraderIA Novo
Status: referencia arquitetural oficial
Escopo: arquitetura documental, sem alteracao operacional

## Declaracao de Escopo

Este documento consolida a arquitetura final do gerenciamento de posicoes do TraderIA Novo.

Ele substitui, como referencia oficial de arquitetura futura, as definicoes dispersas em:

- `TRADE_ENTRY_EXIT_CONTRACT_AUDIT.md`
- `POSITION_MANAGER_TARGET_ARCHITECTURE.md`

Esses documentos continuam validos como historico e diagnostico, mas o contrato oficial para futuras implementacoes e este.

Esta consolidacao nao implementa regra de mercado, nao modifica MT5, nao altera Robo Demo, nao muda resultado de trades e nao habilita fechamento antecipado.

## Fluxo Oficial

```text
Research Lab
  -> Trade Plan
  -> Robo Demo
  -> Position Manager
  -> Relatorio
```

Cada camada possui responsabilidade unica.

## Responsabilidades Oficiais

### Research Lab

Origem da estrategia e do plano.

Responsabilidades:

- decidir setup;
- decidir modelo vencedor;
- decidir timeframe;
- decidir direcao candidata;
- decidir entrada ou regra de entrada;
- decidir stop inicial ou regra de stop inicial;
- decidir RR inicial;
- decidir alvo inicial ou regra de alvo;
- decidir politica pos-entrada;
- decidir parametros da politica pos-entrada.

Restricoes:

- nao administra posicao em tempo real;
- nao acompanha tick a tick;
- nao substitui Position Manager;
- nao deve ser recalculado pelo ciclo leve de gerenciamento.

### Trade Plan

Contrato materializado do plano aprovado pelo Lab.

Responsabilidades:

- preservar o racional do Research Lab;
- materializar campos operacionais de entrada;
- separar plano inicial de gestao pos-entrada;
- registrar origem e versao dos parametros;
- manter compatibilidade com snapshots antigos.

O Trade Plan nao deve:

- trocar stop inicial por trailing;
- misturar stop inicial com politica pos-entrada;
- criar inteligencia de saida propria;
- alterar o racional do Lab sem registrar regra/origem.

### Robo Demo

Executor de abertura.

Responsabilidades:

- abrir posicao demo quando gates aprovarem;
- enviar direcao;
- enviar volume;
- enviar preco operacional;
- enviar stop inicial;
- enviar alvo inicial.

O Robo Demo nao deve:

- decidir saida;
- mover SL;
- fechar posicao por contexto;
- recalcular Lab;
- escolher politica de gestao;
- administrar posicao aberta.

### Position Manager

Gerenciador da vida da posicao aberta.

Responsabilidades:

- atuar somente apos existir posicao aberta;
- carregar Trade Plan valido;
- ler estado da posicao;
- ler estado de mercado leve;
- avaliar saude da posicao;
- decidir entre manter, proteger ou solicitar encerramento;
- executar apenas acoes autorizadas por contrato, flag e provider;
- registrar toda decisao de forma auditavel.

O Position Manager nao deve:

- abrir nova posicao;
- escolher setup;
- depender de saida predefinida para aprovar ou administrar a posicao;
- alterar estrategia do Lab;
- recalcular Lab pesado;
- operar conta real;
- mover SL para piorar risco;
- fechar posicao sem contrato e flag especificos.

### Relatorio

Camada de auditoria e rastreabilidade.

Responsabilidades:

- registrar plano inicial;
- registrar estado da posicao;
- registrar estado de mercado;
- registrar decisao do Position Manager;
- registrar acao solicitada;
- registrar resultado operacional;
- registrar motivo final de saida;
- permitir reconstrucao do ciclo completo da operacao.

O Relatorio nao deve decidir trade nem executar acao operacional.

## Contratos Oficiais

### TradePlanContract

Representa o plano aprovado pelo Research Lab e materializado para execucao.

Campos oficiais:

```text
symbol
timeframe
side
entry_price
initial_stop
initial_stop_policy
initial_risk_distance
initial_rr
initial_target
runtime_exit_mode
runtime_exit_hints
lab_setup
lab_model
lab_alpha
lab_reason
plan_status
plan_version
created_at
```

Compatibilidade:

- campos legados `stop`, `target`, `risk_reward` podem continuar existindo;
- em novo contrato, `stop` deve mapear para `initial_stop`;
- `target` deve mapear para `initial_target`;
- `risk_reward` deve mapear para `initial_rr`;
- `stop_management` deve ser tratado apenas como legado/hint de compatibilidade, nunca como saida obrigatoria.

### PositionLifecyclePlan

Versao do plano usada pelo Position Manager depois da abertura.

Campos oficiais:

```text
symbol
ticket
timeframe
side
entry_price
initial_stop
initial_target
initial_rr
initial_risk_distance
current_stop
current_target
runtime_exit_mode
runtime_exit_hints
runtime_exit_state
lab_setup
lab_model
lab_alpha
plan_version
opened_at
```

### PositionStateSnapshot

Retrato leve e auditavel da posicao e do mercado.

Campos oficiais:

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
time_in_position_minutes
atr
momentum
volatility
spread
support
resistance
market_structure
last_candle_time
data_status
```

### PositionManagerDecision

Decisao auditavel do Position Manager.

Campos oficiais:

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
guardrail_status
source
created_at
```

### PositionExecutionResult

Resultado operacional da acao autorizada.

Campos oficiais:

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

## Estados Oficiais da Posicao

Estados consolidados:

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

Definicoes:

- `NO_POSITION`: nao ha posicao aberta para o simbolo.
- `NEW_POSITION`: posicao recente, ainda sem confirmacao suficiente para gestao ativa.
- `HEALTHY_POSITION`: posicao segue valida e com potencial normal.
- `PROTECTED_POSITION`: stop ja protege entrada ou lucro.
- `TREND_RUNNER`: posicao avancou a favor e segue com contexto favoravel.
- `MOMENTUM_WEAKNESS`: movimento perdeu forca contra a direcao da posicao.
- `REVERSAL_RISK`: ha risco relevante de reversao.
- `TIME_DECAY`: tempo em posicao alto sem progresso adequado.
- `STRUCTURE_BREAK_RISK`: estrutura que sustentava a operacao foi violada ou ameaçada.
- `VOLATILITY_RISK`: volatilidade passou a comprometer a qualidade da permanencia.
- `LOW_PROBABILITY_TO_TARGET`: probabilidade operacional de atingir alvo ficou baixa.
- `BAD_EXECUTION_CONTEXT`: dados insuficientes, spread ruim ou contexto invalido.
- `EXIT_REQUIRED`: condicoes arquiteturais indicam necessidade de encerramento, quando permitido.
- `POSITION_CLOSED`: posicao encerrada.

Decisao de consistencia:

- `HEALTHY_POSITION` fica como estado geral de saude.
- `TREND_RUNNER` fica como subtipo operacional mais forte, quando ha avanco relevante a favor.
- `EXIT_REQUIRED` nao executa por si so; apenas indica que uma acao de saida pode ser solicitada quando o contrato permitir.

## Acoes Oficiais

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

Definicoes:

- `HOLD_POSITION`: manter posicao sem ajuste operacional.
- `PROTECT_POSITION`: classe geral de protecao de risco.
- `MOVE_TO_BREAK_EVEN`: mover SL para entrada ou entrada ajustada.
- `ATR_TRAILING`: mover SL por trailing baseado em ATR.
- `STRUCTURE_PROTECTION`: proteger usando suporte, resistencia, swing ou estrutura.
- `VOLATILITY_PROTECTION`: proteger conforme mudanca de volatilidade.
- `MOMENTUM_PROTECTION`: proteger quando houver perda de momentum.
- `EARLY_EXIT`: decisao de saida antecipada, inicialmente read-only/simulada.
- `FULL_EXIT`: execucao de fechamento total, somente em fase futura autorizada.
- `NO_ACTION_BAD_CONTEXT`: nao agir por falta de dados, spread ruim ou contexto inseguro.

Decisao de consistencia:

- `EARLY_EXIT` e decisao.
- `FULL_EXIT` e acao operacional futura.
- Implementacoes iniciais devem permitir `EARLY_EXIT` apenas como recomendacao ou simulacao.

## Taxonomia Oficial de Encerramento

Motivos aceitos:

```text
TAKE_PROFIT
STOP_LOSS
BREAK_EVEN
TRAILING_STOP
EARLY_EXIT_MOMENTUM_LOSS
EARLY_EXIT_REVERSAL
EARLY_EXIT_TIME_DECAY
EARLY_EXIT_STRUCTURE_BREAK
EARLY_EXIT_VOLATILITY_RISK
EARLY_EXIT_LOW_PROBABILITY
MANUAL_EXIT
ASSISTED_EXIT
PROVIDER_REJECTED
UNKNOWN
```

Padronizacoes:

- `BREAK_EVEN` representa saida final em preco protegido.
- `TRAILING_STOP` representa stop movel executado e acionado.
- `EARLY_EXIT_*` representa fechamento antes de TP/SL original.
- `MANUAL_EXIT` e fechamento externo/manual.
- `ASSISTED_EXIT` e fechamento feito por fluxo assistido autorizado.
- `PROVIDER_REJECTED` registra tentativa rejeitada pelo provider.

## Estados da Politica Pos-Entrada

Estados oficiais:

```text
NOT_APPLICABLE
PENDING
ACTIVE
BLOCKED
EXECUTED
DISABLED_BY_CONFIG
```

Definicoes:

- `NOT_APPLICABLE`: nao ha politica pos-entrada.
- `PENDING`: politica existe, mas condicao de ativacao ainda nao ocorreu.
- `ACTIVE`: politica pode gerar decisao.
- `BLOCKED`: dados ou guardrails impediram decisao/execucao.
- `EXECUTED`: acao autorizada foi executada.
- `DISABLED_BY_CONFIG`: politica gerou candidato, mas execucao esta desligada.

## Guardrails Oficiais

Guardrails obrigatorios:

- Research Lab continua origem da estrategia.
- Trade Plan preserva o racional do Lab.
- Robo Demo nao ganha inteligencia de saida.
- Position Manager nao recalcula Lab.
- Position Manager nao abre novas posicoes.
- Position Manager nao opera conta real.
- Qualquer fechamento antecipado exige contrato e flag especificos.
- Movimento de SL nunca pode piorar risco.
- Movimento de SL nunca pode cruzar o preco atual.
- TP nao deve ser alterado em missoes de protecao.
- Relatorio nao decide operacao.
- Toda decisao deve ser auditavel.
- Toda execucao deve ter rollback documental.
- Snapshots antigos devem continuar legiveis.
- `.traderia` deve ser preservada.

## Dependencias Permitidas

Fluxo permitido:

```text
Research Lab -> Trade Plan
Trade Plan -> Robo Demo
Trade Plan -> Position Manager
Position Manager -> DemoExecutionService
DemoExecutionService -> Provider MT5 Demo
Todos -> Relatorio
```

Fluxos proibidos:

```text
Position Manager -> Research Lab pesado
Robo Demo -> decisao de saida
Relatorio -> execucao
Provider MT5 -> escolha de estrategia
```

## Revisao de Consistencia

Inconsistencias encontradas e consolidadas:

1. `stop_management` misturava politica de saida e stop inicial.
   - Resolucao: separar `initial_stop` de `runtime_exit_decision`; `stop_management` permanece apenas como hint legado.

2. `HEALTHY_POSITION` e `TREND_RUNNER` tinham sobreposicao.
   - Resolucao: `HEALTHY_POSITION` e saude geral; `TREND_RUNNER` e estado favoravel forte.

3. `EARLY_EXIT` e `FULL_EXIT` podiam ser confundidos.
   - Resolucao: `EARLY_EXIT` e decisao; `FULL_EXIT` e execucao futura.

4. Motivos de saida nao diferenciavam assistido/manual.
   - Resolucao: adicionar `ASSISTED_EXIT` e manter `MANUAL_EXIT`.

5. Politica pos-entrada nao tinha ciclo de vida.
   - Resolucao: criar estados `PENDING`, `ACTIVE`, `BLOCKED`, `EXECUTED`, `DISABLED_BY_CONFIG`.

6. Trade Plan nao tinha contrato documental suficiente para compatibilidade legada.
   - Resolucao: mapear campos legados para campos novos.

## Plano de Implementacao Futuro

### TIA-PM-001 - Contratos read-only

Criar contratos documentados em codigo sem mudar comportamento.

### TIA-PM-002 - Separar stop inicial e politica pos-entrada

Adicionar campos novos mantendo compatibilidade.

### TIA-PM-003 - Exibir contrato consolidado

Forex e Relatorio devem mostrar plano inicial separado de gestao pos-entrada.

### TIA-PM-004 - Ativacao de politica pos-entrada

Implementar ciclo `PENDING -> ACTIVE -> EXECUTED/BLOCKED`.

### TIA-PM-005 - Centralizar gestao de SL no Position Manager

Garantir uma unica origem para movimento de SL.

### TIA-PM-006 - Early exit read-only

Adicionar decisao de encerramento antecipado sem execucao.

### TIA-PM-007 - Early exit paper/simulado

Comparar saida original contra saida antecipada proposta.

### TIA-PM-008 - Early exit assistido demo

Permitir fechamento assistido com confirmacao manual e gates.

### TIA-PM-009 - Early exit automatico demo

Somente apos validacao estatistica, auditoria e rollback.

## Criterio de Prontidao

Com este contrato, o projeto esta pronto para futuras implementacoes sem nova definicao arquitetural se:

- novas missoes citarem este documento como fonte oficial;
- alteracoes respeitarem os contratos acima;
- testes cobrirem cada contrato novo;
- execucao permanecer bloqueada ate fase autorizada;
- compatibilidade legada for preservada.

## Conclusao

A arquitetura do Position Manager esta consolidada.

O desenho oficial e:

```text
Lab decide.
Trade Plan materializa.
Robo Demo abre.
Position Manager administra posicao aberta.
Relatorio audita o ciclo completo.
```

O proximo trabalho nao deve rediscutir responsabilidades. Deve implementar por camadas os contratos aqui definidos.
