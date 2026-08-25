# Next Mission

`M24_CONTRACT=M24_SETUP_V19_20260823; SHA256=d918353322bc17fd17e1c7d0ba47272cf19431ef2c60d9cd1686829f2802c05f`

`M25_CONTRACT=M25_XAU_SOURCES_V6_20260820; FINGERPRINT=d0d758099058ffde`

`M26_CONTRACT=M26_SMART_MONEY_V3_20260825; FINGERPRINT=4df7d17616d6a82e`

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-030_A_DEFINIR
```

Objetivo: auditar M24 e M25 em paper/demo com candles novos, sem promover
parametros, confirmando entradas, reentradas, SL favoravel e o isolamento das
cestas. O M25 deve ser observado somente em XAUUSD/M5, acompanhando de forma
independente M8, M10 e M18-M22, sem ativacao automatica.

Pre-condicao de interface concluida em 2026-08-17: o seletor operacional voltou
a renderizar `Todos` e M24 com chaves distintas e o botao `Aplicar modelos`
persiste a escolha antes de atualizar os textos da tela.

Pre-condicao de runtime concluida em 2026-08-19: o ciclo de fundo restaura M25
como cesta exclusiva e expande somente as sete fontes XAU do contrato V2. A
observacao deve confirmar a reconciliacao viva das velas M5 de XAUUSD e a copia
exata de entrada, SL e TP de cada fonte.

O relatorio operacional tambem passou a expor o papel da entrada M24
(`PRINCIPAL`, `REENTRADA` ou `CONTINUAÇÃO`) antes do alvo.

O contrato atual possui entrada inicial a mercado somente depois de novos
cruzamentos do preco/SMA20 e RSI14/50 na mesma direcao. Eles podem ocorrer em
M5 diferentes, mas ambos devem permanecer validos e a distancia atual deve ser
somente informativa. O SL usa a vela que cruzou a SMA20: BUY nasce um pip
abaixo da minima e SELL um pip acima da maxima. O TP e a projecao Fibonacci de
100% da ultima perna estrutural completa anterior, sem fallback fixo; RSI70 BUY
ou RSI30 SELL remove o TP e o retorno confirma Full Exit. Depois, o SL avanca
somente apos rompimento estrutural e nunca recua. A
reentrada e uma ordem Stop atualizada a cada M5, com SL e TP baseados no
micro-pivo 1+1 mais recente.

A observacao deve confirmar que nenhuma posicao M24 fecha por inversao
SMA20/SMA50 e que `INITIAL`, `REENTRY` e `CONTINUATION` preservam as saidas
RSI e de cesta. A primeira reentrada valida apos Full Exit RSI 70/30 nao e
mais descartada.

Tambem deve confirmar a `CONTINUATION`: somente depois do historico MT5
confirmar que a `REENTRY` zerou pelo TP estrutural, entra a mercado com `0,10`
lote no cruzamento do RSI extremo (`BUY > 70`, `SELL < 30`), sem TP, com SL no
extremo do M5 anterior e trailing SMA20 somente a favor.

Observar ainda a `LATERALIZATION`: quando uma REENTRY aberta falhar o TP
Fibonacci e retornar ao range, SL/TP devem ser reposicionados juntos no mesmo
ticket, com alvo no fechamento do microextremo e RR `3:1`, sem nova ordem.

Pendencia registrada em 2026-07-13:

- criar sentinela de velocidade do TraderIA Novo;
- medir aba Relatorios, Saida Teorica MT5, Position Manager e historico MT5;
- preservar leitura de mercado essencial do BETA002;
- impedir que snapshot pesado do Lab volte ao ciclo leve;
- manter tabelas grandes paginadas e rastrear qualquer regressao de lentidao.
- registrar obrigatoriamente todo travamento aparente, congelamento de UI,
  queda do Streamlit ou reinicio manual como incidente arquitetural.

Pendencias de tooling confirmadas em 2026-08-19, fora do escopo M25:

- corrigir o BOM legado de `tests/test_demo_execution_service.py` para o
  compilador interno de `run_static_analysis.py`;
- instalar `pyflakes` se a verificacao opcional passar a ser obrigatoria;
- tratar em missao arquitetural separada a falha historica `UI desacoplada`
  reportada por `architecture_health.py`.

Qualquer proxima missao nao deve:

- executar em conta real;
- abrir nova ordem;
- fechar posicao;
- alterar TP;
- executar automaticamente por ciclo;
- recalcular Lab pesado;
- apagar `.traderia`;
- mascarar falhas do provider MT5.

Para executar, coloque o pacote da proxima missao em `codex/inbox/` e solicite:

```text
Inbox.
```
