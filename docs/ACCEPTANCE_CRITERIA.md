# Acceptance Criteria

`M24_CONTRACT=M24_SETUP_V19_20260823; SHA256=d918353322bc17fd17e1c7d0ba47272cf19431ef2c60d9cd1686829f2802c05f`

`M25_CONTRACT=M25_XAU_SOURCES_V6_20260820; FINGERPRINT=d0d758099058ffde`

## Criterios Gerais

Toda mudanca deve:

- preservar abertura do app em `http://localhost:8532`;
- manter `.traderia/` fora do Git;
- ter validacao local minima;
- evitar ciclos automaticos bloqueantes;
- respeitar o limite read-only/demo do MT5;
- reler no provider a selecao persistida imediatamente antes de `order_send` e
  falhar fechado para qualquer modelo nao marcado;
- atualizar documentacao quando mudar fluxo operacional.

## MT5 Forex

Aceito quando:

- aba abre sem chamar leitura MT5 pesada por ciclo;
- mostra ultimo estado local ou snapshot disponivel;
- nao trava a UI quando MT5 esta lento;
- nao possui botao ou texto prometendo atualizacao automatica por ciclo;
- nao envia ordem real.

## Lab

Aceito quando:

- usa `.traderia/` local da TraderIA Novo;
- nao depende de `TraderIA_WDO`;
- `Atualizar calculos` roda localmente;
- se nao houver candles completos, preserva ultimo snapshot local valido;
- resultados pesados nao entram no Git.

## Relatorios

Aceito quando:

- carrega auditoria local ao abrir;
- guarda cache de sessao;
- atualiza por botao;
- mostra totais de registros, aceitos, auditados, conferencias e divergencias;
- nao reroda por fragmento/ciclo automatico.

## GitHub

Aceito quando:

- codigo e docs sao commitados;
- remoto `origin` aponta para `evilasiocabana-png/TraderIAnovo`;
- `.gitignore` protege runtime local;
- commits tem mensagens claras.

