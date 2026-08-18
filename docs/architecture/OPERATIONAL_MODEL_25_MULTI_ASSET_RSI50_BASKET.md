# Modelo Operacional 25 - M24 Multiativo M5

## Identidade

- ID: `MODELO_25_MULTI_ASSET_RSI50_BASKET`.
- Alpha: `ALPHA025_MULTI_ASSET_RSI50`.
- Beta: `BETA025_BASKET_FULL_EXIT_1000`.
- Timeframe: M5.
- Comentario MT5: `TraderIA M25` com o papel `INITIAL` ou `REENTRY`.
- Conta autorizada: somente Demo.

O M25 e um modelo independente que aplica a mesma logica operacional do M24
aos 19 ativos canonicos. Ele nao altera o M24 e nao compartilha estado,
duplicidade, posicoes ou resultado financeiro com outros modelos.

## Universo

Forex principal:

`AUDUSD`, `EURJPY`, `EURUSD`, `GBPUSD`, `NZDUSD`, `USDCAD`, `USDCHF`, `USDJPY`.

Forex expandido:

`AUDCAD`, `AUDJPY`, `CADCHF`, `EURNZD`, `GBPAUD`, `GBPCAD`, `GBPNZD`, `NZDCAD`,
`NZDJPY`.

Alternativos:

`XAUUSD`, `BTCUSD`.

## Entrada E Reentrada

Cada ativo possui estado proprio. A entrada inicial usa os cruzamentos mantidos
de preco/SMA20 e RSI14/50, filtro absoluto de distancia
`abs(SMA20 - SMA50) / ATR14 >= 0,25`, volume `0,20` e nao envia TP individual.

Depois da entrada inicial aceita, a reentrada usa a correcao e retomada no M5,
volume `0,10`, ordem Stop no extremo da ultima vela fechada, SL no extremo
oposto da mesma vela com um pip de folga e TP no fechamento do candle que
formou o topo/fundo estrutural anterior. O tamanho de pip e resolvido por ativo:
`0,0001` no Forex comum e `0,01` em pares JPY, XAUUSD e BTCUSD.

Existe no maximo uma posicao `INITIAL` e uma `REENTRY` por ativo M25. Posicoes
opostas do mesmo ativo nao podem coexistir. Outro ativo continua livre para
entrar no mesmo ciclo ou em ciclos posteriores.

## Saida

O Position Manager preserva a gestao RSI da copia M24 por ativo:

- no RSI extremo, remove o TP da reentrada;
- no retorno confirmado do RSI, executa o Full Exit tecnico correspondente;
- o SL so pode ser movido a favor;
- a relacao SMA20/SMA50 nao executa Full Exit.

A cesta M25 tambem possui Full Exit financeiro exclusivo em resultado liquido
`>= +US$1.000`, somando os componentes fornecidos pelo MT5. Somente posicoes
com comentario M25 participam desse fechamento.

## Dados E Performance

O ciclo usa o snapshot M5 compartilhado do runtime. Candles e indicadores nao
sao baixados novamente por modelo. O M25 calcula apenas sobre o cache atual e
nao executa Lab, backtest ou pesquisa pesada no ciclo de 10 segundos.

O cache persistido pode aquecer a tela, mas nenhuma ordem e autorizada ate a
janela M5 ser reconciliada com dados vivos do MT5 depois do reinicio.

## Persistencia E Auditoria

- `.traderia/model25_runtime_state.json`: estado de entrada/reentrada por ativo.
- `.traderia/model25_basket_state.json`: estado financeiro compacto da cesta.
- `.traderia/model25_basket_audit.jsonl`: resultados do Full Exit coletivo.

As gravacoes JSON sao atomicas e repetem bloqueios curtos do Windows/OneDrive.
Arquivos `.traderia` permanecem fora do Git.

## Integracao Obrigatoria

O M25 deve permanecer registrado na politica de modelos, DashboardService,
Robo Demo, provider, Position Manager, MT5 Forex, Saida Teorica, Relatorio e
testes. O modelo deve continuar selecionavel sem ativacao automatica e sem
autorizar conta real.
