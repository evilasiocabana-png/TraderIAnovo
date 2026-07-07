# MISSION_TIA-026 — Execucao Simulada da Saida Dinamica e Gestao de Stop

## Objetivo

Evoluir a saida dinamica do estado `read-only/auditavel` para **execucao simulada/paper**, permitindo que o sistema consuma `DynamicExitRecommendation`, calcule um novo stop seguro e registre o resultado em auditoria, sem modificar posicao, SL ou TP no MT5.

Esta missao NAO autoriza ordem real, NAO modifica SL/TP no MT5 e NAO fecha posicao.

## Contexto atual

Hoje o projeto possui:

- `DynamicExitMarketStateClassifier` para classificar cenario da posicao.
- `DynamicExitRecommendationEngine` para recomendar acoes como:
  - `PROTECT_TO_BREAK_EVEN`
  - `TRAIL_BY_ATR`
  - `TRAIL_BY_STRUCTURE`
  - `TIGHTEN_BY_MOMENTUM_LOSS`
  - `TIME_DECAY_EXIT_WATCH`
- Contrato `DynamicExitRecommendation` em modo sem execucao operacional.
- Politica base de stop vinda do `MT5ResearchTradePlan`.

A partir desta missao, a recomendacao deve virar uma **decisao simulada**, registrada e exibida no dashboard.

## Regra principal

O motor de simulacao nao pode pesquisar, otimizar ou recalcular Lab.

Ele deve apenas consumir:

1. posicao aberta ou snapshot da posicao;
2. plano original do Research Lab;
3. leitura atual do mercado;
4. recomendacao dinamica calculada;
5. gates de seguranca;
6. registro paper/simulado.

## Escopo funcional

### 1. Novo contrato de decisao simulada

Criar contrato, por exemplo:

```python
DynamicExitSimulationDecision
```

Campos sugeridos:

```python
symbol: str
ticket: int | None
side: str
policy: str
action: str
current_stop: float | None
candidate_stop: float | None
approved_stop: float | None
allowed_to_simulate: bool
rejection_reasons: tuple[str, ...]
market_state: str
r_multiple: float
source: str
created_at: str
```

### 2. Gate de seguranca para stop simulado

Criar motor/gate que valide:

- posicao aberta existe ou snapshot de posicao valido;
- ticket, se existir, e apenas identificador auditavel;
- simbolo compativel;
- lado BUY/SELL valido;
- plano original `PLANO_VALIDO`;
- recomendacao dinamica com acao simulavel;
- novo stop nao piora risco;
- novo stop respeita direcao:
  - BUY: stop candidato deve ser maior que stop atual e menor que preco atual;
  - SELL: stop candidato deve ser menor que stop atual e maior que preco atual;
- distancia minima ate preco atual respeitada;
- spread nao excessivo;
- apenas uma simulacao por candle ou por janela minima de tempo;
- nao simular se diferenca for irrelevante;
- nao alterar TP.

### 3. Acoes simulaveis nesta fase

Permitir simulacao para:

```text
PROTECT_TO_BREAK_EVEN
TRAIL_BY_ATR
TRAIL_BY_STRUCTURE
TIGHTEN_BY_MOMENTUM_LOSS
```

`TIME_DECAY_EXIT_WATCH` deve continuar apenas observacional nesta missao, sem fechamento simulado.

### 4. Calculo do stop candidato

Se `DynamicExitRecommendation.candidate_stop` estiver ausente, calcular de forma leve conforme a acao:

- `PROTECT_TO_BREAK_EVEN`: entrada + offset minimo para BUY ou entrada - offset minimo para SELL.
- `TRAIL_BY_ATR`: usar ATR atual e fator vindo dos parametros do plano.
- `TRAIL_BY_STRUCTURE`: usar suporte/resistencia, Donchian ou Chandelier se ja estiverem disponiveis na leitura atual; se nao estiverem, rejeitar sem pesquisar.
- `TIGHTEN_BY_MOMENTUM_LOSS`: apertar stop com base em ATR ou em fracao do risco, sem ultrapassar preco atual.

