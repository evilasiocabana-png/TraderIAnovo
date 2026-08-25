# Modelo 23 - Acumulador Financeiro

Data: 2026-08-12
Status: contrato operacional implementado em modo MT5 Demo

## Objetivo

O M23 consolida entradas validas dos modelos operacionais ativos em uma unica
cesta financeira. Ele nao cria uma Alpha propria e nao altera o sinal de origem.

## Fontes Ativas

O M23 captura entradas novas somente dos modelos operacionais ativos:

```text
M1, M2, M5, M7, M8, M10, M18 e M20
```

Esse conjunto e o mesmo usado pelo modo `Todos`. Fora do M23, os modelos ativos
podem ser marcados em qualquer combinacao e somente os marcados enviam suas
proprias ordens. Dentro do M23, essas fontes sao avaliadas pelo agregador.

M3, M4, M6, M9, M11, M12, M13, M14 e M15 permanecem aposentados. M16,
M17, M19, M21 e M22 continuam operacionais de forma independente, mas nao sao
fontes de novas entradas da cesta M23.

O M23 pode operar sozinho ou junto com os modelos-fonte selecionados. No modo
combinado, um sinal aprovado pode produzir duas ordens independentes: a ordem
direta do modelo-fonte e a copia identificada como M23. Essa duplicacao e
intencional, fica separada na auditoria e aumenta a exposicao daquele sinal.

Na Entrada Teorica, o M23 expoe uma copia para cada fonte ativa. O identificador
permanece `S<n>` no comentario da ordem e na auditoria.

## Contrato De Entrada

- herda simbolo, timeframe, direcao, candle e gatilho aprovados;
- preserva todos os gates do modelo-fonte;
- copia o Stop Loss e o Take Profit do modelo-fonte;
- preserva tambem a saida dinamica nativa e o Position Manager da fonte;
- preserva se a entrada da fonte e a mercado ou pendente;
- quando a fonte nao possui TP por contrato, o M23 tambem nao inventa um TP;
- SL/TP individuais e a gestao financeira global coexistem: o primeiro gatilho
  atingido encerra a posicao individual ou toda a cesta;
- permite reentradas normais da fonte quando existir um novo sinal/candle;
- a mesma identidade no mesmo candle continua bloqueada contra duplicacao do ciclo;
- identifica a origem no comentario `TraderIA M23 S<n>`;
- um sinal da rodada encerrada nao pode iniciar a rodada seguinte.

## Gestao Da Cesta

O resultado usado pelo gestor e o valor flutuante executavel informado pelo MT5:

```text
resultado M23 = soma(profit + swap + commission + fee)
```

Somente posicoes com comentario M23 entram nessa soma.
O Full Exit de +US$1.000 fecha exclusivamente esses tickets M23. Posicoes
diretas M1-M22 ficam fora da soma e continuam abertas ate suas proprias regras
de SL, TP ou gestao determinarem a saida.

Os limites em dolar exigem conta Demo com moeda-base USD. A validacao local de
2026-08-12 confirmou `Pepperstone-Demo`, `trade_mode=0` e `currency=USD`.

Regra financeira unica:

```text
resultado >= +US$1.000
  -> Full Exit imediato de toda a cesta a mercado
```

Nao existe stop financeiro global, trailing financeiro, piso por recuo do topo
ou orcamento agregado de SL. Cada posicao continua obedecendo ao SL, TP e saida
dinamica herdados da fonte. A cesta somente acrescenta a zeragem coletiva em
+US$1.000.

O alvo de US$1.000 e um gatilho, nao uma garantia do valor final realizado. Entre
a leitura e as execucoes ticket por ticket podem existir spread, slippage e
movimento do mercado. Por isso o fechamento e a mercado, sem ordem limitada.

## Fechamento

As posicoes sao ordenadas pelo maior resultado flutuante e fechadas ticket por
ticket pelo `DemoExecutionService`. O provider envia `TRADE_ACTION_DEAL`, ordem
oposta, preco executavel bid/ask e preenchimento IOC.

Motivo auditavel: `M23_FULL_EXIT_PLUS_1000_USD`.

## Ciclo leve

Quando o M23 esta selecionado, sozinho ou combinado, uma unica passagem do ciclo
percorre todos os pares e todas as fontes selecionadas. No modo combinado, essa
mesma passagem produz as rotas direta e M23; o orquestrador nao repete a leitura
uma vez por par. Isso preserva os sinais independentes sem multiplicar o custo de
mercado, atrasar a defesa financeira ou elevar CPU e memoria sem necessidade.

A verificacao de duplicidade usa um indice limitado em memoria, sincronizado
incrementalmente com o JSONL de execucao. O historico em disco continua sendo
a fonte auditavel, mas nao deve ser relido e decodificado para cada candidato
do mesmo ciclo. Esse indice mantem somente identidade, candle, modelo, par,
lado, entrada, SL/TP e tipo de ordem; indicadores e evidencias completas ficam
apenas no JSONL, evitando que a auditoria operacional infle a RAM do app.

