# FEATURE_DISCOVERY

## Missao

MISSÃO 236 — FEATURE_DISCOVERY.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Descobrir quais features possuem maior poder explicativo potencial para PETR4 diário, sem criar estratégia e sem alterar código produtivo.

## Features Avaliadas

| Feature | Leitura inicial |
| --- | --- |
| RSI 14 | Útil para reversão; correlação fraca isoladamente |
| ATR 14 percentual | Relevante para regime de volatilidade e retorno futuro 10d |
| ADX 14 | Baixo poder isolado nesta triagem |
| Momentum 3/5/10/20d | Momentum 5d apresentou sinal útil em combinação com volume |
| Médias móveis | Distância da MM200 foi a correlação mais relevante |
| Volume relativo | Melhor como filtro de intensidade do que direção isolada |
| Retornos passados | Retorno 5d teve melhor relação com retorno futuro 5d |
| Bollinger z20 | Útil para reversão, mas moderado |
| Donchian 20 | Útil para breakout e continuidade |
| ROC 10 | Equivalente ao retorno 10d; poder moderado |
| MACD percentual | Correlação negativa relevante com retorno futuro 10d |
| Volatilidade 20d | Importante para regime e risco |
| Gap | Pequena reversão de curto prazo |

## Relação com Retornos Futuros

Top correlações absolutas observadas:

| Feature | Alvo | Correlação |
| --- | --- | ---: |
| dist_ma_200 | future_ret_10d | -0.177 |
| macd_pct | future_ret_10d | -0.161 |
| dist_ma_50 | future_ret_10d | -0.116 |
| dist_ma_200 | future_ret_5d | -0.109 |
| atr14_pct | future_ret_10d | 0.106 |
| ret_5d | future_ret_5d | 0.092 |
| volume_ratio_50 | future_ret_10d | -0.087 |
| vol_20d | future_ret_10d | 0.086 |
| macd_pct | future_ret_5d | -0.086 |
| ret_20d | future_ret_10d | -0.084 |

## Descobertas

### 1. Distância de médias longas importa

Distância da MM200 e MACD percentual aparecem como variáveis mais relevantes para retorno futuro de 10 dias, com sinal negativo.

Interpretação:

```text
Quando PETR4 fica muito esticada acima de tendência longa, o retorno futuro tende a diminuir.
```

### 2. Momentum de curto prazo ainda possui valor

O retorno de 5 dias teve correlação positiva com retorno futuro de 5 dias. Isoladamente é fraco, mas combinado com volume foi a melhor hipótese triada.

### 3. Volume explica intensidade, não direção

Correlação retorno-volume foi -0.097, mas correlação retorno absoluto-volume foi 0.615.

Interpretação:

```text
Volume deve ser filtro de confirmação/intensidade, não gatilho direcional isolado.
```

### 4. Volatilidade precisa entrar como regime

ATR percentual e volatilidade 20d aparecem com relação positiva moderada com retorno futuro de 10 dias, mas volatilidade também aumenta risco.

### 5. Pullback genérico não foi confirmado

A hipótese simples de pullback em tendência MM50 com RSI 40-55 teve retorno médio futuro de 5 dias negativo.

## Features Candidatas para Alpha101

Conjunto recomendado:

- `ret_5d`;
- `volume_ratio_20`;
- `donchian_pos20`;
- `dist_ma_50`;
- `dist_ma_200`;
- `atr14_pct`;
- `vol_20d`;
- `gap`;
- `rsi14`.

## Features Descartadas como Gatilho Isolado

- dia da semana;
- mês;
- volume bruto;
- ADX isolado;
- RSI isolado;
- Bollinger isolado.

Essas features podem entrar como filtros ou diagnóstico, mas não como Alpha principal nesta etapa.

## Declaração Final

A descoberta de features favorece uma Alpha101 de continuidade com volume e breakout/momentum, protegida por filtros de esticamento e volatilidade. A hipótese de pullback contextual não deve ser a tese principal sem nova evidência.
