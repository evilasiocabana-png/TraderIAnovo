## 2026-09-11 - M28 original com sincronizacao de candles

Usuario determinou preservar o setup original minerado e retirar o filtro contextual das 66 operacoes. Overlay realizado desativado para todos os registros, sem reaprender, alterar contratos minerados ou substituir por whitelist. Sincronizacao de dados mantida por solicitacao: leitura MT5 confirmada em ate 60s, sem cache somente restaurado, registro aquecido com horario/OHLC iguais a ultima M5 fechada. Rechecagem antes do executor impede plano envelhecido ou contexto/ocorrencia substituidos. Fontes M23 e suas regras permanecem preservadas. Ver docs/research/M28_ORIGINAL_CONTEXT_SYNC_2026-09-11.md.

## 2026-09-11 - Bloco separado de filtros adicionais M23

Usuario autorizou bloquear novas entradas nos tres contextos exatos de compra M23 originada no M7 no ouro. Catalogo independente em config/m23_additional_filters.json, modo BLOCK explicito, sem reaprender ou sobrescrever o filtro contextual original. Correspondencia exige contexto VALID e todos os sete campos iguais. Bloco de consulta apos Replay dos Sinais M23. Evidencias financeiras ficam apenas no runtime local, fora do Git. Ver docs/research/M23_ADDITIONAL_FILTERS_2026-09-11.md.

## 2026-09-11 - Sincronizacao do contexto M23

Correcao autorizada: contexto independente de contratos M28, candle fechado alinhado ao sinal, 200 fechadas deterministicas e leitura MT5 recente. Contexto ausente/invalido aguarda dados; NO_EVIDENCE com contexto valido preserva entrada. Regras congeladas e posicoes abertas preservadas. Identificadores de regra/contexto e fotografia auditavel separados. Ver docs/research/M23_CONTEXT_SYNC_2026-09-11.md. Replay financeiro integral nao certificado.

# Program Status

`M24_CONTRACT=M24_SETUP_V19_20260823; SHA256=d918353322bc17fd17e1c7d0ba47272cf19431ef2c60d9cd1686829f2802c05f`

`M25_CONTRACT=M25_XAU_SOURCES_V6_20260820; FINGERPRINT=d0d758099058ffde`

`M26_CONTRACT=M26_SMART_MONEY_V3_20260825; FINGERPRINT=4df7d17616d6a82e`

| Programa | Status |
| --- | --- |
| A01 Foundation | active |
| A02 Forex MT5 | planned |
| B01 Lab | planned |
| C01 Reports | planned |
| TIA Dynamic Exit Runtime Full Execution | accepted |
| M7 Trend Momentum Dynamic Protect Only | completed |
| M24 XAU RSI50 Basket | V19 canonical contract; INITIAL/REENTRY com TP Fibonacci; INITIAL, REENTRY e CONTINUATION em 0,10 lote; CONTINUATION Stop no TP da INITIAL sem TP e trailing por candle; lateralizacao da REENTRY aberta reposiciona SL/TP em RR 3:1 sem nova ordem; awaiting demo observation |
| M25 XAU Source Basket | contract V2 restricted to XAUUSD/M5; independently copies M8, M10 and M18-M22 entry/SL/TP; automated validation complete; awaiting demo observation |
| M26 XAU M1 Smart Money | independent deterministic structure/sweep/BOS/FVG/OB/retest contract; Demo-only automated validation in progress |
