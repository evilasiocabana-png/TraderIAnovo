# Safe Mode MT5 e Stop Movel - Auditoria

## Conclusao

Pode usar stop movel em Safe Mode? **DEPENDE**.

O Safe Mode nao significa "sem leitura de mercado". No TraderIA Novo ele mantem leitura leve do MT5 com candles, preco, medias, RSI, momentum, volatilidade, ATR e diagnostico basico. O que ele evita e a Pesquisa Quantitativa pesada durante o ciclo online.

O stop movel pode continuar sendo acompanhado em Safe Mode quando houver:

- posicao aberta valida no MT5;
- ticket, lado, entrada, stop atual e alvo conhecidos;
- plano operacional valido salvo pelo Lab;
- politica de saida definida;
- leitura atualizada de preco/tick/candle;
- ATR disponivel quando a politica exigir ATR;
- ambiente seguro de execucao, com conta Demo e gates do Provider Demo aprovados.

Se qualquer requisito faltar, o sistema deve preservar o estado atual, nao mover stop, exibir alerta e registrar log.

## O Que O Safe Mode Mantem Ativo

`application/mt5_market_data_service.py` carrega o painel Forex em modo heuristico. A leitura continua usando o provider MT5 read-only para buscar candles por par e timeframe. O painel continua preenchendo `last_price`, `last_candle_time`, `trend`, `momentum`, `volatility`, `rsi`, `atr`, `atr_average`, bandas, volume, suporte, resistencia, spread e diagnostico.

Os testes confirmam o comportamento esperado:

- Safe Mode nao chama o motor de score quantitativo pesado mesmo com pedido de recalculo.
- Safe Mode nao roda otimizador de timeframe.
- Safe Mode preserva leitura heuristica e incrementa `refresh_id`.
- Quando o provider falha, o painel retorna offline com erro explicito.

Portanto, Safe Mode e compativel com monitoramento leve do mercado.

## O Que O Safe Mode Nao Deve Fazer

Safe Mode nao deve:

- recalcular o Lab pesado em ciclo online;
- escolher nova estrategia sozinho;
- trocar alpha/setup/timeframe durante posicao aberta;
- abrir ordem;
- fechar posicao;
- mover SL/TP sem gates especificos;
- apagar o ultimo plano valido do Lab;
- substituir leitura operacional por diagnostico pesado.

## Mapa Dos Componentes

| Componente | Papel Atual | Observacao |
|---|---|---|
| `application/mt5_market_data_service.py` | Leitura Forex leve e heuristica | Mantem preco, candles e indicadores no Safe Mode. |
| `application/forex_mt5_service.py` | Exibe estado read-only de mercado e posicoes | Le posicoes abertas e monta leitura dinamica basica por simbolo. |
| `application/dynamic_exit_market_state_service.py` | Classifica estado da posicao | Depende de posicao, preco atual, entrada, stop e spread. |
| `application/dynamic_exit_engine.py` | Motor unificado de recomendacao/autorizacao | Mantem `allowed_to_execute_demo=False` no retorno normal. |
| `infrastructure/execution/mt5_demo_execution_provider.py` | Provider demo MT5 | Pode aplicar stop management em Demo para `BREAK_EVEN` e `ATR_TRAILING_STOP`. |
| `core/position_manager.py` | Gerenciador legado em memoria | Nao e o Position Manager central do MT5 operacional. |

## Dependencias Do Stop Movel

O stop movel automatico implementado no Provider Demo usa:

- posicoes abertas vindas de `positions_get`;
- simbolo e lado da posicao;
- preco de entrada da posicao ou do sinal;
- stop atual da posicao;
- tick atual (`bid` para BUY, `ask` para SELL);
- alvo atual da posicao ou do sinal;
- politica do plano (`BREAK_EVEN` ou `ATR_TRAILING_STOP`);
- parametros de stop management;
- ATR em `market_indicators["atr"]` quando a politica e `ATR_TRAILING_STOP`.

Ele nao precisa recalcular o Lab durante a posicao aberta. Ele precisa de um plano/sinal salvo e dados atuais de mercado.

## Politicas Realmente Executaveis Hoje

O caminho automatico de stop management do Provider Demo aceita somente:

- `BREAK_EVEN`;
- `ATR_TRAILING_STOP`.

As politicas dinamicas adicionais existem como leitura, simulacao, pre-autorizacao ou modo assistido, mas nao devem ser tratadas como execucao automatica ampla. O modo assistido de SL permanece controlado por configuracao e confirmacao manual.

## Matriz De Requisitos