Nao buscar historico pesado para calcular estrutura. Usar somente campos ja disponiveis no snapshot/runtime.

### 5. Integracao com robo/demo/paper

Integrar preferencialmente em:

```text
application/mt5_demo_robot_service.py
application/demo_execution_service.py
application/dashboard_service.py
```

O ciclo simulado deve:

1. detectar posicao aberta ou snapshot de posicao;
2. montar `DynamicExitMarketReading`;
3. classificar estado;
4. recomendar saida dinamica;
5. passar pelo gate;
6. se aprovado, registrar `DynamicExitSimulationDecision`;
7. exibir no dashboard.

Nao chamar API MT5 de modificacao de ordem, SL ou TP.

### 6. Auditoria

Registrar cada decisao simulada com:

- timestamp;
- simbolo;
- lado;
- ticket auditavel, se houver;
- estado de mercado;
- acao recomendada;
- stop atual;
- stop candidato;
- stop aprovado simulado;
- aprovado/rejeitado;
- motivos de rejeicao;
- fonte.

Pode ser em memoria inicialmente, desde que exibido no dashboard. Persistencia em arquivo deve ser opcional e pequena.

### 7. Dashboard

Exibir em `MT5 Forex` ou `Relatorios`:

- estado de saida dinamica;
- acao recomendada;
- stop atual;
- stop candidato;
- decisao do gate;
- motivo da aprovacao/rejeicao;
- ultima simulacao de stop;
- aviso visivel:

```text
Saida dinamica em SIMULACAO/PAPER. Nenhum SL/TP e modificado no MT5.
```

### 8. Configuracao de seguranca

Adicionar flag padrao desligada:

```text
dynamic_exit_simulation_enabled = False
```

A simulacao so pode ocorrer se:

- flag estiver ligada;
- robo demo/paper estiver armado ou em modo de teste;
- gate aprovar.

### 9. Testes obrigatorios

Criar testes para:

1. BUY nao simula stop para baixo.
2. SELL nao simula stop para cima.
3. Break-even aprovado quando posicao esta positiva e stop ainda nao protege entrada.
4. Trailing ATR rejeitado quando ATR ausente.
5. TIME_DECAY nao fecha posicao nem simula fechamento nesta missao.
6. Gate rejeita diferenca irrelevante de stop.
7. Simulacao idempotente: mesma vela nao registra repetidamente.
8. Nenhuma chamada de modificacao MT5, SL, TP ou abertura de ordem e feita.

## Criterios de aceite

- Saida dinamica deixa de ser apenas recomendacao e passa a gerar decisao simulada quando habilitada.
- Default permanece desligado.
- Nenhum SL/TP real e modificado.
- Nenhuma ordem real ou demo e enviada.
- Nenhum fechamento automatico de posicao nesta missao.
- Nenhuma pesquisa pesada ou Lab e disparado durante gestao de stop.
- Stop simulado so melhora risco, nunca piora.
- Auditoria registra toda aprovacao/rejeicao.
- Dashboard mostra estado da saida dinamica simulada.
- Testes novos passam.
- `python -m compileall dashboard_app.py application domain research tests` passa.
- `python scripts\run_critical_ci.py` executado; se falhar por pendencia preexistente, registrar no relatorio.

## Proibido

- Ativar ordem real.
- Modificar SL/TP no MT5.
- Alterar TP automaticamente.
- Fechar posicao por `TIME_DECAY` nesta missao.
- Recalcular Research Lab dentro do ciclo operacional.
- Buscar historico pesado para decidir stop.
- Apagar `.traderia`, banco, logs ou snapshots.
- Mudar contrato visual MT5 fora do necessario.

## Resultado esperado

O TraderIA Novo passa a ter uma primeira camada de gestao dinamica de stop em modo paper/simulado: o sistema rastreia mudanca de cenario, recomenda uma acao, valida gates e registra qual SL teria sido aplicado se a execucao estivesse autorizada.
