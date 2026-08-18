# Modelo Operacional 24 — XAU/M5 RSI50 Basket

## Identidade

- ID: `MODELO_24_XAU_RSI50_BASKET`.
- Variantes: `MODELO_24_XAU_RSI50_BASKET_SOURCE_M<n>`.
- Fontes permitidas: M8, M10, M18, M19, M20, M21 e M22.
- Ativo/timeframe: `XAUUSD/M5`.
- Qualquer linha de outro simbolo e bloqueada antes de materializar plano ou
  chegar ao provider.
- Comentário MT5: `TraderIA M24 S<n>`.
- Estado e auditoria são próprios; M23 nunca compartilha posições, resultado ou arquivo de estado com M24.

## Entrada inicial

O candle M5 precisa estar fechado. A entrada e a mercado depois que dois
eventos direcionais tiverem ocorrido e continuarem validos.

BUY exige:

1. o preco cruzou a SMA20 de baixo para cima e permanece acima dela;
2. o RSI14 cruzou 50 de baixo para cima e permanece acima de 50;
3. os dois cruzamentos podem ter ocorrido em candles M5 diferentes;
4. existe microfundo 1+1 confirmado nos ultimos cinco M5 para definir o SL;
5. os filtros especificos da fonte aprovam a entrada inicial.

Se o primeiro evento perder validade antes do segundo, a entrada BUY nao e
liberada. SELL e simetrico: preco cruza e permanece abaixo da SMA20, RSI14 cruza
e permanece abaixo de 50 e o SL usa o microtopo 1+1 anterior mais proximo.

O segundo evento que completar o conjunto libera a entrada inicial a mercado.
A posicao principal nao depende da relacao SMA20/SMA50 nem para entrar nem para
sair. Seu Full Exit tecnico permanece somente no retorno confirmado do RSI14
de 70 para baixo no BUY ou de 30 para cima no SELL, alem do SL individual e do
Full Exit financeiro da cesta.

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
- o SL inicial usa o extremo oposto da mesma vela que publicou a pendencia:
  minima menos `0,01` no BUY e maxima mais `0,01` no SELL;
- a reentrada nao reaplica os filtros direcionais da fonte;
- BUY usa TP no topo favoravel anterior ao inicio da correcao; SELL usa TP no
  fundo favoravel anterior ao inicio da correcao;
- ao atingir RSI extremo (`BUY >= 70` ou `SELL <= 30`), o TP estrutural e
  removido no MT5 e a posicao passa a aguardar o Full Exit confirmado no
  retorno do RSI (`BUY < 70` ou `SELL > 30`);
- sem alvo estrutural valido no lado lucrativo, a reentrada fica bloqueada;
- o roteamento M24 materializa seu proprio plano M5 mesmo quando o plano-base
  heuristico H1 estiver sem gatilho;
- a perda do RSI50 preserva o Full Exit individual de seguranca somente para
  a posicao de reentrada;
- nenhuma posicao M24, inicial ou reentrada, fecha por relacao SMA20/SMA50.

## Ordem de precedência

1. entrada inicial a mercado depois dos dois cruzamentos mantidos;
2. reentrada pendente pelo estado atual SMA20/RSI50;
3. aguardar.

Depois do aceite da entrada inicial pelo provider Demo, as proximas entradas na
mesma direcao sao reentradas. A INITIAL e global para o M24 e alterna de lado:
depois de uma INITIAL BUY, somente uma INITIAL SELL pode iniciar a proxima
perna, e vice-versa. O estado e persistido entre ciclos e reinicios.

## Limite simultaneo

- o M24 pode manter no maximo uma posicao `INITIAL` e uma posicao `REENTRY`;
- `INITIAL` e `REENTRY` nunca podem coexistir em direcoes opostas; a nova
  `INITIAL` aguarda o Position Manager encerrar a perna anterior;
- ao surgir uma `INITIAL` na direcao oposta, pendencias M24 do lado anterior
  sao canceladas antes de qualquer novo envio;