| Recurso | Necessario? | Disponivel em Safe Mode? | Fonte | Risco |
|---|---:|---:|---|---|
| preco atual | Sim | Sim, se MT5 online | tick/preco do provider MT5 | Medio se tick falhar ou ficar stale |
| candle atual | Sim para contexto | Sim | `get_candles`/Forex heuristic | Medio se candles insuficientes |
| ATR | Sim para ATR trailing | Sim quando ha candles suficientes | `MT5ForexSignalRow.atr`/`market_indicators` | Alto se nao for transportado ao sinal operacional |
| direcao da posicao | Sim | Sim, se posicao aberta legivel | `positions_get` | Alto se posicao nao for encontrada |
| entrada | Sim | Sim, se MT5 expor `price_open` ou sinal tiver `entry` | posicao/sinal | Alto se ausente |
| stop atual | Sim | Sim, se posicao tiver `sl` | posicao MT5 | Alto se ausente; nao mover |
| alvo | Recomendado | Sim, se posicao tiver `tp` ou sinal tiver `target` | posicao/sinal | Medio; TP deve ser preservado |
| maior preco desde entrada | Necessario para certas saidas | Parcial/nao canonico | candles/snapshot, ainda sem campo central | Alto para trailing por estrutura |
| menor preco desde entrada | Necessario para certas saidas | Parcial/nao canonico | candles/snapshot, ainda sem campo central | Alto para trailing por estrutura |
| politica de saida do Lab | Sim | Sim, se plano/sinal salvo existir | Lab/TradePlan/Forex signal | Alto se plano estiver ausente ou stale |

## Cenarios

### Cenario A - Safe Mode ligado, sem posicao aberta

Seguro manter ativo:

- leitura de preco/candles;
- painel Forex;
- diagnostico leve;
- recomendacao read-only sem acao.

Deve bloquear:

- stop movel;
- break-even;
- trailing;
- SL assistido;
- qualquer envio MT5.

Alerta recomendado:

```text
Safe Mode ativo. Mercado monitorado, mas sem posicao aberta para gerenciar stop.
```

### Cenario B - Safe Mode ligado, posicao aberta com plano valido salvo

Seguro manter ativo:

- acompanhamento de posicao;
- calculo de R;
- recomendacao dinamica read-only;
- stop management demo autorizado somente para politicas suportadas e com gates aprovados.

Deve bloquear:

- recalculo pesado do Lab;
- troca automatica de setup;
- politica que exigir dado ausente;
- execucao fora de Demo.

Alerta recomendado:

```text
Safe Mode ativo. Posicao monitorada com plano salvo; stop movel permitido somente por gates seguros.
```

### Cenario C - Safe Mode ligado, posicao aberta sem plano valido

Seguro manter ativo:

- leitura da posicao;
- leitura de preco;
- preservacao do stop atual;
- auditoria e alerta.

Deve bloquear:

- qualquer novo stop candidato;
- break-even automatico;
- trailing automatico;
- SL assistido baseado em plano incompleto.

Alerta recomendado:

```text
Posicao aberta sem plano operacional valido. Stop atual preservado; gestao automatica bloqueada.
```

### Cenario D - Research Lab desligado, Market Data online

Seguro manter ativo:

- leitura leve Forex;
- acompanhamento de posicao com ultimo plano valido;
- relatorio/auditoria.

Deve bloquear:

- novo plano sem Lab;
- reotimizacao de alpha/setup/timeframe;
- stop movel se nao houver plano previamente salvo.

Alerta recomendado:

```text
Research Lab desligado. Mercado online; usando somente ultimo plano valido para acompanhamento.
```

## Riscos Identificados

1. A separacao entre Lab e Position Manager ainda nao esta concentrada em uma unica classe operacional.
2. `core.PositionManager` e simples e em memoria; nao representa o gerenciador real de posicao MT5.
3. O Provider Demo suporta execucao automatica apenas para `BREAK_EVEN` e `ATR_TRAILING_STOP`.
4. Maior/menor preco desde entrada ainda nao aparecem como contrato canonico persistido.
5. Se `market_indicators["atr"]` nao chegar ao Provider Demo, `ATR_TRAILING_STOP` fica corretamente sem acao.
6. Safe Mode pode monitorar mercado, mas nao deve ser confundido com autorizacao de execucao.

## Recomendacao

Manter Safe Mode ligado para preservar leveza e estabilidade. Para stop movel, usar a regra:

```text
Lab gera o plano.
Safe Mode le o mercado.
Position Manager acompanha a posicao.
Provider Demo so move SL quando todos os gates estiverem completos.
```

A melhoria arquitetural futura deve criar um Position Manager MT5 central, persistente e auditavel, responsavel por:

- vincular ticket MT5 ao plano do Lab;
- preservar maior/menor preco desde entrada;
- consolidar estado de stop movel;
- alimentar Dynamic Exit;
- registrar logs por ciclo;
- bloquear acao quando dados minimos estiverem ausentes.

