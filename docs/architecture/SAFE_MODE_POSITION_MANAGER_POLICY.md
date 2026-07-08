# Politica Do Position Manager Em Safe Mode

## Objetivo

Definir como o TraderIA Novo deve tratar posicoes abertas, stop movel, trailing, break-even e saida dinamica quando o MT5 estiver em Safe Mode.

## Regra Principal

Safe Mode pode acompanhar posicao, mas nao pode inventar plano.

```text
Sem plano valido -> observa e preserva.
Com plano valido -> acompanha mercado.
Com dados minimos completos -> pode recomendar.
Com politica suportada e gates aprovados -> pode executar apenas no escopo Demo autorizado.
```

## Separacao De Responsabilidades

### Research Lab

O Lab e responsavel por criar o plano inicial:

- par;
- timeframe;
- alpha/setup;
- direcao;
- entrada;
- stop inicial;
- alvo;
- politica de saida;
- parametros da politica.

O Lab nao deve ser recalculado por ciclo leve do Forex nem durante oscilacao de UI.

### Market Data / Safe Mode

O Safe Mode e responsavel por leitura leve:

- candles;
- preco atual;
- ultimo candle;
- medias;
- RSI;
- momentum;
- volatilidade;
- ATR;
- spread quando disponivel;
- diagnostico de disponibilidade.

Ele nao decide estrategia e nao executa ordem.

### Position Manager Operacional

O Position Manager operacional esperado deve:

- detectar posicao aberta no MT5;
- vincular a posicao ao plano salvo;
- ler ticket, lado, entrada, SL, TP e preco atual;
- calcular R atual;
- preservar maximo/minimo desde entrada;
- avaliar se a politica do Lab ainda e aplicavel;
- chamar Dynamic Exit somente com dados completos;
- bloquear qualquer movimento se o contexto estiver incompleto;
- registrar cada decisao.

Observacao: no codigo atual, `core.PositionManager` e um componente legado em memoria. O gerenciamento real do MT5 esta distribuido entre `ForexMT5Service`, `DynamicExitMarketStateClassifier` e `MT5DemoExecutionProvider`.

### Provider Demo MT5

O Provider Demo e o unico ponto que pode submeter alteracao de SL/TP no ambiente Demo, dentro dos gates permitidos.

Hoje o stop management automatico aceita:

- `BREAK_EVEN`;
- `ATR_TRAILING_STOP`.

Outras politicas dinamicas devem permanecer read-only, simuladas ou assistidas ate autorizacao explicita.

## Condicoes Minimas Para Gerenciar Stop

O sistema so pode calcular ou tentar mover stop quando todos os itens existirem:

- MT5 conectado ou leitura recente valida;
- posicao aberta no simbolo;
- ticket MT5 conhecido;
- lado BUY/SELL conhecido;
- entrada conhecida;
- stop atual conhecido;
- preco atual conhecido;
- plano do Lab valido salvo;
- politica de saida definida;
- parametros da politica disponiveis;
- ATR disponivel quando a politica exigir ATR;
- ambiente Demo confirmado;
- gate de melhora de risco aprovado;
- stop candidato fica antes do mercado;
- TP atual e preservado.

## Regra De Bloqueio

Se qualquer dado minimo faltar:

```text
nao atualizar stop;
nao recalcular Lab;
nao substituir plano;
nao desarmar robo por leitura transitoria;
manter stop atual;
exibir alerta;
registrar log;
aguardar proximo ciclo leve.
```

## Regras Por Politica

### Fixed Stop

Nao move SL. Apenas preserva o plano original.

### Break Even

Pode ser considerado em Demo somente quando:

- posicao andou a favor;
- o gatilho de RR foi atingido;
- o novo stop melhora risco;
- o novo stop nao fica do lado errado do mercado;
- entrada e stop atual sao conhecidos.

### ATR Trailing Stop

Pode ser considerado em Demo somente quando:

- ATR esta disponivel;
- preco atual esta disponivel;
- fator ATR veio do plano;
- o novo stop melhora o risco;
- o novo stop nao fica do lado errado do mercado.

Se ATR estiver ausente, bloquear sem erro operacional.

### Saida Dinamica Read-only

Pode sempre recomendar quando houver dados minimos. Nao deve executar automaticamente sem autorizacao especifica.

### Saida Dinamica Assistida

Deve permanecer desligada por padrao. Quando ligada manualmente, so pode modificar SL de posicao existente em conta Demo e mediante confirmacao/gate.

## Politica De UI

Mensagens recomendadas:

```text
Safe Mode ativo. Mercado monitorado em leitura leve.
```

```text
Posicao monitorada com plano valido. Stop movel sujeito aos gates Demo.
```

```text
Posicao aberta sem plano valido. Stop atual preservado; gestao automatica bloqueada.
```

```text
ATR ausente para trailing. Aguardando nova leitura valida.
```

## Politica De Logs

Cada ciclo que envolver posicao aberta deve ser rastreavel:

- timestamp;
- simbolo;
- ticket;
- politica base do Lab;
- leitura de preco;
- stop atual;
- stop candidato;
- decisao;
- motivo;
- acao executada ou bloqueada;
- erro/gate, quando houver.

Logs de stop management devem continuar preservados em `.traderia`, sem limpeza automatica por Runtime Guard.

## Invariantes

- Nunca mover stop para piorar o risco.
- Nunca mover stop para o lado errado do mercado.
- Nunca alterar TP quando a acao for apenas mover SL.
- Nunca executar em conta real.
- Nunca recalcular Lab pesado no ciclo leve.
- Nunca apagar `.traderia`.
- Nunca limpar plano operacional por oscilacao transitoria.
- Nunca tratar Safe Mode como permissao de execucao.

## Recomendacao De Evolucao

Criar uma camada unica futura:

```text
MT5PositionManager
```

Essa camada deve centralizar posicao, plano, leitura de mercado, estado max/min desde entrada, recomendacao dinamica e log. A implementacao atual funciona, mas esta distribuida; a centralizacao reduziria retrabalho e deixaria o fluxo mais facil de auditar pelo GitHub/GPT/Codex.

