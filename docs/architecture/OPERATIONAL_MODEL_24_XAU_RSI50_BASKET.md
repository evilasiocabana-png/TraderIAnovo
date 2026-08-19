# Modelo Operacional 24 — XAU/M5 RSI50 Basket

`M24_CONTRACT=M24_SETUP_V3_20260819; SHA256=4caa2af5fb100fbf7631fbaf2655b0ab9006f4afbc55ebcf7543590d176eb60b`

Fonte executavel unica: `application/model24_setup_contract.py`. Em caso de
divergencia com uma descricao historica, este marker e o contrato executavel
versionado prevalecem.

## Identidade

- ID: `MODELO_24_XAU_RSI50_BASKET`.
- Origem operacional unica: `M24_PROPRIO`.
- Variantes antigas `MODELO_24_XAU_RSI50_BASKET_SOURCE_M<n>` permanecem
  reconhecidas somente para historico e gestao de posicoes legadas.
- Ativo/timeframe: `XAUUSD/M5`.
- As linhas H1 do monitor servem apenas como envelope do ciclo. A rota M24
  normaliza esse envelope para `XAUUSD/M5` antes de calcular o plano.
- Comentario de novas ordens MT5: `TraderIA M24 INITIAL`,
  `TraderIA M24 REENTRY` ou `TraderIA M24 CONTINUATION`.
- Estado e auditoria são próprios; M23 nunca compartilha posições, resultado ou arquivo de estado com M24.

## Entrada inicial

O candle M5 precisa estar fechado. A entrada e a mercado depois que dois
eventos direcionais tiverem ocorrido e continuarem validos.

BUY exige:

1. o preco cruzou a SMA20 de baixo para cima e permanece acima dela;
2. o RSI14 produziu novo cruzamento acima de 50 e permanece acima;
3. a distancia absoluta `abs(SMA20 - SMA50) / ATR14` e pelo menos `0,25`.

Os dois cruzamentos podem ocorrer em candles M5 diferentes. A ordem so e
liberada quando ambos ja ocorreram na mesma direcao, continuam validos no
candle fechado atual e a distancia permanece `>= 0,25`.

O M24 calcula diretamente seu proprio setup. Ele nao depende de M8, M10 ou
M18-M22 e nao herda ADX, inclinacao da SMA50 ou filtros desses modelos.
Sua rota normaliza internamente qualquer envelope do ciclo para `XAUUSD/M5` e
e avaliada uma unica vez por ciclo. O proprio M24 tambem solicita e atualiza a
janela deslizante de 201 candles M5 em cada ciclo operacional. Assim, a ordem
nao depende de existir uma linha XAUUSD no relatorio-base do Lab. Sao 200
candles fechados para indicadores e um candle atual separado; a janela avanca
sem acumular candles antigos quando um novo M5 fecha.

Se o preco ou o RSI perderem validade, a entrada BUY nao e liberada. SELL e
simetrico: preco cruza e permanece abaixo da SMA20 com RSI14 abaixo de 50. A
entrada inicial nao exige micro-pivo. O SL nasce um pip alem do extremo do
candle que cruzou a SMA20: minima menos um pip para BUY e maxima mais um pip
para SELL.

Depois da abertura, a entrada `INITIAL` preserva esse SL ate existirem dois
candles M5 fechados consecutivos do lado favoravel da SMA20. No BUY, ambos os
fechamentos devem estar acima de suas SMA20; no SELL, ambos devem estar abaixo.
A partir dessa confirmacao, o Position Manager usa a SMA20 atual como candidato
de SL. O candidato so e enviado quando melhora o SL existente e permanece no
lado seguro do preco, portanto o stop nunca recua. A reentrada continua sendo
protegida separadamente pelos micro-pivos 1+1 com margem de um pip.

A confirmacao do preco, RSI e distancia libera a entrada inicial a mercado.
A posicao principal nao depende da relacao SMA20/SMA50 nem para entrar nem para
sair. `INITIAL`, `REENTRY` e `CONTINUATION` fazem Full Exit no cruzamento do RSI14 em 50 contra
a posicao e tambem no retorno confirmado de 70 para baixo no BUY ou de 30 para
cima no SELL, alem do SL individual e do Full Exit financeiro da cesta.

## Reentrada pendente

A reentrada nao exige um novo cruzamento. Ela acompanha uma correcao dentro da
perna vigente usando o estado confirmado no ultimo M5 fechado:

- BUY: fechamento acima da SMA20, RSI14 entre 50 e 70 e ao menos um candle de
  correcao baixista entre os cinco ultimos M5 fechados;
- SELL: fechamento abaixo da SMA20, RSI14 entre 30 e 50 e ao menos um candle de
  correcao altista entre os cinco ultimos M5 fechados;
- BUY_STOP na maxima do ultimo M5 fechado;
- SELL_STOP na minima do ultimo M5 fechado;
- depois de confirmada a correcao, a pendente e atualizada a cada novo candle
  M5: BUY_STOP caminha pela maxima e SELL_STOP caminha pela minima do ultimo
  candle fechado;
