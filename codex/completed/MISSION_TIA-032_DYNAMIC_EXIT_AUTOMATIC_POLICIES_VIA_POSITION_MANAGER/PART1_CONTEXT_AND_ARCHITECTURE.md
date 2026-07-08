# MISSION_TIA-032 - PART 1 - CONTEXT_AND_ARCHITECTURE

## Objetivo desta parte

Consolidar a arquitetura do Position Manager como ponto central para gestao automatica controlada das politicas de saida dinamica em conta demo.

## Escopo principal

Criar ou consolidar um Position Manager central e auditavel para gerenciar posicoes abertas e executar politicas de saida dinamica de forma controlada.

A missao deve permitir que as politicas dinamicas futuras retornem acoes operacionais padronizadas:

```text
HOLD
MOVE_STOP
MOVE_TARGET
BREAK_EVEN
ATR_TRAILING_STOP
PARTIAL_EXIT
FULL_EXIT
NO_ACTION
BLOCKED
```

Nesta primeira implementacao, priorizar execucao automatica segura para acoes que reduzem risco, especialmente:

```text
MOVE_STOP
BREAK_EVEN
ATR_TRAILING_STOP
MARKET_AWARE_STOP_PROTECTION
VOLATILITY_STOP_PROTECTION
MOMENTUM_WEAKNESS_STOP_TIGHTENING
STRUCTURE_BASED_STOP_PROTECTION
```

Acoes mais destrutivas devem continuar bloqueadas por padrao, salvo se ja houver contrato seguro:

```text
FULL_EXIT
PARTIAL_EXIT
MOVE_TARGET
INVERT_POSITION
ADD_POSITION
```

## Separacao obrigatoria de responsabilidades

```text
MT5DemoRobotService abre posicao.
Position Manager acompanha posicao aberta.
DemoExecutionService envia/modifica ordem.
Provider MT5 Demo conversa com MT5.
Research Lab nao e recalculado durante gestao de posicao aberta.
Runtime Guard nao decide e nao executa gestao.
```

## Arquivos esperados

Criar ou atualizar conforme a arquitetura real do repositorio:

```text
core/position_management/
  __init__.py
  position_manager.py
  operational_decision.py
  dynamic_exit_policy_executor.py
  position_audit_log.py

application/
  position_management_service.py

docs/architecture/
  POSITION_MANAGER.md
  MARKET_AWARE_EXIT_PLAN.md
  DYNAMIC_EXIT_AUTOMATIC_POLICIES.md
```

Se a estrutura real do repositorio usar outros caminhos, adaptar mantendo a separacao de responsabilidade.

## Contratos sugeridos

### OpenPosition

```python
@dataclass
class OpenPosition:
    symbol: str
    ticket: int
    side: Literal["BUY", "SELL"]
    entry_price: float
    current_stop: float | None
    current_take_profit: float | None
    volume: float
```

### TradePlan

Usar o contrato ja existente no projeto. Se necessario, criar adaptador sem quebrar compatibilidade.

Campos minimos esperados:

```text
symbol
side
entry
initial_stop
target
timeframe
alpha
setup
exit_policy
risk_parameters
```

### MarketSnapshot

```python
@dataclass
class MarketSnapshot:
    symbol: str
    current_price: float
    last_candle: Any | None
    atr: float | None
    trend: str | None
    momentum: str | None
    volatility_regime: str | None
    structure_state: str | None
```

### OperationalDecision

```python
@dataclass
class OperationalDecision:
    action: str
    symbol: str
    ticket: int | None
    side: str | None
    current_stop: float | None
    proposed_stop: float | None
    confidence: float
    reason: str
    required_data: list[str]
    missing_data: list[str]
    execution_allowed: bool
    execution_mode: str
    execution_status: str
    audit_tags: list[str]
```

## Comportamento da configuracao

Preservar a flag existente:

```text
dynamic_exit_demo_sl_assisted_execution_enabled
```

Default obrigatorio:

```text
False
```

### Quando False

O Position Manager pode:

```text
- detectar posicao aberta;
- carregar Trade Plan;
- ler preco/candle/ATR;
- calcular a melhor acao;
- gerar recomendacao;
- registrar auditoria;
- exibir o que faria.
```

Mas nao pode:

```text
- chamar modify_position_sl;
- chamar close_position;
- alterar TP;
- alterar ordem;
- mover stop.
```

Resultado esperado:

```text
execution_mode: READ_ONLY
execution_status: BLOCKED_BY_CONFIG
```

### Quando True

O Position Manager pode executar automaticamente apenas acoes seguras e permitidas:

```text
- mover SL para ponto mais protetivo;
- aplicar break-even;
- aplicar ATR trailing;
- aplicar protecao de stop por leitura de mercado, desde que nao aumente risco.
```

Resultado esperado:

```text
execution_mode: AUTOMATIC_DEMO
execution_status: EXECUTED ou BLOCKED
```

## Evolucao futura preparada

Sem quebrar compatibilidade, preparar o codigo para evoluir depois para:

```text
dynamic_exit_execution_mode:
  READ_ONLY
  ASSISTED
  AUTOMATIC_DEMO
  AUTOMATIC_REAL_BLOCKED
```

Nesta missao, nao ativar conta real.
