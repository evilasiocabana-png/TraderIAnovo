# Modelo 3 - Nested Structure Continuation

## Status

Ativo somente em conta Demo nos oito pares monitorados.

`USDCAD` e o unico par historicamente certificado. Os outros sete pares usam
o mesmo contrato por expansao operacional solicitada pelo usuario e permanecem
explicitamente marcados como nao certificados individualmente.

## Pesquisa

O candidato foi escolhido entre 6.000 configuracoes por par, comparando `M30`
e `H1`. A selecao usou tres janelas cronologicas:

- treino: 60%;
- validacao: 20%;
- holdout final intocado: 20%.

Custos considerados:

- base: 1,5 bps por operacao completa;
- estresse: 2,5 bps por operacao completa.

## Configuracao Congelada

- pares operacionais Demo: `AUDUSD`, `EURJPY`, `EURUSD`, `GBPUSD`, `NZDUSD`,
  `USDCAD`, `USDCHF` e `USDJPY`;
- par com certificacao historica individual: `USDCAD`;
- timeframe: `H1`;
- familia: `STRUCTURE_CONTINUATION`;
- EMA rapida/lenta: `21/55`;
- ADX minimo: `28`;
- eficiencia minima em 20 candles: `0,40`;
- alinhamento de inclinacao: obrigatorio;
- estrutura: `10` candles;
- buffer de retomada: `0,30 ATR`;
- dias: terca a quinta;
- stop inicial: `1,75 ATR`;
- alvo: `2,5R`;
- saida: SL/TP fixos do plano.

## Evidencia

| Janela | Trades | PF |
|---|---:|---:|
| Treino | 70 | 1,517 |
| Validacao | 27 | 1,130 |
| Validacao estressada | 27 | 1,042 |
| Holdout final | 19 | 1,351 |
| Holdout estressado | 19 | 1,232 |
| Amostra completa | 116 | 1,400 |

Taxa de acerto completa: `35,3%`. Drawdown historico do replay: `2,00%`.

Esses valores sao evidencia historica, nao garantia de resultado futuro.

## Fluxo Operacional

1. O coletor atualiza candles H1 fechados.
2. `LabOperationalModelService` calcula os indicadores com o mesmo construtor
   usado na pesquisa.
3. O sinal exige continuacao da estrutura e todos os filtros congelados.
4. O Trade Plan nasce no proximo preco vivo, dentro do limite de atraso.
5. O Robo Demo valida gates, duplicidade e ausencia de posicao M3 no par.
6. O provider envia entrada, SL inicial e TP fixo ao MT5 Demo.
7. Relatorio e historico registram `MODELO3` e a Alpha.

## Guardrails

- a conta real nao e autorizada;
- somente USDCAD pode exibir as metricas historicas certificadas;
- os demais pares devem exibir
  `USER_APPROVED_DEMO_EXPANSION_UNVALIDATED`;
- a expansao nao pode copiar metricas de USDCAD para outro par;
- Position Manager nao move SL nem fecha antecipadamente neste contrato;
- qualquer recalculo deve gerar novo artefato, nova auditoria e novo ponto de
  restauracao.

## Rollback

Restaurar:

- fonte anterior `m3_alpha_sugerida_2_plus_best_by_pair.json`;
- politica M3 anterior;
- manifesto operacional anterior.

Pontos locais anteriores as mudancas:

`.traderia/restore_points/20260729_195935`

`.traderia/restore_points/20260729_213433`
