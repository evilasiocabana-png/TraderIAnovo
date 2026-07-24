# Auditoria Do Contrato De Saida Do M6

Data: 2026-07-24

## Objetivo

Identificar por que o M6, concebido para reproduzir o `TREND_MOMENTUM`
original, passou a ter stop movel e restaurar o contrato correto sem alterar o
TraderIA original nem apagar o historico operacional.

## Fontes Verificadas

- commit `8e0355e`, de 2026-07-15, no historico do TraderIA original;
- configuracao atual do M6 em
  `application/model6_original_trend_momentum.py`;
- materializacao do plano em `application/dashboard_service.py`;
- reconstrucao de planos abertos a partir de
  `.traderia/mt5_demo_execution.jsonl`;
- auditoria do Position Manager em `.traderia/position_manager.jsonl`;
- posicoes abertas lidas diretamente do MT5 Demo.

O TraderIA original foi consultado apenas em modo leitura. Nenhum arquivo,
commit ou estado operacional foi enviado automaticamente dele para o
TraderIAnovo.

## Linha Do Tempo Comprovada

- 2026-07-22 23:43: criacao local do adaptador M6 original.
- 2026-07-23 00:11: configuracao M6 finalizada com o wrapper dinamico.
- 2026-07-23 00:07: primeiro registro M6 no Position Manager.
- 2026-07-23 04:43: primeiro movimento real de SL M6.
- 2026-07-23 21:58: ultimo movimento real de SL M6 observado antes da correcao.
- 2026-07-24 06:15: processo reiniciado e os sete M6 abertos passaram a
  registrar `RESEARCH_FIXED_SL_TP / FIXED_SL_TP`, sem `new_stop`.

A alteracao atravessou a meia-noite de 22 para 23 de julho. Portanto, o efeito
operacional comecou no dia 23, nao no dia 24.

## Causa Raiz

A configuracao de entrada foi recuperada corretamente:

- M1;
- SMA 20/50;
- momentum 10;
- volatilidade 20;
- RSI14, faixa 30/70;
- minimo de volatilidade `0.00001`;
- decisao no ultimo candle fechado;
- entrada no preco vivo seguinte;
- stop inicial pela maior distancia entre 2 ATR e 0,10% do preco;
- TP RR2.

A contaminacao ocorreu na camada de adaptacao. Ao materializar a ALPHA001 como
M6, foram adicionados campos que nao pertenciam ao contrato de entrada:

- `BETA001_PROTECT_ONLY_V1`;
- `DYNAMIC_POSITION_MANAGER`;
- `atr_trailing_activation_rr=1.5`;
- `break_even_trigger_rr=1.5`.

O commit original possuia um Position Manager global no aplicativo, mas isso
nao transforma automaticamente a configuracao ALPHA001 em uma estrategia de
saida dinamica. A falha foi herdar a politica global sem uma decisao explicita
no contrato do M6.

## Impacto Encontrado

O historico preservado mostra M6 encerrados por TP, SL inicial e SL movido.
Nove encerramentos M6 foram associados a stop previamente movido. Esses dados
nao foram apagados nem reclassificados: continuam como evidencia do periodo
contaminado.

Nao foi identificado `FULL_EXIT` direto no grupo M6 auditado. A contaminacao
foi o movimento de SL por protecao, nao fechamento antecipado por ordem de
mercado.

## Contrato Corrigido

```text
ALPHA001 / MARCO_ZERO_A3BC912
  -> entrada Trend Momentum no M1
  -> SL inicial = max(2 ATR, 0,10% do preco)
  -> TP = 2R
  -> primeiro toque em SL ou TP encerra
  -> Position Manager nao move SL
  -> Position Manager nao fecha a posicao
```

Novos identificadores operacionais:

- Beta: `BETA001_FIXED_SL_TP_RR2_V1`;
- politica: `RESEARCH_FIXED_SL_TP`;
- modo: `FIXED_SL_TP`.

## Posicoes Abertas Durante A Correcao

Sete posicoes M6 estavam abertas. O sistema nao restaurou nem afastou stops que
ja haviam sido alterados. O SL e o TP existentes no MT5 foram preservados, e
somente novos comandos do Position Manager foram bloqueados.

## Regra De Nao Regressao

Uma configuracao historica de entrada nunca pode herdar automaticamente a
politica de saida global. O runtime identifica M6 por modelo, setup e origem;
mesmo um snapshot antigo marcado como dinamico e convertido em HOLD fixo antes
de qualquer chamada de `modify_position_sl` ou `close_position`.
