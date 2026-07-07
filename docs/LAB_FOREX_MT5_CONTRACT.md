# Contrato Lab -> Forex -> MT5

Este contrato define quem decide cada parte do fluxo operacional.

## Principio

O Lab decide parametros. O Forex/MT5 executa o ciclo leve com os parametros ja
definidos. O MT5 exibe e, quando autorizado, recebe a execucao demo conforme
politica operacional.

## Fontes de decisao

| Decisao | Fonte oficial |
|---|---|
| Ativo | Universo Forex configurado. |
| Timeframe decisor | Lab. |
| Setup/modelo | Lab. |
| Entrada teorica | Lab. |
| Zona de interesse | Lab/analise de mercado. |
| Stop/saida | Lab. |
| Tipo de stop movel | Lab. |
| Preco/candles atuais | MT5. |
| Posicao aberta | MT5. |
| Visual no grafico | JSON exportado + indicador MT5. |

## Entrada

Regra desejada:

```text
Pode entrar se:
  ativo esta em zona de interesse
  E Lab autoriza BUY/SELL
  E nao existe posicao aberta conflitante no papel
  E politica operacional permite execucao no horario atual
```

Nao deve entrar se:

- ja existe posicao aberta no mesmo papel e a regra nao permite reforco;
- o Lab esta em WAIT;
- o ativo esta fora da zona de interesse;
- falta leitura MT5 confiavel;
- o mercado esta fechado ou bloqueado por politica operacional;
- o parametro de timeframe/setup nao esta definido.

## Timeframe

O timeframe do Lab e a autoridade da decisao. O timeframe do grafico MT5 pode
ser diferente e serve apenas para visualizacao.

Exemplo:

```text
Lab decide EURJPY em H1.
Grafico aberto pode estar em M30.
O sinal deve preservar H1 como timeframe decisor.
```

## Saida

A saida deve vir do Lab assim como a entrada. O sistema nao deve forcar
`FIXED_STOP` para todos quando o Lab indicar stop movel melhor para ativo,
setup e timeframe.

Tipos conhecidos:

- `FIXED_STOP`
- `ATR_TRAILING_STOP`
- `BREAK_EVEN`
- `CHANDELIER_EXIT`
- `PARABOLIC_SAR`
- `DONCHIAN_CHANNEL_STOP`
- `MOVING_AVERAGE_EXIT`
- `TIME_STOP`
- `VOLATILITY_STOP`

## Posicoes abertas

Quando ha posicao aberta:

- O visual deve aparecer no ativo posicionado.
- O candle de entrada deve ser marcado quando o horario de abertura estiver
  disponivel.
- O stop/saida exibido deve acompanhar o contrato vindo do Lab.
- A aba relatorio deve atualizar por ciclo para acompanhar resultado em
  negociacao.

Quando nao ha posicao aberta:

- O grafico deve permanecer limpo por padrao.
- Sinais pendentes devem ser discretos e depender de regra explicita.

## Runner e Streamlit

O projeto possui dois acionadores relevantes:

| Acionador | Papel |
|---|---|
| `dashboard_app.py` | UI e atualizacao interativa do dashboard. |
| `scripts/mt5_forex_cycle_runner.py` | Ciclo leve externo para manter JSON visual atualizado. |

Antes de alterar ciclo, definir qual acionador sera autoridade para a tarefa
alterada.

## Criterios de aceite para mudancas nesse fluxo

- O app continua abrindo.
- O MT5 continua recebendo/leendo o JSON.
- O grafico nao fica poluido em ativos sem posicao.
- Ativos posicionados mostram entrada, stop, alvo/saida e candle de entrada.
- O relatorio atualiza a cada ciclo relevante.
- A saida respeita o stop management vindo do Lab.
- O Git nao recebe runtime, logs, bancos ou snapshots.
