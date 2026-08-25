# Modelo Operacional 24 — XAU/M5 RSI50 Basket

`M24_CONTRACT=M24_SETUP_V19_20260823; SHA256=d918353322bc17fd17e1c7d0ba47272cf19431ef2c60d9cd1686829f2802c05f`

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
3. a vela que cruzou a SMA20 possui minima/maxima valida para posicionar o SL.

Os dois cruzamentos podem ocorrer em candles M5 diferentes. A ordem so e
liberada quando ambos ja ocorreram na mesma direcao e continuam validos no
candle fechado atual. `abs(SMA20-SMA50)/ATR14` continua calculada apenas para
auditoria e nao bloqueia a entrada.

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
entrada inicial usa a propria vela do cruzamento do preco com a SMA20 para o
SL: BUY usa um pip abaixo da minima dessa vela e SELL usa um pip acima da
maxima.

A `INITIAL` mede a ultima perna estrutural completa anterior ao candle-sinal e
projeta 100% dessa distancia a partir da entrada: BUY soma a perna e SELL
subtrai. O alvo fica congelado no plano e o provider o preserva como preco
absoluto; nao existe fallback fixo de `7,50` pontos.

Depois da abertura, a `INITIAL` preserva esse SL ate o mercado confirmar nova
estrutura. No BUY, um M5 fechado deve romper o microtopo anterior; somente
entao o Position Manager usa o microfundo criado entre o topo e o rompimento,
menos um pip, como candidato. No SELL, rompe-se o microfundo e protege-se acima
do microtopo criado. O candidato so e enviado quando melhora o SL existente e
permanece no lado seguro do preco. A reentrada continua protegida separadamente
pelos micro-pivos 1+1 com margem de um pip.

A confirmacao do preco, RSI e distancia libera a entrada inicial a mercado.
A posicao principal nao depende da relacao SMA20/SMA50 nem para entrar nem para
sair. A `INITIAL` libera o Full Exit RSI50 a partir da terceira vela M5 fechada
posterior a entrada; `REENTRY` e `CONTINUATION` preservam suas regras RSI. O
retorno confirmado de 70 para baixo no BUY ou de 30 para cima no SELL, o SL
individual e o Full Exit financeiro da cesta continuam ativos.

## Reentrada pendente

A reentrada nao exige um novo cruzamento nem usa faixa de RSI como filtro. Ela
acompanha o retorno do preco a SMA20 nos cinco ultimos M5 fechados e a retomada:

- BUY: o ultimo M5 fecha acima da SMA20 e rompe a maxima da vela anterior;
- SELL: o ultimo M5 fecha abaixo da SMA20 e rompe a minima da vela anterior;
- antes do rompimento, usa BUY_STOP na maxima ou SELL_STOP na minima do ultimo
  M5 fechado;
- se o preco vivo ja ultrapassou esse gatilho, entra imediatamente a mercado;
- depois de confirmada a correcao, a pendente e atualizada a cada novo candle
  M5: BUY_STOP caminha pela maxima e SELL_STOP caminha pela minima do ultimo
  candle fechado;
- o SL usa o micro-pivo 1+1 confirmado mais recente: minima do microfundo
  menos um pip no BUY e maxima do microtopo mais um pip no SELL;
- a reentrada nao reaplica os filtros direcionais da fonte;
- BUY e SELL usam TP pela projecao Fibonacci de 100% da ultima perna estrutural
  completa anterior, projetada a partir do preco da reentrada;
- ao atingir RSI extremo (`BUY >= 70` ou `SELL <= 30`), o TP estrutural e
  removido no MT5 e a posicao passa a aguardar o Full Exit confirmado no
  retorno do RSI (`BUY < 70` ou `SELL > 30`);
- sem alvo estrutural valido no lado lucrativo, a reentrada fica bloqueada;
- o roteamento M24 materializa seu proprio plano M5 mesmo quando o plano-base
  heuristico H1 estiver sem gatilho;
- a perda do RSI50 preserva o Full Exit individual de seguranca; na `INITIAL`,
  as duas primeiras velas M5 fechadas posteriores ao candle de entrada possuem
  carencia e o Full Exit RSI50 so pode atuar a partir da terceira; posições
  legadas sem horario rastreavel preservam o comportamento anterior;
- nenhuma posicao M24, inicial ou reentrada, fecha por relacao SMA20/SMA50.

## CONTINUATION associada a INITIAL

A `CONTINUATION` e armada quando a `INITIAL` e aceita com TP Fibonacci valido.
O runtime registra lado, preco e horario do alvo e publica uma unica ordem Stop
por lado um pip alem desse TP, para que a INITIAL conclua primeiro.

- BUY usa `BUY_STOP` acima do TP inicial; SELL usa `SELL_STOP` abaixo do TP;
- o SL inicial usa o fundo do ultimo M5 fechado no BUY e o topo no SELL;
- depois da abertura, o extremo do ultimo M5 fechado move o SL somente a favor;
  nunca afrouxa nem cruza o preco;
