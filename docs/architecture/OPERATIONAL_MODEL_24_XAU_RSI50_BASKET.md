# Modelo Operacional 24 — XAU/M5 RSI50 Basket

## Identidade

- ID: `MODELO_24_XAU_RSI50_BASKET`.
- Variantes: `MODELO_24_XAU_RSI50_BASKET_SOURCE_M<n>`.
- Fontes permitidas: M8, M10, M18, M19, M20, M21 e M22.
- Ativo/timeframe: `XAUUSD/M5`.
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
A saida individual continua sendo a saida nativa da fonte, incluindo Full Exit
RSI 70/30 e inversao SMA20/50.

## Reentrada pendente

A reentrada nao exige que preco ou RSI produzam um novo cruzamento. Ela usa o
estado confirmado no ultimo M5 fechado:

- BUY: fechamento acima da SMA20 e RSI14 acima de 50;
- SELL: fechamento abaixo da SMA20 e RSI14 abaixo de 50;
- BUY_STOP na maxima do ultimo M5 fechado;
- SELL_STOP na minima do ultimo M5 fechado;
- a pendente e atualizada a cada novo candle M5 enquanto as duas condicoes
  permanecerem validas;
- o SL fica no microfundo 1+1 anterior mais proximo no BUY ou no microtopo 1+1
  anterior mais proximo no SELL, limitado aos ultimos cinco M5 fechados;
- sem micro pivo recente e valido, a reentrada permanece bloqueada;
- a reentrada nao reaplica os filtros direcionais da fonte e nao possui TP
  individual;
- o roteamento M24 materializa seu proprio plano M5 mesmo quando o plano-base
  heuristico H1 estiver sem gatilho;
- a perda do RSI50 ou a inversao SMA20/50 preserva o Full Exit individual de
  seguranca.

## Ordem de precedência

1. entrada inicial a mercado depois dos dois cruzamentos mantidos;
2. reentrada pendente pelo estado atual SMA20/RSI50;
3. aguardar.

Depois do aceite da entrada inicial pelo provider Demo, as proximas entradas na
mesma direcao sao reentradas. A mudanca de direcao reinicia a classificacao.

## Bloqueio da primeira reentrada apos RSI extremo

Quando um Full Exit individual for executado porque o RSI14 saiu de acima de
70 para abaixo de 70 no BUY, ou de abaixo de 30 para acima de 30 no SELL:

1. a primeira oportunidade valida de reentrada na mesma direcao e ignorada;
2. repeticoes do mesmo sinal durante a mesma vela M5 continuam bloqueadas;
3. somente a segunda oportunidade valida, identificada por uma nova vela M5
   fechada, pode ser liberada;
4. a regra vale para a reentrada pendente;
5. Full Exit por inversao SMA20/50 ou perda do RSI50 de uma reentrada nao arma
   esse descarte.

A mudanca de direcao elimina a trava pertencente ao lado anterior.

## Cesta financeira

- TP nativo MT5: sempre `0.0` para M24.
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
  das condicoes, reentrada pendente com RSI presente, ausencia de micropivo,
  SL no micro pivo, trailing monotono, isolamento M23/M24,
  descarte bilateral da primeira reentrada apos RSI extremo, seleção das sete
  fontes, retirada de TP e comentário MT5.
