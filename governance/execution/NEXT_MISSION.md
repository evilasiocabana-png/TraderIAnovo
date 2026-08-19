# Next Mission

`M24_CONTRACT=M24_SETUP_V3_20260819; SHA256=4caa2af5fb100fbf7631fbaf2655b0ab9006f4afbc55ebcf7543590d176eb60b`

Proxima missao recomendada, ainda nao autorizada automaticamente:

```text
MISSION_TIA-030_A_DEFINIR
```

Objetivo: auditar M24 e M25 em paper/demo com candles novos, sem promover
parametros, confirmando entradas, reentradas, SL favoravel e o isolamento das
cestas. O M25 deve ser observado nos 19 ativos sem ativacao automatica.

Pre-condicao de interface concluida em 2026-08-17: o seletor operacional voltou
a renderizar `Todos` e M24 com chaves distintas e o botao `Aplicar modelos`
persiste a escolha antes de atualizar os textos da tela.

Pre-condicao de runtime concluida em 2026-08-18: o ciclo de fundo restaura M25
pela lista canonica de modelos ativos, igual ao seletor visual. O filtro legado
limitado as fontes do M23 foi removido; a observacao deve confirmar a
reconciliacao viva das 201 velas M5 nos 19 ativos.

O relatorio operacional tambem passou a expor o papel da entrada M24
(`PRINCIPAL`, `REENTRADA` ou `CONTINUAÇÃO`) antes do alvo.

O contrato atual possui entrada inicial a mercado somente depois de novos
cruzamentos do preco/SMA20 e RSI14/50 na mesma direcao. Eles podem ocorrer em
M5 diferentes, mas ambos devem permanecer validos e a distancia atual deve ser
`>= 0,25 ATR`; nao exige micro-pivo inicial. O SL nasce no extremo do candle
do cruzamento do preco mais um pip e,
apos dois fechamentos favoraveis, acompanha a SMA20 somente a favor. A
reentrada e uma ordem Stop atualizada a cada M5, com SL e TP baseados no
micro-pivo 1+1 mais recente.

A observacao deve confirmar que nenhuma posicao M24 fecha por inversao
SMA20/SMA50 e que `INITIAL`, `REENTRY` e `CONTINUATION` preservam as saidas
RSI e de cesta. A primeira reentrada valida apos Full Exit RSI 70/30 nao e
mais descartada.

Tambem deve confirmar a nova `CONTINUATION`: somente depois do historico MT5
confirmar que a `REENTRY` zerou pelo TP estrutural, entra a mercado com `0,40`
lote se o preco continuar alem do alvo e o RSI permanecer extremo (`BUY > 70`,
`SELL < 30`), usa SL no pivo 1+1 anterior e faz Full Exit no retorno de 70/30.

Pendencia registrada em 2026-07-13:

- criar sentinela de velocidade do TraderIA Novo;
- medir aba Relatorios, Saida Teorica MT5, Position Manager e historico MT5;
- preservar leitura de mercado essencial do BETA002;
- impedir que snapshot pesado do Lab volte ao ciclo leve;
- manter tabelas grandes paginadas e rastrear qualquer regressao de lentidao.
- registrar obrigatoriamente todo travamento aparente, congelamento de UI,
  queda do Streamlit ou reinicio manual como incidente arquitetural.

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
