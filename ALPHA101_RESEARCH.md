# ALPHA101_RESEARCH

## Missao

MISSÃO 238 — ALPHA101_RESEARCH.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Selecionar uma hipótese quantitativa candidata à Alpha101 com base nas missões 234 a 237.

## Hipótese Selecionada

```text
ALPHA101_DAILY_VOLUME_MOMENTUM_BREAKOUT
```

PETR4 diário tende a apresentar continuidade de curto prazo quando há momentum positivo de 5 dias acompanhado por volume acima da média e proximidade de rompimento de máxima de 20 dias, desde que o ativo não esteja excessivamente esticado em relação à tendência longa.

## Mercado

| Campo | Valor |
| --- | --- |
| Ativo | PETR4 |
| Exchange | B3 |
| Timeframe | 1d |
| Dataset | `historical_data/datasets/B3/PETR4/1d/data.csv` |
| Período analisado | 2016-06-28 a 2026-06-26 |
| Candles | 2491 |
| Operação real | Proibida |

## Racional

A análise exploratória indicou que:

- `volume_momentum_5d` apresentou retorno médio futuro de 5 dias de 0.776%;
- `volume_momentum_5d` teve hit rate de 58.70%;
- `breakout_20d` apresentou retorno médio futuro de 5 dias de 0.607%;
- `breakout_20d` teve hit rate de 59.72%;
- volume explica intensidade do movimento, com correlação de 0.615 entre volume e retorno absoluto;
- distância excessiva da MM200 reduz retorno futuro de 10 dias, indicando necessidade de filtro de esticamento.

## Timeframe

```text
1d
```

## Holding

Holding exploratório:

```text
5 pregões
```

O holding de 5 dias foi escolhido porque a triagem usou retorno futuro de 5 dias e porque PETR4 diário apresentou pequena persistência nessa janela.

## Entrada

Entrada candidata long-only:

- retorno de 5 dias positivo;
- volume atual acima da média de 20 dias;
- fechamento próximo da máxima de 20 dias;
- volatilidade dentro de faixa aceitável;
- distância da MM200 abaixo de limite de esticamento.

Versão inicial:

```text
BUY se ret_5d > 0
e volume_ratio_20 > 1.2
e donchian_pos20 > 0.80
e atr14_pct <= limite de risco
e dist_ma_200 <= limite de esticamento
```

## Saída

Saída candidata:

- após 5 candles;
- ou perda de momentum;
- ou queda abaixo de referência de risco;
- ou sinal explícito de WAIT em ambiente de risco.

Nesta fase, a saída operacional permanece apenas objeto de pesquisa. Nenhuma ordem real é autorizada.

## Gestão

Gestão inicial:

- não operar vendido nesta versão;
- não piramidar posição;
- limitar uma posição paper por vez;
- registrar todos os sinais como `StrategySignal`;
- avaliar drawdown e número de trades antes de qualquer certificação.

## Features

Features principais:

- `ret_5d`;
- `volume_ratio_20`;
- `donchian_pos20`;
- `atr14_pct`;
- `dist_ma_200`.

Features secundárias:

- `rsi14`;
- `gap`;
- `vol_20d`.

## Limitações

- A hipótese foi descoberta no próprio dataset PETR4.
- Existe risco de overfitting.
- A triagem não inclui custos, slippage ou impostos.
- A hipótese é long-only e pode depender de ciclos de alta.
- PETR4 possui risco específico e drawdowns grandes.
- Dados diários não capturam microestrutura.

## Critérios de Aceitação

Para avançar:

- gerar sinais suficientes para análise;
- preservar retorno médio positivo em validação exploratória;
- não depender de um único ano;
- não depender de poucos outliers;
- manter drawdown controlado em simulação;
- superar baseline simples ou justificar valor como filtro de pesquisa;
- funcionar em Replay sem executar ordens reais.

## Critérios de Rejeição

Rejeitar se:

- resultado desaparecer fora dos melhores anos;
- Profit Factor ficar abaixo de 1.0;
- drawdown for incompatível com swing diário;
- a Alpha não gerar amostra suficiente;
- a performance depender de poucos eventos extremos;
- a implementação exigir quebrar contratos existentes.

## Decisão de Pesquisa

Status:

```text
READY_FOR_FACTORY_APPROVAL
```

## Declaração Final

A Alpha101 candidata deixa de ser uma hipótese de pullback e passa a ser uma hipótese de continuidade diária por volume, momentum e breakout em PETR4. A mudança é orientada pelos dados da Sprint 17, não por preferência por indicadores.
