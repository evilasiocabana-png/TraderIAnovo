# HYPOTHESIS_GENERATION

## Missao

MISSÃO 235 — HYPOTHESIS_GENERATION.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Gerar hipóteses quantitativas baseadas exclusivamente na análise exploratória do dataset PETR4 diário.

## Fonte

Documento base:

```text
DATASET_EXPLORATORY_ANALYSIS.md
```

## Hipóteses Quantitativas

### 1. Volume Momentum 5D

Hipótese: retornos positivos de 5 dias acompanhados por volume acima da média tendem a apresentar continuidade nos próximos 5 dias.

Fundamento estatístico: melhor triagem inicial, com retorno médio futuro de 0.776% e hit rate de 58.70%.

Possíveis features:

- retorno 5d;
- volume relativo 20d;
- volatilidade 20d;
- distância da MM50.

Riscos:

- concentração em anos de forte tendência;
- sensibilidade a janela de volume;
- entrada após movimento já esticado.

Como validar:

- walk-forward anual;
- comparação com buy-and-hold;
- custos e slippage;
- estabilidade por subperíodos.

### 2. Breakout 20D

Hipótese: fechamento próximo da máxima de 20 dias tende a indicar continuidade de curto prazo.

Fundamento estatístico: retorno médio futuro de 0.607% e hit rate de 59.72%.

Possíveis features:

- posição Donchian 20d;
- volume relativo;
- ATR;
- filtro de drawdown.

Riscos:

- falso rompimento;
- compra no topo local;
- concentração em ciclos de alta.

Como validar:

- holding de 5, 10 e 20 dias;
- filtro por volume;
- filtro por volatilidade extrema.

### 3. Reversão por RSI < 30

Hipótese: sobrevenda intensa em PETR4 diário tende a gerar recuperação nos próximos 5 dias.

Fundamento estatístico: retorno médio futuro de 0.375% e hit rate de 56.52%.

Possíveis features:

- RSI 14;
- ATR percentual;
- gap;
- volume de capitulação.

Riscos:

- catching falling knife;
- sequência de queda prolongada;
- drawdown alto.

Como validar:

- stop temporal;
- filtro de queda extrema;
- confirmação de candle positivo.

### 4. Bollinger Low Reversion

Hipótese: fechamento muito abaixo da banda inferior de Bollinger pode gerar reversão curta.

Fundamento estatístico: retorno médio futuro de 0.301% e hit rate de 55.37%.

Possíveis features:

- Bollinger z-score;
- RSI;
- volume relativo;
- gap.

Riscos:

- tendência de baixa persistente;
- baixa robustez fora de crises.

Como validar:

- separar anos de crise;
- limitar holding;
- comparar com RSI.

### 5. Low Vol Trend

Hipótese: tendência positiva em ambiente de volatilidade abaixo da mediana tende a continuar de forma mais estável.

Fundamento estatístico: 797 ocorrências, retorno médio futuro de 0.263% e hit rate de 55.96%.

Possíveis features:

- preço acima da MM50;
- volatilidade 20d abaixo da mediana;
- momentum 5d;
- volume.

Riscos:

- retorno médio pequeno;
- edge pode desaparecer com custos;
- excesso de trades.

Como validar:

- custos conservadores;
- filtro de seletividade;
- comparação com buy-and-hold.

### 6. Monday-Wednesday Bias

Hipótese: segunda, terça e quarta apresentaram retornos médios superiores a quinta e sexta.

Fundamento estatístico: médias positivas de 0.232% a 0.246% nos dias centrais/iniciais da semana.

Possíveis features:

- dia da semana;
- retorno anterior;
- gap;
- volume.

Riscos:

- sazonalidade espúria;
- baixa causalidade;
- instabilidade por calendário.

Como validar:

- teste por ano;
- teste sem anos extremos;
- comparação com entrada aleatória.

### 7. January/July/October Seasonality

Hipótese: janeiro, julho e outubro tiveram médias diárias superiores.

Fundamento estatístico: os três meses apresentaram maiores médias diárias.

Possíveis features:

- mês;
- tendência prévia;
- volatilidade;
- retorno acumulado do ano.

Riscos:

- amostra pequena por mês;
- efeito calendário instável;
- viés de mineração.

Como validar:

- validação por ano;
- teste de estabilidade;
- não usar isoladamente como Alpha.

### 8. Gap Reversion

Hipótese: gaps relevantes possuem componente de reversão no dia seguinte.

Fundamento estatístico: correlação de gap com retorno futuro de 1 dia foi -0.079.

Possíveis features:

- gap percentual;
- direção do candle;
- volume;
- ATR.

Riscos:

- correlação fraca;
- gap pode refletir notícia fundamental;
- alto risco de cauda.

Como validar:

- bins de gap;
- separar gaps positivos e negativos;
- controlar volatilidade.

### 9. Distance From MA200 Mean Reversion

Hipótese: distância elevada da MM200 tende a reduzir retorno futuro de 10 dias.

Fundamento estatístico: correlação com retorno futuro de 10 dias foi -0.177, a maior da triagem.

Possíveis features:

- distância da MM200;
- MACD percentual;
- RSI;
- volatilidade.

Riscos:

- pode bloquear tendências fortes;
- sinal lento;
- dependência de regime.

Como validar:

- bins de distância;
- teste long-only e flat;
- filtro de volume.

### 10. Volatility Expansion Follow-Through

Hipótese: aumento de ATR percentual pode anteceder retornos futuros de 10 dias.

Fundamento estatístico: correlação ATR14 percentual com retorno futuro de 10 dias foi 0.106.

Possíveis features:

- ATR14 percentual;
- volume relativo;
- momentum 5d;
- range do candle.

Riscos:

- volatilidade também aumenta risco;
- drawdown pode crescer;
- sinal pode capturar crise.

Como validar:

- retorno ajustado por drawdown;
- filtros de direção;
- comparação com volatilidade baixa.

## Ranking Inicial

| Ranking | Hipótese | Prioridade |
| --- | --- | --- |
| 1 | Volume Momentum 5D | Alta |
| 2 | Breakout 20D | Alta |
| 3 | Distance From MA200 Mean Reversion | Média |
| 4 | RSI < 30 Reversion | Média |
| 5 | Low Vol Trend | Média |
| 6 | Bollinger Low Reversion | Média |
| 7 | Volatility Expansion Follow-Through | Média |
| 8 | Gap Reversion | Baixa |
| 9 | Monday-Wednesday Bias | Baixa |
| 10 | Monthly Seasonality | Baixa |

## Declaração Final

As hipóteses candidatas mais fortes para Alpha101 são Volume Momentum 5D e Breakout 20D. Nenhuma hipótese autoriza operação real; todas exigem validação incremental, controle de overfitting e comparação com baseline.
