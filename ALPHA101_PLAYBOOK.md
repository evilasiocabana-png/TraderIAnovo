# ALPHA101_PLAYBOOK

## Missao

MISSÃO 240 — ALPHA101_PLAYBOOK.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Transformar a hipótese aprovada `ALPHA101_DAILY_VOLUME_MOMENTUM_BREAKOUT` em playbook de pesquisa, pronto para implementação controlada.

## Status

```text
APPROVED_WITH_RESTRICTIONS
```

## Contexto

Alpha101 é uma Alpha diária para PETR4, orientada a continuidade de curto prazo.

Ela não é intraday, não é WDO, não é Alpha001 e não usa opening range.

## Setup

Setup candidato:

```text
PETR4 em momentum positivo de 5 dias,
com volume acima da média de 20 dias,
fechando próximo da máxima de 20 dias,
sem esticamento excessivo versus MM200,
e sem volatilidade extrema.
```

## Entrada

Condição long-only:

- `ret_5d > 0`;
- `volume_ratio_20 >= 1.2`;
- `donchian_pos20 >= 0.80`;
- `atr14_pct <= 0.08`;
- `dist_ma_200 <= 0.50`;
- dados suficientes para calcular as janelas.

Decisão:

```text
BUY
```

Caso contrário:

```text
WAIT
```

## Saída

Saída conceitual para validação:

- holding temporal de 5 pregões;
- ou perda de momentum;
- ou filtro de risco acionado;
- ou fechamento paper por mecanismo de replay existente.

Na implementação inicial, a Strategy apenas gera `StrategySignal`. Saídas financeiras e paper trading permanecem responsabilidade das camadas existentes.

## Gestão

Regras:

- long-only;
- uma posição paper por vez quando usada no Replay;
- sem venda descoberta;
- sem pirâmide;
- sem execução real;
- sem chamada a Broker;
- sem chamada direta ao RiskEngine.

## Replay

No Replay:

- a Alpha deve receber candles processados;
- calcular features somente com histórico disponível até o candle atual;
- retornar `WAIT` se houver dados insuficientes;
- retornar `BUY` apenas quando todas as condições estiverem satisfeitas;
- expor motivos claros no `StrategySignal`.

## Research

No Research:

- avaliar sinais gerados;
- contar BUY/WAIT;
- comparar com baseline;
- medir performance exploratória;
- documentar amostra e limitações.

## Validation

Métricas obrigatórias:

- total de sinais;
- total de BUY;
- total de WAIT;
- retorno acumulado;
- win rate;
- profit factor;
- expectancy;
- drawdown;
- Sharpe;
- estabilidade por ano.

## Critérios de Invalidação

Invalidar ou bloquear certificação se:

- não gerar amostra suficiente;
- Profit Factor < 1.0;
- retorno depender de poucos outliers;
- drawdown for excessivo;
- performance concentrar em poucos anos;
- qualquer contrato arquitetural for violado.

## Limites

- pesquisa apenas;
- simulação apenas;
- sem recomendação financeira;
- sem operação real;
- sem corretora;
- sem IA executora.

## Declaração Final

Alpha101 está especificada como uma Alpha de pesquisa long-only para PETR4 diário, baseada em momentum, volume e breakout, com filtros de volatilidade e esticamento. Ela pode ser implementada apenas como `StrategySignal`, sem execução operacional.