- o SL usa o micro-pivo 1+1 confirmado mais recente: minima do microfundo
  menos um pip no BUY e maxima do microtopo mais um pip no SELL;
- a reentrada nao reaplica os filtros direcionais da fonte;
- BUY usa TP no fechamento da vela que formou o microtopo 1+1 confirmado mais
  recente; SELL usa o fechamento da vela que formou o microfundo 1+1;
- a busca percorre a janela deslizante de ate 200 velas M5 fechadas e nunca usa
  a maxima/minima do pivo como preco do TP;
- ao atingir RSI extremo (`BUY >= 70` ou `SELL <= 30`), o TP estrutural e
  removido no MT5 e a posicao passa a aguardar o Full Exit confirmado no
  retorno do RSI (`BUY < 70` ou `SELL > 30`);
- sem alvo estrutural valido no lado lucrativo, a reentrada fica bloqueada;
- o roteamento M24 materializa seu proprio plano M5 mesmo quando o plano-base
  heuristico H1 estiver sem gatilho;
- a perda do RSI50 preserva o Full Exit individual de seguranca para a entrada
  inicial e para a reentrada;
- nenhuma posicao M24, inicial ou reentrada, fecha por relacao SMA20/SMA50.

## CONTINUATION apos TP da REENTRY

A `CONTINUATION` somente pode ser armada por uma `REENTRY` aceita com TP
estrutural. O runtime registra lado, preco e horario do alvo, mas a entrada
permanece bloqueada ate o historico read-only do MT5 confirmar que a posicao
foi efetivamente encerrada por `DEAL_REASON_TP` naquele alvo.

Depois dessa confirmacao:

- BUY entra a mercado quando o fechamento continua acima do TP anterior e
  `RSI14 > 70`;
- SELL entra a mercado quando o fechamento continua abaixo do TP anterior e
  `RSI14 < 30`;
- o SL fica um pip alem do microfundo/microtopo 1+1 confirmado mais recente;
- nao existe TP individual;
- o volume e `0,40` lote;
- BUY faz Full Exit quando o RSI retorna para abaixo de 70; SELL faz Full Exit
  quando retorna para acima de 30;
- a regra e simetrica e o watch e consumido somente depois do aceite da ordem
  a mercado pelo provider Demo.

O M25 nao reutiliza este contrato. Seu contrato V2 opera somente XAUUSD/M5 e
copia os planos executaveis de M8, M10 e M18-M22, preservando entrada, SL, TP e
saida nativa de cada fonte.

## Ordem de precedência

1. entrada inicial a mercado depois dos cruzamentos do preco/SMA20 e RSI14/50,
   ainda que ocorram em candles diferentes, desde que ambos continuem validos;
2. `CONTINUATION` pronta apos TP confirmado da `REENTRY`, continuidade do preco
   e RSI extremo;
3. reentrada pendente pelo estado atual SMA20/RSI50;
4. aguardar.

Depois do aceite da entrada inicial pelo provider Demo, as proximas entradas na
mesma direcao sao reentradas. A INITIAL e global para o M24 e alterna de lado:
depois de uma INITIAL BUY, somente uma INITIAL SELL pode iniciar a proxima
perna, e vice-versa. O estado e persistido entre ciclos e reinicios.

## Limite simultaneo

- o M24 admite varias rodadas de reentrada durante a mesma perna valida;
- cada rodada pode manter no maximo uma posicao `REENTRY` aberta por vez;
- depois que a `REENTRY` encerrar, um novo candle e uma nova oportunidade
  valida podem iniciar a rodada seguinte;
- `INITIAL`, `REENTRY` e `CONTINUATION` nunca podem coexistir em direcoes opostas; a nova
  `INITIAL` aguarda o Position Manager encerrar a perna anterior;
- ao surgir uma `INITIAL` na direcao oposta, pendencias M24 do lado anterior
  sao canceladas antes de qualquer novo envio;
- existe no maximo uma ordem `REENTRY` pendente global por rodada para o M24;
- uma nova `REENTRY` aguarda o encerramento da `REENTRY` posicionada;
- repeticoes do mesmo candle, identidade de plano ou sinal permanecem
  bloqueadas por idempotencia;
- existe no maximo uma posicao aberta por papel: uma `INITIAL`, uma `REENTRY`
  e uma `CONTINUATION`;
- o provider aplica a trava antes do `order_send`, independentemente da tela;
- novas ordens gravam `INITIAL`, `REENTRY` ou `CONTINUATION` no comentario MT5; posicoes abertas
  anteriores a esta regra sao classificadas pelo ticket do log de execucao.

## Reentrada apos RSI extremo

O descarte automatico da primeira oportunidade foi removido. Depois de um
Full Exit no retorno do RSI 70/30, a primeira reentrada valida do mesmo lado
pode ser liberada imediatamente. Permanecem apenas as travas normais de
idempotencia, papel ja aberto, pendencia existente e lado oposto.

