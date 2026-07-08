# MISSION_TIA-032 - PART 2 - POLICIES_AND_PROVIDER_PORTS

## Objetivo desta parte

Implementar a execucao automatica controlada das politicas de saida dinamica seguras via Position Manager e consolidar as portas de Provider/DemoExecutionService.

## Regra de seguranca central

Nenhuma politica automatica pode aumentar risco.

O sistema nunca pode:

```text
- afastar stop contra o trader;
- remover stop;
- alterar entrada;
- abrir nova posicao;
- aumentar posicao;
- inverter posicao;
- trocar alpha/setup/timeframe com posicao aberta;
- recalcular Research Lab pesado para gerenciar posicao aberta;
- usar diagnostico MT5 como gatilho operacional;
- executar em conta real;
- executar sem Trade Plan valido;
- executar sem posicao aberta;
- executar sem preco atual;
- executar sem dados minimos da politica;
- executar com ATR ausente quando a politica exigir ATR;
- executar com candle/estrutura ausente quando a politica exigir estrutura;
- executar se a classificacao da acao for desconhecida.
```

Se houver duvida:

```text
BLOCKED
```

## Politicas de saida a automatizar

### 1. BREAK_EVEN

Pode executar se:

```text
- posicao aberta;
- Trade Plan valido;
- preco atual valido;
- entrada valida;
- stop atual conhecido;
- gatilho de R atingido;
- novo stop for mais protetivo.
```

BUY:

```text
novo_stop >= entrada
novo_stop > stop_atual
```

SELL:

```text
novo_stop <= entrada
novo_stop < stop_atual
```

### 2. ATR_TRAILING_STOP

Pode executar se:

```text
- posicao aberta;
- Trade Plan valido;
- preco atual valido;
- ATR valido;
- multiplicador ATR definido;
- novo stop for mais protetivo.
```

BUY:

```text
candidate_stop = current_price - ATR * multiplier
candidate_stop > current_stop
```

SELL:

```text
candidate_stop = current_price + ATR * multiplier
candidate_stop < current_stop
```

### 3. MARKET_AWARE_STOP_PROTECTION

Nova politica automatizavel, mas conservadora.

Objetivo:

```text
Apertar stop quando a leitura de mercado indicar perda de forca, proximidade de resistencia/suporte contra a posicao, rejeicao ou risco aumentado, sem fechar posicao automaticamente.
```

Pode executar apenas:

```text
MOVE_STOP
```

Nao pode executar `FULL_EXIT` nesta missao.

### 4. VOLATILITY_STOP_PROTECTION

Objetivo:

```text
Ajustar stop conforme mudanca de volatilidade.
```

Regras:

```text
- se volatilidade contraiu e operacao esta positiva, pode apertar stop;
- se volatilidade expandiu, nao afastar stop;
- nunca aumentar risco.
```

### 5. MOMENTUM_WEAKNESS_STOP_TIGHTENING

Objetivo:

```text
Quando momentum enfraquece contra a posicao, proteger lucro ou reduzir risco movendo SL para ponto mais protetivo.
```

Somente:

```text
MOVE_STOP
```

### 6. STRUCTURE_BASED_STOP_PROTECTION

Objetivo:

```text
Usar estrutura de mercado para proteger stop atras de suporte/resistencia recente.
```

Regras:

```text
BUY: stop pode subir para abaixo de fundo/suporte relevante, se for acima do stop atual.
SELL: stop pode descer para acima de topo/resistencia relevante, se for abaixo do stop atual.
```

Se nao houver estrutura confiavel:

```text
BLOCKED_MISSING_STRUCTURE
```

## Provider MT5 Demo

Adicionar ou consolidar portas:

```python
get_open_position(symbol)
modify_position_sl(symbol, ticket, new_stop)
get_current_price(symbol)
get_recent_candles(symbol, timeframe, limit)
get_atr(symbol, timeframe, period)
```

Se alguma porta ja existir com outro nome, criar adaptador mantendo compatibilidade.

## DemoExecutionService

O DemoExecutionService deve ser o unico servico autorizado a chamar provider para modificacao de ordem/SL, se essa for a arquitetura atual.

Fluxo preferido:

```text
PositionManager
  -> gera OperationalDecision
  -> PositionManagementService
  -> DemoExecutionService.modify_position_sl(...)
  -> Provider MT5 Demo.modify_position_sl(...)
```

## Auditoria obrigatoria

Registrar evento para todos os cenarios:

```text
POSITION_ABSENT
TRADE_PLAN_ABSENT
MARKET_DATA_ABSENT
ATR_ABSENT
STRUCTURE_ABSENT
STOP_HELD
STOP_MOVE_CANDIDATE
STOP_MOVE_BLOCKED_BY_CONFIG
STOP_MOVE_BLOCKED_NOT_PROTECTIVE
STOP_MOVED
STOP_MOVE_FAILED
POLICY_READ_ONLY
POLICY_AUTOMATIC_EXECUTED
POLICY_BLOCKED_UNSUPPORTED_ACTION
```

Cada log deve conter:

```text
timestamp
symbol
ticket
side
policy
action
current_stop
proposed_stop
current_price
reason
execution_mode
execution_status
missing_data
```

## Interface / Dashboard

Se houver painel do Robo Demo ou Relatorio, mostrar:

```text
- posicao aberta detectada;
- politica de saida ativa;
- decisao atual do Position Manager;
- SL atual;
- SL proposto;
- motivo;
- modo de execucao: READ_ONLY ou AUTOMATIC_DEMO;
- ultimo evento de auditoria.
```

Nao criar botoes perigosos de conta real.

## Safe Mode

Safe Mode pode acompanhar stop somente se houver:

```text
- posicao aberta;
- Trade Plan valido;
- preco atual;
- dados minimos da politica;
- Provider Demo seguro;
- configuracao de execucao ligada.
```

Se faltar qualquer requisito:

```text
preservar estado
bloquear movimento
auditar motivo
```