- existe no maximo uma ordem `REENTRY` pendente global para o M24, mesmo que
  M8, M10 ou outra fonte produzam o mesmo gatilho no ciclo;
- uma nova entrada do mesmo papel aguarda o encerramento da posicao existente;
- INITIAL e REENTRY podem coexistir, totalizando no maximo duas posicoes M24;
- o provider aplica a trava antes do `order_send`, independentemente da tela;
- novas ordens gravam `INITIAL` ou `REENTRY` no comentario MT5; posicoes abertas
  anteriores a esta regra sao classificadas pelo ticket do log de execucao.

## Bloqueio da primeira reentrada apos RSI extremo

Quando um Full Exit individual for executado porque o RSI14 saiu de acima de
70 para abaixo de 70 no BUY, ou de abaixo de 30 para acima de 30 no SELL:

1. a primeira oportunidade valida de reentrada na mesma direcao e ignorada;
2. repeticoes do mesmo sinal durante a mesma vela M5 continuam bloqueadas;
3. somente a segunda oportunidade valida, identificada por uma nova vela M5
   fechada, pode ser liberada;
4. a regra vale para a reentrada pendente;
5. Full Exit por perda do RSI50 de uma reentrada nao arma esse descarte.

A mudanca de direcao elimina a trava pertencente ao lado anterior.

O Position Manager deve reconhecer uma posicao M24 pelo contrato completo, e
nao apenas por `operational_model`. O snapshot historico pode preservar M8,
M10 ou M18-M22 como modelo-fonte. Nesse caso, `ALPHA024`, a politica
`M24_SOURCE_EXIT_PLUS_BASKET_1000` ou os parametros `source_operational_model`
e `m24_entry_role` continuam identificando o M24 e obrigam o registro do Full
Exit extremo. Sem esse reconhecimento, o fechamento ocorre, mas o descarte da
primeira reentrada nao seria armado.

## Cesta financeira

- entrada `INITIAL`: TP nativo MT5 `0.0`;
- entrada `REENTRY`: TP no fechamento do candle que formou o topo/fundo
  estrutural anterior a correcao;
- entrada inicial e reentrada exigem `abs(SMA20 - SMA50) / ATR14 >= 0,25`;
- essa distancia mede somente separacao/forca e nunca define BUY ou SELL;
- entrada `INITIAL`: volume `0,20` lote;
- entrada `REENTRY`: volume `0,10` lote;
- Alvo coletivo: resultado líquido da cesta M24 `>= +US$1.000`, somando `profit + swap + commission + fee` expostos pelo MT5.
- Atingido o alvo, todas e somente as posições com comentário M24 são fechadas a mercado.
- Posições M23 e posições diretas não participam da cesta M24.

## Persistência

- `.traderia/model24_runtime_state.json`: consumo da entrada inicial por fonte/direção.
- `.traderia/model24_basket_state.json`: estado financeiro compacto da cesta.
- `.traderia/model24_basket_audit.jsonl`: auditoria dos Full Exits coletivos.

## Segurança e validação

- Somente conta MT5 Demo passa pelo provider.
- A criação e os testes do modelo não enviam ordens.
- O candle dos indicadores deve coincidir com o candle do Trade Plan.
- A ausencia de plano-base H1 nao pode interromper o roteamento proprio M5.
- O avaliador aceita tanto campos OHLC tecnicos (`close/high/low/time`) quanto o
  contrato canonico `Candle` (`fechamento/maxima/minima/data`) usado no runtime.
- M24 é modelo ativo e selecionável, mas não é ativado automaticamente pela implantação.
- Testes dedicados cobrem cruzamentos iniciais em velas distintas, manutencao
  das condicoes, reentrada pendente com RSI presente, SL pela vela de
  referencia, remocao de TP no RSI extremo, trailing monotono, isolamento M23/M24,
  descarte bilateral da primeira reentrada apos RSI extremo, seleção das sete
  fontes, TP estrutural bilateral nas reentradas e comentario MT5.
