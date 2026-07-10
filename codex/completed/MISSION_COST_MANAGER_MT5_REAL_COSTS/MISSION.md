# MISSION_COST_MANAGER_MT5_REAL_COSTS

## Objetivo

Implementar no TraderIA Novo um `CostManager` centralizado para custos reais do MT5.

O objetivo é criar um módulo único responsável por ler, calcular e expor os custos reais de operação por símbolo, sem valores fixos no código.

---

## Contexto operacional

No Forex, separar claramente:

- **Rollover** = evento de virada do dia operacional da corretora.
- **Swap** = custo ou crédito financeiro aplicado ao manter posição aberta durante o rollover.
- **Spread** = diferença entre bid e ask no momento da operação.
- **Comissão** = custo cobrado pela corretora pela execução, quando aplicável.
- **Fee** = taxas adicionais registradas pelo MT5/corretora, quando existirem.

O TraderIA Novo deve conseguir estimar custos antes da entrada e registrar custos reais após a execução.

---

## Requisitos de implementação

### 1. Criar módulo CostManager

Criar um módulo centralizado responsável por custos operacionais.

Sugestão de nome:

```text
CostManager
```

O restante do sistema não deve consultar custos diretamente no MT5, mas sim por meio desse módulo.

---

### 2. Ler dados do MT5 por símbolo

O `CostManager` deve ler do MT5, quando disponível:

- `bid`
- `ask`
- `spread`
- `swap_long`
- `swap_short`
- `trade_tick_value`
- `trade_tick_size`
- `contract_size`
- `digits`
- `point`

Esses dados devem vir do `symbol_info`/tick do MT5 ou da camada já existente de acesso ao MT5 no projeto.

---

### 3. Criar snapshot padronizado por símbolo

Criar uma estrutura padronizada, por exemplo:

```python
SymbolCostSnapshot
```

Campos mínimos esperados:

```text
symbol
bid
ask
spread_points
spread_price
spread_money_estimate
swap_long
swap_short
tick_value
tick_size
contract_size
digits
point
source
captured_at
warnings
```

A estrutura deve tolerar campos ausentes no MT5 sem quebrar o sistema.

---

### 4. Função para retornar custos por símbolo

Criar função semelhante a:

```python
get_symbol_cost_snapshot(symbol: str) -> SymbolCostSnapshot
```

Ela deve retornar:

- spread em pontos;
- spread em preço;
- spread estimado em dinheiro;
- swap compra;
- swap venda;
- valor do tick;
- tamanho do tick;
- demais metadados úteis.

---

### 5. Estimar custo antes da entrada

Criar função semelhante a:

```python
estimate_trade_cost(symbol: str, volume: float, direction: str) -> TradeCostEstimate
```

Ela deve estimar, quando possível:

- custo de spread;
- swap esperado para compra ou venda;
- comissão, se disponível;
- fee, se disponível;
- custo total estimado;
- campos desconhecidos como `unknown` ou `None`, sem usar número fixo.

Importante:

- Não usar corretagem hardcoded.
- Se a comissão não estiver disponível antes da execução, registrar como desconhecida/estimada.
- O custo real deve ser preenchido depois pelo histórico do MT5.

---

### 6. Ler custo real após execução

Criar função semelhante a:

```python
get_real_trade_cost(position_id: int | None = None, ticket: int | None = None) -> RealTradeCost
```

Deve buscar no histórico do MT5 usando `history_deals_get` ou camada equivalente do projeto.

Campos esperados:

- `commission`
- `swap`
- `fee`
- `profit`
- `net_profit`
- `deals_count`
- `tickets`

Critério importante:

```text
net_profit = profit + commission + swap + fee
```

Respeitar o formato real retornado pelo MT5/corretora.

---

### 7. Integração com fluxo do TraderIA Novo

Integrar sem alterar a lógica decisória do Lab.

O Lab continua decidindo:

- ativo;
- direção;
- timeframe;
- entrada;
- stop inicial;
- alvo;
- RR.

O `CostManager` apenas fornece custos para:

- exibição operacional;
- auditoria;
- histórico;
- decisão futura do robô/Position Manager sobre manter ou não uma posição próxima ao rollover.

Não alterar a lógica de entrada nesta missão.

---

### 8. Exibição operacional

O TraderIA deve conseguir exibir para cada símbolo:

- spread atual;
- swap long;
- swap short;
- custo estimado da operação;
- custo real após execução, quando disponível.

A exibição pode ser simples inicialmente, desde que funcional.

---

### 9. Robustez

O sistema deve continuar funcionando mesmo se:

- o MT5 retornar campo vazio;
- o símbolo não estiver selecionado no Market Watch;
- o histórico ainda não tiver deals suficientes;
- a corretora não fornecer comissão antes da execução;
- o swap vier zerado ou indisponível.

Nesses casos, registrar aviso em `warnings`, sem derrubar o app.

---

### 10. Testes

Criar testes unitários com mocks do MT5.

Testar pelo menos:

- snapshot com todos os campos disponíveis;
- snapshot com campos ausentes;
- cálculo de spread em preço;
- estimativa de spread em dinheiro;
- direção buy usando `swap_long`;
- direção sell usando `swap_short`;
- custo real agregado via histórico;
- comportamento sem comissão disponível;
- comportamento sem histórico.

---

## Documentação

Atualizar ou criar documentação explicando:

- diferença entre spread, comissão, swap e fee;
- diferença entre rollover e swap;
- que rollover é o evento de virada do dia;
- que swap é o custo/crédito financeiro decorrente do rollover;
- que os valores devem vir do MT5/corretora;
- que não deve existir custo hardcoded no código.

Sugestão de arquivo:

```text
docs/MT5_COST_MANAGER.md
```

---

## Critérios de aceite

A missão será considerada concluída quando:

1. Existir um `CostManager` centralizado.
2. O TraderIA conseguir ler custos reais do MT5 por símbolo.
3. O TraderIA conseguir estimar custo antes da entrada.
4. O TraderIA conseguir registrar custo real após execução.
5. Spread, swap, comissão e fee estiverem separados conceitualmente.
6. Nenhum custo de corretagem estiver hardcoded.
7. O sistema continuar funcionando se campos do MT5 vierem ausentes.
8. Existirem testes unitários com mocks.
9. A documentação estiver atualizada.
10. A lógica de entrada do Lab permanecer inalterada.

---

## Restrições

- Não alterar a estratégia de entrada do Lab.
- Não alterar o cálculo de RR nesta missão.
- Não implementar ainda decisão automática de fechar posição antes do rollover.
- Não criar regra fixa de corretagem.
- Não acoplar o dashboard diretamente ao MT5 para custos.
- Não misturar `RolloverManager` com `SwapManager`/`CostManager`.

---

## Resultado esperado

Ao final, o TraderIA Novo deve possuir uma camada confiável para custos operacionais reais, permitindo que futuras missões usem esses dados para decidir se vale a pena manter, encerrar ou evitar operações próximas ao rollover.
