# Modelo Operacional 26 - Smart Money XAUUSD/M5

## Contrato vigente

- ID: `MODELO_26_XAU_M5_SMART_MONEY`.
- Contrato: `M26_SMART_MONEY_V1_20260825`.
- Fingerprint: `1a5af96d8383950d`.
- Alpha: `ALPHA026_SMART_MONEY_CONFLUENCE`.
- Beta: `BETA026_STRUCTURAL_LIQUIDITY_EXIT`.
- Universo: exclusivamente `XAUUSD`.
- Timeframe: exclusivamente `M5`.
- Janela: 200 candles fechados mais o candle atual, que nao participa da decisao.
- Volume Demo: `0,10`.
- Conta autorizada: somente Demo.

O M26 e independente do M25. Ele nao copia fontes, nao altera contratos
anteriores e nao e selecionado automaticamente.

## Pipeline de entrada

Uma entrada so existe quando todos os gates abaixo forem confirmados em candles
M5 fechados:

1. estrutura 2+2: dois topos e dois fundos confirmados;
2. varredura de liquidez: rompe o ultimo extremo e fecha de volta;
3. BOS na direcao da estrutura;
4. deslocamento: corpo minimo de 0,60 ATR14 e 60% do range;
5. FVG de tres candles com tamanho minimo de 0,10 ATR14;
6. Order Block: ultima vela contraria entre as cinco anteriores ao impulso;
7. reteste confirmado da zona de interesse FVG/OB em ate 12 candles.

BUY exige estrutura de alta, varredura abaixo do fundo e BOS de alta. SELL e o
espelho exato. O motor usa a mesma decisao para a Entrada Teorica e para o
Trade Plan; a interface nao recalcula o setup.

## Risco e saida

- entrada a mercado no fechamento do candle que confirma o reteste;
- SL estrutural alem da varredura e do Order Block, com margem de `0,01`;
- TP estrutural com RR minimo de `2,0`;
- stop management `FIXED_STOP`;
- sem Position Manager dinamico, Full Exit ou cesta adicional nesta versao.

O plano e rejeitado se SL/TP estiverem do lado incorreto, o risco nao for
positivo ou o RR ficar abaixo de 2.

## Runtime e seguranca

- reutiliza o snapshot compartilhado XAUUSD/M5;
- nao faz leitura MT5 adicional para renderizar a tabela;
- nao executa Lab pesado ou backtest no ciclo leve;
- recalcula a decisao somente com a janela entregue pelo ciclo;
- o candle em formacao e ignorado;
- idempotencia do provider continua por modelo, simbolo e candle;
- comentario MT5: `M26`;
- conta Real continua bloqueada.

## Rastreabilidade visual

A Entrada Teorica mostra estrutura, varredura, BOS/deslocamento, FVG,
Order Block, reteste, zona POI, ATR14, entrada, SL, TP, RR, motivo e
versao/fingerprint. Posicoes abertas preservam a identidade M26 na Saida
Teorica e no historico.

## Rollback

O rollback consiste em retirar M26 das listas ativas/selecionaveis e remover a
rota de materializacao, preservando o arquivo do modelo e os registros
historicos. M25 e demais modelos nao precisam ser alterados.
