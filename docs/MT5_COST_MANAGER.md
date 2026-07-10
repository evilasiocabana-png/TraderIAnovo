# MT5 Cost Manager

## Objetivo

O `CostManager` centraliza os custos operacionais reais e estimados do MT5.

Ele separa conceitos que nao devem ser misturados:

- **Spread**: diferenca entre `ask` e `bid` no momento da leitura.
- **Comissao/corretagem**: custo registrado pelo MT5/corretora na execucao.
- **Fee**: taxa adicional quando a corretora ou o MT5 informarem esse campo.
- **Swap**: custo ou credito financeiro por manter posicao aberta apos o rollover.
- **Rollover**: evento de virada do dia operacional do servidor/corretora.

Rollover nao e custo. Swap e o custo ou credito que pode decorrer de manter a
posicao durante o rollover.

## Fonte dos dados

Os dados devem vir do MT5/corretora:

- `symbol_info`
- `symbol_info_tick`
- `positions_get`
- `history_deals_get`
- payloads ja normalizados pela camada de auditoria MT5

Nao deve existir corretagem, swap ou fee hardcoded no codigo.

## Snapshot por simbolo

`SymbolCostSnapshot` transporta:

- simbolo;
- bid;
- ask;
- spread em pontos;
- spread em preco;
- estimativa monetaria do spread;
- swap long;
- swap short;
- tick value;
- tick size;
- contract size;
- digits;
- point;
- fonte;
- horario de captura;
- avisos de campos ausentes.

Campos ausentes nao derrubam o sistema. Eles entram em `warnings`.

## Estimativa pre-entrada

`estimate_trade_cost(symbol, volume, direction)` estima quando possivel:

- custo de spread;
- swap esperado conforme BUY/SELL;
- custo total conhecido.

Comissao e fee antes da execucao podem ser desconhecidos. Nesses casos, ficam
como `None` e aparecem em `unknown`.

## Custo real apos execucao

`RealTradeCost` agrega:

- `commission`;
- `swap`;
- `fee`;
- `profit`;
- `net_profit`;
- quantidade de deals;
- tickets envolvidos.

A regra oficial e:

```text
net_profit = profit + commission + swap + fee
```

No dashboard, **Custo aberto** representa:

```text
commission + swap + fee
```

Ja **Risco em aberto** continua sendo o risco projetado pelo plano/stop.

## Guardrails

- O `CostManager` nao decide entrada.
- O `CostManager` nao altera RR.
- O `CostManager` nao move stop.
- O `CostManager` nao substitui o Research Lab.
- O dashboard nao deve consultar custo diretamente no MT5.
- Futuras decisoes sobre rollover devem consumir custo por esta camada.
