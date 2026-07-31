# Modelo 4 - Liquidity Reclaim Experimental

## Status

Ativo somente em conta Demo nos oito pares monitorados.

Nenhum par possui certificacao final. `AUDUSD` e a origem da melhor evidencia
fora da amostra disponivel; os outros sete pares usam o mesmo contrato por
expansao operacional solicitada pelo usuario.

## Escolha

O candidato AUDUSD foi preferido porque apresentou a melhor combinacao
disponivel entre tamanho de amostra, holdout, custo estressado e consistencia:

| Janela | Trades | PF |
|---|---:|---:|
| Amostra completa | 100 | 1,468 |
| Validacao | 11 | 1,266 |
| Holdout | 14 | 2,121 |
| Holdout estressado | 14 | 2,017 |

Retorno liquido historico completo: `10,09%`.
Drawdown historico completo: `4,70%`.

O holdout pequeno impede chamar o candidato de certificado. Resultado
historico nao garante resultado futuro.

## Contrato Congelado

- timeframe de entrada: `M30`;
- familia: `LIQUIDITY_RECLAIM`;
- direcao: `BUY_ONLY`;
- EMA rapida/lenta: `34/144`;
- ADX minimo/maximo: `28/35`;
- eficiencia minima em 20 candles: `0,10`;
- lookback estrutural: `40`;
- wick minimo: `0,50`;
- RSI extremo: `40`;
- dias: exceto segunda-feira;
- stop inicial: `2,5 ATR`;
- alvo: `3R`;
- saida: SL/TP fixos;
- Position Manager: desligado para este contrato.

Embora o carregador preserve M30/H1/H4 para compatibilidade com o adaptador
M4, o overlay vencedor nao exige alinhamento H1/H4 nem forca relativa.

## Fluxo

1. O runtime carrega os candles fechados exigidos pelo adaptador M4.
2. O motor calcula Liquidity Reclaim no M30 com os parametros congelados.
3. Somente um sinal BUY fechado pode criar Trade Plan.
4. A entrada usa o proximo preco vivo dentro da janela temporal aceita.
5. O Robo Demo valida gates, duplicidade e posicao existente.
6. O provider envia entrada, SL inicial e TP fixo somente ao MT5 Demo.
7. Historico e Relatorio registram `MODELO4` e a Alpha usada.

## Evidencia e Expansao

- `AUDUSD`: `BEST_AVAILABLE_DEMO_CANDIDATE_UNCERTIFIED`;
- demais pares: `USER_APPROVED_DEMO_EXPANSION_UNVALIDATED`;
- metricas de AUDUSD nunca podem ser copiadas para os demais pares;
- conta real permanece bloqueada.

## Rollback

Fonte anterior:

`.traderia/research/modelo_4_pesquisa_contextual_mtf.json`

Ponto de restauracao:

`.traderia/restore_points/20260729_223138`
