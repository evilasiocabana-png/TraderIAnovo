# FEATURE_IMPORTANCE

## Missao

MISSÃO 237 — FEATURE_IMPORTANCE.md

Sprint 17 — Alpha Discovery Lab

## Objetivo

Rankear as features candidatas para PETR4 diário considerando importância exploratória, correlação, redundância, estabilidade e risco de overfitting.

## Critérios de Ranking

As features foram avaliadas por:

- magnitude da correlação com retornos futuros;
- coerência econômica/quantitativa;
- utilidade como gatilho ou filtro;
- redundância com outras features;
- risco de mineração estatística;
- compatibilidade com Replay e Research Lab.

## Ranking Final

| Ranking | Feature | Papel | Justificativa |
| --- | --- | --- | --- |
| 1 | `ret_5d` | Gatilho | Melhor sinal de continuidade curta quando combinado com volume |
| 2 | `volume_ratio_20` | Filtro | Volume acompanha intensidade e melhora hipótese de momentum |
| 3 | `donchian_pos20` | Gatilho/filtro | Breakout 20d teve bom hit rate e retorno médio futuro |
| 4 | `dist_ma_200` | Filtro de esticamento | Maior correlação absoluta com retorno futuro 10d |
| 5 | `macd_pct` | Filtro de esticamento | Redundante com distância de médias, mas útil para tendência |
| 6 | `atr14_pct` | Filtro de regime | Volatilidade explica risco e retorno futuro 10d |
| 7 | `vol_20d` | Filtro de regime | Ajuda a separar ambientes |
| 8 | `rsi14` | Filtro secundário | Útil para evitar sobrecompra/sobrevenda extrema |
| 9 | `gap` | Filtro de entrada | Pequeno efeito de reversão no dia seguinte |
| 10 | `bollinger_z20` | Filtro de reversão | Útil, mas menos alinhado com a hipótese principal |

## Redundância

| Grupo | Features | Observação |
| --- | --- | --- |
| Momentum | `ret_3d`, `ret_5d`, `roc10` | Usar poucas janelas para evitar redundância |
| Tendência longa | `dist_ma_50`, `dist_ma_200`, `macd_pct` | `dist_ma_200` e `macd_pct` são correlacionadas conceitualmente |
| Volatilidade | `atr14_pct`, `vol_20d`, `range_pct` | Preferir ATR/vol20 como filtros, não gatilhos |
| Reversão | `rsi14`, `bollinger_z20`, `gap` | Úteis para bloquear entradas ruins |

## Ranking por Uso na Alpha101

### Núcleo

- `ret_5d`;
- `volume_ratio_20`;
- `donchian_pos20`.

### Filtros de Risco

- `atr14_pct`;
- `vol_20d`;
- `dist_ma_200`.

### Filtros Secundários

- `rsi14`;
- `gap`.

## Risco de Overfitting

Riscos identificados:

- muitas features para apenas um ativo;
- escolha de parâmetros após olhar o resultado;
- sazonalidade com baixa amostra;
- resultado concentrado em poucos anos fortes;
- ausência de custos na triagem.

Mitigação:

- começar com regra simples;
- usar poucos parâmetros;
- validar por ano;
- comparar com buy-and-hold;
- documentar qualquer mudança de hipótese como nova missão.

## Feature Set Recomendado para Alpha101

Feature set mínimo:

```text
ret_5d
volume_ratio_20
donchian_pos20
atr14_pct
dist_ma_200
```

Uso pretendido:

- `ret_5d`: momentum curto;
- `volume_ratio_20`: confirmação de participação;
- `donchian_pos20`: proximidade de rompimento;
- `atr14_pct`: regime de risco;
- `dist_ma_200`: evitar esticamento excessivo.

## Declaração Final

O ranking favorece uma Alpha101 simples, de continuidade diária em PETR4, baseada em momentum de 5 dias com confirmação de volume e proximidade de rompimento, filtrada por volatilidade e esticamento de tendência longa.