- nao existe TP individual na `CONTINUATION`;
- o volume e `0,10` lote;
- BUY faz Full Exit quando o RSI atinge 70; SELL quando atinge 30;
- a regra e simetrica e o watch e consumido somente depois do aceite da ordem
  Stop pelo provider Demo.

O M25 nao reutiliza este contrato. Seu contrato V2 opera somente XAUUSD/M5 e
copia os planos executaveis de M8, M10 e M18-M22, preservando entrada, SL, TP e
saida nativa de cada fonte.

## Lateralizacao da REENTRY aberta

A lateralizacao nao envia nova ordem e nao aumenta a posicao. Ela inicia apenas
quando uma `REENTRY` de `0,10` permanece aberta, nao alcanca o TP Fibonacci e
forma um microtopo no BUY ou microfundo no SELL antes de retornar ao range.

- BUY reposiciona o TP no fechamento do microtopo anterior;
- SELL reposiciona o TP no fechamento do microfundo anterior;
- o SL e calculado para RR `3:1` em relacao ao novo alvo;
- um SL existente mais protetivo e preservado e nunca e afrouxado;
- SL e TP sao enviados juntos numa unica requisicao `TRADE_ACTION_SLTP`;
- o estado e auditado como `LATERALIZATION`, mas o volume continua sendo o
  `0,10` da REENTRY original; `0,10` e somente a classificacao reservada do
  modo e nunca gera nova ordem.

## Ordem de precedência

1. entrada inicial a mercado depois dos cruzamentos do preco/SMA20 e RSI14/50,
   ainda que ocorram em candles diferentes, desde que ambos continuem validos;
2. `CONTINUATION` Stop armada um pip alem do TP aceito da `INITIAL`;
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

- entrada `INITIAL`: TP nativo MT5 na projecao Fibonacci de 100% da ultima
  perna estrutural completa anterior;
- entrada `INITIAL`: SL na minima da vela que cruzou a SMA20 menos `0,01` no
  BUY ou na maxima dessa vela mais `0,01` no SELL;
- trailing da `INITIAL`: BUY somente avanca o SL para abaixo do novo
  microfundo 1+1 depois que um M5 fechado romper o microtopo anterior; SELL
  somente avanca para acima do novo microtopo depois de romper o microfundo;
  o SL nunca recua;
- entrada `REENTRY`: TP Fibonacci de 100% da perna estrutural anterior;
- entrada `CONTINUATION`: sem TP individual; SL inicial no extremo do M5
  anterior e protecao posterior pela SMA20;
- `abs(SMA20-SMA50)/ATR14` e apenas telemetria de separacao/forca; nao define
  BUY/SELL e nao bloqueia `INITIAL`, `REENTRY` ou `CONTINUATION`;
- entrada `INITIAL`: volume `0,10` lote;
- entrada `REENTRY`: volume `0,10` lote;
- entrada `CONTINUATION`: volume `0,10` lote;
- modo `LATERALIZATION`: nao adiciona volume; reaproveita a REENTRY `0,10` e
  reposiciona SL/TP do mesmo ticket;
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
  atual, manutencao das condicoes, SL inicial bilateral na extremidade da vela
  que cruzou a SMA20,
  reentrada pendente, acompanhamento do SL inicial somente apos rompimento
  estrutural confirmado, carencia de dois M5 para Full Exit RSI50 da INITIAL,
  remocao de TP no RSI extremo, trailing monotono,
  isolamento M23/M24,
  liberacao da primeira reentrada apos RSI extremo, rota autonoma unica, TP
  estrutural bilateral nas reentradas, `CONTINUATION` bilateral e comentario MT5.
## Inversao RSI50 e troca de lado

- A reentrada faz `FULL_EXIT` quando o RSI14 cruza 50 contra o lado no ultimo
  M5 fechado. A entrada inicial usa o mesmo cruzamento somente a partir da
  terceira vela M5 fechada posterior ao candle congelado na abertura.
- Para `SELL`, o cruzamento confirmado de baixo para cima de 50 encerra a
  venda. Para `BUY`, o cruzamento confirmado de cima para baixo encerra a
  compra.
- O encerramento libera a avaliacao da entrada inicial oposta no ciclo
  seguinte; a nova entrada continua exigindo o cruzamento proprio do preco na
  SMA20 e a confirmacao do RSI atual.
- A entrada inicial do M24 possui TP individual na projecao Fibonacci de 100%
  da perna estrutural anterior e valida RR positivo. Ao atingir RSI70 no BUY ou
  RSI30 no SELL, o Position Manager remove esse TP e aguarda o retorno do RSI
  para Full Exit. Reentradas preservam seu alvo Fibonacci. A `CONTINUATION`
  nao usa TP individual e protege o SL pela SMA20 depois da abertura.

## TP da reentrada

- `BUY`: projeta acima da entrada 100% da ultima perna estrutural completa.
- `SELL`: projeta abaixo da entrada 100% da ultima perna estrutural completa.
- Sem uma perna anterior valida e lucrativa, a reentrada aguarda novo encaixe.
