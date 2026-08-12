# Modelo 3 - XAUUSD M5 RSI14/50 + SMA20

Data: 2026-08-11  
Status: contrato ativo para MT5 Demo  
ID: `MODELO_3_XAU_M5_RSI50_FLIP`

## Regra congelada

- ativo: `XAUUSD`;
- timeframe: `M5`;
- janela operacional: exatamente as ultimas 52 velas M5, incluindo a vela atual;
- indicadores: RSI de Wilder de 14 periodos e SMA aritmetica de 20 periodos,
  calculados no ultimo candle fechado;
- `RSI14 > 50` e `fechamento > SMA20`: abrir `BUY`;
- `RSI14 < 50` e `fechamento < SMA20`: abrir `SELL`;
- `RSI14 == 50`: nao abrir nem inverter;
- se RSI e fechamento/SMA20 divergirem, aguardar novo candle fechado;
- se uma `BUY` estiver aberta e o RSI fechar abaixo de 50, executar `FULL_EXIT`;
- se uma `SELL` estiver aberta e o RSI fechar acima de 50, executar `FULL_EXIT`;
- depois do fechamento integral, o proximo ciclo pode abrir a posicao oposta a mercado;
- SL inicial: `0,01` alem do ultimo pivo M5 confirmado com estrutura 2+2;
- sem Take Profit fixo.

## Identidades

- Alpha: `ALPHAXAU3_RSI14_50_FLIP`, versao `M3_ENTRY_V2`;
- Beta: `BETAXAU3_RSI50_POSITION_FLIP`, versao `M3_EXIT_V1`;
- modo Beta: `FULL_EXIT_AND_REVERSE_RSI50`;
- gestao: `M3_RSI50_POSITION_FLIP`;
- comentario MT5: `TraderIA M3`.

## Fluxo operacional

```text
snapshot compartilhado XAUUSD/M5
  -> ultimas 52 velas M5
  -> RSI14 e SMA20 no ultimo M5 fechado
  -> entrada somente quando RSI50 e fechamento/SMA20 concordam
  -> Trade Plan sem TP e com SL estrutural
  -> gates do Robo Demo
  -> Provider MT5 Demo
  -> Position Manager avalia RSI14/50
  -> Full Exit quando o lado muda
  -> proximo ciclo libera a entrada oposta
  -> Relatorio filtra pelo ID exato do novo M3
```

O fechamento sempre precede a nova entrada. Nao existe ordem atomica que feche
e reverta no mesmo envio, o que preserva duplicidade, auditoria e isolamento por
modelo.

## Compatibilidade historica

O ID anterior `MODELO_3_LAB_ALL_FOREX_WINNERS` permanece legivel nos relatorios,
mas esta aposentado para novas entradas. Posicoes historicas nunca recebem a
politica de saida do novo M3 apenas por compartilharem o numero 3.

## Guardrails

- conta real continua proibida;
- uma posicao M3 por `XAUUSD`;
- candle M5 precisa estar fechado;
- as 52 velas, RSI, SMA20 e pivo precisam ter dados suficientes;
- nenhuma pesquisa ou backtest roda no ciclo leve;
- reinicio do runtime requer verificacao de que o Robo Demo nao disparara ordem
  sem supervisao.
