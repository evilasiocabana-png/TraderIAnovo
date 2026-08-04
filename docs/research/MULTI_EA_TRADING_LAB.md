# Multi EA Trading — sublaboratorio exploratorio

Data da implementacao: 2026-08-03.

## Objetivo

O sublaboratorio compara hipoteses de entrada com o extrato publico do sinal
`Multi EA Trading`. Ele nao tenta atribuir ao autor uma configuracao que nao foi
publicada. O resultado distingue tres tipos de informacao:

- `INFORMADO_PUBLICAMENTE`: numeros visiveis nos PDFs e na pagina MQL5;
- `OBSERVADO_NO_CSV`: medidas reproduziveis a partir das posicoes fechadas;
- `HIPOTESE_INFERIDA`: configuracoes testadas contra candles historicos.

O status permanente e `RESEARCH_ONLY`. Nenhum resultado deste sublaboratorio
pode alimentar o robo Demo, o manifesto operacional ou o plano de trade.

## Fontes da amostra

- extrato CSV com 322 posicoes fechadas e cinco lancamentos `Balance`;
- 5.000 candles por serie nos timeframes M1, M5, M15, M30 e H1;
- cache Forex operacional aberto exclusivamente em modo read-only;
- XAUUSD armazenado em uma base separada do cache operacional.

O CSV nao informa fuso horario. Toda associacao temporal e, portanto,
classificada como `FUSO_NAO_INFORMADO` e `AMOSTRA_EXPLORATORIA`.

## Persistencia isolada

Os artefatos ficam somente em:

```text
.traderia/research/multi_ea_trading/positions.csv
.traderia/research/multi_ea_trading/history.sqlite
.traderia/research/multi_ea_trading/fit_v1.json
```

O banco `.traderia/traderia_mt5_history.sqlite` permanece intocado. O alias
publico `GOLD` e normalizado para `XAUUSD` apenas dentro deste sublaboratorio.

## Metodo

Para cada entrada do extrato, o motor usa apenas o ultimo candle completamente
fechado antes do horario informado. Isso evita lookahead. As familias testadas
incluem tendencia por EMA, tendencia com momentum, reversao a media por
Z-Score/RSI, a hipotese estrita ALPHA017 e rompimento Donchian.

O ranking informa separadamente cobertura do gatilho, acerto direcional,
eventos `WAIT`, treino e holdout cronologico. A ordenacao dos parametros usa
somente o treino; o holdout nao participa da escolha. O score mede vantagem
direcional acima do baseline aleatorio de 50% e penaliza gatilhos esparsos.
Uma boa aproximacao estatistica nao prova que o EA original use aquela regra.
Saidas, stop, take profit,
trailing, logica de grade, tamanho de lote e coordenacao entre EAs nao podem ser
reconstruidos com exatidao a partir deste extrato.

Em uma instalacao sem o CSV persistido, a importacao pode ser feita por
`DashboardService.run_multi_ea_trading_lab(source_path=...)` ou pela variavel
`TRADERIA_MULTI_EA_POSITIONS_CSV`. O painel continua sem upload direto para
respeitar a fronteira arquitetural da aplicacao.

## Parametros publicos preservados

O relatorio compacto registra todas as estatisticas fornecidas, incluindo 346
operacoes publicas, 58,95% de acerto, fator de lucro 2,00, payoff esperado de
USD 1,20, alavancagem 1:500, drawdowns, crescimento, atividade, distribuicao
por ativo, saldo, equity, depositos e retiradas. Esses numeros sao exibidos
separadamente dos 322 trades fechados presentes no CSV para evitar misturar
fontes diferentes.

## Resultado da amostra de 2026-08-03

- XAUUSD: 25.000 candles baixados, sendo 5.000 em cada um de M1, M5, M15,
  M30 e H1; a checagem final conta timestamps unicos ja persistidos.
- Total analisavel: 40 series completas e 200.000 candles dos oito ativos do
  extrato que possuem historico local.
- Cobertura temporal: 212 de 322 posicoes, ou 65,84%.
- CSV: 195 trades positivos, 126 negativos e um neutro; resultado liquido
  reproduzido de USD 415,16 apos comissao e swap.
- Comportamento: maximo de 14 posicoes simultaneas, 184 posicoes com
  sobreposicao oposta no mesmo simbolo e 121 fechamentos em 50 clusters de ate
  120 segundos.

Nenhuma hipotese global foi identificada como o setup original. EMA 20/50 foi
selecionada no treino com score 0,1703, mas caiu para 0,0333 no holdout e foi
classificada como `INSTAVEL_NO_HOLDOUT`. A reversao a media global com Z-Score
20/1,5 e RSI14 30/70 ficou em segundo lugar no treino (0,1640) e permaneceu
apenas `HIPOTESE_FRACA`; isso nao autoriza uso operacional.

No ouro, a aproximacao parcial mais consistente foi M15 com reversao a media:
Z-Score de 20 periodos com limiar 1,5 e RSI 14 em 25/75 ou 30/70. Ela gerou 14
gatilhos corretos entre 33 entradas temporalmente elegiveis, sem lado oposto,
e score 0,3241 no holdout. A classificacao e `HOLDOUT_INCONCLUSIVO`, pois o
holdout contem somente quatro gatilhos, a regra cobre apenas parte das entradas,
o fuso do CSV nao foi informado e a mesma regra nao explica o portfolio inteiro.

A ALPHA017 estrita com Z-Score, RSI, ADX e largura Bollinger/ATR nao gerou
gatilhos nesta associacao temporal e foi classificada como
`NAO_SUPORTADA_PELA_AMOSTRA`. Portanto, ela nao deve ser apresentada como a
configuracao encontrada do sinal original.
