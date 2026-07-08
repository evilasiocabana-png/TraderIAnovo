# Market Aware Exit Plan

## Objetivo

Transformar a saida do TraderIA Novo em acompanhamento de mercado apos a entrada, sem recalcular o Lab pesado e sem deixar o MT5 escolher estrategia sozinho.

## Modelo Operacional

```text
Lab estrategico
  -> define entrada, stop inicial, alvo e politica de saida

Runtime leve / Safe Mode
  -> le preco, candle, ATR e estado atual

Position Manager
  -> acompanha posicao aberta
  -> calcula break-even ou ATR trailing
  -> preserva stop se o contexto nao for seguro

Provider Demo
  -> modifica somente SL, somente em Demo, somente com gate ativo
```

## Separacao Entre Entrada E Gestao

### Entrada

Responsavel:

```text
MT5DemoRobotService
```

Funcoes:

- validar candle novo;
- validar regime;
- validar Trade Plan;
- enviar ordem inicial via `DemoExecutionService`;
- incluir stop inicial e alvo.

### Gestao

Responsavel:

```text
PositionManagerService
```

Funcoes:

- detectar posicao aberta;
- carregar plano salvo;
- ler preco atual;
- ler ATR do plano/sinal salvo;
- calcular SL candidato;
- registrar decisao;
- solicitar modificacao de SL quando autorizado.

## Safe Mode

Safe Mode pode acompanhar saida quando houver:

- posicao aberta;
- Trade Plan valido salvo;
- preco atual;
- stop atual;
- politica de saida;
- ATR quando necessario.

Safe Mode nao pode:

- recalcular Research Lab pesado;
- trocar alpha/setup/timeframe;
- abrir nova ordem;
- mover SL sem gate;
- alterar TP;
- mascarar erro de plano ausente.

## Politica De Execucao

A execucao real de modificacao de SL em Demo respeita:

```text
dynamic_exit_demo_sl_assisted_execution_enabled
```

Default:

```text
False
```

Com default desligado, o Position Manager calcula e registra o stop candidato, mas nao envia alteracao ao MT5.

## Criterios De Movimento De SL

BUY:

```text
novo_stop > stop_atual
novo_stop < preco_atual
```

SELL:

```text
novo_stop < stop_atual
novo_stop > preco_atual
```

Se qualquer criterio falhar, manter o stop atual.

## Politicas Ativas

### Break-even

Usa distancia entre entrada e stop atual para calcular R. So recomenda mover quando o preco andou a favor pelo gatilho configurado.

### ATR trailing

Usa:

```text
preco_atual +/- ATR * fator
```

Se ATR estiver ausente, nao move.

### Market aware stop protection

Pode proteger stop quando a operacao ja esta positiva e existe estrutura segura, momentum contra ou ATR disponivel. A unica acao permitida e `MOVE_STOP`.

### Volatility stop protection

Pode apertar stop quando ha ATR e volatilidade no plano/sinal salvo. Expansao de volatilidade nunca autoriza afastar stop.

### Momentum weakness stop tightening

Pode mover stop para entrada quando o momentum enfraquece contra a posicao e a operacao esta positiva.

### Structure based stop protection

BUY usa suporte/fundo recente; SELL usa resistencia/topo recente. Se estrutura estiver ausente, bloqueia com `STRUCTURE_ABSENT`.

## Roadmap Seguro

1. Manter `BREAK_EVEN` e `ATR_TRAILING_STOP` como politicas operacionais iniciais.
2. Manter `FULL_EXIT`, `PARTIAL_EXIT`, `MOVE_TARGET`, inversao e aumento de posicao bloqueados.
3. Usar Dynamic Exit adicional como leitura/auditoria para politicas ainda nao seguras.
4. Persistir maximo/minimo desde entrada em camada futura.
5. Autorizar novas politicas destrutivas uma por vez, com testes e rollback.