O Position Manager deve reconhecer uma posicao M24 pelo contrato completo, e
nao apenas por `operational_model`. Um snapshot historico pode preservar M8,
M10 ou M18-M22 como modelo-fonte legado. Nesse caso, `ALPHA024`, a politica
`M24_SOURCE_EXIT_PLUS_BASKET_1000` ou os parametros `source_operational_model`
e `m24_entry_role` continuam identificando o M24 e obrigam o registro do Full
Exit extremo e a continuidade do estado auditavel.

IDs legados de fonte servem somente para ler historico antigo. Novas decisoes,
ordens e estados usam uma unica identidade M24.

## Cesta financeira

- entrada `INITIAL`: TP nativo MT5 `0.0`;
- entrada `REENTRY`: TP no fechamento do candle que formou o topo/fundo
  estrutural anterior a correcao;
- entrada `CONTINUATION`: TP nativo MT5 `0.0`;
- entrada inicial e reentrada exigem `abs(SMA20 - SMA50) / ATR14 >= 0,25`;
- essa distancia mede somente separacao/forca e nunca define BUY ou SELL;
- entrada `INITIAL`: volume `0,30` lote;
- entrada `REENTRY`: volume `0,20` lote;
- entrada `CONTINUATION`: volume `0,40` lote;
- Alvo coletivo: resultado líquido da cesta M24 `>= +US$1.000`, somando `profit + swap + commission + fee` expostos pelo MT5.
- Atingido o alvo, todas e somente as posições com comentário M24 são fechadas a mercado.
- Posições M23 e posições diretas não participam da cesta M24.

## Persistência

- `.traderia/model24_runtime_state.json`: consumo da entrada inicial e estado
  da perna unica `M24_PROPRIO`; estados legados sao migrados em leitura.
- `.traderia/model24_basket_state.json`: estado financeiro compacto da cesta.
- `.traderia/model24_basket_audit.jsonl`: auditoria dos Full Exits coletivos.

## Segurança e validação

- Somente conta MT5 Demo passa pelo provider.
- A criação e os testes do modelo não enviam ordens.
- O candle dos indicadores deve coincidir com o candle do Trade Plan.
- O estado agregado do ciclo deve preservar o gargalo proprio do M24; uma
  linha generica posterior, como BTCUSD/H1, nao pode ocultar seu diagnostico.
- A tabela `Entrada Teorica MT5 - Modelo 24` exibe `Envio` imediatamente depois
  de `Timeframe`, seguido do motivo completo calculado pelo ciclo de fundo.
- A ausencia de plano-base H1 nao pode interromper o roteamento proprio M5.
- O avaliador aceita tanto campos OHLC tecnicos (`close/high/low/time`) quanto o
  contrato canonico `Candle` (`fechamento/maxima/minima/data`) usado no runtime.
- M24 é modelo ativo e selecionável, mas não é ativado automaticamente pela implantação.
- Testes dedicados cobrem cruzamento inicial do preco com confirmacao do RSI
  atual, manutencao das condicoes, reentrada pendente, SL um pip alem do
  micro-pivo 1+1, confirmacao de dois fechamentos antes do trailing SMA20 da
  entrada inicial, remocao de TP no RSI extremo, trailing monotono, isolamento M23/M24,
  liberacao da primeira reentrada apos RSI extremo, rota autonoma unica, TP
  estrutural bilateral nas reentradas, `CONTINUATION` bilateral e comentario MT5.
## Inversao RSI50 e troca de lado

- Tanto a entrada inicial quanto a reentrada fazem `FULL_EXIT` quando o RSI14
  cruza 50 contra o lado da posicao no ultimo candle M5 fechado.
- Para `SELL`, o cruzamento confirmado de baixo para cima de 50 encerra a
  venda. Para `BUY`, o cruzamento confirmado de cima para baixo encerra a
  compra.
- O encerramento libera a avaliacao da entrada inicial oposta no ciclo
  seguinte; a nova entrada continua exigindo o cruzamento proprio do preco na
  SMA20 e a confirmacao do RSI atual.
- A entrada inicial do M24 nao possui TP individual e, por isso, nao depende de
  RR positivo para ser validada. Reentradas com alvo estrutural continuam
  validando o TP herdado do proprio setup.

## TP da reentrada

- `BUY`: fechamento do candle que formou o microtopo 1+1 confirmado mais
  recente e que esteja acima da entrada.
- `SELL`: fechamento do candle que formou o microfundo 1+1 confirmado mais
  recente e que esteja abaixo da entrada.
- A maxima/minima confirma o micro pivo, mas nao e usada como preco do TP.
- O runtime nao pula o microtopo/microfundo mais recente para usar uma
  estrutura antiga. Se o fechamento ainda estiver do lado invalido da entrada
  pendente, a reentrada aguarda novo encaixe.
