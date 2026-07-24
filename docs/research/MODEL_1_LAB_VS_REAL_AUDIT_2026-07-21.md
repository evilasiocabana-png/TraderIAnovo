# Auditoria M1: Research Lab versus resultado realizado

Data da auditoria: 2026-07-21

## Conclusao executiva

O resultado negativo do M1 nao demonstrava, sozinho, que a Alpha escolhida pelo
Lab havia falhado. A operacao real e o estudo historico nao estavam executando o
mesmo contrato.

Foram encontradas cinco divergencias materiais:

1. o Lab antigo contava candles direcionais consecutivos como novos trades;
2. o resultado era inferido pelo fechamento depois de uma janela fixa, em vez
   de verificar o primeiro toque real em SL ou TP;
3. politicas Beta recebiam multiplicadores teoricos sem serem simuladas;
4. os trades realizados do M1 estavam registrados em M1, enquanto a nova busca
   multi-timeframe escolheu H1;
5. a expectativa do Lab era bruta, mas o resultado realizado inclui comissao,
   swap e fee.

O M1 foi restaurado para materializar sem alteracao a entrada, direcao,
timeframe, stop inicial, alvo e RR produzidos pelo Research Lab. Somente o M4
transforma esse plano para criar seu espelho.

## Evidencia realizada do M1

Fonte: historico read-only do MT5 cruzado com
`.traderia/mt5_demo_execution.jsonl`.

| Metrica | Resultado |
|---|---:|
| Posicoes M1 auditadas | 257 |
| Fechadas | 252 |
| Abertas no instante da auditoria | 5 |
| Vitorias / perdas / zero bruto | 87 / 144 / 21 |
| Lucro bruto positivo acumulado | 962,59 |
| Prejuizo bruto acumulado | -1.120,22 |
| Resultado bruto | -157,63 |
| Profit factor bruto | 0,859 |
| Comissao + swap + fee | -268,01 |
| Resultado liquido | -425,64 |
| Profit factor liquido | 0,671 |
| Custo medio contabilizado por trade fechado | -1,064 |

Todos os 252 registros fechados estavam identificados como timeframe M1. Isso
nao coincide com os vencedores H1 encontrados pelo recálculo atual.

### Mudanca temporal do resultado

| Dia | Trades | Vitorias | Perdas | Bruto | Liquido |
|---|---:|---:|---:|---:|---:|
| 2026-07-14 | 10 | 8 | 2 | 53,73 | 42,21 |
| 2026-07-15 | 70 | 34 | 35 | 76,94 | 5,65 |
| 2026-07-16 | 50 | 14 | 36 | -134,37 | -188,98 |
| 2026-07-17 | 20 | 4 | 16 | -114,77 | -136,99 |
| 2026-07-19 | 9 | 5 | 4 | 21,57 | 12,12 |
| 2026-07-20 | 37 | 12 | 24 | -72,07 | -112,19 |
| 2026-07-21 | 56 | 10 | 27 | 11,34 | -47,46 |

O snapshot anterior permaneceu associado a uma janela que ainda continha o
trecho positivo. A deterioracao a partir de 16 de julho nao era refletida por
um novo estudo equivalente. Reutilizar uma confirmacao congelada como se fosse
probabilidade permanente produziu uma expectativa incorreta.

## Falhas da metodologia anterior

### Contagem sobreposta

Uma sequencia BUY, BUY, BUY podia ser contada como tres oportunidades. No
runtime, a entrada deve nascer somente na transicao WAIT para BUY ou SELL e uma
nova posicao nao pode nascer enquanto o trade teorico anterior estiver aberto.

### Resultado por horizonte fixo

O metodo antigo comparava o fechamento alguns candles depois. Isso podia chamar
de vitoria um trade cujo stop havia sido tocado antes, ou ignorar um TP atingido
antes do fim da janela.

### Beta nao executada

O Lab expandia cada Alpha em varias Betas e alterava o score por heuristica. A
politica de saida nao era reproduzida candle a candle; portanto o titulo de
"Beta vencedora" nao tinha evidencia correspondente.

### Vazamento de informacao atual