## Validacao Minima

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m py_compile dashboard_app.py application\dashboard_service.py
```

## Validacao Funcional Recomendada

```powershell
python - <<'PY'
from application.dashboard_service import DashboardService
s = DashboardService()
print(len(s.get_mt5_research_constants().rows))
report = s.get_mt5_trade_audit_report()
print(report.total_local_records, report.total_audited, report.total_matched)
PY
```

## Modelo 24 XAU RSI50 Basket

Aceito quando:

- opera uma unica rota autonoma `M24_PROPRIO` somente em XAUUSD/M5; IDs de
  fontes M8, M10 e M18-M22 sao reconhecidos apenas em historico legado;
- nunca reutiliza precos/SL do XAUUSD para gerar candidato em outro simbolo;
- entrada inicial exige novo cruzamento do preco na SMA20 e novo cruzamento do
  RSI14 em 50 na mesma direcao; podem ocorrer em candles M5 diferentes, mas
  ambos devem existir e permanecer validos;
- a distancia `abs(SMA20-SMA50)/ATR14` pode ser exibida para auditoria, mas
  nao pode bloquear nenhuma entrada M24;
- entrada inicial entra a mercado com SL referenciado na vela que cruzou a
  SMA20: minima dessa vela menos `0,01` no BUY e maxima mais `0,01` no SELL;
- o SL inicial so avanca depois de rompimento estrutural: BUY rompe o topo
  anterior e protege abaixo do microfundo criado; SELL faz o inverso; nunca
  pode afrouxar;
- entrada principal nao exige SMA20 acima/abaixo da SMA50 e nao executa Full
  Exit quando essas duas medias invertem; BUY e SELL sao simetricos;
- reentrada nao exige novo cruzamento nem faixa de RSI: exige retorno a SMA20 e
  retomada pelo rompimento da maxima/minima do ultimo M5;
- antes do rompimento usa ordem Stop atualizada a cada novo candle; se o preco
  vivo ja ultrapassou o gatilho, entra a mercado;
- plano-base H1 sem gatilho nao bloqueia a materializacao do plano proprio M5
  do M24;
- o avaliador M24 aceita diretamente os objetos `Candle` canonicos recebidos do
  cache operacional, sem conversao manual de campos;
- a entrada inicial M24 envia TP pela projecao Fibonacci de 100% da ultima
  perna estrutural completa anterior; BUY soma a perna ao preco de entrada e
  SELL subtrai, sem fallback fixo;
- ao atingir RSI70 no BUY inicial ou RSI30 no SELL inicial, o Position Manager
  remove o TP e preserva a posicao ate o Full Exit no retorno do RSI;
- a reentrada exige TP Fibonacci de 100% da ultima perna estrutural completa;
- a reentrada exige SL em micro pivo 1+1 confirmado nos ultimos cinco
  candles M5 fechados;
- o SL da reentrada so avanca para um novo micro pivo favoravel e nunca
  afrouxa;
- depois de Full Exit BUY no retorno do RSI abaixo de 70 ou SELL no retorno
  acima de 30, a primeira reentrada valida na mesma direcao pode ser liberada;
- `CONTINUATION` e armada pelo TP Fibonacci aceito da `INITIAL`, uma unica vez
  por lado, em ordem Stop um pip alem do alvo para a `INITIAL` concluir primeiro;
- `CONTINUATION` usa `0,10` lote, sem TP individual e SL no extremo do ultimo M5
  fechado; o SL acompanha esse extremo somente a favor a cada candle novo;
- BUY `CONTINUATION` faz Full Exit ao RSI14 atingir 70 e SELL ao atingir 30;
- `LATERALIZATION` nunca abre ou aumenta posicao: uma `REENTRY` aberta que nao
  executou o TP Fibonacci e retornou ao range reposiciona TP no fechamento do
  microtopo anterior no BUY ou microfundo anterior no SELL e SL em RR `3:1`;
- o reposicionamento de range altera SL/TP juntos, preserva SL mais protetivo e
  mantem o volume original `0,10`; `0,10` e apenas classificacao reservada;
- existe no maximo uma posicao M24 aberta por papel (`INITIAL`, `REENTRY` e
  `CONTINUATION`) e lados opostos nunca coexistem;
- o Full Exit RSI50 da entrada inicial fica bloqueado nas duas primeiras velas
  M5 fechadas posteriores a entrada e e liberado a partir da terceira;
  reentrada/continuacao, retorno RSI 70/30, SL individual e cesta preservam
  suas regras; inversao SMA20/50 nao encerra nenhuma posicao M24;
- cesta fecha somente posicoes M24 em +US$1.000 liquidos;
- comentarios, estado, auditoria e relatorio distinguem M24 de M23;
- a tabela `Em negociacao` mostra `Tipo de entrada` antes de `Alvo`, usando
  `PRINCIPAL`, `REENTRADA` ou `CONTINUAÇÃO` somente quando o contrato persistido
  comprovar;
- testes nao conectam nem enviam ordem ao MT5.

## Modelo 25 - cesta das fontes XAU

Aceito quando:

- opera exclusivamente `XAUUSD/M5`;
- avalia exatamente M8, M10, M18, M19, M20, M21 e M22;
- copia sem recalculo direcao, candle, ordem, entrada, SL e TP da fonte;
- mantem estado, duplicidade e papeis `INITIAL/REENTRY` independentes por fonte;
- admite no maximo uma posicao de cada papel por fonte e bloqueia lados opostos;
- usa `0,10` lote na inicial e `0,10` na reentrada;
- nao inventa TP: preserva a ausencia de alvo ou o alvo estrutural da fonte;
- usa somente o snapshot M5 compartilhado e nao chama Lab pesado no runtime;
- mostra a distância SMA20/SMA50 normalizada pelo ATR14 apenas para auditoria,
  sem bloquear entrada inicial ou reentrada;
- rejeita no Robo Demo e no provider qualquer simbolo diferente de XAUUSD;
- fecha somente a cesta M25 ao atingir `+US$1.000` liquidos;
- aparece no seletor, Entrada Teorica, Saida Teorica e Relatorio;
- nao entra em `Todos` nem se combina acidentalmente com M23/M24;
- preserva o historico V1 sem ler seu estado no roteamento V2;
- preserva bloqueio de conta real e testes nao enviam ordens ao MT5.
