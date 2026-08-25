# Modelo Operacional 25 - Cesta das fontes XAU

## Contrato vigente

- ID canonico preservado: `MODELO_25_MULTI_ASSET_RSI50_BASKET`.
- Contrato: `M25_XAU_SOURCES_V6_20260820`.
- O M25 nao calcula filtro adicional de distancia: recebe o sinal executavel da fonte sem alterar entrada, SL ou TP.
- Alpha: `ALPHA025_XAU_SOURCE_AGGREGATOR`, versao `M25_ENTRY_V5`.
- Beta: `BETA025_BASKET_FULL_EXIT_1000`, versao `M25_EXIT_V2`.
- Universo: exclusivamente `XAUUSD`.
- Timeframe: exclusivamente `M5`.
- Fontes, nesta ordem: `M8`, `M10`, `M18`, `M19`, `M20`, `M21`, `M22`.
- Conta autorizada: somente Demo.

O M25 nao calcula um setup proprio. Ele avalia independentemente as sete fontes
autorizadas e copia somente planos executaveis. Para cada plano, preserva sem
recalculo a direcao, o candle do sinal, o tipo de ordem, a entrada, o SL e o TP
da fonte. A identidade da fonte acompanha a variante e o comentario MT5, por
exemplo `..._SOURCE_M8` e `TraderIA M25 S8`.

## Leitura informativa da distância das médias

O M25 calcula uma vez, para auditoria visual,
no ultimo M5 fechado da janela deslizante de 200 velas:

`distance_atr = abs(SMA20 - SMA50) / ATR14`

O valor aparece na coluna `Envio` e em `Distancia medias`, mas não funciona como
filtro. Qualquer distância válida, baixa ou alta, preserva a decisão do
plano-fonte e não bloqueia `INITIAL`, `REENTRY` ou renovação da pendência.

## Posicoes e lotes

- entrada inicial: `0,10` lote;
- reentrada: `0,10` lote;
- no maximo uma `INITIAL` e uma `REENTRY` por fonte;
- fontes distintas podem manter posicoes independentes do mesmo lado;
- lados opostos nunca coexistem dentro da cesta M25;
- qualquer tentativa de M25 fora de XAUUSD e rejeitada novamente no Robo Demo
  e no provider, mesmo se contornar o Dashboard.

M8 e M10 podem produzir planos sem TP. M18-M22 preservam o TP estrutural quando
a propria fonte o exigir. Nenhum alvo e inventado pelo agregador.

## Saida

Cada posicao conserva a saida tecnica de seu modelo-fonte. O Position Manager
resolve a fonte persistida no plano antes de avaliar RSI, SMA, SL ou TP. Como
protecao adicional, a cesta fecha somente posicoes M25 quando o resultado
liquido agregado atingir `+US$1.000`.

## Estado, historico e auditoria

- `.traderia/model25_basket_state.json`: estado financeiro da cesta V3;
- `.traderia/model25_basket_audit.jsonl`: auditoria dos Full Exits coletivos;
- `.traderia/model25_runtime_state.json`: artefato legado V1, preservado apenas
  como historico e nao lido pelo roteamento V3.

O contrato e a impressao digital ficam gravados nos parametros do plano e
visiveis na Entrada Teorica. Logs e avaliacoes antigos nao sao apagados; eles
continuam identificados pelas versoes V1. O ID canonico foi mantido para que
posicoes e auditorias anteriores nao se tornem orfas.

## Barreiras contra regressao

O M25 e selecionavel como cesta exclusiva. Ele nao pertence ao conjunto de
fontes diretas, nao entra em `Todos` e nao pode ser combinado por engano com
M23/M24. Testes verificam o universo XAUUSD, as sete fontes exatas, a copia
literal de entrada/SL/TP, o isolamento por fonte, a rejeicao de outro simbolo e
o Full Exit exclusivo.