Alguns indicadores historicos reutilizavam leituras do candle atual. ADX,
Bollinger, volume e medias agora sao reconstruidos no ponto historico avaliado.

### Diferenca entre teoria e execucao

O replay antigo nao reproduzia spread, slippage, comissao e alteracoes
posteriores do Position Manager. O custo contabilizado no MT5 foi suficiente
para piorar o resultado de -157,63 bruto para -425,64 liquido.

## Metodologia corrigida

Identificador: `SCENARIO_TRADE_PLAN_REPLAY_V2`.

Para cada par, Alpha, timeframe, ATR e RR:

1. reconstroi os indicadores apenas com candles disponiveis naquele instante;
2. abre oportunidade somente na transicao WAIT para BUY/SELL;
3. usa o fechamento do candle de gatilho como entrada teorica;
4. calcula a distancia do stop pela mesma regra do Trade Plan;
5. calcula o alvo pelo RR realmente pesquisado;
6. percorre os OHLC futuros ate o primeiro toque de SL ou TP;
7. em candle ambiguo que toca ambos, registra o stop primeiro;
8. impede trades teoricos sobrepostos;
9. ignora operacao ainda sem desfecho no fim da amostra;
10. certifica a entrada sem atribuir uma Beta que nao foi executada.

## Base recalculada

O snapshot local contem 200.000 candles: 8 pares, 5 timeframes e 5.000 candles
por mercado.

| TF | Inicio mais antigo | Fim mais recente | Candles por par |
|---|---|---|---:|
| M1 | 2026-07-16 09:54 UTC | 2026-07-21 22:12 UTC | 5.000 |
| M5 | 2026-06-26 10:40 UTC | 2026-07-21 22:10 UTC | 5.000 |
| M15 | 2026-05-08 18:30 UTC | 2026-07-21 22:00 UTC | 5.000 |
| M30 | 2026-02-25 16:00 UTC | 2026-07-21 22:00 UTC | 5.000 |
| H1 | 2025-09-30 10:00 UTC | 2026-07-21 22:00 UTC | 5.000 |

Snapshot operacional: `2026-07-21T20:28:20.629352+00:00`.

## Vencedores encontrados

| Par | TF | Alpha | RR | ATR | N | Acerto | PF | Expectancy | DD | Status ICT |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| AUDUSD | H1 | ALPHA013 | 2,0 | 2,5 | 109 | 41,28% | 1,627 | 0,0014673 | 6,38% | D / HIPOTESE_PROMISSORA |
| EURJPY | H1 | ALPHA006 | 2,0 | 2,0 | 102 | 39,22% | 1,376 | 0,0004852 | 2,08% | E / REJEITADA |
| EURUSD | H1 | ALPHA013 | 2,0 | 2,5 | 108 | 40,74% | 1,412 | 0,0006677 | 3,41% | E / REJEITADA |
| GBPUSD | H1 | ALPHA013 | 2,0 | 2,5 | 118 | 41,53% | 1,503 | 0,0009152 | 3,77% | D / HIPOTESE_PROMISSORA |
| NZDUSD | H1 | ALPHA013 | 2,0 | 2,5 | 107 | 43,93% | 1,703 | 0,0016138 | 3,15% | C / PESQUISA_REPLAY |
| USDCAD | H1 | ALPHA003 | 1,5 | 1,5 | 104 | 57,69% | 2,052 | 0,0004490 | 0,50% | B / CERTIFICADA_B |
| USDCHF | H1 | ALPHA009 | 2,0 | 1,5 | 127 | 42,52% | 1,511 | 0,0004296 | 1,13% | D / HIPOTESE_PROMISSORA |
| USDJPY | H1 | ALPHA002 | 1,5 | 2,5 | 113 | 46,02% | 1,342 | 0,0006634 | 4,23% | D / HIPOTESE_PROMISSORA |

Somente USDCAD atingiu a faixa ICT B. Os demais cenarios podem ter PF bruto
acima de 1, mas nao atingiram nota ICT 70. No contrato operacional atual essa
nota e informativa: ela nao invalida o vencedor do Lab e nao bloqueia ordem M1.

## Como o ICT foi calculado