O M23 envia no mesmo ciclo todos os sinais independentes que estiverem prontos.
Cada aceite e sequencial e obriga uma nova avaliacao financeira da cesta antes
da proxima exposicao. Uma fonte pode reentrar quando houver novo sinal
executavel; apenas o mesmo sinal/candle e deduplicado.

Durante uma volta pesada, a cesta tambem e reavaliada entre pares e candidatos.
Assim, a defesa nao fica limitada ao inicio da proxima volta. Depois que um
fechamento e aceito, existe uma janela curta de confirmacao para impedir que o
mesmo ticket receba outra solicitacao enquanto o MT5 atualiza `positions_get`.

Se algum ticket for rejeitado, o estado fica `EXIT_PARTIAL` e o proximo ciclo
tenta novamente. Nenhuma entrada nova e aceita durante a zeragem.

O monitor de RAM tolera ciclos ocupados: o health check aguarda ate 15 segundos
e exige cinco falhas consecutivas antes de reiniciar o Streamlit. Uma leitura
temporariamente ocupada nao pode ser confundida com queda do app.

## Estado Persistente

Estado compacto:

```text
.traderia/model23_basket_state.json
```

Auditoria append-only:

```text
.traderia/model23_basket_audit.jsonl
```

Estados:

- `WAITING_NEW_ROUND`;
- `ACCUMULATING`;
- `CLOSING`;
- `EXIT_SUBMITTED`;
- `EXIT_PARTIAL`.

A nova rodada e liberada somente depois que o MT5 confirmar cesta vazia. O
timestamp da zeragem impede reaproveitar candles antigos.

Uma cesta que desapareca por zeragem manual tambem grava `accept_signals_after`.
Assim, o M23 exige um candle posterior ao encerramento manual e nao reabre a
rodada usando sinais antigos.

## Guardrails De Runtime

- o gestor financeiro roda no inicio e entre etapas do ciclo, antes de novas entradas;
- falha ao ler posicoes no MT5 bloqueia novas entradas, em vez de assumir cesta vazia;
- estados `CLOSING`, `EXIT_SUBMITTED` e `EXIT_PARTIAL` bloqueiam novas entradas;
- depois que uma zeragem comeca, o motivo permanece persistido; o gestor aguarda
  a confirmacao curta do MT5 e repete somente se ainda houver tickets restantes;
- uma melhora momentanea do resultado depois do disparo nao cancela o Full Exit;
- M9/M11/M12 aceitam somente XAUUSD/M5 pelo motor proprio;
- M13/M14/M15 aceitam somente pares Forex/M5 pelo motor proprio;
- fonte fora do seu escopo retorna `WAIT` e nunca herda o plano-base H1;
- o painel diferencia resultado MT5 real de risco/lucro projetado;
- M23 mostra o contrato de saida da fonte e o alvo coletivo de +US$1.000.

## Reentrada XAU e TP estrutural

Para copias XAU com reentrada pendente, o M23 acrescenta um gate seguro sem
alterar o modelo-fonte:

- SELL exige correcao M5 por dois candles fechados com maxima e minima
  ascendentes; arma `SELL_STOP` na minima do ultimo candle fechado;
- BUY exige a correcao oposta; arma `BUY_STOP` na maxima do ultimo candle
  fechado;
- SELL usa como TP o ultimo fundo M5 confirmado, obrigatoriamente abaixo da
  entrada;
- BUY usa como TP o ultimo topo M5 confirmado, obrigatoriamente acima da
  entrada;
- sem alvo estrutural valido, somente a rota M23 falha fechada e aguarda;
- um novo candle fechado pode atualizar/substituir o gatilho pendente, enquanto
  a mesma identidade no mesmo candle continua bloqueada como duplicidade.

O ticket pode encerrar pelo TP estrutural ou pelas saidas nativas herdadas da
fonte. A regra adicional da cesta permanece: ao atingir +US$1.000 liquidos, o
M23 fecha a mercado todos os tickets M23 ainda abertos.

As sondas externas usadas para ler candles e posicoes possuem timeout obrigatorio.
No Windows, o timeout encerra a arvore do processo e aguarda sua finalizacao; uma
sonda orfa nao pode permanecer disputando `MetaTrader5.initialize()` com o ciclo
seguinte. `AGUARDANDO_DADOS_MT5` bloqueia entradas e jamais autoriza o gestor a
interpretar ausencia de leitura como cesta vazia.

## Fronteiras

- modelos-fonte ativos decidem entrada, SL e TP por seus contratos originais;
- modelos aposentados permanecem somente no historico;
- M23 roteia e identifica a entrada e preserva todo o contrato de saida da fonte;
- provider MT5 abre e fecha posicoes Demo;
- `Model23BasketManager` nunca cria entrada;
- Position Manager avalia cada ticket M23 com a politica do seu modelo-fonte;
- Relatorio apenas audita M23.

## Rollback

Desmarcar M23 interrompe somente novas copias da cesta. Os modelos diretos que
permanecerem marcados continuam operando. Posicoes M23 ja abertas continuam sob
o gestor da cesta ate zerarem. O codigo M1-M22 permanece como fonte independente.