ICT significa `Indice de Certificacao TraderIA`; nao e a metodologia de trading
conhecida como Inner Circle Trader. O indice ja existia no projeto antes desta
auditoria e e calculado depois da simulacao historica:

```text
ICT = 25% score(acerto)
    + 25% score(profit factor)
    + 20% score(expectancy)
    + 15% score(drawdown)
    + 10% score(amostra)
    +  5% score(recovery factor)
```

Antes da nota, existem minimos de PF 1,30, expectancy positiva, pelo menos 100
trades e drawdown maximo de 25%. Os oito vencedores atuais passaram nesses
minimos. A classificacao posterior e A+ a partir de 90, A a partir de 80, B a
partir de 70, C a partir de 60, D a partir de 50 e E abaixo de 50.

No USDCAD, os scores internos foram 69,23 para acerto, 91,04 para PF, 56,22
para expectancy, 100 para drawdown, 50,80 para amostra e 0 para recovery. A
conta ponderada foi:

```text
69,23 x 0,25 + 91,04 x 0,25 + 56,22 x 0,20
+ 100 x 0,15 + 50,80 x 0,10 + 0 x 0,05 = 71,39
```

O componente recovery ficou zerado nos oito pares. O adaptador atual usa retorno
medio por trade dividido pelo drawdown total; essa escala merece calibracao
especifica antes de o ICT ganhar qualquer autoridade de bloqueio. Ate essa
decisao, o ICT permanece uma referencia complementar e o vencedor de cada par
continua definido pela evidencia historica do Lab.

## Prova reproduzivel no Replay

A aba Replay permite selecionar cada par e acionar `Gerar prova visual`. A
execucao usa o vencedor persistido, le os 5.000 candles exatos no SQLite local,
reconstroi todos os trades sem sobreposicao e compara candles, quantidade de
trades, taxa de acerto, Profit Factor, expectancy e drawdown com o snapshot.

Os oito vencedores por par foram reexecutados e retornaram
`CONFERE_COM_SNAPSHOT`. Cada prova registra dois hashes SHA-256, um para a base
OHLC e outro para o ledger de execucao, em:

```text
.traderia/research/replay_proofs/{PAR}_{TF}_{ALPHA}.json
```

No Lab, a visao principal mostra os oito vencedores, um por par, com nota e
status ICT transparentes. Manutencao e ranking completo ficam recolhidos em
`Atualizar ou auditar o Lab`; nenhuma evidencia e apagada.

## Contrato operacional final

```text
Research Lab
  decide Alpha + TF + direcao + stop inicial + RR + alvo
        |
        v
M1
  materializa o plano sem recalcular nem normalizar RR
        |
        +--> M4 transforma uma copia independente em plano espelhado RR1
        |
        v
Robô Demo
  executa somente plano certificado
        |
        v
Position Manager
  acompanha apenas depois da abertura
```

M1 e M4 possuem gates, identidade e ocupacao independentes. A existencia de um
nao e pre-condicao para enviar o outro.

## O que esta corrigido e o que ainda nao e promessa

Corrigido:

- M1 volta a usar integralmente o plano do Lab;
- M4 e o unico modelo que adapta o plano M1;
- 5.000 candles reais sao persistidos para todos os 40 mercados;
- replay usa SL/TP e evita look-ahead e sobreposicao;
- Lab nao escolhe Beta por multiplicador teorico;
- linha reprovada permanece explicavel, mas nao executavel;
- sinal stale e consumido uma vez, sem repetir rejeicao a cada ciclo;
- lote de 200.000 candles nao fica retido no cache nem publica 200.000 eventos.

Limites que impedem prometer que o futuro repetira o historico:

- as metricas ainda sao brutas e nao incluem todos os custos no replay;
- a selecao usa a amostra inteira e ainda precisa de validacao walk-forward ou
  out-of-sample especifica para este Lab Forex;
- o Position Manager pode alterar o desfecho posterior ao plano inicial;
- regime de mercado, spread e slippage mudam depois da amostra.

Portanto, `resultado esperado` significa aderencia estatistica ao mesmo contrato,
nao garantia de lucro. A correcao impede executar uma configuracao diferente da
que foi medida e torna qualquer nova divergencia rastreavel.
